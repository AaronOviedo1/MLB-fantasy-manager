import os
from dotenv import load_dotenv
from espn_api.baseball import League
from mlb_api import MLBClient
from decision_engine import MatchupAnalyzer, LineupDecisionMaker

load_dotenv()

class LineupOptimizer:
    
    def __init__(self):
        self.league = League(
            league_id=int(os.getenv('LEAGUE_ID')),
            year=int(os.getenv('SEASON')),
            espn_s2=os.getenv('ESPN_S2'),
            swid=os.getenv('SWID')
        )
        
        self.my_team = None
        for team in self.league.teams:
            if team.team_id == int(os.getenv('TEAM_ID')):
                self.my_team = team
                break
        
        self.mlb_client = MLBClient()
    
    def get_player_matchup_today(self, player):
        """
        Encuentra el juego y matchup de un jugador para hoy
        
        Para pitchers, verifica si es el starter programado
        
        Returns: (plays_today, opponent_team, is_home, opposing_pitcher, is_probable_starter)
        """
        games_today = self.mlb_client.get_todays_games()
        
        # Convertir abreviación ESPN a nombre completo
        player_team_abbr = player.proTeam
        player_team_full = self.mlb_client.TEAM_MAPPING.get(player_team_abbr)
        
        if not player_team_full:
            return False, None, False, None, False
        
        # Determinar si es pitcher
        is_pitcher = player.position in ['SP', 'RP', 'P']
        
        # Buscar el juego del equipo del jugador
        for game in games_today:
            is_away = game['away_team'] == player_team_full
            is_home = game['home_team'] == player_team_full
            
            if is_away or is_home:
                opponent = game['home_team'] if is_away else game['away_team']
                opposing_pitcher = game['home_pitcher'] if is_away else game['away_pitcher']
                
                # Para STARTING PITCHERS: verificar si es el probable pitcher
                is_probable_starter = False
                if is_pitcher and player.position == 'SP':
                    # Verificar si el nombre del jugador coincide con el probable pitcher
                    probable = game['away_pitcher'] if is_away else game['home_pitcher']
                    
                    if probable and probable['name']:
                        # Comparación flexible de nombres (por si hay diferencias menores)
                        player_last_name = player.name.split()[-1].lower()
                        probable_last_name = probable['name'].split()[-1].lower()
                        
                        is_probable_starter = player_last_name == probable_last_name
                
                # Para RELIEVERS: siempre pueden jugar si su equipo juega
                elif is_pitcher and player.position in ['RP', 'P']:
                    is_probable_starter = True  # RPs pueden entrar cualquier día
                
                return True, opponent, is_home, opposing_pitcher, is_probable_starter
        
        return False, None, False, None, False
    
    def optimize_daily_lineup(self, dry_run=True):
        """
        Analiza el roster y genera recomendaciones
        dry_run=True: solo muestra recomendaciones sin hacer cambios
        """
        print(f"\n🔄 Optimizando lineup para {self.my_team.team_name}")
        print("=" * 80)
        
        recommendations = {
            'to_activate': [],
            'to_bench': [],
            'keep_as_is': []
        }
        
        # Analizar cada jugador
        for player in self.my_team.roster:
            is_active = player.lineupSlot != 'BE'
            position = player.position
            
            # Determinar si es pitcher o bateador
            is_pitcher = position in ['SP', 'RP', 'P']
            
            # Obtener matchup de hoy (ACTUALIZADO con is_probable_starter)
            plays_today, opponent, is_home, opposing_pitcher, is_probable_starter = self.get_player_matchup_today(player)
            
            # REGLA ESPECIAL PARA STARTING PITCHERS
            if position == 'SP':
                if not plays_today:
                    # Equipo no juega hoy
                    if is_active:
                        recommendations['to_bench'].append({
                            'player': player,
                            'reason': 'Su equipo no juega hoy',
                            'score': -10,
                            'position': position
                        })
                    continue
                
                if not is_probable_starter:
                    # El equipo juega pero este SP NO es el starter programado
                    if is_active:
                        recommendations['to_bench'].append({
                            'player': player,
                            'reason': 'No es el starter programado hoy',
                            'score': -10,
                            'position': position
                        })
                    continue
            
            # Para RELIEVERS y BATEADORES: la lógica normal
            if not plays_today:
                if is_active:
                    recommendations['to_bench'].append({
                        'player': player,
                        'reason': 'No juega hoy',
                        'score': -10,
                        'position': position
                    })
                continue
            
            # Analizar matchup
            if is_pitcher:
                # Obtener stats del pitcher
                pitcher_stats = self.mlb_client.get_pitcher_stats(player.name)
                
                # Obtener stats del equipo contrario
                team_stats = self.mlb_client.get_team_batting_stats(opponent) if opponent else None
                
                # Análisis de decisión
                should_start, reason, score = MatchupAnalyzer.analyze_pitcher_matchup(
                    player.name,
                    pitcher_stats,
                    team_stats,
                    is_home
                )
            else:
                # Bateador
                batter_stats = self.mlb_client.get_batter_stats(player.name)
                
                # Stats del pitcher contrario
                opposing_pitcher_stats = None
                if opposing_pitcher:
                    opposing_pitcher_stats = self.mlb_client.get_pitcher_stats(
                        opposing_pitcher['name']
                    )
                
                should_start, reason, score = MatchupAnalyzer.analyze_batter_matchup(
                    player.name,
                    batter_stats,
                    opposing_pitcher_stats,
                    is_home
                )
            
            # Generar recomendación
            matchup_info = f"vs {opponent}" if opponent else "Matchup desconocido"
            
            if should_start and not is_active:
                recommendations['to_activate'].append({
                    'player': player,
                    'reason': f"{matchup_info} | {reason}",
                    'score': score,
                    'position': position
                })
            elif not should_start and is_active:
                recommendations['to_bench'].append({
                    'player': player,
                    'reason': f"{matchup_info} | {reason}",
                    'score': score,
                    'position': position
                })
            else:
                recommendations['keep_as_is'].append({
                    'player': player,
                    'reason': f"{matchup_info} | {reason}",
                    'score': score,
                    'position': position,
                    'is_active': is_active
                })
        
        # Priorizar cambios
        recommendations = LineupDecisionMaker.prioritize_lineup_changes(recommendations)
        
        return recommendations
    
    def print_recommendations(self, recommendations):
        """Imprime las recomendaciones de forma clara"""
        print("\n" + "=" * 80)
        print("📋 RECOMENDACIONES DE LINEUP")
        print("=" * 80)
        
        if recommendations['to_activate']:
            print("\n✅ MOVER A LINEUP ACTIVO:")
            for i, rec in enumerate(recommendations['to_activate'], 1):
                score_emoji = "🔥" if rec['score'] >= 5 else "👍" if rec['score'] >= 0 else "🤔"
                print(f"\n{i}. {rec['player'].name} ({rec['position']}) {score_emoji}")
                print(f"   Confianza: {rec['score']}")
                print(f"   Razón: {rec['reason']}")
        
        if recommendations['to_bench']:
            print("\n\n⏸️  MOVER A BENCH:")
            for i, rec in enumerate(recommendations['to_bench'], 1):
                score_emoji = "🚫" if rec['score'] <= -5 else "⚠️" if rec['score'] < 0 else "🤷"
                print(f"\n{i}. {rec['player'].name} ({rec['position']}) {score_emoji}")
                print(f"   Confianza: {rec['score']}")
                print(f"   Razón: {rec['reason']}")
        
        if not recommendations['to_activate'] and not recommendations['to_bench']:
            print("\n✨ Tu lineup ya está optimizado - no hay cambios recomendados")
        
        print("\n" + "=" * 80)


# Script principal
if __name__ == "__main__":
    import sys
    from notifier import TelegramNotifier
    
    optimizer = LineupOptimizer()
    recs = optimizer.optimize_daily_lineup(dry_run=True)
    
    # Imprimir en consola
    optimizer.print_recommendations(recs)
    
    # SIEMPRE enviar por Telegram
    print("\n" + "=" * 80)
    print("📱 Enviando notificación por Telegram...")
    print("=" * 80)
    
    notifier = TelegramNotifier()
    if notifier.enabled:
        success = notifier.send_daily_lineup_report(recs, optimizer.my_team.team_name)
        if success:
            print("✅ Notificación enviada a Telegram\n")
        else:
            print("❌ Error enviando notificación\n")
    else:
        print("⚠️  Telegram no configurado - solo mostrando en consola\n")
    
    # Preguntar si quiere ver opciones adicionales
    if recs['to_activate'] or recs['to_bench']:
        print("=" * 80)
        print("💡 El reporte ya fue enviado a tu Telegram")
        print("=" * 80)