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
        """Envía un mensaje a Telegram. Si el texto excede 4096 chars, lo divide."""
        if not self.enabled:
            print("⚠️  Telegram deshabilitado")
            return False

        # Telegram permite hasta 4096 caracteres por mensaje
        MAX_LEN = 4000
        chunks = self._split_message(text, MAX_LEN)

        url = f"{self.base_url}/sendMessage"
        all_ok = True
        for chunk in chunks:
            payload = {
                'chat_id': self.chat_id,
                'text': chunk,
                'parse_mode': parse_mode
            }
            try:
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
            except Exception as e:
                print(f"❌ Error enviando mensaje: {e}")
                all_ok = False
        return all_ok

    @staticmethod
    def _split_message(text, max_len):
        """Divide un mensaje largo en chunks respetando saltos de línea."""
        if len(text) <= max_len:
            return [text]

        chunks = []
        current = ""
        for line in text.split('\n'):
            # +1 por el \n que vamos a re-agregar
            if len(current) + len(line) + 1 > max_len:
                if current:
                    chunks.append(current)
                current = line + '\n'
            else:
                current += line + '\n'
        if current:
            chunks.append(current)
        return chunks
    
    def send_daily_lineup_report(self, recommendations, team_name, waiver_recommendations=None):
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
        total_analyzed = total_changes + len(recommendations.get('keep_as_is', []))

        if total_changes == 0:
            message += "✨ <b>Tu lineup está optimizado</b>\n"
            message += f"No hay cambios recomendados para hoy. ({total_analyzed} jugadores analizados)\n"
        else:
            message += f"📊 <b>{total_changes} cambios recomendados</b> ({total_analyzed} jugadores analizados)\n\n"
            
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

        # MANTENER COMO ESTÁ (análisis del resto del roster)
        keep_as_is = recommendations.get('keep_as_is', [])
        if keep_as_is:
            # Separar activos y banqueados
            staying_active = [r for r in keep_as_is if r.get('is_active')]
            staying_bench = [r for r in keep_as_is if not r.get('is_active')]

            # Ordenar activos por score descendente (mejores primero)
            staying_active.sort(key=lambda x: x.get('score', 0), reverse=True)
            staying_bench.sort(key=lambda x: x.get('score', 0), reverse=True)

            if staying_active:
                message += "\n✅ <b>MANTENER ACTIVOS:</b>\n\n"
                for i, rec in enumerate(staying_active, 1):
                    message += self._format_keep_entry(i, rec)

            if staying_bench:
                message += "\n💤 <b>MANTENER EN BENCH:</b>\n\n"
                for i, rec in enumerate(staying_bench, 1):
                    message += self._format_keep_entry(i, rec)

        # WAIVER WIRE PICKUPS
        if waiver_recommendations:
            message += "\n━━━━━━━━━━━━━━━━━━━━\n"
            message += "🔥 <b>WAIVER WIRE PICKUPS RECOMENDADOS:</b>\n\n"

            for i, rec in enumerate(waiver_recommendations, 1):
                player = rec['player']
                score = rec['score']
                reason = rec['reason']
                position = rec['position']
                drop = rec.get('drop_candidate')

                emoji = "🔥" if score >= 7 else "👍"
                message += f"{i}. {emoji} <b>[{position}] {player.name}</b> (Score: {score})\n"

                if drop:
                    message += f"   Drop: {drop.name}\n"

                message += f"   <i>{reason}</i>\n\n"

        message += "\n━━━━━━━━━━━━━━━━━━━━\n"
        message += "💡 <i>Abre ESPN para hacer los cambios</i>"

        return self.send_message(message)

    @staticmethod
    def _format_keep_entry(idx, rec):
        """Formatea una entrada de keep_as_is en formato compacto."""
        player = rec['player']
        score = rec.get('score', 0)
        reason = rec.get('reason', '')
        position = rec.get('position', '')

        # Emoji según score (escala unificada)
        if score >= 5:
            emoji = "🔥"
        elif score >= 2:
            emoji = "👍"
        elif score >= -2:
            emoji = "➖"
        elif score >= -6:
            emoji = "⚠️"
        else:
            emoji = "🚫"

        # Mostrar score con signo
        score_str = f"+{score}" if score > 0 else str(score)

        line = f"{idx}. {emoji} <b>{player.name}</b> ({position}) {score_str}\n"

        # Parsear razón compacta: matchup + máximo 2 razones clave
        parts = [p.strip() for p in reason.split('|') if p.strip()]
        if parts:
            matchup = parts[0]  # "vs Team" o "Matchup desconocido"
            extras = parts[1:3]  # máximo 2 razones adicionales
            if extras:
                line += f"   {matchup} | <i>{' | '.join(extras)}</i>\n"
            else:
                line += f"   {matchup}\n"

        return line
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