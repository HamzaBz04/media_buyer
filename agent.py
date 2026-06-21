import os
import requests
from meta_client import MetaAdsClient

class MediaBuyerAgent:
    """Agent 5 : The Media Buyer."""
    
    def __init__(self):
        self.meta_client = MetaAdsClient()
        # The threshold defined by the client (e.g., 15.0)
        self.target_cpl = 15.0 
        
        # Telegram Credentials
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def send_telegram_message(self, text: str):
        """Sends a formatted message to Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            print("⚠️ [TELEGRAM] Token or Chat ID missing. Cannot send message.")
            return

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            print("✅ [TELEGRAM] Message sent successfully!")
        except Exception as e:
            print(f"❌ [TELEGRAM ERROR] Failed to send: {e}")

    def _check_and_alert_cpl(self, platform_name: str, current_cpl: float):
        """
        Checks if the current CPL exceeds the threshold and sends an alert.
        """
        if current_cpl > self.target_cpl:
            alert_text = (
                f"🚨 <b>ALERTE CPL DÉPASSÉ</b> 🚨\n\n"
                f"Plateforme : <b>{platform_name.upper()}</b>\n"
                f"CPL Actuel : <b>{current_cpl}€</b>\n"
                f"Seuil Maximum : {self.target_cpl}€\n\n"
                f"<i>Veuillez vérifier les campagnes immédiatement.</i>"
            )
            print(f"⚠️ [ALERTE] Déclenchement de l'alerte Telegram pour {platform_name} !")
            self.send_telegram_message(alert_text)
        else:
            print(f"✅ [CPL CHECK] {platform_name} est dans les clous ({current_cpl}€ <= {self.target_cpl}€).")

    def generate_daily_metrics_report(self):
        """Generates the daily metrics report for yesterday."""
        print("\n📝 [MEDIA BUYER] Rédaction du rapport quotidien...")
        
        # 1. Fetch yesterday's data
        meta_data = self.meta_client.get_yesterdays_performance()
        
        # 2. Calculate CPL
        cpl = round(meta_data["spend"] / meta_data["leads"], 2) if meta_data.get("leads", 0) > 0 else 0.0
        
        # 3. Check for alerts immediately after calculation
        self._check_and_alert_cpl("Meta Ads", cpl)
        
        # 4. Format and send the daily report (existing logic)
        report_text = (
            "📈 <b>RAPPORT QUOTIDIEN MEDIA BUYER</b>\n"
            "<i>Données de la journée d'hier</i>\n\n"
            "🔵 <b>Meta Ads</b>\n"
            f"💰 Dépenses : {meta_data['spend']}€\n"
            f"👁️ Impressions : {meta_data['impressions']}\n"
            f"🖱️ Clics : {meta_data['clicks']}\n"
            f"🎯 Leads : {meta_data['leads']}\n"
            f"📊 <b>CPL : {cpl}€</b>"
        )
        self.send_telegram_message(report_text)

    # ================= HARDCODED ==================================
    # def generate_daily_metrics_report(self):
    #     """Generates the daily metrics report for yesterday."""
    #     print("\n📝 [MEDIA BUYER] Rédaction du rapport quotidien...")
        
    #     # 1. Fetch yesterday's data
    #     meta_data = self.meta_client.get_yesterdays_performance()
        
    #     # 2. Calculate CPL (La vraie logique)
    #     cpl = round(meta_data["spend"] / meta_data["leads"], 2) if meta_data.get("leads", 0) > 0 else 0.0
        
    #     # 🧪 ==========================================
    #     # 🧪 ZONE DE TEST : SIMULATION DE CRISE
    #     # On force le CPL à 50.0€ (bien au-dessus de la cible de 15.0€)
    #     cpl = 50.0 
    #     print(f"🔧 [TEST MODE] CPL forcé manuellement à {cpl}€")
    #     # 🧪 ==========================================

    #     # 3. Check for alerts immediately after calculation
    #     self._check_and_alert_cpl("Meta Ads", cpl)
        
    #     # 4. Format and send the daily report
    #     report_text = (
    #         "📈 <b>RAPPORT QUOTIDIEN MEDIA BUYER</b>\n"
    #         "<i>Données de la journée d'hier</i>\n\n"
    #         "🔵 <b>Meta Ads</b>\n"
    #         f"💰 Dépenses : {meta_data['spend']}€\n"
    #         f"👁️ Impressions : {meta_data['impressions']}\n"
    #         f"🖱️ Clics : {meta_data['clicks']}\n"
    #         f"🎯 Leads : {meta_data['leads']}\n"
    #         f"📊 <b>CPL : {cpl}€</b>"
    #     )
    #     self.send_telegram_message(report_text)
    # ==================================================

    def handle_manual_summary_request(self, campaign_id: str):
        """
        Traite une demande manuelle de l'opérateur pour une campagne précise.
        """
        print(f"\n🔄 [MEDIA BUYER] Demande manuelle reçue pour la campagne {campaign_id}")
        
        # 1. Interrogation du client Meta
        data = self.meta_client.get_campaign_summary(campaign_id)
        
        # 2. Gestion de l'erreur si la campagne n'existe pas
        if data["status"] == "NOT_FOUND":
            self.send_telegram_message(
                f"❌ <b>Erreur :</b> La campagne <code>{campaign_id}</code> est introuvable sur Meta Ads."
            )
            return

        # 3. Calcul du CPL
        cpl = round(data["spend"] / data["leads"], 2) if data.get("leads", 0) > 0 else 0.0

        # 4. Formatage du rapport à la demande
        report_text = (
            f"📊 <b>RÉSUMÉ DE CAMPAGNE (À LA DEMANDE)</b>\n"
            f"🆔 ID : <code>{campaign_id}</code>\n"
            f"⚙️ <b>Statut :</b> {data['status']} | Budget : {data['daily_budget']}€/jour\n\n"
            f"📅 <b>Performances (7 derniers jours) :</b>\n"
            f"💰 Dépenses : {data['spend']}€\n"
            f"🎯 Leads : {data['leads']}\n"
            f"📈 <b>CPL : {cpl}€</b>"
        )
        
        # 5. Envoi immédiat sur Telegram
        self.send_telegram_message(report_text)

# ==========================================
# 🧪 ZONE DE TEST LOCAL
# ==========================================
if __name__ == "__main__":
    print("🚀 Lancement du test de l'Agent Media Buyer...\n")
    agent = MediaBuyerAgent()
    
    # Simulation de la commande d'un opérateur via Telegram
    faux_id_campagne = "123456789"
    agent.handle_manual_summary_request(faux_id_campagne)
    
    # Tu peux aussi tester avec un mauvais ID pour vérifier la gestion d'erreur :
    # agent.handle_manual_summary_request("999999999")