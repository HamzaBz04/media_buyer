import os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import calendar # <-- NOUVEAU
from datetime import datetime
from meta_client import MetaAdsClient
from langfuse import get_client, observe, propagate_attributes
import json

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
        
    # Le décorateur Tenacity : essaie 3 fois maximum, en attendant 2s, puis 4s, puis 8s entre chaque échec.
    @retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
    )
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
        
       # Remplacement de requests par httpx (Client synchrone pour compatibilité avec ton CRON)
        try:
         with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

         print("✅ [TELEGRAM] Message sent successfully!")

        except httpx.HTTPStatusError as e:
         print(f"❌ [TELEGRAM ERROR] HTTP {e.response.status_code}: {e.response.text}")

        except httpx.RequestError as e:
         print(f"❌ [TELEGRAM ERROR] Request failed: {e}")

        except Exception as e:
         print(f"❌ [TELEGRAM ERROR] Unexpected error: {e}")

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
        Trace l'audit dans Langfuse selon les normes strictes de l'API_SPEC.
        """
        print("\n📊 [MEDIA BUYER] Analyse du Pacing Budgétaire...")

        today = datetime.now()
        _, days_in_month = calendar.monthrange(today.year, today.month) 
        time_elapsed_pct = today.day / days_in_month
        
        # Appel réseau protégé par Tenacity
        current_spend = self.meta_client.get_current_month_spend()
        
        # Sécurité : Éviter la division par zéro
        if monthly_budget <= 0:
            print("⚠️ [PACING ERROR] Le budget mensuel doit être supérieur à 0.")
            return

        spend_pct = current_spend / monthly_budget
        variance = spend_pct - time_elapsed_pct

        # 1. Variables pour Langfuse (Conformité XAI)
        decision_taken = "no_alert"
        status_flag = "ON_TRACK"
        reason = f"Rythme normal. Dépense actuelle ({current_spend}€ / {monthly_budget}€) avec un écart de {variance:+.1%} (dans la limite saine des 15%)."

        if abs(variance) > 0.15:
            decision_taken = "send_alert"
            status_flag = "OVER_SPEND" if variance > 0 else "UNDER_SPEND"
            
            # Message humain clair pour le Dashboard
            etat = "SUR-DÉPENSE" if variance > 0 else "SOUS-DÉPENSE"
            reason = f"Anomalie de pacing détectée ({etat}). L'écart est de {variance:+.1%} (dépassement du seuil de tolérance de 15%). Alerte envoyée à l'opérateur."
            
            alert_text = (
                f"🚨 <b>ALERTE PACING BUDGÉTAIRE</b> 🚨\n\n"
                f"📊 <b>État :</b> {etat}\n"
                f"💰 <b>Dépense :</b> {current_spend}€ / {monthly_budget}€\n"
                f"⏱️ <b>Temps écoulé :</b> {time_elapsed_pct:.1%}\n"
                f"💸 <b>Budget consommé :</b> {spend_pct:.1%}\n"
                f"⚠️ <b>Écart :</b> {variance:+.1%}"
            )
            self.send_telegram_message(alert_text)
            print(f"⚠️ [ALERTE] Écart de pacing critique !")
        else:
            print("✅ [PACING OK] Le rythme de dépense est normal.")

        # 2. 🟢 ENREGISTREMENT DANS LANGFUSE (100% Conforme API_SPEC)
        with propagate_attributes(
            tags=["media_buyer", "monitoring", "pacing"], 
            metadata={
                "client_id": client_id,
                "campaign_id": "account_level", # L'audit concerne le compte entier
                "decision_reason": reason,
                "metrics": {
                    "monthly_budget": monthly_budget,
                    "current_spend": current_spend,
                    "variance": variance,
                    "status_flag": status_flag
                }
            }
        ):
            # Événement tracé pour remonter directement dans l'écran "Campaigns Overview"
             langfuse.start_observation(
                as_type="event",
                name="pacing_audit",
                output=f"Audit de pacing terminé. Statut : {status_flag}"
            )
            
        return {"status": decision_taken, "variance": variance}
    
   
    @observe(name="[Decision MB] Budget Pacing & Ad Pause")
    def enforce_adset_rules(self, adset_id: str, cpl_3_days: float, client_id: str = "global"):
        """
        Vérifie si l'Ad Set respecte la règle des 3 jours. 
        Trace la décision dans Langfuse selon les normes strictes de l'API_SPEC.
        """
        print(f"\n🛡️ [MEDIA BUYER] Vérification des règles pour l'Ad Set {adset_id}...")

        max_allowed_cpl = self.target_cpl * 2 
        
        # 1. Variables pour Langfuse (Conformité XAI)
        decision_taken = "no_action"
        old_status = "ACTIVE"
        new_status = "ACTIVE"
        reason = f"Le CPL sur 3 jours ({cpl_3_days}€) est sain (inférieur au plafond de {max_allowed_cpl}€). L'Ad Set reste actif."

        if cpl_3_days > max_allowed_cpl:
            print(f"⚠️ [DÉCISION] CPL critique. Action requise : PAUSE.")
            
            # Action sur Meta
            success = self.meta_client.pause_adset(adset_id)
            
            if success:
                decision_taken = "pause"
                new_status = "PAUSED"
                reason = f"CPL critique de {cpl_3_days}€ détecté (dépassement du plafond de {max_allowed_cpl}€ sur 3 jours). Coupure d'urgence de l'Ad Set pour protéger le budget."
                
                alert_text = (
                    f"🛑 <b>ACTION AUTOMATIQUE : AD SET COUPÉ</b> 🛑\n\n"
                    f"🆔 <b>Ad Set ID :</b> <code>{adset_id}</code>\n"
                    f"📉 <b>Raison :</b> Sous-performance sévère ({cpl_3_days}€ > {max_allowed_cpl}€).\n"
                )
                self.send_telegram_message(alert_text)
            else:
                decision_taken = "api_error"
                reason = f"Échec API lors de la tentative de mise en pause de l'Ad Set {adset_id} (CPL: {cpl_3_days}€)."
        else:
            print("✅ [DÉCISION] L'Ad Set est rentable. On le laisse tourner.")

        # 2. 🟢 ENREGISTREMENT DANS LANGFUSE (100% Conforme API_SPEC)
        with propagate_attributes(
            tags=["media_buyer", "autonomous_action", "pause"], # "pause" est filtré par le front-end
            metadata={
                "client_id": client_id,
                "campaign_id": adset_id, # L'ID cible pour l'interface
                "decision_reason": reason,
                "metrics": {
                    "cpl_observed": cpl_3_days,
                    "cpl_threshold": max_allowed_cpl,
                    "old_status": old_status, # État AVANT (pour le bouton Revert)
                    "new_status": new_status  # État APRÈS
                }
            }
        ):
            # Le front-end écoute l'événement "autonomous_action"
             langfuse.start_observation(
                as_type="event",
                name="autonomous_action",
                output=f"Action exécutée : {decision_taken}"
            )

        return {"status": decision_taken, "reason": reason}

   
    @observe(name="[Monitoring MB] Conversion Tracking Watchdog")
    def verify_conversions_watchdog(self, pixel_id: str = "123456789_MOCK_PIXEL", client_id: str = "global"):
        """
        Vérifie le tracking. Si aucun événement n'est reçu, déclenche l'alerte Telegram.
        Trace l'état de santé dans Langfuse (utilisé par le Dashboard Frontend pour le statut S1).
        """
        print(f"\n🩺 [MEDIA BUYER] Démarrage du Watchdog de tracking (Pixel: {pixel_id})...")
        
        pixel_data = self.meta_client.verify_pixel_activity(pixel_id=pixel_id, event_name="Lead")
        
        # Variables par défaut pour Langfuse
        decision_taken = "no_alert"
        health_status = "unknown"
        events_count = 0
        reason = "Impossible de vérifier le statut du Pixel (Erreur API)."

        if pixel_data.get("status") == "success":
            events_count = pixel_data.get("events_last_24h", 0)
            
            if events_count == 0:
                decision_taken = "alert_sent"
                health_status = "stopped"  # Le mot-clé exact attendu par l'API_SPEC pour l'alerte S1
                reason = f"Anomalie critique (S1) : 0 événement 'Lead' reçu sur le Pixel {pixel_id} depuis 24h. Le tracking est coupé."
                
                print("🚨 [ALERTE] Anomalie de tracking détectée. Préparation du message Telegram...")
                
                alert_text = (
                    f"🚨 <b>ALERTE CRITIQUE - TRACKING</b> 🚨\n\n"
                    f"Le système a détecté une anomalie majeure de remontée de données :\n"
                    f"🔹 <b>Pixel ID :</b> <code>{pixel_id}</code>\n"
                    f"🔹 <b>Problème :</b> AUCUN événement 'Lead' reçu depuis 24h.\n\n"
                    f"⚠️ <i>Action immédiate : Veuillez vérifier l'intégration API ou Google Tag Manager.</i>"
                )
                self.send_telegram_message(alert_text)
            else:
                health_status = "healthy"
                reason = f"Le tracking fonctionne correctement ({events_count} conversions sur 24h)."
                print(f"✅ [WATCHDOG] {reason}")

        # 🟢 ENREGISTREMENT DANS LANGFUSE (100% Conforme API_SPEC)
        with propagate_attributes(
            tags=["media_buyer", "monitoring", "conversion_tracking"],
            metadata={
                "client_id": client_id,
                "pixel_id": pixel_id,
                "health_status": health_status, # L'indicateur clé pour l'écran "Integrations"
                "events_count": events_count,
                "decision_reason": reason
            }
        ):
            # Envoi d'un événement discret pour le tableau de bord
             langfuse.start_observation(
                as_type="event",
                name="pixel_health_check",
                output=f"Vérification de santé du Pixel : {health_status}"
            )
            
        return {"health_status": health_status, "events_last_24h": events_count}
    # fonction pour envoyer un résumé hebdomadaire à l'analyste
    # Le décorateur Tenacity : essaie 3 fois maximum, en attendant 2s, puis 4s, puis 8s entre chaque échec.
    @retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
    )
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
        ANALYST_WEBHOOK_URL = os.getenv(
            "ANALYST_WEBHOOK_URL",
            "http://127.0.0.1:8005/analyst/receive-weekly-data"
        )
        
        try:
            # 🛑 Commenté pour l'instant car ton Analyste n'est pas encore en ligne !
            # with httpx.Client(timeout=10.0) as client:
            #     response = client.post(
            #         ANALYST_WEBHOOK_URL,
            #         json=payload
            #     )
            #     response.raise_for_status()
            
            print(f"✅ [INTER-AGENT] Données JSON prêtes à être expédiées :")
           
            print(json.dumps(payload, indent=4))
        except httpx.HTTPStatusError as e:
            print(
                f"❌ Analyst returned HTTP {e.response.status_code}: "
                f"{e.response.text}"
            )

        except httpx.RequestError as e:
            print(f"❌ Impossible de joindre l'Analyste : {e}")

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
    
    # fonction pour ajuster automatiquement l'enchère d'un Ad Set en fonction du ROAS
    @observe(name="[Phase C MB] Automatic Bid Adjustment")
    def adjust_bid_based_on_roas(self, adset_id: str, current_roas: float, target_roas: float = 2.0, client_id: str = "global"):
        """
        Ajuste l'enchère de +10% si le ROAS dépasse la cible, ou de -10% s'il est en dessous.
        Trace le raisonnement exact dans Langfuse selon les normes strictes de l'API_SPEC.
        """
        print(f"\n⚖️ [MEDIA BUYER] Analyse du ROAS pour l'Ad Set {adset_id}...")
        
        # 1. Lecture de l'enchère actuelle
        current_bid_cents = self.meta_client.get_adset_bid(adset_id)
        if current_bid_cents == 0:
            print("⚠️ Impossible de faire l'ajustement : Enchère introuvable.")
            return

        # 2. Variables par défaut pour l'explicabilité (XAI)
        decision_taken = "no_action"
        reason = f"Le ROAS actuel ({current_roas}) est aligné avec la cible ({target_roas}). Maintien de l'enchère à {current_bid_cents/100}€."
        new_bid_cents = current_bid_cents

        # 3. La logique mathématique de la Phase C
        if current_roas > target_roas:
            new_bid_cents = int(current_bid_cents * 1.10) 
            decision_taken = "increase_bid"
            reason = f"ROAS performant ({current_roas} > {target_roas}). Augmentation de l'enchère de 10% (de {current_bid_cents/100}€ à {new_bid_cents/100}€) pour maximiser l'acquisition."
            
        elif current_roas < target_roas:
            new_bid_cents = int(current_bid_cents * 0.90) 
            decision_taken = "decrease_bid"
            reason = f"ROAS sous-performant ({current_roas} < {target_roas}). Réduction de l'enchère de 10% (de {current_bid_cents/100}€ à {new_bid_cents/100}€) pour protéger le budget."

        # 4. Action API
        if decision_taken != "no_action":
            success = self.meta_client.update_adset_bid(adset_id, new_bid_cents)
            if not success:
                decision_taken = "api_error"
                reason += " [ÉCHEC DE LA MODIFICATION SUR L'API META]"
                
            self.send_telegram_message(
                f"📈 <b>AJUSTEMENT D'ENCHÈRE (Phase C)</b> 📉\n\n"
                f"🆔 <b>Ad Set :</b> <code>{adset_id}</code>\n"
                f"🎯 <b>ROAS Cible :</b> {target_roas} | <b>Actuel :</b> {current_roas}\n\n"
                f"🤖 <b>Action :</b> {decision_taken}\n"
                f"💸 <b>Nouvelle enchère :</b> {new_bid_cents/100}€"
            )

        # 5. 🟢 ENREGISTREMENT LANGFUSE (100% Conforme API_SPEC)
        with propagate_attributes(
            tags=["media_buyer", "phase_c", "bid_adjustment"],
            metadata={
                "client_id": client_id,
                "campaign_id": adset_id, # L'API front-end utilise ce champ pour filtrer
                "decision_reason": reason,
                "metrics": {
                    "current_roas": current_roas,
                    "target_roas": target_roas,
                    "old_bid_eur": current_bid_cents / 100,  # L'état AVANT pour le bouton Revert
                    "new_bid_eur": new_bid_cents / 100       # L'état APRÈS pour le bouton Revert
                }
            }
        ):
            # On force un log_event pour que le Dashboard frontend détecte immédiatement l'action autonome
            langfuse.start_observation(
              as_type="event",
              name="autonomous_action",
              metadata={"output": f"Action exécutée : {decision_taken}"}
)
            print(f"✅ [DÉCISION FINALE] {reason}")
            
        return {"status": decision_taken, "new_bid": new_bid_cents / 100}
    
    @observe(name="[Phase C MB] Dayparting Optimization")
    def optimize_dayparting(self, adset_id: str, client_id: str = "global"):
        """
        [PHASE C] Analyse les heures de conversion et ajuste le calendrier de diffusion.
        Implémente la Validation 2 du cahier des charges.
        """
        print(f"\n🕒 [MEDIA BUYER] Analyse Dayparting pour l'Ad Set {adset_id}...")

        # 1. Récupération de l'historique (Mock pour contourner la limite Sandbox)
        historique = self.meta_client.get_hourly_performance_mock()
        total_conv = historique["total_conversions"]
        hourly_data = historique["hourly_data"]

        # 2. Logique de décision mathématique (Les seuils)
        schedule_payload = []
        audit_reasons = []

        for creneau, conversions in hourly_data.items():
            pourcentage = (conversions / total_conv) * 100

            if pourcentage > 10.0:
                # Cas 1 : Créneau fort (> 10%) -> Maintien Actif
                # (L'API Meta n'accepte plus 'bid_adjustment' ici)
                schedule_payload.append({
                    "start_minute": 1140, # 19h (19 * 60)
                    "end_minute": 1200,   # 20h
                    "days": [1]           # 1 = Lundi
                })
                audit_reasons.append(f"[{creneau}] Fort ({pourcentage:.1%} > 10%) -> Maintien actif")

            elif pourcentage < 2.0:
                # Cas 2 : Créneau faible (< 2%) -> Pause 
                # (En l'excluant du payload, Meta coupe la diffusion)
                audit_reasons.append(f"[{creneau}] Faible ({pourcentage:.1%} < 2%) -> Mise en pause")

            else:
                # Cas 3 : Créneau moyen (2% - 10%) -> Maintien Actif
                schedule_payload.append({
                    "start_minute": 840, # 14h (14 * 60)
                    "end_minute": 900,   # 15h
                    "days": [1]
                })
                audit_reasons.append(f"[{creneau}] Moyen ({pourcentage:.1%}) -> Maintien actif")

        # 3. Action API
        decision_taken = "update_schedule"
        reason = " | ".join(audit_reasons)
        
        success = self.meta_client.update_adset_schedule(adset_id, schedule_payload)
        if not success:
            decision_taken = "api_error"
            reason = "[ÉCHEC API META] " + reason
        else:
            self.send_telegram_message(
                f"🕒 <b>DAYPARTING OPTIMISÉ (Phase C)</b> 🕒\n\n"
                f"🆔 <b>Ad Set :</b> <code>{adset_id}</code>\n"
                f"📊 <b>Analyse :</b> {len(hourly_data)} créneaux évalués.\n"
                f"✅ <i>Nouveau calendrier intelligent appliqué avec succès sur Meta.</i>"
            )

        # 4. 🟢 ENREGISTREMENT LANGFUSE (Conforme SDK v4)
       
        
        with propagate_attributes(
            tags=["media_buyer", "autonomous_action", "daypart"],
            metadata={
                "client_id": client_id,
                "campaign_id": adset_id,
                "decision_reason": f"Optimisation horaires. Résultat : {reason}"[:195], # Coupe à 195 caractères maximum
                "action_taken": decision_taken,
                "metrics": {
                    "total_conversions_analyzed": total_conv,
                    "old_schedule": "24/7_DEFAULT", 
                    "new_schedule": schedule_payload 
                }
            }
        ):
            langfuse.start_observation(
                as_type="event",
                name="dayparting_audit",
                output=f"Calendrier mis à jour avec {len(schedule_payload)} créneaux actifs."
            )

        print(f"✅ [DÉCISION FINALE DAYPARTING] {reason}")
        return {"status": decision_taken, "schedule": schedule_payload}





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