from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from mlb_api import MLBClient
from decision_engine import MatchupAnalyzer


class WaiverAnalyzer:
    """
    Analiza jugadores disponibles en waivers (free agents de ESPN) y genera
    recomendaciones de pickup/drop comparando contra el propio roster.

    Escala de score: -10 (no vale la pena) a +10 (pickup excelente).
    Solo recomienda pickups con score >= MIN_PICKUP_SCORE.
    """

    MAX_RECOMMENDATIONS = 3
    MIN_PICKUP_SCORE = 5

    PITCHER_POSITIONS = {'SP', 'RP', 'P'}

    def __init__(self, league, my_team, mlb_client: MLBClient):
        self.league = league
        self.my_team = my_team
        self.mlb_client = mlb_client

    # ------------------------------------------------------------------ #
    #  Obtención de datos ESPN                                             #
    # ------------------------------------------------------------------ #

    def get_free_agents(self, size: int = 50) -> list:
        """Obtiene jugadores disponibles en waivers de ESPN."""
        try:
            free_agents = self.league.free_agents(size=size)
            print(f"DEBUG Waivers: {len(free_agents)} free agents encontrados")
            return free_agents
        except Exception as e:
            print(f"❌ Error obteniendo free agents: {e}")
            return []

    # ------------------------------------------------------------------ #
    #  Matchups próximos                                                   #
    # ------------------------------------------------------------------ #

    def get_upcoming_matchups(self, player, days: int = 3) -> List[Dict]:
        """
        Retorna los matchups de un jugador en los próximos N días.
        Para SPs también verifica si es el probable starter.
        """
        player_team_full = self.mlb_client.TEAM_MAPPING.get(player.proTeam)
        if not player_team_full:
            return []

        is_sp = player.position == 'SP'
        matchups = []
        today = datetime.now()

        for day_offset in range(days):
            date_str = (today + timedelta(days=day_offset)).strftime('%Y-%m-%d')
            games = self.mlb_client.get_games_for_date(date_str)

            for game in games:
                is_away = game['away_team'] == player_team_full
                is_home = game['home_team'] == player_team_full

                if not (is_away or is_home):
                    continue

                opponent = game['home_team'] if is_away else game['away_team']
                opposing_pitcher = game['home_pitcher'] if is_away else game['away_pitcher']

                # Para SPs: verificar si es el probable starter en este juego
                is_probable_starter = False
                if is_sp:
                    my_probable = game['away_pitcher'] if is_away else game['home_pitcher']
                    if my_probable and my_probable.get('name'):
                        player_last = player.name.split()[-1].lower()
                        probable_last = my_probable['name'].split()[-1].lower()
                        is_probable_starter = player_last == probable_last
                else:
                    # RPs pueden lanzar cualquier día que su equipo juegue
                    is_probable_starter = True

                matchups.append({
                    'date': date_str,
                    'opponent': opponent,
                    'is_home': is_home,
                    'opposing_pitcher': opposing_pitcher,
                    'is_probable_starter': is_probable_starter,
                })
                break  # Solo un juego por día para este equipo

        return matchups

    # ------------------------------------------------------------------ #
    #  Scoring de pickups                                                  #
    # ------------------------------------------------------------------ #

    def _score_batter_pickup(self, player, matchups: List[Dict]) -> Tuple[int, str]:
        """
        Calcula el score de pickup para un bateador.
        Usa stats recientes (7 días) para el texto de razón y stats de
        temporada para el scoring base.
        Returns: (score, reason)
        """
        score = 0
        reasons = []

        # Stats de temporada para scoring
        season_stats = self.mlb_client.get_batter_stats(player.name)
        # Stats recientes para el texto de razón
        recent_stats = self.mlb_client.get_batter_recent_stats(player.name, days=7)

        if season_stats:
            avg = MatchupAnalyzer.safe_float(season_stats.get('avg', 0.0))
            ops = MatchupAnalyzer.safe_float(season_stats.get('ops', 0.0))

            if avg >= 0.280:
                score += 2
            elif avg >= MatchupAnalyzer.GOOD_BATTER_AVG:
                score += 1
            elif avg <= MatchupAnalyzer.STRUGGLING_BATTER_AVG:
                score -= 2

            if ops >= 0.850:
                score += 3
            elif ops >= MatchupAnalyzer.GOOD_BATTER_OPS:
                score += 2
            elif ops <= MatchupAnalyzer.STRUGGLING_BATTER_OPS:
                score -= 2

        # Texto de razón: priorizar stats recientes si están disponibles
        if recent_stats:
            r_avg = MatchupAnalyzer.safe_float(recent_stats.get('avg', 0.0))
            if r_avg >= 0.300:
                reasons.append(f"Batea {r_avg:.3f} últimos 7 días")
            elif r_avg > 0:
                reasons.append(f"AVG {r_avg:.3f} (7 días)")
        elif season_stats:
            avg = MatchupAnalyzer.safe_float(season_stats.get('avg', 0.0))
            if avg > 0:
                reasons.append(f"AVG {avg:.3f} temporada")

        # Cantidad de juegos próximos
        games_count = len(matchups)
        if games_count >= 3:
            score += 2
            reasons.append(f"{games_count} juegos próximos {games_count} días")
        elif games_count >= 2:
            score += 1
        elif games_count == 0:
            score -= 3

        # Calidad de los pitchers contrarios
        weak_pitcher_names = []
        for m in matchups:
            pitcher = m.get('opposing_pitcher')
            if pitcher and pitcher.get('name'):
                p_stats = self.mlb_client.get_pitcher_stats(pitcher['name'])
                if p_stats:
                    era = MatchupAnalyzer.safe_float(p_stats.get('era', 4.5))
                    if era >= 4.50:
                        score += 1
                        weak_pitcher_names.append(pitcher['name'].split()[-1])
                    elif era <= MatchupAnalyzer.ELITE_PITCHER_ERA:
                        score -= 1

        if weak_pitcher_names:
            reasons.append(f"vs pitchers débiles ({', '.join(weak_pitcher_names[:2])})")

        # Ventaja de local
        home_games = sum(1 for m in matchups if m.get('is_home'))
        if home_games >= 2:
            score += 1

        reason_text = " | ".join(reasons) if reasons else "Sin datos suficientes"
        return score, reason_text

    def _score_pitcher_pickup(self, player, matchups: List[Dict]) -> Tuple[int, str]:
        """
        Calcula el score de pickup para un pitcher.
        Usa stats recientes (últimas 3 salidas ≈ 21 días) cuando están disponibles.
        Returns: (score, reason)
        """
        score = 0
        reasons = []
        is_sp = player.position == 'SP'

        # Preferir stats recientes; si no, usar los de temporada
        recent_stats = self.mlb_client.get_pitcher_recent_stats(player.name, days=21)
        season_stats = self.mlb_client.get_pitcher_stats(player.name)
        stats = recent_stats or season_stats
        stats_label = "últimas salidas" if recent_stats else "temporada"

        if stats:
            era = MatchupAnalyzer.safe_float(stats.get('era', 5.0))
            whip = MatchupAnalyzer.safe_float(stats.get('whip', 1.5))

            if era <= MatchupAnalyzer.ELITE_PITCHER_ERA:
                score += 4
                reasons.append(f"ERA {era:.2f} {stats_label}")
            elif era <= MatchupAnalyzer.GOOD_PITCHER_ERA:
                score += 2
                reasons.append(f"ERA {era:.2f} {stats_label}")
            elif era >= 5.0:
                score -= 3

            if whip <= MatchupAnalyzer.ELITE_PITCHER_WHIP:
                score += 2
            elif whip >= 1.40:
                score -= 1

        # Para SPs: verificar starts programados y calidad del oponente
        starts_found = 0
        for m in matchups:
            if not m.get('is_probable_starter'):
                continue

            starts_found += 1

            if is_sp:
                team_stats = self.mlb_client.get_team_batting_stats(m['opponent'])
                if team_stats:
                    team_ops = MatchupAnalyzer.safe_float(team_stats.get('ops', 0.700))
                    opp_short = m['opponent'].split()[-1]
                    if team_ops <= MatchupAnalyzer.WEAK_OFFENSE_OPS:
                        score += 2
                        reasons.append(f"Próximo vs {opp_short} (débil ofensiva)")
                    elif team_ops >= MatchupAnalyzer.STRONG_OFFENSE_OPS:
                        score -= 1

        if is_sp:
            if starts_found == 0:
                score -= 4
                reasons.append("Sin start programado esta semana")
            else:
                score += 1  # Bonus por tener start confirmado

        reason_text = " | ".join(reasons) if reasons else "Sin datos suficientes"
        return score, reason_text

    # ------------------------------------------------------------------ #
    #  Candidato a drop                                                    #
    # ------------------------------------------------------------------ #

    def _find_drop_candidate(self, is_pitcher: bool) -> Optional[object]:
        """
        Encuentra el jugador más débil del mismo tipo (pitcher/bateador)
        en el roster propio. Excluye jugadores en IL.
        """
        candidates = []
        for player in self.my_team.roster:
            if player.lineupSlot == 'IL':
                continue
            player_is_pitcher = player.position in self.PITCHER_POSITIONS
            if player_is_pitcher != is_pitcher:
                continue
            candidates.append(player)

        if not candidates:
            return None

        # Puntuar cada candidato (menor score = peor jugador = candidato a drop)
        scored = []
        for p in candidates:
            if is_pitcher:
                stats = self.mlb_client.get_pitcher_stats(p.name)
                drop_score = -MatchupAnalyzer.safe_float(stats.get('era', 5.0)) if stats else -10.0
            else:
                stats = self.mlb_client.get_batter_stats(p.name)
                drop_score = MatchupAnalyzer.safe_float(stats.get('ops', 0.0)) if stats else 0.0
            scored.append((p, drop_score))

        scored.sort(key=lambda x: x[1])
        return scored[0][0]

    # ------------------------------------------------------------------ #
    #  Método principal                                                    #
    # ------------------------------------------------------------------ #

    def analyze_waivers(self) -> List[Dict]:
        """
        Analiza free agents y retorna hasta MAX_RECOMMENDATIONS pickups
        con score >= MIN_PICKUP_SCORE.

        Cada recomendación tiene:
          player, position, score, reason, drop_candidate
        """
        print("\n🔍 Analizando Waiver Wire...")
        print("-" * 60)

        free_agents = self.get_free_agents(size=50)
        if not free_agents:
            print("⚠️  No se encontraron free agents")
            return []

        today = datetime.now().date()
        two_days_out = {today, today + timedelta(days=1)}
        scored_pickups = []

        for player in free_agents:
            is_pitcher = player.position in self.PITCHER_POSITIONS

            # Obtener matchups de los próximos 3 días
            matchups = self.get_upcoming_matchups(player, days=3)

            # Requisito: debe jugar al menos uno de los próximos 2 días
            near_term = [
                m for m in matchups
                if datetime.strptime(m['date'], '%Y-%m-%d').date() in two_days_out
            ]
            if not near_term:
                continue

            if is_pitcher:
                score, reason = self._score_pitcher_pickup(player, matchups)
            else:
                score, reason = self._score_batter_pickup(player, matchups)

            if score < self.MIN_PICKUP_SCORE:
                continue

            drop_candidate = self._find_drop_candidate(is_pitcher)
            scored_pickups.append({
                'player': player,
                'position': player.position,
                'score': score,
                'reason': reason,
                'drop_candidate': drop_candidate,
            })

        # Mejores primero
        scored_pickups.sort(key=lambda x: x['score'], reverse=True)
        recommendations = scored_pickups[:self.MAX_RECOMMENDATIONS]

        print(f"✅ {len(recommendations)} recomendaciones de waivers generadas")
        return recommendations
