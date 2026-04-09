import os
from dotenv import load_dotenv
import requests
from datetime import datetime

load_dotenv()

class TelegramNotifier:
    """
    Sistema de notificaciones por Telegram
    """
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            print("⚠️  Telegram no configurado - verifica .env")
            self.enabled = False
        else:
            self.enabled = True
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, text, parse_mode='HTML'):
        """Envía un mensaje a Telegram"""
        if not self.enabled:
            print("⚠️  Telegram deshabilitado")
            return False
        
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            return False
    
    def send_daily_lineup_report(self, recommendations, team_name):
        """
        Envía el reporte diario de lineup optimizado
        """
        # Construir mensaje
        today = datetime.now().strftime('%A, %B %d, %Y')
        
        message = f"🏆 <b>{team_name}</b>\n"
        message += f"📅 {today}\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Contadores
        total_changes = len(recommendations['to_activate']) + len(recommendations['to_bench'])
        
        if total_changes == 0:
            message += "✨ <b>Tu lineup está optimizado</b>\n"
            message += "No hay cambios recomendados para hoy.\n"
        else:
            message += f"📊 <b>{total_changes} cambios recomendados</b>\n\n"
            
            # ACTIVACIONES
            if recommendations['to_activate']:
                message += "✅ <b>MOVER A LINEUP ACTIVO:</b>\n\n"
                
                for i, rec in enumerate(recommendations['to_activate'], 1):
                    player = rec['player']
                    score = rec['score']
                    reason = rec['reason']
                    position = rec['position']
                    
                    # Emoji según confianza
                    if score >= 5:
                        emoji = "🔥"
                    elif score >= 2:
                        emoji = "👍"
                    else:
                        emoji = "🤔"
                    
                    # Determinar si es pitcher o bateador
                    is_pitcher = position in ['SP', 'RP', 'P']
                    
                    message += f"{i}. {emoji} <b>{player.name}</b> ({position})\n"
                    message += f"   Confianza: {score}\n"
                    
                    # Parsear la razón para mostrar info útil
                    parts = reason.split('|')
                    matchup = parts[0].strip()  # "vs Team"
                    message += f"   {matchup}\n"
                    
                    # Mostrar 2-3 razones principales
                    key_reasons = []
                    for part in parts[1:4]:  # Máximo 3 razones adicionales
                        clean = part.strip()
                        if clean:
                            key_reasons.append(clean)
                    
                    if key_reasons:
                        message += f"   <i>{' | '.join(key_reasons)}</i>\n"
                    
                    message += "\n"
            
            # BENCH
            if recommendations['to_bench']:
                message += "\n⏸️ <b>MOVER A BENCH:</b>\n\n"
                
                for i, rec in enumerate(recommendations['to_bench'], 1):
                    player = rec['player']
                    score = rec['score']
                    reason = rec['reason']
                    position = rec['position']
                    
                    # Emoji según qué tan malo es el matchup
                    if score <= -7:
                        emoji = "🚫"
                    elif score <= -3:
                        emoji = "⚠️"
                    else:
                        emoji = "🤷"
                    
                    is_pitcher = position in ['SP', 'RP', 'P']
                    
                    message += f"{i}. {emoji} <b>{player.name}</b> ({position})\n"
                    
                    # Parsear razón
                    parts = reason.split('|')
                    matchup = parts[0].strip()
                    message += f"   {matchup}\n"
                    
                    # Mostrar razones principales
                    key_reasons = []
                    for part in parts[1:3]:  # Máximo 2 razones
                        clean = part.strip()
                        if clean:
                            key_reasons.append(clean)
                    
                    if key_reasons:
                        message += f"   <i>{' | '.join(key_reasons)}</i>\n"
                    
                    message += "\n"
        
        message += "\n━━━━━━━━━━━━━━━━━━━━\n"
        message += "💡 <i>Abre ESPN para hacer los cambios</i>"
        
        return self.send_message(message)
    def send_test_message(self):
        """Envía mensaje de prueba"""
        message = "🧪 <b>Test MLB Fantasy Bot</b>\n\n"
        message += "✅ Bot configurado correctamente!\n"
        message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(message)


# Script de prueba
if __name__ == "__main__":
    notifier = TelegramNotifier()
    
    print("📱 Probando conexión con Telegram...\n")
    
    if notifier.enabled:
        print("✅ Telegram configurado")
        print(f"🤖 Bot Token: {notifier.bot_token[:20]}...")
        print(f"💬 Chat ID: {notifier.chat_id}\n")
        
        print("📤 Enviando mensaje de prueba...")
        success = notifier.send_test_message()
        
        if success:
            print("✅ ¡Mensaje enviado! Revisa tu Telegram")
        else:
            print("❌ Error enviando mensaje")
    else:
        print("❌ Telegram no configurado - verifica tu .env")