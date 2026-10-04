# CONTEXT.md — Newsletter_Reader

## 1. Informazioni Generali
- **Progetto:** Newsletter_Reader — Unified Modular Headless Newsletter Ingestion Engine
- **Data Inizio:** 2026-10-03
- **Autore:** Francesco Colombini
- **Stack Tecnologico:** Python 3.11, Docker, Google GenAI SDK (Gemini 2.5 Flash), Notion Client, Pydantic v2, PyYAML, APScheduler, SQLite, HTML2Text.
- **Repository:** https://github.com/FRA-0023/Newsletter_Reader

---

## 2. Stato Attuale del Progetto (2026-10-04)
- **Situazione Presente:** Motore unificato pienamente operativo in background nativo (pythonw.exe). Completato con successo il decommissioning dei container Docker legacy (Crypto, Mozi, World Population) con migrazione di 135 record storici in data/state.db. Disco virtuale Docker ridotto da ~23 GB a ~12,4 GB (recuperati >10,5 GB su C:).
- **Situazione Presente:** Motore unificato pienamente operativo, multi-dominio e resiliente. I file privati di configurazione (config/domains.yaml), i template di prompt (	emplates/*) e lo stato locale (CONTEXT.md, data/*.db) sono rigorosamente isolati in .gitignore.
- **Nuove Funzionalità Aggiunte:**
  1. *Fail-Fast su 429:* Eliminato qualsiasi loop/sleep su quota esaurita. Se Gemini risponde 429, il processo termina all'istante senza consumare risorse, preservando le email non lette.
  2. *Daily Intelligence Briefing:* Servizio cumulativo serale (APScheduler alle 20:00 o CLI daily-briefing) che sintetizza con Gemini tutte le newsletter ingerite nella giornata in un memo esecutivo unificato (Plain Text + HTML reattivo) inviato via SMTP.
  3. *Isolamento Privacy & Git:* Forniti config/domains.example.yaml e 	emplates/default.md.example sul repository pubblico; la configurazione reale rimane esclusiva dell'host locale.
- **Verifica Funzionale:** 8 test unitari su 8 superati (pytest), validazione CLI completata, test end-to-end con estrazione reale su 4 email confermato.

---

## 3. Mappa dei Bounded Context & Componenti
- config/domains.yaml (privato) / config/domains.example.yaml (pubblico): Definizione dichiarativa di domini, filtri, schedulazione e sink Notion.
- 	emplates/ (privato) / 	emplates/default.md.example: Asset di prompt esterni disaccoppiati dal codice Python.
- src/core/schemas.py: Contratti tipizzati Pydantic per Structured Outputs (ExecutiveDigest, Notion Payloads, DailyBriefingOutput).
- src/core/engine.py: Orchestratore pipeline singola email (IMAP -> Gemini -> Notion -> Push Digest -> SQLite).
- src/core/daily_briefing.py: Orchestratore del briefing cumulativo giornaliero (Query SQLite -> Sintesi Gemini -> SMTP).
- src/adapters/:
  - imap_client.py: Lettura IMAP con filtraggio mittente e troncamento disclaimers.
  - gemini_client.py: Client Gemini con fail-fast su 429 e retry su 503.
  - 
otion_client.py: Dispatcher blocchi Notion.
  - email_notifier.py: Invio digest atomici e briefing giornalieri via SMTP SSL.
  - sqlite_store.py: Persistenza e recupero record giornalieri.
- src/cli.py & src/daemon.py: Interfacce di esecuzione atomica e demone orario continuo.
- scripts/: Script headless per Windows (0 MB RAM idle).

---

## 4. Log delle Sessioni

### 2026-10-04 — Decommissioning Docker Legacy, Migrazione Dati, Compattazione VHDX & Hardening
- **Attività svolte:**
  - **Migrazione e Salvaguardia Dati (Tier 1 Data Loss Prevention):** Estratti e unificati nel database SQLite centrale (data/state.db) tutti i dati storici dei bot dismessi: 126 record da World_Population_Newsletter, 6 da Mozi_Minute e 1 da Crypto_Newsletter (135 totali). Creati backup completi dei volumi in data/backups/.
  - **Dismissione Ambienti Docker Legacy:** Rimossi container, volumi ed immagini di Crypto_Newsletter, Mozi_Minute e World_Population_Newsletter. Isolati e preservati gli ambienti degli altri progetti (n8n e travel_finder).
  - **Compattazione Disco Virtuale WSL (docker_data.vhdx):** Prunata la cache di build (14 GB), eseguito fstrim ext4 e compattazione fisica via DiskPart. Dimensione ridotta da 22,99 GB a 12,43 GB, restituendo oltre 10,5 GB a Windows (disco C:).
  - **Risoluzione Stallo VHD & Hardening Script:** Creati script Windows robusti e sequenziali (scripts/compact_docker_disk.bat/.ps1 e scripts/unlock_docker_disk.bat/.ps1) per gestire lock e detach del disco virtuale in modo pulito.
  - **Neutralizzazione Avvii Fantasma:** Disattivati i task nel Windows Task Scheduler e neutralizzati i launcher legacy (.bat) dei vecchi progetti per impedire ricreazioni accidentali di container/immagini Docker.
  - **Verifica Operativa:** Bot unificato in background su Windows Startup (pythonw.exe, PID 7204/29920) attivo con tutti i 6 domini operativi.

### 2026-10-03 — Scaffolding, Resilienza 429, Daily Briefing & Isolamento Privacy
- **Attività svolte:**
  - Risoluzione root cause focus-stealing: abbandonato pattern batch start/kill di Docker Desktop a favore di architettura Dual-Mode (0-RAM host locale vs Docker container).
  - Implementati e verificati 5 domini: World Population, Crypto Gateway, Mozi Minute, Tristan Burns, David Cohen.
  - Riconfigurata gestione errori Gemini: fail-fast immediato su 429 (quota) e retry solo su 503 (server).
  - Implementato il Daily Intelligence Briefing cumulativo con modello DailyBriefingOutput e rendering responsive.
  - Spostati in .gitignore: CONTEXT.md, config/domains.yaml, 	emplates/*, .pytest_cache/.
  - Introdotti template d'esempio (config/domains.example.yaml, 	emplates/default.md.example).
  - Eseguita suite completa di 8 test (tutti passati).
