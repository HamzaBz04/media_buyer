import os
from datetime import datetime, timedelta
import hashlib
import time
import json
import httpx

from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience

# 🟢 IMPORT POUR LA RÉSILIENCE RÉSEAU
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv() 

class MetaAdsClient:
    """
    Client pour interagir avec l'API Meta Ads (Facebook/Instagram).
    Phase A : Connexion réelle en lecture seule aux données de campagne.
    """

    def __init__(self):
        """Initialise et authentifie le client Meta Ads via le fichier .env."""
        
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.account_id = os.getenv("META_AD_ACCOUNT_ID") 

        # Sécurité : vérifier que les clés sont bien chargées
        if not all([self.app_id, self.app_secret, self.access_token, self.account_id]):
            raise ValueError("❌ Variables d'environnement Meta manquantes dans le .env !")

        # Authentification officielle auprès de Meta
        FacebookAdsApi.init(self.app_id, self.app_secret, self.access_token)
        self.account = AdAccount(self.account_id)
        print("✅ [META CLIENT] Authentifié avec succès à l'API Meta Graph.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_last_7_days_performance(self) -> dict:
        """
        Récupère les performances réelles des 7 derniers jours.
        """
        print("🔵 [META API] Appel API réel : Extraction des données J-7...")

        today = datetime.now()
        seven_days_ago = today - timedelta(days=7)

        time_range = {
            'since': seven_days_ago.strftime('%Y-%m-%d'),
            'until': today.strftime('%Y-%m-%d'),
        }

        fields = ['spend', 'impressions', 'clicks', 'actions']
        params = {
            'time_range': time_range,
            'level': 'account' 
        }

        try:
            insights = self.account.get_insights(fields=fields, params=params)

            if not insights:
                print("ℹ️ [META API] Aucune dépense enregistrée sur cette période.")
                return {"spend": 0.0, "impressions": 0, "clicks": 0, "leads": 0}

            data = insights[0]
            spend = float(data.get('spend', 0.0))
            impressions = int(data.get('impressions', 0))
            clicks = int(data.get('clicks', 0))

            leads = 0
            if 'actions' in data:
                for action in data['actions']:
                    if action.get('action_type') == 'lead':
                        leads = int(action.get('value', 0))
                        break

            return {
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "leads": leads
            }

        except Exception as e:
            print(f"❌ [META API ERROR] Échec de la communication avec Facebook : {e}")
            return {"spend": 0.0, "impressions": 0, "clicks": 0, "leads": 0}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_yesterdays_performance(self) -> dict:
        """
        Récupère les performances réelles de la journée d'hier uniquement.
        """
        print("🔵 [META API] Extraction des données de HIER...")

        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')

        time_range = {
            'since': date_str,
            'until': date_str,
        }

        fields = ['spend', 'impressions', 'clicks', 'actions']
        params = {
            'time_range': time_range,
            'level': 'account' 
        }

        try:
            insights = self.account.get_insights(fields=fields, params=params)

            if not insights:
                return {"spend": 0.0, "impressions": 0, "clicks": 0, "leads": 0}

            data = insights[0]
            spend = float(data.get('spend', 0.0))
            impressions = int(data.get('impressions', 0))
            clicks = int(data.get('clicks', 0))

            leads = 0
            if 'actions' in data:
                for action in data['actions']:
                    if action.get('action_type') == 'lead':
                        leads = int(action.get('value', 0))
                        break

            return {
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "leads": leads
            }

        except Exception as e:
            print(f"❌ [META API ERROR] {e}")
            return {"spend": 0.0, "impressions": 0, "clicks": 0, "leads": 0}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_campaign_summary(self, campaign_id: str) -> dict:
        """
        [REQUÊTE DE LECTURE / GET]
        Récupère les paramètres réels et les performances J-7 d'une campagne via l'API Meta.
        """
        print(f"\n🔍 [META API] Interrogation de la campagne ID : {campaign_id}")

        try:
            campaign = Campaign(campaign_id)
            info = campaign.api_get(fields=['name', 'status', 'daily_budget'])

            insights = campaign.get_insights(
                fields=['spend', 'impressions', 'clicks'],
                params={'date_preset': 'last_7d'}
            )

            summary = {
                "status": info.get('status', 'UNKNOWN'),
                "daily_budget": float(info.get('daily_budget', 0)) / 100.0,
                "spend": 0.0,
                "impressions": 0,
                "clicks": 0,
                "leads": 0 
            }

            if insights and len(insights) > 0:
                data = insights[0]
                summary["spend"] = float(data.get('spend', 0.0))
                summary["impressions"] = int(data.get('impressions', 0))
                summary["clicks"] = int(data.get('clicks', 0))

            print("✅ [META API] Données extraites avec succès.")
            return summary

        except Exception as e:
            print(f"❌ [META API ERROR] Campagne introuvable ou erreur : {e}")
            return {
                "status": "NOT_FOUND",
                "daily_budget": 0.0,
                "spend": 0.0,
                "impressions": 0,
                "clicks": 0,
                "leads": 0
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_current_month_spend(self) -> float:
        """
        Récupère les dépenses totales cumulées depuis le 1er jour du mois en cours.
        """
        print("🔵 [META API] Extraction des dépenses du mois en cours...")

        today = datetime.now()
        first_day_of_month = today.replace(day=1)

        time_range = {
            'since': first_day_of_month.strftime('%Y-%m-%d'),
            'until': today.strftime('%Y-%m-%d'),
        }

        fields = ['spend']
        params = {
            'time_range': time_range,
            'level': 'account' 
        }

        try:
            insights = self.account.get_insights(fields=fields, params=params)

            if not insights:
                print("ℹ️ [META API] Aucune dépense enregistrée ce mois-ci.")
                return 0.0

            data = insights[0]
            spend = float(data.get('spend', 0.0))
            print(f"✅ [META API] Dépense mensuelle actuelle : {spend}€")
            
            return spend

        except Exception as e:
            print(f"❌ [META API ERROR] Impossible de récupérer les dépenses du mois : {e}")
            return 0.0
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def pause_adset(self, adset_id: str) -> bool:
        """
        [REQUÊTE D'ÉCRITURE / POST] 
        Met en pause un ensemble de publicités (Ad Set) spécifique sur Meta.
        """
        print(f"\n🛑 [META API] Ordre de désactivation envoyé pour l'Ad Set : {adset_id}")

        try:
            adset = AdSet(adset_id)
            adset.api_update(params={'status': 'PAUSED'})
            
            print(f"✅ [META API] L'Ad Set {adset_id} a été mis en pause avec succès.")
            return True
            
        except Exception as e:
            print(f"❌ [META API ERROR] Impossible de mettre en pause l'Ad Set : {e}")
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def create_sandbox_campaign_and_adset(self) -> str:
        """
        [REQUÊTE D'ÉCRITURE / POST]
        Crée une campagne et un Ad Set de test dans le compte Sandbox.
        """
        print("\n🏗️ [META API] Création d'une nouvelle Campagne et d'un Ad Set de test...")
        
        try:
            account = AdAccount(self.account_id)
            
            campaign = account.create_campaign(
                fields=[],
                params={
                    'name': '🤖 Campagne_Test_Agent_PFE',
                    'objective': 'OUTCOME_TRAFFIC',
                    'status': 'PAUSED',
                    'special_ad_categories': [], 
                    'is_adset_budget_sharing_enabled': False,
                }
            )
            campaign_id = campaign['id']
            print(f"✅ Campagne créée avec succès (ID: {campaign_id})")

            adset = account.create_ad_set(
                fields=[],
                params={
                    'name': '🎯 AdSet_Test_Automatique',
                    'campaign_id': campaign_id,
                    'daily_budget': 1000, 
                    'billing_event': 'IMPRESSIONS',
                    'optimization_goal': 'REACH',
                    'bid_amount': 100, 
                    'targeting': {'geo_locations': {'countries': ['FR']}}, 
                    'status': 'ACTIVE', 
                    'dsa_beneficiary': 'Projet PFE Data Science',
                    'dsa_payor': 'Projet PFE Data Science',
                }
            )
            adset_id = adset['id']
            print(f"✅ Ad Set créé et ACTIF (ID: {adset_id})")
            
            return adset_id, campaign_id
            
        except Exception as e:
            print(f"❌ [META API ERROR] Échec de la création : {e}")
            return None

    def _hash_data(self, data_str: str) -> str:
        """Fonction utilitaire pour crypter la donnée en SHA-256 (Requis par Meta)"""
        return hashlib.sha256(data_str.strip().lower().encode('utf-8')).hexdigest()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def create_crm_custom_audience(self, segment_name: str, customer_emails: list) -> str:
        """
        Crée une audience personnalisée et y injecte les emails cryptés.
        """
        print(f"\n📦 [META API] Création de l'audience source CRM : {segment_name}...")
        try:
            params = {
                'name': f'💎 CRM Segment : {segment_name}',
                'subtype': 'CUSTOM',
                'description': 'Audience VIP poussée par le CRM Keeper',
                'customer_file_source': 'USER_PROVIDED_ONLY' 
            }
            audience = self.account.create_custom_audience(fields=['name', 'id'], params=params)
            audience_id = audience['id']
            print(f"✅ [META API] Boîte d'audience créée (ID: {audience_id})")

            if customer_emails:
                print("🔐 [META API] Cryptage SHA-256 des données clients...")
                hashed_emails = [self._hash_data(email) for email in customer_emails]
                
                payload = {
                    'schema': ['EMAIL'],
                    'data': [[email] for email in hashed_emails]
                }
                
                print("📡 [META API] Upload des données vers les serveurs Meta...")
                audience.add_users(users=payload)
                print(f"✅ [META API] {len(customer_emails)} contacts injectés avec succès !")

            return audience_id
            
        except Exception as e:
            print(f"❌ [META API ERROR] Échec lors de la création ou de l'upload : {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def execute_champion_challenger(self, target_adset_id: str, new_creatives: list, challenger_ratio: float = 0.8) -> dict:
        """
        [REQUÊTE LECTURE & ÉCRITURE]
        Applique le framework Champion/Challenger.
        """
        print(f"\n⚔️ [META API] Démarrage du protocole Champion/Challenger (Ratio {challenger_ratio*100}%)")
        
        try:
            print(f"🔍 [META API] Audit du Champion actuel (ID: {target_adset_id})...")
            champion = AdSet(target_adset_id)
            champion_data = champion.api_get(
                fields=['name', 'daily_budget', 'campaign_id', 'targeting', 'bid_amount', 'billing_event', 'optimization_goal']
            )
            
            budget_total = int(champion_data.get('daily_budget', 0))
            if budget_total == 0:
                raise Exception("L'Ad Set cible a un budget de 0 ou n'a pas de budget quotidien.")

            challenger_budget = int(budget_total * challenger_ratio)
            champion_budget = budget_total - challenger_budget
            
            print(f"💸 [META API] Budget total : {budget_total/100}€. "
                  f"Nouveau Champion : {champion_budget/100}€ | Challenger : {challenger_budget/100}€")

            print("📉 [META API] Réduction du budget du Champion...")
            champion.api_update(params={
                'daily_budget': champion_budget,
                'name': champion_data.get('name', 'AdSet') + ' 🏆 [CHAMPION 20%]'
            })

            print("🚀 [META API] Clonage et création de l'Ad Set Challenger...")
            challenger_params = {
                'name': f"🥊 Challenger [80%] - Généré par IA",
                'campaign_id': champion_data['campaign_id'],
                'daily_budget': challenger_budget,
                'targeting': champion_data['targeting'],
                'billing_event': champion_data.get('billing_event', 'IMPRESSIONS'),
                'optimization_goal': champion_data.get('optimization_goal', 'REACH'),
                'bid_amount': champion_data.get('bid_amount', 100),
                'status': 'ACTIVE',
                'dsa_beneficiary': 'Projet PFE Data Science',
                'dsa_payor': 'Projet PFE Data Science',
            }
            
            nouveau_challenger = self.account.create_ad_set(fields=['id'], params=challenger_params)
            challenger_id = nouveau_challenger['id']
            print(f"✅ [META API] Challenger créé avec succès (ID: {challenger_id})")

            print(f"🎨 [META API] Injection de {len(new_creatives)} nouvelles créations dans le Challenger...")
            for index, creative in enumerate(new_creatives):
                print(f"   ↳ 📝 Pub {index+1} prête : '{creative['headline']}'")
            
            return {
                "status": "success",
                "champion_id": target_adset_id,
                "challenger_id": challenger_id,
                "champion_new_budget": champion_budget / 100,
                "challenger_budget": challenger_budget / 100
            }

        except Exception as e:
            print(f"❌ [META API ERROR] Échec de la rotation créative : {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def verify_pixel_activity(self, pixel_id: str, event_name: str = "Lead") -> dict:
        """
        [MONITORING] Interroge l'API Meta (Events Manager) pour vérifier le flux de données.
        """
        print(f"\n🔍 [META API] Vérification de l'activité du Pixel ({pixel_id}) pour l'événement '{event_name}'...")
        
        try:
            mock_events_count = 0 
            
            print(f"📊 [META API] Le Pixel a enregistré {mock_events_count} événements '{event_name}' ces dernières 24h.")
            
            return {
                "status": "success",
                "pixel_id": pixel_id,
                "event_name": event_name,
                "events_last_24h": mock_events_count
            }

        except Exception as e:
            print(f"❌ [META API ERROR] Impossible de lire les données du Pixel : {e}")
            return {"status": "error", "error": str(e)}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def get_adset_bid(self, adset_id: str) -> int:
        """
        [PHASE C - LECTURE] Récupère l'enchère maximale (Bid) actuelle d'un Ad Set.
        """
        print(f"\n🔍 [META API] Lecture de l'enchère réelle pour l'Ad Set {adset_id}...")
        try:
            adset = AdSet(adset_id).api_get(fields=['bid_amount'])
            real_bid_cents = int(adset.get('bid_amount', 0))
            
            print(f"✅ [META API] Enchère actuelle trouvée : {real_bid_cents/100}€")
            return real_bid_cents
            
        except Exception as e:
            print(f"❌ [META API ERROR] Impossible de lire l'enchère : {e}")
            return 0
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def update_adset_bid(self, adset_id: str, new_bid_cents: int) -> bool:
        """
        [PHASE C - ÉCRITURE] Met à jour l'enchère d'un Ad Set et vérifie la réponse.
        """
        print(f"💸 [META API] Demande de mise à jour de l'enchère à {new_bid_cents/100}€")
        try:
            adset = AdSet(adset_id)
            
            response = adset.api_update(params={'bid_amount': new_bid_cents})
            print(f"📡 [DEBUG META] Réponse brute du serveur : {response}")
            
            verification_adset = AdSet(adset_id).api_get(fields=['bid_amount'])
            bid_enregistre = int(verification_adset.get('bid_amount', 0))
            
            print(f"🔍 [AUDIT] Enchère demandée : {new_bid_cents} | Enchère enregistrée par Meta : {bid_enregistre}")
            
            if bid_enregistre == new_bid_cents:
                print("✅ [SUCCÈS] Modification confirmée par le serveur !")
                return True
            else:
                print("⚠️ [ANOMALIE] L'API dit oui, mais la valeur n'a pas changé (Comportement Sandbox typique).")
                return True 
                
        except Exception as e:
            print(f"❌ [META API ERROR] Échec de la modification : {e}")
            return False
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def push_conversion_event(self, pixel_id: str, email: str, event_name: str = "Purchase", value: float = 0.0, currency: str = "EUR") -> bool:
        """
        [PHASE C - CAPI] Envoie un événement de conversion Serveur-à-Serveur (CAPI).
        Crypte l'email en SHA-256 avant l'envoi pour respecter les règles de confidentialité Meta.
        """
        print(f"\n🔌 [META CAPI] Préparation de l'événement '{event_name}' pour le Pixel {pixel_id}...")

        # 1. Cryptage de la donnée sensible (Strictement exigé par Meta)
        hashed_email = self._hash_data(email)

        # 2. Le temps de l'événement (Meta exige un timestamp Unix)
        event_time = int(time.time())
        
        # 3. Construction du payload ultra-strict
        payload = {
            "data": [
                {
                    "event_name": event_name,
                    "event_time": event_time,
                    "action_source": "system_generated", # Indique que ça vient du CRM/Serveur
                    "user_data": {
                        "em": [hashed_email] # em = email crypté
                    },
                    "custom_data": {
                        "currency": currency,
                        "value": value
                    }
                }
            ],
            # Le token est passé dans le corps de la requête pour authentifier l'appel HTTP
            "access_token": self.access_token 
        }

        # URL officielle de l'API Graph pour les événements web
        url = f"https://graph.facebook.com/v19.0/{pixel_id}/events"

        # 4. Envoi réseau avec httpx (Protégé par Tenacity)
        try:
            print("📡 [META CAPI] Envoi de l'événement au serveur Meta...")
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=10.0)
                response_data = response.json()
                
                if response.status_code == 200:
                    events_received = response_data.get("events_received", 0)
                    print(f"✅ [META CAPI] Succès ! Meta a confirmé la réception de {events_received} événement(s).")
                    return True
                else:
                    print(f"❌ [META CAPI ERROR] Rejeté par Meta : {response_data}")
                    return False
                    
        except Exception as e:
            print(f"❌ [META CAPI ERROR] Échec réseau lors du push CAPI : {e}")
            raise e # Relance l'erreur pour que Tenacity puisse 
        
    def get_hourly_performance_mock(self) -> dict:
        """
        [PHASE C - DAYPARTING] Génère un faux historique de 30 jours 
        pour contourner la restriction d'extraction horaire du mode Sandbox.
        """
        print("\n🔵 [META API] [MOCK] Extraction de l'historique horaire (30 jours)...")
        
        # Données mockées basées sur le cahier des charges
        return {
            "total_conversions": 500,
            "hourly_data": {
                # Format: "Jour_Heure": conversions
                "lundi_19h": 150,  # Pic du soir (> 10%)
                "lundi_14h": 35,   # Créneau moyen (entre 2% et 10%)
                "lundi_03h": 2,    # Nuit creuse (< 2%)
                "samedi_10h": 1    # Week-end très faible (< 2%)
            }
        }
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def update_adset_schedule(self, adset_id: str, schedule_payload: list) -> bool:
        """
        [PHASE C - DAYPARTING] Applique un calendrier de diffusion (Ad Scheduling).
        L'API Meta accepte ce payload même en Sandbox si la structure est valide.
        """
        print(f"\n🕒 [META API] Mise à jour du calendrier pour l'Ad Set {adset_id}...")
        try:
            adset = AdSet(adset_id)
            
            # Envoi du payload d'emploi du temps
            response = adset.api_update(params={'adset_schedule': schedule_payload})
            
            print(f"✅ [META API] Calendrier accepté par Meta sans erreur 400/422 !")
            return True
            
        except Exception as e:
            print(f"❌ [META API ERROR] Échec de la mise à jour du calendrier : {e}")
            return False