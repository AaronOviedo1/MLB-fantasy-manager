# MLB Fantasy Manager

Agente inteligente para optimizar lineup de MLB Fantasy Baseball.

## Features
- Análisis automático de matchups (bateadores vs pitchers)
- Verificación de probable pitchers para SPs
- Sistema de scoring inteligente
- Notificaciones por Telegram
- Ejecución diaria automatizada (9:00 AM)

## Stack
- Python 3.11
- ESPN Fantasy Baseball API
- MLB Stats API
- Telegram Bot API
- GitHub Actions (cron)

## Configuración
Requiere secrets en GitHub Actions:
- ESPN_S2
- SWID
- LEAGUE_ID
- TEAM_ID
- SEASON
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID