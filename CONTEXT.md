# CONTEXT.md — Newsletter_Reader

## 1. Informazioni Generali
- **Progetto:** Newsletter_Reader — Unified Modular Headless Newsletter Ingestion Engine
- **Data Inizio:** 2026-10-03
- **Autore:** Francesco Colombini
- **Stack Tecnologico:** Python 3.11, Docker, Google GenAI SDK (Gemini 2.5 Flash), Notion Client, Pydantic v2, PyYAML, APScheduler, SQLite, HTML2Text.
- **Repository:** https://github.com/FRA-0023/Newsletter_Reader

---

## 2. Stato Attuale del Progetto (2026-10-03)
- **Situazione Presente:** Architettura unificata completata e validata. Integra i 3 bot preesistenti (World Population, Crypto Gateway, Mozi Minute) e il nuovo dominio Tristan Burns in un singolo motore modulare configurato via config/domains.yaml.
- **Verifica Funzionale:** Eseguito test end-to-end in modalità dry-run su casella Gmail reale: rilevate ed estratte con successo 4 newsletter con parsing Pydantic strutturato su Notion e generazione del digest email a 3 bullet.
- **Resilienza API:** Implementato interceptor dedicato per rate limit (HTTP 429) con pause adattive e per errori temporanei di disponibilità server (HTTP 503) con backoff esponenziale.
- **Runtime:** Configurato in architettura Dual-Mode:
  1. *Host Windows nativo*: 0 MB di RAM a riposo via scripts/start_headless.vbs o Windows Task Scheduler (pythonw.exe).
  2. *Container Docker*: docker compose up -d multi-piattaforma.
- **Prossimo Passo:** Monitoraggio dell'esecuzione automatica in background alla prima emissione oraria programmata.

---

## 3. Mappa dei Bounded Context & Componenti
- config/domains.yaml: Master configuration declarativa per tutti i domini.
- 	emplates/*.md: Separazione netta di prompt e codice (world_population, crypto, mozi_minute, tristan_burns).
- src/core/schemas.py: Contratti Pydantic per Structured Outputs single-pass (ExecutiveDigest + Notion payload).
- src/core/engine.py: Orchestratore pipeline deterministica.
- src/adapters/:
  - imap_client.py: Ingestione IMAP Gmail con filtro mittente e troncamento disclaimers.
  - gemini_client.py: Inferenza Gemini strutturata con gestione 429/503.
  - 
otion_client.py: Dispatcher blocchi Notion per database target.
  - email_notifier.py: Invio immediato digest 3-bullet via SMTP SSL.
  - sqlite_store.py: Idempotenza transazionale su data/state.db.
- src/cli.py & src/daemon.py: Entrypoint CLI e demone orario continuo APScheduler.
- scripts/: Helper headless per Windows (
egister_startup_task.ps1, start_headless.vbs, ootstrap_env.ps1).

---

## 4. Log delle Sessioni

### 2026-10-03 — Scaffolding Architetturale, Test Reale e Setup GitHub
- **Attività svolte:**
  - Analisi root-cause del focus-stealing: individuato avvio/chiusura forzata di Docker Desktop.exe nei vecchi script batch.
  - Progettazione architettura Dual-Mode (0-RAM host vs Docker appliance).
  - Implementazione completa di configurazione (domains.yaml), template esterni, schemi Pydantic e adapter I/O.
  - Aggiunta quarto dominio: Tristan Burns (Beehiiv) con database Notion dedicato e schema business framework.
  - Configurazione gestione eccezioni Gemini: blocco adattivo su quota 429 e retry esponenziale su 503/server overload.
  - Esecuzione test end-to-end con esito positivo: 4 email elaborate in dry-run.
  - Allestimento documentazione esecutiva in inglese (README.md), licenza MIT e persistenza stato in CONTEXT.md.
