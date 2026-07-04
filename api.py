from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
from langfuse import get_client, observe, propagate_attributes


# 🟢 IMPORT DE TON CLIENT META
from meta_client import MetaAdsClient

app = FastAPI(title="Media Buyer API - Phase B")

# 🟢 INITIALISATION DU CLIENT (Se fait une seule fois au démarrage)
try:
    meta_client = MetaAdsClient()
except Exception as e:
    print(f"⚠️ Attention: Impossible d'initialiser MetaAdsClient : {e}")
    meta_client = None

# 🟢 INITIALISATION DU CLIENT LANGFUSE (SDK v4, remplace langfuse_context / update_current_trace)
langfuse = get_client()


# 🛡️ 1. Modèle Pydantic (Le vigile à l'entrée)
class AdsAlertPayload(BaseModel):
    platform: str = Field(..., pattern="^(meta|google)$", description="La plateforme source")
    # 💡 J'ai renommé campaign_id en target_id car sur Meta, on coupe souvent l'Ad Set (l'audience) plutôt que la campagne entière
    target_id: str = Field(..., description="L'ID de l'Ad Set ou de la Campagne concernée") 
    alert_type: str = Field(..., description="Le type d'alerte (ex: cpl_spike, budget_depleted)")
    metric_value: float = Field(..., description="La valeur de la métrique")
    threshold_value: Optional[float] = Field(None, description="Le seuil dépassé")

# 1. Le modèle exact (Le contrat de données)
class CRMPayload(BaseModel):
    segment_name: str = Field(..., description="Nom du segment (ex: high_value_ecom)")
    country: str = Field("FR", description="Code pays")
    lookalike_percentage: int = Field(1, description="Pourcentage de Lookalike")
    customer_emails: List[str] = Field(..., description="Liste des emails extraits du CRM")
from typing import List, Dict, Any

# ==========================================
# 🎨 MODÈLES POUR LA ROTATION CRÉATIVE
# ==========================================

class NewCreative(BaseModel):
    """Représente une seule nouvelle publicité générée par le Content Strategist."""
    image_url: str = Field(..., description="L'URL de la nouvelle image générée")
    primary_text: str = Field(..., description="Le nouveau texte (Copywriting) de la pub")
    headline: str = Field(..., description="Le titre accrocheur sous l'image")

class CreativeRotationPayload(BaseModel):
    """Le colis envoyé par le Content Strategist au Media Buyer."""
    target_adset_id: str = Field(..., description="L'ID de l'ancien Ad Set (Le Champion)")
    new_creatives: List[NewCreative] = Field(..., description="La liste des nouvelles publicités à tester")
    challenger_ratio: float = Field(0.8, description="Le pourcentage du budget pour la nouveauté (ex: 0.8 pour 80%)")

# 2. La route de réception de high_value_segment (Le webhook du CRM Keeper)
@app.post("/crm/push-segment")
def receive_high_value_segment(payload: CRMPayload):
    """
    Écoute le CRM Keeper. Reçoit la liste des emails VIP et l'envoie à Meta.
    """
    print(f"\n📥 [WEBHOOK CRM] Réception du segment : {payload.segment_name}")
    print(f"📦 [WEBHOOK CRM] Nombre d'emails reçus : {len(payload.customer_emails)}")
    print(f"📧 [DEBUG] Emails à crypter : {payload.customer_emails}")
    
    if not meta_client:
        raise HTTPException(status_code=500, detail="Client Meta hors ligne.")

    try:
        # 1. Création de l'audience source et injection des emails
        source_id = meta_client.create_crm_custom_audience(payload.segment_name, payload.customer_emails)
        
        if not source_id:
            raise HTTPException(status_code=500, detail="Échec de la création de l'audience source.")

        # 2. Création du Lookalike
        lal_id = meta_client.create_lookalike_audience(
            source_audience_id=source_id,
            country_code=payload.country,
            percentage=payload.lookalike_percentage
        )
        
        return {
            "status": "success",
            "message": f"Audience uploadée ({len(payload.customer_emails)} contacts) et Lookalike généré.",
            "data": {"source_id": source_id, "lookalike_id": lal_id}
        }
        
    except Exception as e:
        # 🛡️ GESTION DE L'ERREUR META (Audience too small)
        erreur_str = str(e).lower()
        if "too small" in erreur_str or "100" in erreur_str:
            print("⚠️ [META API] Avertissement : L'audience a été créée, mais Meta refuse de générer le Lookalike car il y a moins de 100 contacts. C'est normal en dev !")
            return {
                "status": "partial_success",
                "message": "Audience source créée, mais Lookalike en attente (volume insuffisant pour l'algorithme Meta).",
            }
        else:
            print(f"❌ [ERREUR INATTENDUE] {e}")
            raise HTTPException(status_code=500, detail=str(e))


