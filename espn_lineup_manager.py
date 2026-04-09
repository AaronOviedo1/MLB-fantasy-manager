import os
from dotenv import load_dotenv
from espn_api.baseball import League
import requests

load_dotenv()

class ESPNLineupManager:
    """
    Maneja cambios de lineup usando la API de ESPN
    """
    
    # Mapeo de slots de ESPN Baseball
    SLOT_MAP = {
        'C': 0,
        '1B': 1,
        '2B': 2,
        '3B': 3,
        'SS': 4,
        '2B/SS': 5,
        '1B/3B': 6,
        'LF': 7,
        'CF': 8,
        'RF': 9,
        'OF': 10,
        'DH': 11,
        'UTIL': 12,
        'P': 13,
        'SP': 14,
        'RP': 15,
        'BE': 16,  # Bench
        'IL': 17   # Injured List
    }
    
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
        
        self.espn_s2 = os.getenv('ESPN_S2')
        self.swid = os.getenv('SWID')
        self.league_id = os.getenv('LEAGUE_ID')
        self.team_id = os.getenv('TEAM_ID')
        self.season = os.getenv('SEASON')
    
    def get_eligible_slots(self, player):
        """Retorna los slots elegibles para un jugador"""
        return player.eligibleSlots
    
    def find_best_active_slot(self, player):
        """
        Encuentra el mejor slot activo para un jugador
        basado en sus posiciones elegibles
        """
        eligible = player.eligibleSlots
        
        # Prioridad de slots (de más específico a menos)
        priority_order = ['C', '1B', '2B', '3B', 'SS', 'OF', 'P', 'UTIL']
        
        for slot in priority_order:
            if slot in eligible and slot != 'BE' and slot != 'IL':
                return slot
        
        return 'BE'  # Si no encuentra, bench
    
    def move_player(self, player, target_slot):
        """
        Mueve un jugador a un slot específico
        Usa la API HTTP de ESPN directamente
        """
        # URL de la API
        url = f"https://fantasy.espn.com/apis/v3/games/flb/seasons/{self.season}/segments/0/leagues/{self.league_id}"
        
        cookies = {
            'espn_s2': self.espn_s2,
            'SWID': self.swid
        }
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Obtener roster actual
        response = requests.get(
            f"{url}?view=mRoster&view=mTeam",
            cookies=cookies
        )
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo roster: {response.status_code}")
            return False
        
        data = response.json()
        
        # Encontrar el equipo
        team_data = None
        for team in data.get('teams', []):
            if team['id'] == int(self.team_id):
                team_data = team
                break
        
        if not team_data:
            print(f"❌ Equipo {self.team_id} no encontrado")
            return False
        
        # Actualizar el slot del jugador
        roster_entries = team_data['roster']['entries']
        player_updated = False
        
        for entry in roster_entries:
            if entry['playerId'] == player.playerId:
                # Convertir target_slot a ID
                slot_id = self.SLOT_MAP.get(target_slot, 16)
                entry['lineupSlotId'] = slot_id
                player_updated = True
                break
        
        if not player_updated:
            print(f"❌ Jugador {player.name} no encontrado en roster")
            return False
        
        # Enviar actualización
        payload = {
            'lineup': roster_entries
        }
        
        # PUT request para actualizar
        update_response = requests.put(
            url,
            json=payload,
            cookies=cookies,
            headers=headers,
            params={'teamId': self.team_id, 'view': 'mRoster'}
        )
        
        if update_response.status_code == 200:
            return True
        else:
            print(f"❌ Error actualizando: {update_response.status_code}")
            print(f"Response: {update_response.text[:200]}")
            return False
    
    def activate_player(self, player):
        """Mueve un jugador de bench a lineup activo"""
        best_slot = self.find_best_active_slot(player)
        return self.move_player(player, best_slot)
    
    def bench_player(self, player):
        """Mueve un jugador a bench"""
        return self.move_player(player, 'BE')


# Test
if __name__ == "__main__":
    manager = ESPNLineupManager()
    
    print(f"🏆 Equipo: {manager.my_team.team_name}\n")
    print("📋 Roster actual:\n")
    
    for player in manager.my_team.roster[:10]:
        slot = player.lineupSlot
        eligible = player.eligibleSlots
        print(f"{player.name:25} → {slot:5} (Elegible: {', '.join(eligible[:5])})")
    
    print("\n" + "="*80)
    print("💡 Para probar un cambio real, descomenta el código de abajo")
    print("="*80)
    
    # DESCOMENTA ESTO PARA PROBAR UN CAMBIO REAL:
    # test_player = manager.my_team.roster[0]  # Primer jugador
    # print(f"\n🧪 Probando mover {test_player.name} a bench...")
    # success = manager.bench_player(test_player)
    # if success:
    #     print("✅ Cambio exitoso!")
    # else:
    #     print("❌ Cambio falló")