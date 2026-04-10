import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

MLB_BASE = "https://statsapi.mlb.com/api/v1"

class MLBClient:

    # Caches a nivel de clase: viven durante toda la corrida del script.
    # Evitan re-descargar la lista completa de jugadores, equipos y schedules
    # en cada llamada a los métodos de stats.
    _players_cache: Dict[int, List[Dict]] = {}
    _teams_cache: Dict[int, List[Dict]] = {}
    _schedule_cache: Dict[str, List[Dict]] = {}  # clave: fecha YYYY-MM-DD

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
    
    @classmethod
    def get_games_for_date(cls, date_str: str) -> List[Dict]:
        """
        Obtiene todos los juegos para una fecha específica (formato: YYYY-MM-DD).
        Usa cache para evitar llamadas repetidas a la misma fecha en la misma corrida.
        """
        if date_str in cls._schedule_cache:
            return cls._schedule_cache[date_str]

        url = f"{MLB_BASE}/schedule?sportId=1&date={date_str}&hydrate=probablePitcher"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            games = []
            for date in data.get('dates', []):
                for game in date.get('games', []):
                    game_info = {
                        'game_id': game['gamePk'],
                        'away_team': game['teams']['away']['team']['name'],
                        'home_team': game['teams']['home']['team']['name'],
                        'game_time': game['gameDate'],
                        'status': game['status']['detailedState'],
                        'away_pitcher': None,
                        'home_pitcher': None
                    }

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

            cls._schedule_cache[date_str] = games
            return games
        except Exception as e:
            print(f"❌ Error obteniendo juegos para {date_str}: {e}")
            return []

    @classmethod
    def get_todays_games(cls) -> List[Dict]:
        """Obtiene todos los juegos de hoy (incluye finalizados, en progreso y programados)"""
        today = datetime.now().strftime('%Y-%m-%d')
        games = cls.get_games_for_date(today)
        print(f"DEBUG: Se encontraron {len(games)} juegos para hoy")
        return games
    
    @classmethod
    def _get_all_players(cls, season: int) -> List[Dict]:
        """
        Devuelve la lista completa de jugadores MLB para la temporada,
        usando cache para evitar re-descargas. Solo hace request en el
        primer llamado por temporada durante la corrida del script.
        """
        if season in cls._players_cache:
            return cls._players_cache[season]

        try:
            url = f"{MLB_BASE}/sports/1/players?season={season}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            players = response.json().get('people', [])
            cls._players_cache[season] = players
            print(f"DEBUG: Cache MISS - descargados {len(players)} jugadores MLB ({season})")
            return players
        except Exception as e:
            print(f"⚠️  Error descargando lista de jugadores MLB: {e}")
            cls._players_cache[season] = []
            return []

    @classmethod
    def _get_all_teams(cls, season: int) -> List[Dict]:
        """
        Devuelve la lista completa de equipos MLB para la temporada,
        usando cache. Solo hace request en el primer llamado por temporada.
        """
        if season in cls._teams_cache:
            return cls._teams_cache[season]

        try:
            url = f"{MLB_BASE}/teams?sportId=1&season={season}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            teams = response.json().get('teams', [])
            cls._teams_cache[season] = teams
            print(f"DEBUG: Cache MISS - descargados {len(teams)} equipos MLB ({season})")
            return teams
        except Exception as e:
            print(f"⚠️  Error descargando lista de equipos MLB: {e}")
            cls._teams_cache[season] = []
            return []

    @staticmethod
    def get_pitcher_stats(pitcher_name: str, season: int = 2026) -> Optional[Dict]:
        """
        Busca estadísticas de un pitcher por nombre
        Retorna ERA, WHIP, K/9, etc.
        """
        try:
            # Buscar el pitcher por nombre en la lista cacheada
            players = MLBClient._get_all_players(season)

            pitcher_id = None
            needle = pitcher_name.lower()
            for player in players:
                if needle in player['fullName'].lower():
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
            # Obtener lista de equipos cacheada
            teams = MLBClient._get_all_teams(season)

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
            # Buscar el jugador por nombre en la lista cacheada
            players = MLBClient._get_all_players(season)

            player_id = None
            needle = batter_name.lower()
            for player in players:
                if needle in player['fullName'].lower():
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

    @staticmethod
    def get_batter_recent_stats(batter_name: str, days: int = 7, season: int = 2026) -> Optional[Dict]:
        """
        Obtiene estadísticas de un bateador en los últimos N días usando un rango de fechas.
        Útil para detectar jugadores en racha caliente.
        """
        try:
            players = MLBClient._get_all_players(season)
            player_id = None
            needle = batter_name.lower()
            for player in players:
                if needle in player['fullName'].lower():
                    player_id = player['id']
                    break

            if not player_id:
                return None

            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            url = (f"{MLB_BASE}/people/{player_id}/stats"
                   f"?stats=byDateRange&group=hitting&season={season}"
                   f"&startDate={start_date}&endDate={end_date}")
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('stats') and len(data['stats']) > 0:
                splits = data['stats'][0].get('splits', [])
                if splits:
                    stats = splits[0]['stat']
                    return {
                        'avg': float(stats.get('avg', 0.0) or 0.0),
                        'obp': float(stats.get('obp', 0.0) or 0.0),
                        'slg': float(stats.get('slg', 0.0) or 0.0),
                        'ops': float(stats.get('ops', 0.0) or 0.0),
                        'home_runs': stats.get('homeRuns', 0),
                        'rbi': stats.get('rbi', 0),
                    }
            return None
        except Exception as e:
            print(f"⚠️  Error obteniendo stats recientes de {batter_name}: {e}")
            return None

    @staticmethod
    def get_pitcher_recent_stats(pitcher_name: str, days: int = 21, season: int = 2026) -> Optional[Dict]:
        """
        Obtiene estadísticas de un pitcher en los últimos N días (aprox. 3 salidas).
        """
        try:
            players = MLBClient._get_all_players(season)
            player_id = None
            needle = pitcher_name.lower()
            for player in players:
                if needle in player['fullName'].lower():
                    player_id = player['id']
                    break

            if not player_id:
                return None

            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            url = (f"{MLB_BASE}/people/{player_id}/stats"
                   f"?stats=byDateRange&group=pitching&season={season}"
                   f"&startDate={start_date}&endDate={end_date}")
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('stats') and len(data['stats']) > 0:
                splits = data['stats'][0].get('splits', [])
                if splits:
                    stats = splits[0]['stat']
                    return {
                        'era': stats.get('era', 0.0),
                        'whip': stats.get('whip', 0.0),
                        'strikeouts': stats.get('strikeOuts', 0),
                        'innings_pitched': stats.get('inningsPitched', '0.0'),
                        'wins': stats.get('wins', 0),
                    }
            return None
        except Exception as e:
            print(f"⚠️  Error obteniendo stats recientes de {pitcher_name}: {e}")
            return None