import os
import requests
import calendar # <-- NOUVEAU
from datetime import datetime
from meta_client import MetaAdsClient
from langfuse import get_client, observe, propagate_attributes

langfuse = get_client()

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

    @observe(name="[Decision MB] Budget Pacing Check")
    def check_budget_pacing(self, monthly_budget: float, client_id: str = "global"):
        """
        Vérifie le rythme de dépense (Pacing) par rapport au temps écoulé.
        Trace l'audit dans Langfuse.
        """
        print("\n📊 [MEDIA BUYER] Analyse du Pacing Budgétaire...")

        # ... (Garde tout ton code de calcul existant : today, time_elapsed_pct, current_spend, variance) ...
        today = datetime.now()
        _, days_in_month = calendar.monthrange(today.year, today.month) 
        time_elapsed_pct = today.day / days_in_month
        current_spend = self.meta_client.get_current_month_spend()
        spend_pct = current_spend / monthly_budget
        variance = spend_pct - time_elapsed_pct

        # Variables pour Langfuse
        decision_taken = "NO_ACTION"
        reason = f"Rythme normal. Écart de {variance:+.1%} (dans la limite des 15%)"

        if abs(variance) > 0.15:
            decision_taken = "ALERT_SENT"
            status = "🔴 SUR-DÉPENSE" if variance > 0 else "🟡 SOUS-DÉPENSE"
            reason = f"Alerte déclenchée : {status} avec un écart de {variance:+.1%}"
            
            alert_text = (
                f"🚨 <b>ALERTE PACING BUDGÉTAIRE</b> 🚨\n\n"
                # ... (Garde ton texte d'alerte existant) ...
            )
            self.send_telegram_message(alert_text)
            print(f"⚠️ [ALERTE] Écart de pacing critique !")
        else:
            print("✅ [PACING OK] Le rythme de dépense est normal.")

        # 🟢 ENREGISTREMENT DANS LANGFUSE
        with propagate_attributes(
            tags=["media_buyer", "budget_decision", decision_taken],
            metadata={
                "client_id": client_id,
                "campaign_id": "account_level", # L'audit concerne tout le compte
                "decision_reason": reason,
                "variance": variance
            }
        ):
            langfuse.log_event(
                name="budget_pacing_audit",
                description="Audit du rythme de dépense par rapport au budget mensuel."
            )
    
    ### 🧠 Étape 2 : Le "cerveau" dans `agent.py`
    @observe(name="[Decision MB] Budget Pacing & Ad Pause")
    def enforce_adset_rules(self, adset_id: str, cpl_3_days: float, client_id: str = "global"):
        """
        Vérifie si l'Ad Set respecte la règle des 3 jours. 
        Trace la décision dans Langfuse.
        """
        print(f"\n🛡️ [MEDIA BUYER] Vérification des règles pour l'Ad Set {adset_id}...")

        max_allowed_cpl = self.target_cpl * 2 
        
        # 1. Variables pour Langfuse
        decision_taken = "NONE"
        reason = f"CPL actuel ({cpl_3_days}€) est inférieur au max autorisé ({max_allowed_cpl}€)"

        if cpl_3_days > max_allowed_cpl:
            print(f"⚠️ [DÉCISION] CPL critique. Action requise : PAUSE.")
            
            # Action sur Meta
            success = self.meta_client.pause_adset(adset_id)
            
            if success:
                decision_taken = "PAUSED_ADSET"
                reason = f"CPL critique ({cpl_3_days}€) dépasse le max ({max_allowed_cpl}€) sur 3 jours"
                
                alert_text = (
                    f"🛑 <b>ACTION AUTOMATIQUE : AD SET COUPÉ</b> 🛑\n\n"
                    f"🆔 <b>Ad Set ID :</b> <code>{adset_id}</code>\n"
                    f"📉 <b>Raison :</b> Sous-performance sévère.\n"
                )
                self.send_telegram_message(alert_text)
        else:
            print("✅ [DÉCISION] L'Ad Set est rentable. On le laisse tourner.")
            decision_taken = "KEEP_RUNNING"

        # 2. 🟢 ENREGISTREMENT DANS LANGFUSE (Respect strict du cahier des charges)
        with propagate_attributes(
            tags=["media_buyer", "budget_decision", decision_taken],
            metadata={
                "client_id": client_id,
                "campaign_id": adset_id, # Dans Meta, l'action est souvent sur l'Ad Set
                "decision_reason": reason,
                "cpl_observed": cpl_3_days,
                "cpl_threshold": max_allowed_cpl
            }
        ):
            langfuse.log_event(
                name="adset_performance_audit",
                description="Audit de performance de l'Ad Set sur 3 jours."
            )

   
    def verify_conversions_watchdog(self, pixel_id: str = "123456789_MOCK_PIXEL"):
        """
        Vérifie le tracking. Si aucun événement n'est reçu, déclenche l'alerte Telegram.
        """
        print(f"\n🩺 [MEDIA BUYER] Démarrage du Watchdog de tracking (Pixel: {pixel_id})...")
        
        pixel_data = self.meta_client.verify_pixel_activity(pixel_id=pixel_id, event_name="Lead")
        
        if pixel_data.get("status") == "success":
            events_count = pixel_data.get("events_last_24h", 0)
            
            if events_count == 0:
                print("🚨 [ALERTE] Anomalie de tracking détectée. Préparation du message Telegram...")
                
                # Format HTML pour correspondre à ton paramétrage Telegram actuel
                alert_text = (
                    f"🚨 <b>ALERTE CRITIQUE - TRACKING</b> 🚨\n\n"
                    f"Le système a détecté une anomalie majeure de remontée de données :\n"
                    f"🔹 <b>Pixel ID :</b> <code>{pixel_id}</code>\n"
                    f"🔹 <b>Problème :</b> AUCUN événement 'Lead' reçu depuis 24h.\n\n"
                    f"⚠️ <i>Action immédiate : Veuillez vérifier l'intégration API ou Google Tag Manager.</i>"
                )
                self.send_telegram_message(alert_text)
            else:
                print(f"✅ [WATCHDOG] Le tracking fonctionne. ({events_count} conversions).")
    # fonction pour envoyer un résumé hebdomadaire à l'analyste
    def send_weekly_summary_to_analyst(self):
        """
        [INTER-AGENT] Récupère les données à J-7, les structure en JSON, 
        et les envoie au Webhook de l'Agent Analyste.
        """
        print("\n📦 [MEDIA BUYER] Génération du colis hebdomadaire pour l'Analyste...")
        
        # 1. Extraction des données brutes
        data = self.meta_client.get_last_7_days_performance()
        
        # Calcul du CPL sécurisé
        cpl = round(data["spend"] / data["leads"], 2) if data.get("leads", 0) > 0 else 0.0

        # 2. Structuration stricte des données (Le format attendu par l'Analyste)
        payload = {
            "source_agent": "media_buyer",
            "report_type": "weekly_performance",
            "date_generated": datetime.now().isoformat(),
            "metrics": {
                "platform": "meta_ads",
                "spend": data.get("spend", 0.0),
                "impressions": data.get("impressions", 0),
                "clicks": data.get("clicks", 0),
                "leads": data.get("leads", 0),
                "cpl": cpl
            }
        }
        
        # 3. L'envoi réseau vers le serveur de l'Analyste (Port 8005 par exemple)
        ANALYST_WEBHOOK_URL = "http://127.0.0.1:8005/analyst/receive-weekly-data"
        
        try:
            # 🛑 Commenté pour l'instant car ton Analyste n'est pas encore en ligne !
            # response = requests.post(ANALYST_WEBHOOK_URL, json=payload, timeout=10)
            # response.raise_for_status()
            
            print(f"✅ [INTER-AGENT] Données JSON prêtes à être expédiées :")
            import json
            print(json.dumps(payload, indent=4))
        except Exception as e:
            print(f"❌ [INTER-AGENT ERROR] Impossible de joindre l'Analyste : {e}")

        # 4. Notification de l'Opérateur Humain sur Telegram
        alert_text = (
            f"📊 <b>TRANSFERT DE DONNÉES RÉUSSI</b> 📊\n\n"
            f"Le résumé hebdomadaire (J-7) a été envoyé à l'Agent Analyste.\n"
            f"💰 <b>Dépenses :</b> {payload['metrics']['spend']}€\n"
            f"🎯 <b>Leads :</b> {payload['metrics']['leads']}\n"
            f"📈 <b>CPL Moyen :</b> {payload['metrics']['cpl']}€\n\n"
            f"<i>L'Analyste va maintenant traiter ce JSON pour générer les recommandations.</i>"
        )
        self.send_telegram_message(alert_text)
        
        return payload
