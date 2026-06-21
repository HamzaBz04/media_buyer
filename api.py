from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

app = FastAPI(title="Media Buyer API - Phase A")

# 🛡️ 1. Modèle Pydantic (Le vigile à l'entrée)
class AdsAlertPayload(BaseModel):
    platform: str = Field(..., pattern="^(meta|google)$", description="La plateforme source (meta ou google)")
    campaign_id: str = Field(..., description="L'ID de la campagne concernée")
    alert_type: str = Field(..., description="Le type d'alerte (ex: cpl_spike, budget_depleted)")
    metric_value: float = Field(..., description="La valeur de la métrique qui a déclenché l'alerte")
    threshold_value: Optional[float] = Field(None, description="Le seuil qui a été dépassé (optionnel)")

# 🚀 2. La route principale du Webhook
@app.post("/ads/alert")
async def receive_ads_alert(payload: AdsAlertPayload):
    """
    Reçoit les alertes de performance directement depuis les plateformes publicitaires.
    """
    print(f"\n🚨 [WEBHOOK ALERT] Alerte reçue de {payload.platform.upper()} !")
    
    # 📝 3. Format de log OBLIGATOIRE (Selon les règles globales de ton système)
    log_entry = {
        "agent_name": "media_buyer",
        "action_type": "receive_alert",
        "input_summary": f"Alert '{payload.alert_type}' on campaign {payload.campaign_id}",
        "output_summary": "Alert validated and registered",
        "lead_id": None,
        "client_id": "global", # En Phase A, l'alerte est globale
        "model_used": "rule-based",
        "latency_ms": 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    print(f"📝 Log enregistré : {log_entry}")
    
    return {
        "status": "success", 
        "message": "Alerte reçue, validée et journalisée.",
        "data": payload.model_dump()
    }

# 🛑 4. Gestionnaire d'erreurs (Rejette les mauvais payloads avec une erreur 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"\n❌ [WEBHOOK ERROR] Payload invalide rejeté sur /ads/alert !")
    
    # Log de l'erreur
    error_log = {
        "agent_name": "media_buyer",
        "action_type": "receive_alert_failed",
        "input_summary": "Invalid webhook payload received",
        "output_summary": "Rejected with HTTP 422",
        "lead_id": None,
        "client_id": "unknown",
        "model_used": "rule-based",
        "latency_ms": 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    print(f"📝 Log d'erreur : {error_log}")
    
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Payload invalide rejeté."}
    )