from typing import Dict, Optional, Tuple

class MatchupAnalyzer:
    """
    Analiza matchups y toma decisiones inteligentes sobre lineup
    """
    
    # Umbrales para clasificar jugadores/equipos
    ELITE_PITCHER_ERA = 3.00
    ELITE_PITCHER_WHIP = 1.10
    GOOD_PITCHER_ERA = 3.75
    GOOD_PITCHER_WHIP = 1.25
    
    STRONG_OFFENSE_AVG = 0.260
    STRONG_OFFENSE_OPS = 0.750
    WEAK_OFFENSE_AVG = 0.230
    WEAK_OFFENSE_OPS = 0.680
    
    GOOD_BATTER_AVG = 0.270
    GOOD_BATTER_OPS = 0.800
    STRUGGLING_BATTER_AVG = 0.220
    STRUGGLING_BATTER_OPS = 0.650
    
    @staticmethod
    def safe_float(value, default=0.0):
        """Convierte un valor a float de forma segura"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def analyze_batter_matchup(
        batter_name: str,
        batter_stats: Optional[Dict],
        opposing_pitcher_stats: Optional[Dict],
        is_home_game: bool = False
    ) -> Tuple[bool, str, int]:
        """
        Analiza si un bateador debe iniciar basado en el matchup
        
        Returns:
            (should_start: bool, reason: str, confidence_score: int)
            confidence_score: -10 (muy mala idea) a +10 (excelente idea)
        """
        reasons = []
        score = 0
        
        # REGLA 1: Si no hay stats del bateador, ser conservador
        if not batter_stats:
            return True, "Sin datos suficientes - iniciará por defecto", 0
        
        # REGLA 2: Analizar stats del bateador
        avg = MatchupAnalyzer.safe_float(batter_stats.get('avg', 0.0))
        ops = MatchupAnalyzer.safe_float(batter_stats.get('ops', 0.0))
        
        if avg >= MatchupAnalyzer.GOOD_BATTER_AVG:
            score += 3
            reasons.append(f"✅ Buen promedio ({avg:.3f})")
        elif avg <= MatchupAnalyzer.STRUGGLING_BATTER_AVG:
            score -= 2
            reasons.append(f"⚠️ Bateando bajo ({avg:.3f})")
        
        if ops >= MatchupAnalyzer.GOOD_BATTER_OPS:
            score += 3
            reasons.append(f"✅ Excelente OPS ({ops:.3f})")
        elif ops <= MatchupAnalyzer.STRUGGLING_BATTER_OPS:
            score -= 2
            reasons.append(f"⚠️ OPS bajo ({ops:.3f})")
        
        # REGLA 3: Analizar pitcher contrario (si hay datos)
        if opposing_pitcher_stats:
            era = MatchupAnalyzer.safe_float(opposing_pitcher_stats.get('era', 5.00))
            whip = MatchupAnalyzer.safe_float(opposing_pitcher_stats.get('whip', 1.50))
            
            if era <= MatchupAnalyzer.ELITE_PITCHER_ERA:
                score -= 4
                reasons.append(f"❌ Pitcher élite (ERA {era:.2f})")
            elif era <= MatchupAnalyzer.GOOD_PITCHER_ERA:
                score -= 2
                reasons.append(f"⚠️ Buen pitcher (ERA {era:.2f})")
            elif era >= 4.50:
                score += 3
                reasons.append(f"✅ Pitcher vulnerable (ERA {era:.2f})")
            
            if whip <= MatchupAnalyzer.ELITE_PITCHER_WHIP:
                score -= 2
                reasons.append(f"❌ WHIP bajo ({whip:.2f})")
            elif whip >= 1.40:
                score += 2
                reasons.append(f"✅ WHIP alto ({whip:.2f})")
        
        # REGLA 4: Home field advantage
        if is_home_game:
            score += 1
            reasons.append("✅ Juega en casa")
        
        # Decisión final
        should_start = score >= -2  # Umbral: solo banquear si score muy negativo
        
        reason_text = " | ".join(reasons) if reasons else "Sin análisis detallado"
        
        return should_start, reason_text, score
    
    @staticmethod
    def analyze_pitcher_matchup(
        pitcher_name: str,
        pitcher_stats: Optional[Dict],
        opposing_team_stats: Optional[Dict],
        is_home_game: bool = False
    ) -> Tuple[bool, str, int]:
        """
        Analiza si un pitcher debe iniciar basado en el matchup
        
        Returns:
            (should_start: bool, reason: str, confidence_score: int)
        """
        reasons = []
        score = 0
        
        # REGLA 1: Si no hay stats, ser conservador
        if not pitcher_stats:
            return True, "Sin datos suficientes - iniciará por defecto", 0
        
        # REGLA 2: Analizar stats del pitcher
        era = MatchupAnalyzer.safe_float(pitcher_stats.get('era', 5.00))
        whip = MatchupAnalyzer.safe_float(pitcher_stats.get('whip', 1.50))
        strikeouts = MatchupAnalyzer.safe_float(pitcher_stats.get('strikeouts', 0))
        
        if era <= MatchupAnalyzer.ELITE_PITCHER_ERA:
            score += 4
            reasons.append(f"✅ ERA élite ({era:.2f})")
        elif era <= MatchupAnalyzer.GOOD_PITCHER_ERA:
            score += 2
            reasons.append(f"✅ Buen ERA ({era:.2f})")
        elif era >= 4.50:
            score -= 3
            reasons.append(f"❌ ERA alto ({era:.2f})")
        
        if whip <= MatchupAnalyzer.ELITE_PITCHER_WHIP:
            score += 3
            reasons.append(f"✅ WHIP excelente ({whip:.2f})")
        elif whip >= 1.40:
            score -= 2
            reasons.append(f"⚠️ WHIP preocupante ({whip:.2f})")
        
        # REGLA 3: Analizar ofensiva del equipo contrario
        if opposing_team_stats:
            team_avg = MatchupAnalyzer.safe_float(opposing_team_stats.get('avg', 0.250))
            team_ops = MatchupAnalyzer.safe_float(opposing_team_stats.get('ops', 0.700))
            
            if team_avg >= MatchupAnalyzer.STRONG_OFFENSE_AVG:
                score -= 3
                reasons.append(f"❌ Equipo batea {team_avg:.3f}")
            elif team_avg <= MatchupAnalyzer.WEAK_OFFENSE_AVG:
                score += 2
                reasons.append(f"✅ Ofensiva débil ({team_avg:.3f})")
            
            if team_ops >= MatchupAnalyzer.STRONG_OFFENSE_OPS:
                score -= 2
                reasons.append(f"❌ OPS del equipo alto ({team_ops:.3f})")
            elif team_ops <= MatchupAnalyzer.WEAK_OFFENSE_OPS:
                score += 2
                reasons.append(f"✅ OPS del equipo bajo ({team_ops:.3f})")
        
        # REGLA 4: Home field advantage para pitchers
        if is_home_game:
            score += 1
            reasons.append("✅ Juega en casa")
        
        # Decisión final
        should_start = score >= -2
        
        reason_text = " | ".join(reasons) if reasons else "Sin análisis detallado"
        
        return should_start, reason_text, score


class LineupDecisionMaker:
    """
    Toma decisiones finales sobre cambios al lineup
    """
    
    @staticmethod
    def prioritize_lineup_changes(recommendations: Dict) -> Dict:
        """
        Prioriza los cambios recomendados por confianza/score
        """
        # Ordenar activaciones por score (mejores matchups primero)
        if 'to_activate' in recommendations:
            recommendations['to_activate'].sort(
                key=lambda x: x.get('score', 0),
                reverse=True
            )
        
        # Ordenar banqueados por score (peores matchups primero)
        if 'to_bench' in recommendations:
            recommendations['to_bench'].sort(
                key=lambda x: x.get('score', 0)
            )
        
        return recommendations
    
class RosterConstraints:
    """
    Maneja las restricciones del roster (bench limits, pitcher starts, etc)
    """
    
    MAX_BENCH = 3
    MAX_IL = 2
    MAX_PITCHER_STARTS_PER_WEEK = 10
    
    ACTIVE_POSITIONS = {
        'C': 1,
        '1B': 1,
        '2B': 1,
        '3B': 1,
        'SS': 1,
        'OF': 3,  # Cualquier combinación de LF/CF/RF
        'UTIL': 1,  # Cualquier bateador
        'P': 7     # Cualquier combinación de SP/RP
    }
    
    @staticmethod
    def get_position_priority(position: str, player_stats: dict) -> int:
        """
        Determina prioridad de posición para UTIL y P slots
        
        Para UTIL: Priorizar jugadores con mejor OPS
        Para P: Priorizar SP sobre RP (más puntos potenciales)
        """
        if position in ['SP']:
            return 10  # Alta prioridad
        elif position in ['RP']:
            return 5   # Media prioridad
        else:
            # Bateadores - usar OPS como prioridad
            ops = player_stats.get('ops', 0.0) if player_stats else 0.0
            return int(ops * 10)
    
    @staticmethod
    def should_use_bench_spot(current_bench_count: int, matchup_score: int) -> bool:
        """
        Decide si vale la pena usar un spot de bench
        
        Con solo 3 bench spots, solo banquear si:
        - Score muy negativo (matchup terrible)
        - No hay necesidad de flexibilidad
        """
        if current_bench_count >= RosterConstraints.MAX_BENCH:
            return False
        
        # Solo banquear si matchup es REALMENTE malo
        return matchup_score <= -5
    
    @staticmethod
    def calculate_pitcher_starts_remaining(team_roster, current_week_starts: int) -> int:
        """
        Calcula cuántos starts de pitcher quedan disponibles esta semana
        """
        return max(0, RosterConstraints.MAX_PITCHER_STARTS_PER_WEEK - current_week_starts)
    
    @staticmethod
    def prioritize_pitcher_starts(pitcher_recommendations: list, starts_remaining: int) -> list:
        """
        Prioriza qué pitchers iniciar basado en starts restantes
        
        Si solo quedan 2 starts, elegir los 2 mejores matchups
        """
        if starts_remaining <= 0:
            return []
        
        # Ordenar por score (mejores primero)
        sorted_pitchers = sorted(
            pitcher_recommendations,
            key=lambda x: x['score'],
            reverse=True
        )
        
        # Retornar solo los mejores hasta el límite
        return sorted_pitchers[:starts_remaining]