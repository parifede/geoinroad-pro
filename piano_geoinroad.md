# /📱 Piano d'Azione: Progetto "Geoinroad Pro"

## 🤖 1. Architettura del Team IA

Per garantire zero regressioni e un codice privo di bug, il flusso di lavoro è orchestrato da due agenti principali:

* **Agente Alpha (Team Lead & Lead Developer):** Si occupa della stesura del codice, della logica di iniezione JavaScript, dell'architettura Python (Flet) e della gestione del database SQLite.
* **Agente Beta (QA, Validation & Security):** Si dedica **esclusivamente** al controllo incrociato. Dopo ogni sotto-fase completata da Alpha, Beta esegue un audit sul codice per verificare assenza di conflitti di versione, gestione sicura delle credenziali, prevenzione di memory leak e gestione corretta degli stati asincroni.

---

## 🛠️ 2. Stack Tecnologico e Versioning (Verificato)

Per evitare l'incompatibilità delle dipendenze (dependency hell) e assicurare la stabilità, il progetto è ancorato a queste versioni specifiche (Target: Android/Samsung):

* **Linguaggio:** Python `3.12.x`
* **Framework UI & Core:** `flet == 0.21.2` 
* **Motore Web:** `flet-webview == 0.2.1`
* **Sicurezza OS:** `keyring == 24.3.1`
* **Database:** `sqlite3` (Libreria standard)

---

## 🗺️ 3. Fasi Operative (Action Plan)

### Fase 1: Inizializzazione Ambiente e Core UI
**Obiettivo:** Creare lo scheletro dell'app e la navigazione base.
* **Sotto-fase 1.1:** Setup dell'ambiente virtuale (`venv`) e installazione rigorosa delle dipendenze.
* **Sotto-fase 1.2:** Inizializzazione del progetto Flet con struttura a componenti.
* **Sotto-fase 1.3:** Creazione del Router per gestire lo scambio fluido tra la "Schermata di Login Nativa", la "WebView" e la "Dashboard Statistiche".

### Fase 2: Implementazione WebView e Sicurezza Biometrica
**Obiettivo:** Mostrare il sito e proteggerlo.
* **Sotto-fase 2.1:** Implementazione di `flet-webview` che punta all'URL di Dimetior.
* **Sotto-fase 2.2:** Creazione dell'interfaccia nativa di "Lock Screen".
* **Sotto-fase 2.3:** Integrazione delle API biometriche (FaceID/Fingerprint) per sbloccare l'app.
* **Sotto-fase 2.4:** Implementazione di `keyring` per salvare e recuperare crittograficamente le credenziali.

### Fase 3: Iniezione JavaScript e Auto-Login
**Obiettivo:** Automatizzare l'inserimento dati e recuperare le ore dal sito.
* **Sotto-fase 3.1:** Stesura dello script JS (`auto_login.js`) per compilare gli `input` del sito.
* **Sotto-fase 3.2:** Iniezione asincrona dello script (`on_page_ended`).
* **Sotto-fase 3.3:** Modifica del DOM per inserire il bottone "📊 Statistiche App".
* **Sotto-fase 3.4:** Scrittura dello scraper JS per inviare i valori a Python.

### Fase 4: Database Locale e Dashboard Statistiche
**Obiettivo:** Trasformare i dati raccolti in grafici nativi.
* **Sotto-fase 4.1:** Setup di SQLite e creazione della tabella `timelogs`.
* **Sotto-fase 4.2:** Creazione API interna Python per il salvataggio dei log.
* **Sotto-fase 4.3:** Sviluppo della UI "Dashboard" in Flet (BarCharts, trend).

### Fase 5: Compilazione, Testing e Rilascio
**Obiettivo:** Trasformare lo script Python in un'app installabile.
* **Sotto-fase 5.1:** Utilizzo del comando `flet build apk`.
* **Sotto-fase 5.2:** Configurazione dei permessi nativi (INTERNET, USE_BIOMETRIC).
* **Sotto-fase 5.3:** Esecuzione di test end-to-end su dispositivo Samsung.

---

## 🚀 ESECUZIONE ATTUALE: Fasi 1-5 completate ✅

### Stack effettivo (aggiornato)
- Python `3.12.10`
- `flet == 0.84.0`
- `flet-webview == 0.84.0`
- `flet-secure-storage == 0.84.0`
- Flutter `3.41.9` (stable)
- Android SDK `36.1.0`

### Struttura del Progetto
```text
geoinroad_pro/
│
├── pyproject.toml         ← configurazione build + [project] dependencies
├── requirements.txt       ← solo per venv locale
├── main.py
├── app_config.py
├── app_state.py
├── views/
│   ├── lock_screen.py
│   ├── web_view.py
│   └── dashboard.py
├── services/
│   ├── credential_store.py
│   ├── js_bridge.py
│   └── timelog_repository.py
├── assets/
│   └── auto_login.js
└── build/
    └── apk/
        └── geoinroad-pro.apk  ← APK 108 MB (build 2026-05-02)