from mlb_api import MLBClient
from datetime import datetime

print(f"🎮 Juegos de MLB para hoy ({datetime.now().strftime('%Y-%m-%d')})\n")
print("=" * 80)

games = MLBClient.get_todays_games()

if not games:
    print("⚠️  No hay juegos programados para hoy (o es día de descanso)")
else:
    print(f"\n📅 {len(games)} juegos programados:\n")
    
    for i, game in enumerate(games, 1):
        print(f"{i}. {game['away_team']} @ {game['home_team']}")
        print(f"   🕐 {game['game_time']}")
        print(f"   📊 Status: {game['status']}")
        
        # Mostrar pitchers probables
        if game['away_pitcher']:
            print(f"   🔴 Visitante: {game['away_pitcher']['name']}")
        if game['home_pitcher']:
            print(f"   🔵 Local: {game['home_pitcher']['name']}")
        
        print("-" * 80)

# Probar búsqueda de stats (usando uno de tus jugadores)
print("\n\n🔍 Probando búsqueda de estadísticas...\n")

# Probar con Zack Wheeler (uno de tus pitchers)
print("Buscando stats de Zack Wheeler...")
pitcher_stats = MLBClient.get_pitcher_stats("Zack Wheeler", 2026)
if pitcher_stats:
    print(f"✅ ERA: {pitcher_stats['era']}")
    print(f"✅ WHIP: {pitcher_stats['whip']}")
    print(f"✅ K: {pitcher_stats['strikeouts']}")
else:
    print("⚠️  No se encontraron estadísticas (puede ser muy temprano en la temporada)")

# Probar stats de bateador
print("\nBuscando stats de Aaron Judge...")
batter_stats = MLBClient.get_batter_stats("Aaron Judge", 2026)
if batter_stats:
    print(f"✅ AVG: {batter_stats['avg']:.3f}")
    print(f"✅ OPS: {batter_stats['ops']:.3f}")
    print(f"✅ HR: {batter_stats['home_runs']}")
else:
    print("⚠️  No se encontraron estadísticas")