import os
from dotenv import load_dotenv
from espn_api.baseball import League

load_dotenv()

# Conectar a tu liga
league = League(
    league_id=int(os.getenv('LEAGUE_ID')),
    year=int(os.getenv('SEASON')),
    espn_s2=os.getenv('ESPN_S2'),
    swid=os.getenv('SWID')
)

# Encontrar tu equipo
my_team = None
for team in league.teams:
    if team.team_id == int(os.getenv('TEAM_ID')):
        my_team = team
        break

print(f"🏆 Equipo: {my_team.team_name}")
print(f"📊 Récord: {my_team.wins}-{my_team.losses}")
print("\n⚾ Roster Actual:\n")

for player in my_team.roster:
    status = "✅ ACTIVO" if player.lineupSlot != 'BE' else "⏸️  BENCH"
    print(f"{status} | {player.name} ({player.position}) - {player.proTeam}")