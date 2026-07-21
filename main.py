import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from api import app
from agent import MediaBuyerAgent

media_buyer = MediaBuyerAgent()
scheduler = BackgroundScheduler()

# Exécution tous les jours à 8h00
scheduler.add_job(
    media_buyer.generate_daily_metrics_report, 
    'cron', 
    hour=8, 
    minute=0
)

# ASTUCE DE TEST : Décommente la ligne ci-dessous pour forcer l'envoi toutes les 10 secondes le temps de vérifier que ça marche !
# scheduler.add_job(media_buyer.generate_daily_metrics_report, 'interval', seconds=10)
# [NOUVEAU CRON] Surveillance du Pixel toutes les 6 heures
scheduler.add_job(
    media_buyer.verify_conversions_watchdog, 
    'interval', 
    hours=6
)
# [NOUVEAU CRON] Résumé hebdomadaire pour l'Analyste (Tous les lundis à 8h00)
scheduler.add_job(
    media_buyer.send_weekly_summary_to_analyst, 
    'cron', 
    day_of_week='mon', 
    hour=8, 
    minute=0
)
@app.on_event("startup")
def startup_event():
    scheduler.start()
    print("🚀 [MEDIA BUYER] Agent démarré. CRON de 8h00 actif.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)