# 🚀 2. La route principale du Webhook (Désormais Connectée à Meta !)
@app.post("/ads/alert")
async def receive_ads_alert(payload: AdsAlertPayload):
    """
    Reçoit les alertes et déclenche IMMÉDIATEMENT l'action corrective sur Facebook.
    """
    print(f"\n🚨 [WEBHOOK ALERT] Alerte reçue de {payload.platform.upper()} !")
    
    action_taken = "Aucune action"
    
    # ⚡ LE CERVEAU AUTONOME : Si le CPL explose, l'API coupe la pub toute seule
    if payload.alert_type == "cpl_spike" and payload.platform == "meta" and meta_client:
        print(f"⚔️ [RÉACTION AUTONOME] Le CPL est critique ({payload.metric_value} > {payload.threshold_value}). Coupure immédiate !")
        success = meta_client.pause_adset(payload.target_id)
        action_taken = "Mise en pause réussie" if success else "Échec de la mise en pause"

    # 📝 Format de log OBLIGATOIRE
    log_entry = {
        "agent_name": "media_buyer",
        "action_type": "process_alert",
        "input_summary": f"Alert '{payload.alert_type}' on target {payload.target_id}",
        "output_summary": action_taken,
        "lead_id": None,
        "client_id": "global",
        "model_used": "rule-based",
        "latency_ms": 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    print(f"📝 Log enregistré : {log_entry}")
    
    return {
        "status": "success", 
        "message": f"Alerte traitée. Action: {action_taken}",
        "data": payload.model_dump()
    }

# ==========================================
# 📊 3. ROUTES D'EXTRACTION DE DONNÉES (À LA DEMANDE)
# ==========================================

@app.get("/performance/last-7-days")
def get_performance_7d():
    """L'Orchestrateur demande le résumé global de la semaine."""
    if not meta_client:
        raise HTTPException(status_code=500, detail="Client Meta non initialisé")
    data = meta_client.get_last_7_days_performance()
    return {"status": "success", "data": data}

@app.get("/campaign/{campaign_id}/summary")
def get_summary(campaign_id: str):
    """L'Orchestrateur demande les détails d'une campagne spécifique."""
    if not meta_client:
        raise HTTPException(status_code=500, detail="Client Meta non initialisé")
    
    data = meta_client.get_campaign_summary(campaign_id)
    if data.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Campagne introuvable sur Meta")
    return {"status": "success", "data": data}

@app.post("/sandbox/create")
@observe(name="[API Write MB] Sandbox Environment Creation")
def create_sandbox_env():
    """Génère un environnement de test complet sur le compte Sandbox."""
    if not meta_client:
        raise HTTPException(status_code=500, detail="Client Meta non initialisé")
        
    result = meta_client.create_sandbox_campaign_and_adset()
    if result:
        adset_id, campaign_id = result
        # 🟢 ENREGISTREMENT DANS LANGFUSE
        with propagate_attributes(
                tags=["media_buyer", "api_write", "sandbox_creation"],
                metadata={
                    "client_id": "global",
                    "campaign_id": campaign_id,
                    "decision_reason": "Initialisation d'un environnement de test Sandbox (Campagne + Ad Set).",
                    "new_adset_id": adset_id
                }
            ):
                pass
        return {"status": "success", "campaign_id": campaign_id, "adset_id": adset_id}
    raise HTTPException(status_code=500, detail="Échec de la création Sandbox")

# 🛑 4. Gestionnaire d'erreurs (Rejette les mauvais payloads avec une erreur 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"\n❌ [WEBHOOK ERROR] Payload invalide rejeté sur /ads/alert !")
    # ... (Ton code de log d'erreur reste identique ici) ...
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Payload invalide rejeté."}
    )

