# Media Buyer Agent

Le **Media Buyer** est le bras armé de l'architecture Multi-Agents. Il exécute les stratégies publicitaires directement sur l'environnement de production (Meta Ads API), agit comme un système de surveillance (Watchdog) proactif pour protéger le budget du client, et applique les optimisations algorithmiques (A/B testing, Lookalikes) de manière totalement autonome en fonction des signaux envoyés par les autres agents du système.

---

# Responsibilities

- **Budget pacing:** daily check of spend vs days remaining in month. Alert if pacing is off by more than 15%.
- **Automatic ad set pausing:** if an ad set's CPL exceeds 2x the target for 3 consecutive days, pause it and notify operator.
- **Lookalike Audience creation:** when CRM Keeper pushes a new high-value segment, create a Lookalike Audience from it on Meta automatically.
- **Creative rotation:** when Content Strategist generates new variants, deploy them at 80% traffic. Old variants get 20% for comparison.
- **Conversion event verification:** confirm form submission fires the correct conversion event on Meta Pixel and Google Ads. Alert if firing stops.
- **Weekly performance summary:** structured data sent to Analyst every Monday morning.
- **Langfuse integration:** trace all API write operations and budget decisions. Tag with `client_id`, `campaign_id`, `decision_reason`.

---

# What this agent does NOT do

- **Il ne rédige pas de publicités :** La création textuelle et visuelle relève strictement de l'Agent Content Strategist.
- **Il ne stocke pas les données clients :** La gestion de la base de données (emails, téléphones) appartient au CRM Keeper.
- **Il ne génère pas de stratégies complexes :** L'analyse macro et l'ajustement global des KPIs sont réservés à l'Agent Analyste.
- **Il ne gère pas la facturation client :** Il optimise le budget alloué sur les plateformes mais ne gère pas les transactions bancaires.

---

# Setup

1. Installe le gestionnaire d'environnement **uv** si ce n'est pas déjà fait.
2. Clone le dépôt (via l'organisation **114Agency**) et navigue dans le dossier de l'agent.
3. Synchronise les dépendances :

```bash
uv sync
```

ou

```bash
uv pip install -r requirements.txt
```

4. Crée un fichier `.env` à la racine du dossier.
5. Copie-colle les variables d'environnement requises (voir section suivante) et remplis-les avec tes clés.
6. Lance le serveur via la commande de développement.

---

# Environment variables

| Variable name | Description | Required | Example value |
|--------------|-------------|----------|---------------|
| `META_APP_ID` | L'ID de l'application Meta Developers | Oui | `123456789012345` |
| `META_APP_SECRET` | La clé secrète de l'application Meta | Oui | `abc123def456ghi789` |
| `META_ACCESS_TOKEN` | Le jeton d'accès (System User ou Graph API) | Oui | `EAAB...` |
| `META_AD_ACCOUNT_ID` | L'ID du compte publicitaire cible | Oui | `act_1985127601779112` |
| `TELEGRAM_BOT_TOKEN` | Token du bot d'alerte généré via BotFather | Oui | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TELEGRAM_CHAT_ID` | L'ID du salon de réception des alertes | Oui | `-100123456789` |
| `LANGFUSE_PUBLIC_KEY` | Clé publique d'observabilité Langfuse | Oui | `pk-lf-1a2b3c...` |
| `LANGFUSE_SECRET_KEY` | Clé secrète d'observabilité Langfuse | Oui | `sk-lf-1a2b3c...` |
| `LANGFUSE_HOST` | URL du serveur Langfuse | Oui | `https://cloud.langfuse.com` |

---

# Running the agent

## Development mode (avec rechargement automatique)

```bash
uv run uvicorn api:app --reload --port 8004
```

## Production mode

```bash
uv run uvicorn api:app --host 0.0.0.0 --port 8004 --workers 4
```

---

# Running tests

```bash
uv run pytest tests/
```

---

# Current phase

## Phase B (Active Management)

L'agent a dépassé le stade de lecture simple (Phase A). La Phase B est totalement achevée, transformant l'agent en Watchdog capable de manipuler l'API Meta (création d'audiences, rotation créative, gestion d'état des Ad Sets) et de communiquer structuré avec le CRM Keeper, l'Analyste et l'opérateur humain via Telegram. Le traçage des décisions est opérationnel sur Langfuse (SDK v4).

---

# Phase validation checklist

- [x] Budget pacing: daily check of spend vs days remaining in month. Alert if pacing is off by more than 15%.
- [x] Automatic ad set pausing: if an ad set's CPL exceeds 2x the target for 3 consecutive days, pause it and notify operator.
- [x] Lookalike Audience creation: when CRM Keeper pushes a new high-value segment, create a Lookalike Audience from it on Meta automatically.
- [x] Creative rotation: when Content Strategist generates new variants, deploy them at 80% traffic. Old variants get 20% for comparison.
- [x] Conversion event verification: confirm form submission fires the correct conversion event on Meta Pixel and Google Ads. Alert if firing stops.
- [x] Weekly performance summary: structured data sent to Analyst every Monday morning.
- [x] Langfuse integration (mid-Phase B): trace all API write operations and budget decisions. Tag with `client_id`, `campaign_id`, `decision_reason`.

---

# Known limitations

- **Environnement Sandbox Meta :** En raison des restrictions administratives des comptes développeurs, l'upload final des images vers l'objet AdCreative est simulé (Mock) pour contourner l'obligation d'un Business Manager payant vérifié.
- **Taille d'audience Lookalike :** L'API Sandbox accepte la création de la Custom Audience mais peut refuser la génération de la Lookalike si le volume d'emails fourni est inférieur au seuil algorithmique (souvent < 100).
- **Monitoring Pixel :** Actuellement réalisé par interrogation passive (polling API) et simulation locale, le compte de test ne générant pas de vrai trafic web pour déclencher de vrais événements Lead.

---

# Inputs and outputs

## Input 1: Demande de rotation créative (Reçu du Content Strategist)

**Format :** JSON (via `POST /ads/rotate-creatives`)

**Exemple :**

```json
{
  "target_adset_id": "120247096711530625",
  "challenger_ratio": 0.8,
  "new_creatives": [
    {
      "image_url": "https://server.com/img_v2.jpg",
      "primary_text": "Découvrez l'offre exclusive !",
      "headline": "Promo spéciale"
    }
  ]
}
```

---

## Output 1: Modification Meta Ads & Observabilité

**Format :** API Call vers `graph.facebook.com` + Trace envoyée à Langfuse.

**Exemple (Métadonnées Langfuse) :**

```json
{
  "tags": [
    "media_buyer",
    "api_write",
    "creative_rotation"
  ],
  "metadata": {
    "client_id": "global",
    "campaign_id": "120247096711530625",
    "decision_reason": "Déploiement stratégique 80/20 initié par le Content Strategist avec 1 nouvelles variantes.",
    "new_challenger_id": "120247096760750625"
  }
}
```

---

## Output 2: Résumé Hebdomadaire (Envoyé à l'Agent Analyste)

**Format :** JSON via CRON

**Exemple :**

```json
{
  "source_agent": "media_buyer",
  "report_type": "weekly_performance",
  "date_generated": "2026-05-15T08:00:00",
  "metrics": {
    "platform": "meta_ads",
    "spend": 450.50,
    "impressions": 12500,
    "clicks": 450,
    "leads": 28,
    "cpl": 16.08
  }
}
```