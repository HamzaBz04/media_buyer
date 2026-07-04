# Agent 5 : The Media Buyer

L'agent Media Buyer est responsable de l'acquisition payante et se situe dans la couche d'acquisition (Acquisition layer). Son rôle principal est de s'assurer que les bonnes personnes voient la bonne publicité au bon coût. Sa principale mesure de succès n'est pas le nombre de clics, mais le coût par SQL (Sales Qualified Lead).

## Responsibilities
* Créer et gérer les structures de campagnes sur Meta Ads et Google Ads pour chaque client.
* Configurer le ciblage d'audience : Lookalike Audiences, ciblage par intérêts, et segments de retargeting CRM.
* Allouer et rythmer (pacing) les budgets sur les campagnes en fonction des performances et des plafonds mensuels des clients.
* Surveiller les KPI quotidiens : CPM, CPC, CTR, CPL, coût par SQL, ROAS.
* Mettre en pause les ensembles de publicités sous-performants et réallouer le budget aux campagnes gagnantes.
* Uploader les nouveaux assets créatifs fournis par l'agent Content & Conversion Strategist et les déployer dans les campagnes actives.
* Vérifier le suivi des conversions via le Pixel Meta et les événements de conversion Google Ads.
* Envoyer des données de performance structurées à l'Analyst (Agent 7) tous les jours.

## What this agent does NOT do
* L'agent ne crée en aucun cas les textes publicitaires (ad copy) ou les visuels créatifs. Il reçoit ces éléments terminés de la part du Content & Conversion Strategist.

## Setup
Toute la gestion des dépendances Python de ce projet utilise exclusivement `uv`.
1. Cloner le dépôt et naviguer dans le dossier de l'agent.
2. Synchroniser les dépendances et l'environnement : `uv sync`.
3. Copier le fichier d'environnement : `cp .env.example .env`
4. Remplir les variables d'environnement dans le `.env`.

## Environment variables

| Variable Name | Description | Required | Example Value |
| :--- | :--- | :--- | :--- |
| `META_APP_ID` | Identifiant de l'application Meta for Developers | Yes | `1234567890123` |
| `META_APP_SECRET` | Clé secrète de l'application Meta | Yes | `abc123def456...` |
| `META_ACCESS_TOKEN` | Jeton d'accès de l'API Graph (permissions: ads_read) | Yes | `EAAxxxxxxxx...` |
| `META_AD_ACCOUNT_ID` | ID du compte publicitaire cible (doit inclure le préfixe) | Yes | `act_1234567890` |
| `TELEGRAM_BOT_TOKEN` | Jeton fourni par BotFather pour le bot de notification | Yes | `123456:ABC-DEF...` |
| `TELEGRAM_CHAT_ID` | ID du chat ou du groupe où envoyer les rapports | Yes | `987654321` |

## Running the agent
Démarrer l'agent en mode développement (avec rechargement automatique) :
`uv run uvicorn main:app --reload` 

Démarrer l'agent en mode production :
`uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4` 

## Running tests
Pour exécuter la suite de tests :
`uv run pytest tests/` 

## Current phase
**Phase A (POC) : Complétée.**
L'agent est actuellement capable de lire les données des API publicitaires (Meta Ads configuré) et de générer des rapports de métriques quotidiens formatés sur Telegram à 8h00. Un système d'alerte CPL en temps réel est implémenté, ainsi qu'une simulation d'interrogation manuelle de résumé de campagne.


## Phase validation checklist
* [x] Connect to a real Meta Ads account → pull last 7 days of data correctly. 
* [ ] Connect to a real Google Ads account → pull last 7 days of data correctly.  *(À finaliser lors de la Phase A - Google)*
* [x] Receive daily metrics report at 8am with correct numbers verified against the platform UI. 
* [x] Set a CPL threshold → manually spike a metric above it → Telegram alert arrives within 5 minutes. 

## Known limitations
* L'agent opère de manière strictement "Read-only" (lecture seule) pour le moment. Aucune modification budgétaire ou mise en pause d'ad set n'est active.
* La récupération du statut des campagnes manuelles (`get_campaign_summary`) est temporairement simulée (mockée) pour éviter la contrainte de facturation d'un compte Meta actif durant le développement.
* L'intégration Google Ads API nécessite l'approbation d'un Developer Token.

## Inputs and outputs
* **Inputs :**
  * Alertes webhook externes via `POST /ads/alert` (ex: Meta/Google performance alerts) validées par Pydantic. Format: JSON Payload.
  * Commandes Telegram (ex: ID de campagne ciblé `123456789`).
* **Outputs :**
  * Rapports formatés envoyés sur Telegram (Rapport quotidien de 8h00, Alertes CPL, Résumé de campagne manuelle).
  * Fichiers de logs structurés locaux (Format JSON strict incluant `agent_name`, `action_type`, `latency_ms`, etc.).