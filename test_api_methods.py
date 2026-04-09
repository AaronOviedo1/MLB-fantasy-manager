import os
from dotenv import load_dotenv
from espn_api.baseball import League

load_dotenv()

league = League(
    league_id=int(os.getenv('LEAGUE_ID')),
    year=int(os.getenv('SEASON')),
    espn_s2=os.getenv('ESPN_S2'),
    swid=os.getenv('SWID')
)

my_team = None
for team in league.teams:
    if team.team_id == int(os.getenv('TEAM_ID')):
        my_team = team
        break

print("🔍 Investigando métodos disponibles del Team object:\n")
print("Métodos disponibles:")
for method in dir(my_team):
    if not method.startswith('_'):
        print(f"  - {method}")

print("\n\n🔍 Investigando un Player object:\n")
player = my_team.roster[0]
print(f"Player: {player.name}")
print(f"Position: {player.position}")
print(f"Lineup Slot: {player.lineupSlot}")
print(f"\nAtributos del player:")
for attr in dir(player):
    if not attr.startswith('_'):
        try:
            value = getattr(player, attr)
            if not callable(value):
                print(f"  - {attr}: {value}")
        except:
            pass