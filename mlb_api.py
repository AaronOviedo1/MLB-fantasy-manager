import requests
from datetime import datetime
from typing import List, Dict, Optional

MLB_BASE = "https://statsapi.mlb.com/api/v1"

class MLBClient:
    
    # Mapeo de abreviaciones ESPN a nombres completos MLB
    TEAM_MAPPING = {
        'NYY': 'New York Yankees',
        'Phi': 'Philadelphia Phillies',
        'NYM': 'New York Mets',
        'Cin': 'Cincinnati Reds',
        'Mil': 'Milwaukee Brewers',
        'Sea': 'Seattle Mariners',
        'Oak': 'Oakland Athletics',
        'ChC': 'Chicago Cubs',
        'SF': 'San Francisco Giants',
        'Det': 'Detroit Tigers',
        'LAA': 'Los Angeles Angels',
        'SD': 'San Diego Padres',
        'Atl': 'Atlanta Braves',
        'Pit': 'Pittsburgh Pirates',
        'Bos': 'Boston Red Sox',
        'TB': 'Tampa Bay Rays',
        'Tor': 'Toronto Blue Jays',
        'Bal': 'Baltimore Orioles',
        'Cle': 'Cleveland Guardians',
        'CWS': 'Chicago White Sox',
        'Min': 'Minnesota Twins',
        'KC': 'Kansas City Royals',
        'Hou': 'Houston Astros',
        'Tex': 'Texas Rangers',
        'LAD': 'Los Angeles Dodgers',
        'Ari': 'Arizona Diamondbacks',
        'Col': 'Colorado Rockies',
        'StL': 'St. Louis Cardinals',
        'Wsh': 'Washington Nationals',
        'Mia': 'Miami Marlins',
    }
    
    @staticmethod
    @staticmethod
    def get_todays_games() -> List[Dict]:
        """Obtiene todos los juegos de hoy (incluye finalizados, en progreso y programados)"""
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{MLB_BASE}/schedule?sportId=1&date={today}&hydrate=probablePitcher"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            games = []
            for date in data.get('dates', []):
                for game in date.get('games', []):
                    # Incluir TODOS los estados: Pre-Game, In Progress, Final, etc.
                    game_info = {
                        'game_id': game['gamePk'],
                        'away_team': game['teams']['away']['team']['name'],
                        'home_team': game['teams']['home']['team']['name'],
                        'game_time': game['gameDate'],
                        'status': game['status']['detailedState'],
                        'away_pitcher': None,
                        'home_pitcher': None
                    }
                    
                    # Obtener pitchers probables si están disponibles
                    try:
                        if 'probablePitcher' in game['teams']['away']:
                            game_info['away_pitcher'] = {
                                'id': game['teams']['away']['probablePitcher']['id'],
                                'name': game['teams']['away']['probablePitcher']['fullName']
                            }
                        if 'probablePitcher' in game['teams']['home']:
                            game_info['home_pitcher'] = {
                                'id': game['teams']['home']['probablePitcher']['id'],
                                'name': game['teams']['home']['probablePitcher']['fullName']
                            }
                    except KeyError:
                        pass
                    
                    games.append(game_info)
            
            print(f"DEBUG: Se encontraron {len(games)} juegos para hoy")
            return games
        except Exception as e:
            print(f"❌ Error obteniendo juegos: {e}")
            return []
    
    @staticmethod
    def get_pitcher_stats(pitcher_name: str, season: int = 2026) -> Optional[Dict]:
        """
        Busca estadísticas de un pitcher por nombre
        Retorna ERA, WHIP, K/9, etc.
        """
        try:
            # Buscar el pitcher por nombre
            search_url = f"{MLB_BASE}/sports/1/players?season={season}"
            response = requests.get(search_url, timeout=10)
            players = response.json().get('people', [])
            
            pitcher_id = None
            for player in players:
                if pitcher_name.lower() in player['fullName'].lower():
                    pitcher_id = player['id']
                    break
            
            if not pitcher_id:
                return None
            
            # Obtener stats del pitcher
            stats_url = f"{MLB_BASE}/people/{pitcher_id}/stats?stats=season&season={season}&group=pitching"
            response = requests.get(stats_url, timeout=10)
            data = response.json()
            
            if data.get('stats') and len(data['stats']) > 0:
                splits = data['stats'][0].get('splits', [])
                if splits:
                    stats = splits[0]['stat']
                    return {
                        'era': stats.get('era', 0.0),
                        'whip': stats.get('whip', 0.0),
                        'strikeouts': stats.get('strikeOuts', 0),
                        'walks': stats.get('baseOnBalls', 0),
                        'innings_pitched': stats.get('inningsPitched', '0.0'),
                        'wins': stats.get('wins', 0),
                        'losses': stats.get('losses', 0)
                    }
            return None
        except Exception as e:
            print(f"⚠️  Error obteniendo stats de pitcher {pitcher_name}: {e}")
            return None
    
    @staticmethod
    def get_team_batting_stats(team_name: str, season: int = 2026) -> Optional[Dict]:
        """
        Obtiene estadísticas ofensivas de un equipo
        Retorna AVG, OPS, HR, etc.
        """
        try:
            # Obtener lista de equipos
            teams_url = f"{MLB_BASE}/teams?sportId=1&season={season}"
            response = requests.get(teams_url, timeout=10)
            teams = response.json().get('teams', [])
            
            team_id = None
            for team in teams:
                if team['name'] == team_name:
                    team_id = team['id']
                    break
            
            if not team_id:
                return None
            
            # Obtener stats del equipo
            stats_url = f"{MLB_BASE}/teams/{team_id}/stats?stats=season&season={season}&group=hitting"
            response = requests.get(stats_url, timeout=10)
            data = response.json()
            
            if data.get('stats') and len(data['stats']) > 0:
                splits = data['stats'][0].get('splits', [])
                if splits:
                    stats = splits[0]['stat']
                    return {
                        'avg': stats.get('avg', '.000'),
                        'obp': stats.get('obp', '.000'),
                        'slg': stats.get('slg', '.000'),
                        'ops': stats.get('ops', '.000'),
                        'home_runs': stats.get('homeRuns', 0),
                        'runs': stats.get('runs', 0)
                    }
            return None
        except Exception as e:
            print(f"⚠️  Error obteniendo stats del equipo {team_name}: {e}")
            return None
    
    @staticmethod
    def get_batter_stats(batter_name: str, season: int = 2026) -> Optional[Dict]:
        """
        Busca estadísticas de un bateador por nombre
        Retorna AVG, OPS, HR, etc.
        """
        try:
            # Buscar el jugador por nombre
            search_url = f"{MLB_BASE}/sports/1/players?season={season}"
            response = requests.get(search_url, timeout=10)
            players = response.json().get('people', [])
            
            player_id = None
            for player in players:
                if batter_name.lower() in player['fullName'].lower():
                    player_id = player['id']
                    break
            
            if not player_id:
                return None
            
            # Obtener stats del bateador
            stats_url = f"{MLB_BASE}/people/{player_id}/stats?stats=season&season={season}&group=hitting"
            response = requests.get(stats_url, timeout=10)
            data = response.json()
            
            if data.get('stats') and len(data['stats']) > 0:
                splits = data['stats'][0].get('splits', [])
                if splits:
                    stats = splits[0]['stat']
                    return {
                        'avg': float(stats.get('avg', 0.0)),
                        'obp': float(stats.get('obp', 0.0)),
                        'slg': float(stats.get('slg', 0.0)),
                        'ops': float(stats.get('ops', 0.0)),
                        'home_runs': stats.get('homeRuns', 0),
                        'rbi': stats.get('rbi', 0),
                        'stolen_bases': stats.get('stolenBases', 0)
                    }
            return None
        except Exception as e:
            print(f"⚠️  Error obteniendo stats de {batter_name}: {e}")
            return None