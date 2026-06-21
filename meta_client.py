import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
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

    def get_last_7_days_performance(self) -> dict:
        """
        Récupère les performances réelles des 7 derniers jours.

        Returns:
            dict: Données agrégées (spend, impressions, clicks, leads).
        """
        print("🔵 [META API] Appel API réel : Extraction des données J-7...")

        # 1. Calcul de la fenêtre de tir (Les 7 derniers jours)
        today = datetime.now()
        seven_days_ago = today - timedelta(days=7)

        time_range = {
            'since': seven_days_ago.strftime('%Y-%m-%d'),
            'until': today.strftime('%Y-%m-%d'),
        }

        # 2. Définition des paramètres de la requête
        fields = ['spend', 'impressions', 'clicks', 'actions']
        params = {
            'time_range': time_range,
            'level': 'account' # Récupère le résumé global du compte
        }

        try:
            # 3. L'appel réseau vers les serveurs de Facebook
            insights = self.account.get_insights(fields=fields, params=params)

            # Si le compte n'a pas diffusé de pubs ces 7 derniers jours
            if not insights:
                print("ℹ️ [META API] Aucune dépense enregistrée sur cette période.")
                return {"spend": 0.0, "impressions": 0, "clicks": 0, "leads": 0}

            # 4. Parsing (Analyse) des données retournées
            data = insights[0]
            spend = float(data.get('spend', 0.0))
            impressions = int(data.get('impressions', 0))
            clicks = int(data.get('clicks', 0))

            # Meta range les conversions (leads) dans un tableau complexe appelé "actions"
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
            # On retourne 0 pour éviter de faire planter l'agent
            return {"spend": 0.0, "impressions": 0, "clicks": 0, "leads": 0}
    def get_yesterdays_performance(self) -> dict:
        """
        Récupère les performances réelles de la journée d'hier uniquement.
        """
        print("🔵 [META API] Extraction des données de HIER...")

        # Calcul exact de la date d'hier
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
    
    def get_campaign_summary(self, campaign_id: str) -> dict:
        """
        Récupère les paramètres et les performances J-7 d'une campagne spécifique.
        (Version Mock sans carte bancaire pour valider la Phase A)
        """
        print(f"🔍 [META API] Interrogation de la campagne ID : {campaign_id}")

        # Simulation : Si l'ID correspond à notre fausse campagne "connue"
        if campaign_id == "123456789":
            return {
                "status": "ACTIVE",
                "daily_budget": 20.0,
                "spend": 135.50,
                "impressions": 12500,
                "clicks": 450,
                "leads": 12
            }
        else:
            # Si l'ID envoyé est inconnu
            return {
                "status": "NOT_FOUND",
                "daily_budget": 0.0,
                "spend": 0.0,
                "impressions": 0,
                "clicks": 0,
                "leads": 0
            }