@app.post("/crm/push-segment")
@observe(name="[API Write] CRM Audience Creation")
def receive_high_value_segment(payload: CRMPayload):
    """
    Écoute le CRM Keeper. Reçoit la liste des emails VIP et l'envoie à Meta.
    """
    print(f"\n📥 [WEBHOOK CRM] Réception du segment : {payload.segment_name}")
    print(f"📦 [WEBHOOK CRM] Nombre de clients reçus : {len(payload.customer_emails)}")
    
    if not meta_client:
        raise HTTPException(status_code=500, detail="Client Meta hors ligne.")

    # 1. On passe la liste d'emails à la fonction de création
    source_id = meta_client.create_crm_custom_audience(payload.segment_name, payload.customer_emails)
    
    if not source_id:
        raise HTTPException(status_code=500, detail="Échec de la création de l'audience source.")

    # 2. Création immédiate du Lookalike basé sur ces données
    lal_id = meta_client.create_lookalike_audience(
        source_audience_id=source_id,
        country_code=payload.country,
        percentage=payload.lookalike_percentage
    )

    if not lal_id:
        raise HTTPException(status_code=500, detail="Échec de la création du Lookalike.")
    
    # 🟢 ENREGISTREMENT DANS LANGFUSE (v4 : propagate_attributes remplace update_current_trace)
    with propagate_attributes(
        tags=["media_buyer", "api_write", "audience_creation"],
        metadata={
            "client_id": "global",
            "campaign_id": f"segment_{payload.segment_name}",
            "decision_reason": f"Push CRM automatisé de {len(payload.customer_emails)} contacts pour génération d'audience Custom et Lookalike ({payload.lookalike_percentage}%).",
            "source_id": str(source_id),
            "lookalike_id": str(lal_id)
        }
    ):
        pass
    return {
        "status": "success",
        "message": f"Audience uploadée ({len(payload.customer_emails)} contacts) et Lookalike généré.",
        "data": {
            "source_audience_id": source_id,
            "lookalike_audience_id": lal_id
        }
    }
# route pour La Route de Réception la rotation créative
@app.post("/ads/rotate-creatives")
@observe(name="[API Write MB] Champion/Challenger Rotation")
def trigger_creative_rotation(payload: CreativeRotationPayload):
    """
    Écoute le Content Strategist. 
    Applique le Framework Champion/Challenger (80/20) sur Meta Ads.
    """
    print(f"\n🎨 [WEBHOOK CONTENT] Demande de rotation créative reçue !")
    print(f"🎯 Cible (Champion) : Ad Set {payload.target_adset_id}")
    
    if not meta_client:
        raise HTTPException(status_code=500, detail="Client Meta hors ligne.")

    # 🟢 APPEL AU MUSCLE META
    resultat = meta_client.execute_champion_challenger(
        target_adset_id=payload.target_adset_id,
        new_creatives=[c.model_dump() for c in payload.new_creatives],
        challenger_ratio=payload.challenger_ratio
    )

    if not resultat:
        raise HTTPException(status_code=500, detail="Échec de l'opération sur l'API Meta.")
    # 🟢 ENREGISTREMENT DANS LANGFUSE (v4 : propagate_attributes remplace update_current_trace)
    with propagate_attributes(
        tags=["media_buyer", "api_write", "creative_rotation"],
        metadata={
            "client_id": "global",
            "campaign_id": payload.target_adset_id, # On identifie le Champion ciblé
            "decision_reason": f"Déploiement stratégique 80/20 initié par le Content Strategist avec {len(payload.new_creatives)} nouvelles variantes.",
            "new_challenger_id": str(resultat.get("challenger_id"))
        }
    ):
        pass
    return {
        "status": "success",
        "message": "Rotation 80/20 exécutée avec succès sur Facebook.",
        "data": resultat
    }
# Route temporaire pour forcer le Watchdog de tracking sans attendre le CRON
@app.get("/test/verify-conversions")
def force_verify_conversions():
    """Route temporaire pour forcer le Watchdog sans attendre le CRON."""
    print("\n🚀 [TEST MANUEL] Lancement du Watchdog de tracking...")
    # On instancie l'agent localement juste pour le test manuel
    from agent import MediaBuyerAgent
    test_agent = MediaBuyerAgent()
    test_agent.verify_conversions_watchdog()
    
    return {"message": "Diagnostic exécuté ! Regarde ton Telegram si le Pixel est à 0."}

# Route temporaire pour forcer l'envoi du résumé hebdomadaire à l'Analyste
@app.get("/test/weekly-summary")
def force_weekly_summary():
    """Route temporaire pour forcer l'envoi du résumé hebdomadaire."""
    print("\n🚀 [TEST MANUEL] Lancement de l'exportation vers l'Analyste...")
    from agent import MediaBuyerAgent
    test_agent = MediaBuyerAgent()
    payload = test_agent.send_weekly_summary_to_analyst()
    
    return {
        "message": "Résumé hebdomadaire généré ! Vérifie Telegram et la console.",
        "payload_envoye": payload
    }