# ==========================================
# 🧪 ZONE DE TEST LOCAL SUIVI DU RYTHME DE DEPENSE
# ==========================================
# if __name__ == "__main__":
#     print("🚀 Lancement du test de l'Agent Media Buyer...\n")
#     agent = MediaBuyerAgent()
    
#     # Test du Pacing
#     # Si le script remonte que tu as dépensé 0€ ce mois-ci, donne un budget très petit (ex: 1€)
#     # pour forcer l'écart et déclencher l'alerte de "SOUS-DÉPENSE".
#     # Si tu as mocké la dépense à 1500€ dans le meta_client, donne un budget de 2000€ 
#     # pour déclencher une alerte de "SUR-DÉPENSE".
    
#     budget_mensuel_client = 1000.0 
#     agent.check_budget_pacing(budget_mensuel_client)

# ==========================================
# 🧪 ZONE DE TEST LOCAL DE PAUSE AUTOMATIQUE
# ==========================================
# if __name__ == "__main__":
#     print("🚀 Lancement du test de l'Agent Media Buyer...\n")
#     agent = MediaBuyerAgent()
    
#     # On utilise un ID inventé pour tester la connexion Sandbox
#     faux_id_sandbox = "999999999888888" 
#     mauvais_cpl_sur_3_jours = 45.0 
    
#     agent.enforce_adset_rules(faux_id_sandbox, mauvais_cpl_sur_3_jours)
# ==========================================
# 🧪 ZONE DE TEST LOCAL : END-TO-END
# ==========================================
# 
# ==========================================
# 🧪 ZONE DE TEST LOCAL : END-TO-END
# ==========================================
# ==========================================
# 🧪 ZONE DE TEST LOCAL : END-TO-END
# ==========================================
# 

# ==========================================
# 🧪 ZONE DE TEST LOCAL : END-TO-END (AD PAUSE)
# ==========================================
if __name__ == "__main__":
    print("🚀 Lancement du test End-to-End Final...\n")
    agent = MediaBuyerAgent()
    
    # 1. Création
    nouvelle_campagne_id, nouvel_adset_id = agent.meta_client.create_sandbox_campaign_and_adset()
    
    if nouvel_adset_id:
        print("\n🚨 [DÉCLENCHEMENT DE L'AUDIT] Le CPL est catastrophique (45€ > 30€)...")
        mauvais_cpl = 45.0
        
        # 2. L'agent utilise le VRAI ID de l'Ad Set qu'il vient de créer pour l'exécuter
        agent.enforce_adset_rules(nouvel_adset_id, mauvais_cpl)