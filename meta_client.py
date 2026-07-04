import os
from datetime import datetime, timedelta
import hashlib # 🟢 NOUVEAU (Pour crypter les emails)

from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.customaudience import CustomAudience
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
        [REQUÊTE DE LECTURE / GET]
        Récupère les paramètres réels et les performances J-7 d'une campagne via l'API Meta.
        """
        print(f"\n🔍 [META API] Interrogation de la campagne ID : {campaign_id}")

        try:
            from facebook_business.adobjects.campaign import Campaign
            campaign = Campaign(campaign_id)

            # 1. Lecture des informations de base
            # L'API Meta va chercher le statut actuel de la campagne
            info = campaign.api_get(fields=['name', 'status', 'daily_budget'])

            # 2. Lecture des performances (Insights) sur les 7 derniers jours
            insights = campaign.get_insights(
                fields=['spend', 'impressions', 'clicks'],
                params={'date_preset': 'last_7d'}
            )

            # 3. Construction du dictionnaire de réponse (Format attendu par ton agent)
            summary = {
                "status": info.get('status', 'UNKNOWN'),
                # Meta renvoie souvent le budget en centimes, on divise par 100
                "daily_budget": float(info.get('daily_budget', 0)) / 100.0,
                "spend": 0.0,
                "impressions": 0,
                "clicks": 0,
                "leads": 0 
            }

            # Si la campagne a généré des statistiques (Insights non vides)
            if insights and len(insights) > 0:
                data = insights[0]
                summary["spend"] = float(data.get('spend', 0.0))
                summary["impressions"] = int(data.get('impressions', 0))
                summary["clicks"] = int(data.get('clicks', 0))

            print("✅ [META API] Données extraites avec succès.")
            return summary

        except Exception as e:
            # Si l'ID est faux ou introuvable, l'API génère une erreur.
            # On la capture silencieusement et on renvoie le statut NOT_FOUND à l'agent.
            print(f"❌ [META API ERROR] Campagne introuvable ou erreur : {e}")
            return {
                "status": "NOT_FOUND",
                "daily_budget": 0.0,
                "spend": 0.0,
                "impressions": 0,
                "clicks": 0,
                "leads": 0
            }
    def get_current_month_spend(self) -> float:
        """
        Récupère les dépenses totales cumulées depuis le 1er jour du mois en cours.
        Nécessaire pour le calcul du Budget Pacing (Phase B).
        """
        print("🔵 [META API] Extraction des dépenses du mois en cours...")

        # 1. Calcul dynamique du premier jour du mois
        today = datetime.now()
        first_day_of_month = today.replace(day=1)

        time_range = {
            'since': first_day_of_month.strftime('%Y-%m-%d'),
            'until': today.strftime('%Y-%m-%d'),
        }

        # Nous n'avons besoin que de la dépense ('spend') pour cette fonctionnalité
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
    
    def pause_adset(self, adset_id: str) -> bool:
        """
        [REQUÊTE D'ÉCRITURE / POST] 
        Met en pause un ensemble de publicités (Ad Set) spécifique sur Meta.
        """
        print(f"\n🛑 [META API] Ordre de désactivation envoyé pour l'Ad Set : {adset_id}")

        # Vraie logique API Sandbox / Production
        try:
           
            adset = AdSet(adset_id)
            
            # C'est cette ligne exacte qui modifie la base de données de Facebook
            adset.api_update(params={'status': 'PAUSED'})
            
            print(f"✅ [META API] L'Ad Set {adset_id} a été mis en pause avec succès.")
            return True
            
        except Exception as e:
            print(f"❌ [META API ERROR] Impossible de mettre en pause l'Ad Set : {e}")
            return False

    def create_sandbox_campaign_and_adset(self) -> str:
        """
        [REQUÊTE D'ÉCRITURE / POST]
        Crée une campagne et un Ad Set de test dans le compte Sandbox.
        Retourne l'ID du nouvel Ad Set créé.
        """
        print("\n🏗️ [META API] Création d'une nouvelle Campagne et d'un Ad Set de test...")
        
        try:
            account_id = os.getenv("META_AD_ACCOUNT_ID")
            account = AdAccount(account_id)
            
            # 1. Création de la Campagne (Dossier principal)
            campaign = account.create_campaign(
                fields=[],
                params={
                    'name': '🤖 Campagne_Test_Agent_PFE',
                    'objective': 'OUTCOME_TRAFFIC',
                    'status': 'PAUSED',
                    'special_ad_categories': [], # Requis par la loi Meta
                    'is_adset_budget_sharing_enabled': False,
                }
            )
            campaign_id = campaign['id']
            print(f"✅ Campagne créée avec succès (ID: {campaign_id})")

            # 2. Création de l'Ad Set (La cible)
            adset = account.create_ad_set(
                fields=[],
                params={
                    'name': '🎯 AdSet_Test_Automatique',
                    'campaign_id': campaign_id,
                    'daily_budget': 1000, # Budget en centimes (1000 = 10€)
                    'billing_event': 'IMPRESSIONS',
                    'optimization_goal': 'REACH',
                    'bid_amount': 100, # Enchère max (1€)
                    'targeting': {'geo_locations': {'countries': ['FR']}}, # Ciblage simple : France
                    'status': 'ACTIVE', # On l'active pour le test !
                    'dsa_beneficiary': 'Projet PFE Data Science',
                    'dsa_payor': 'Projet PFE Data Science',
                }
            )
            adset_id = adset['id']
            print(f"✅ Ad Set créé et ACTIF (ID: {adset_id})")
            
            return adset_id,campaign_id
            
        except Exception as e:
            print(f"❌ [META API ERROR] Échec de la création : {e}")
            return None
        
   
# ... tes autres imports ...

    def _hash_data(self, data_str: str) -> str:
        """Fonction utilitaire pour crypter la donnée en SHA-256 (Requis par Meta)"""
        return hashlib.sha256(data_str.strip().lower().encode('utf-8')).hexdigest()

    def create_crm_custom_audience(self, segment_name: str, customer_emails: list) -> str:
        """
        Crée une audience personnalisée et y injecte les emails cryptés.
        """
        print(f"\n📦 [META API] Création de l'audience source CRM : {segment_name}...")
        try:
            # 1. Création de la "boîte" (l'audience vide)
            params = {
                'name': f'💎 CRM Segment : {segment_name}',
                'subtype': 'CUSTOM',
                'description': 'Audience VIP poussée par le CRM Keeper',
                'customer_file_source': 'USER_PROVIDED_ONLY' # Indique que ça vient de ton CRM
            }
            audience = self.account.create_custom_audience(fields=['name', 'id'], params=params)
            audience_id = audience['id']
            print(f"✅ [META API] Boîte d'audience créée (ID: {audience_id})")

            # 2. Préparation et cryptage des données
            if customer_emails:
                print("🔐 [META API] Cryptage SHA-256 des données clients...")
                hashed_emails = [self._hash_data(email) for email in customer_emails]
                
                # Formatage strict exigé par l'API Meta
                payload = {
                    'schema': ['EMAIL'],
                    'data': [[email] for email in hashed_emails]
                }
                
                # 3. Injection des données dans la boîte
                print("📡 [META API] Upload des données vers les serveurs Meta...")
                audience.add_users(users=payload)
                print(f"✅ [META API] {len(customer_emails)} contacts injectés avec succès !")

            return audience_id
            
        except Exception as e:
            print(f"❌ [META API ERROR] Échec lors de la création ou de l'upload : {e}")
            return None
    # fonction pour exécuter le protocole Champion/Challenger
    def execute_champion_challenger(self, target_adset_id: str, new_creatives: list, challenger_ratio: float = 0.8) -> dict:
        """
        [REQUÊTE LECTURE & ÉCRITURE]
        Applique le framework Champion/Challenger.
        Réduit le budget de l'Ad Set actuel (20%) et crée un clone (80%) pour tester les nouvelles créatures.
        """
        print(f"\n⚔️ [META API] Démarrage du protocole Champion/Challenger (Ratio {challenger_ratio*100}%)")
        
        try:
            
            
            # 1. LECTURE : Récupération du Champion (L'ancien Ad Set)
            print(f"🔍 [META API] Audit du Champion actuel (ID: {target_adset_id})...")
            champion = AdSet(target_adset_id)
            champion_data = champion.api_get(
                fields=['name', 'daily_budget', 'campaign_id', 'targeting', 'bid_amount', 'billing_event', 'optimization_goal']
            )
            
            # Les budgets sur Meta sont toujours en centimes
            budget_total = int(champion_data.get('daily_budget', 0))
            if budget_total == 0:
                raise Exception("L'Ad Set cible a un budget de 0 ou n'a pas de budget quotidien.")

            # 2. MATHÉMATIQUES : Le calcul de la répartition
            challenger_budget = int(budget_total * challenger_ratio)
            champion_budget = budget_total - challenger_budget
            
            print(f"💸 [META API] Budget total : {budget_total/100}€. "
                  f"Nouveau Champion : {champion_budget/100}€ | Challenger : {challenger_budget/100}€")

            # 3. ÉCRITURE (DOWNGRADE) : On étouffe le Champion (20%)
            print("📉 [META API] Réduction du budget du Champion...")
            champion.api_update(params={
                'daily_budget': champion_budget,
                'name': champion_data.get('name', 'AdSet') + ' 🏆 [CHAMPION 20%]'
            })

            # 4. ÉCRITURE (CLONAGE) : Création du Challenger (80%)
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
                # Rappel : Obligatoire pour la conformité européenne DSA
                'dsa_beneficiary': 'Projet PFE Data Science',
                'dsa_payor': 'Projet PFE Data Science',
            }
            
            nouveau_challenger = self.account.create_ad_set(fields=['id'], params=challenger_params)
            challenger_id = nouveau_challenger['id']
            print(f"✅ [META API] Challenger créé avec succès (ID: {challenger_id})")

            # 5. UPLOAD DES CRÉATIONS (MOCK POUR LA SOUTENANCE)
            # En production, il faut uploader l'image pour obtenir un 'image_hash', 
            # puis lier ce hash et le texte à un objet 'AdCreative', puis à un objet 'Ad'.
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
    # fonction pour vérifier l'activité du Pixel
    def verify_pixel_activity(self, pixel_id: str, event_name: str = "Lead") -> dict:
        """
        [MONITORING] Interroge l'API Meta (Events Manager) pour vérifier le flux de données.
        """
        print(f"\n🔍 [META API] Vérification de l'activité du Pixel ({pixel_id}) pour l'événement '{event_name}'...")
        
        try:
            # En production : appel à graph.facebook.com/v25.0/{pixel_id}/stats
            
            # 🟢 MOCK POUR LE SANDBOX
            # On force le compteur à 0 pour simuler un Pixel cassé et déclencher l'alerte
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
    