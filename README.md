# Agent 5 : The Media Buyer

[cite_start]L'agent Media Buyer est responsable de l'acquisition payante et se situe dans la couche d'acquisition (Acquisition layer)[cite: 424]. [cite_start]Son rôle principal est de s'assurer que les bonnes personnes voient la bonne publicité au bon coût[cite: 426]. [cite_start]Sa principale mesure de succès n'est pas le nombre de clics, mais le coût par SQL (Sales Qualified Lead)[cite: 432].

## Responsibilities
* [cite_start]Créer et gérer les structures de campagnes sur Meta Ads et Google Ads pour chaque client[cite: 434].
* [cite_start]Configurer le ciblage d'audience : Lookalike Audiences, ciblage par intérêts, et segments de retargeting CRM[cite: 435].
* [cite_start]Allouer et rythmer (pacing) les budgets sur les campagnes en fonction des performances et des plafonds mensuels des clients[cite: 436].
* [cite_start]Surveiller les KPI quotidiens : CPM, CPC, CTR, CPL, coût par SQL, ROAS[cite: 437].
* [cite_start]Mettre en pause les ensembles de publicités sous-performants et réallouer le budget aux campagnes gagnantes[cite: 438].
* [cite_start]Uploader les nouveaux assets créatifs fournis par l'agent Content & Conversion Strategist et les déployer dans les campagnes actives[cite: 439].
* [cite_start]Vérifier le suivi des conversions via le Pixel Meta et les événements de conversion Google Ads[cite: 440].
* [cite_start]Envoyer des données de performance structurées à l'Analyst (Agent 7) tous les jours[cite: 441].

## What this agent does NOT do
* [cite_start]L'agent ne crée en aucun cas les textes publicitaires (ad copy) ou les visuels créatifs[cite: 429]. [cite_start]Il reçoit ces éléments terminés de la part du Content & Conversion Strategist[cite: 430].

## Setup
[cite_start]Toute la gestion des dépendances Python de ce projet utilise exclusivement `uv`[cite: 44].
1. Cloner le dépôt et naviguer dans le dossier de l'agent.
2. [cite_start]Synchroniser les dépendances et l'environnement : `uv sync`[cite: 167].
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
[cite_start]`uv run uvicorn main:app --reload` [cite: 78]

Démarrer l'agent en mode production :
[cite_start]`uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4` [cite: 79]

## Running tests
Pour exécuter la suite de tests :
[cite_start]`uv run pytest tests/` [cite: 173]

## Current phase
**Phase A (POC) : Complétée.**
L'agent est actuellement capable de lire les données des API publicitaires (Meta Ads configuré) et de générer des rapports de métriques quotidiens formatés sur Telegram à 8h00. Un système d'alerte CPL en temps réel est implémenté, ainsi qu'une simulation d'interrogation manuelle de résumé de campagne.


## Phase validation checklist
* [cite_start][x] Connect to a real Meta Ads account → pull last 7 days of data correctly. [cite: 450, 451]
* [cite_start][ ] Connect to a real Google Ads account → pull last 7 days of data correctly. [cite: 452, 453] *(À finaliser lors de la Phase A - Google)*
* [cite_start][x] Receive daily metrics report at 8am with correct numbers verified against the platform UI. [cite: 454]
* [cite_start][x] Set a CPL threshold → manually spike a metric above it → Telegram alert arrives within 5 minutes. [cite: 455]

## Known limitations
* [cite_start]L'agent opère de manière strictement "Read-only" (lecture seule) pour le moment[cite: 443]. Aucune modification budgétaire ou mise en pause d'ad set n'est active.
* La récupération du statut des campagnes manuelles (`get_campaign_summary`) est temporairement simulée (mockée) pour éviter la contrainte de facturation d'un compte Meta actif durant le développement.
* L'intégration Google Ads API nécessite l'approbation d'un Developer Token.

## Inputs and outputs
* **Inputs :**
  * [cite_start]Alertes webhook externes via `POST /ads/alert` (ex: Meta/Google performance alerts) validées par Pydantic[cite: 76, 80]. Format: JSON Payload.
  * Commandes Telegram (ex: ID de campagne ciblé `123456789`).
* **Outputs :**
  * Rapports formatés envoyés sur Telegram (Rapport quotidien de 8h00, Alertes CPL, Résumé de campagne manuelle).
  * [cite_start]Fichiers de logs structurés locaux (Format JSON strict incluant `agent_name`, `action_type`, `latency_ms`, etc.)[cite: 122, 123].