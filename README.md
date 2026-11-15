# Geoin ROAD Pro

> **App non ufficiale, non affiliata a Geoin ROAD né all'azienda. Ognuno usa le proprie credenziali, e i dati restano solo sul proprio telefono.**

## Per i colleghi: come installarla

### 1. Scarica l'APK

1. Dal telefono apri la pagina [Releases](https://github.com/parifede/geoinroad-pro/releases/latest).
2. Nella versione più recente, sotto **Assets**, tocca il file che finisce con `.apk` (per esempio `geoinroad-pro-v1.4.0.apk`). Lascia stare le versioni segnate **Pre-release**: sono di prova.
3. Aspetta la fine del download (circa 75 MB).

### 2. Consenti l'installazione da origini sconosciute

L'app non viene dal Play Store, quindi Android la blocca la prima volta.

1. Apri il file scaricato, dalla notifica del download o dall'app **File** / **Download**.
2. Se compare l'avviso sulle origini sconosciute, tocca **Impostazioni** e attiva **Consenti da questa fonte** per l'app con cui hai aperto il file (Chrome, File...).
3. Torna indietro e tocca **Installa**.
4. Se Play Protect avvisa che l'app non è riconosciuta, tocca **Altri dettagli** e poi **Installa comunque**.

I nomi delle voci cambiano un po' da telefono a telefono.

### 3. Primo accesso

1. Apri **Geoinroad Pro** e inserisci utente e password del portale Geoin ROAD, le stesse che usi sul sito. Tocca **Salva ed Entra**.
2. Se il telefono ha impronta o PIN, Android ti chiede di confermare: serve a proteggere le credenziali salvate. Da lì in poi te lo chiede a ogni apertura dell'app.
3. Si apre il diario. Il menu rapido è il pulsante in basso a sinistra; da lì apri **Statistiche lavoro**.
4. La prima volta le statistiche si riempiono da sole: prima il mese in corso, poi i mesi passati, uno alla volta. Ci vuole un po', e puoi usare l'app nel frattempo.
5. Facoltativo: in **Statistiche** → **Mese** → **Imposta** puoi inserire paga oraria, ore settimanali da contratto, paga straordinaria e diaria per vedere una stima lorda del mese. Le cifre restano sul telefono. È una stima indicativa, non è la busta paga.

### Aggiornare

- Scarica il nuovo APK dalle Releases e installalo sopra quello vecchio: credenziali e dati restano.
- **Se hai la 1.3.0 o una versione precedente** (anche una pre-release), Android rifiuta l'aggiornamento: quelle versioni erano firmate con un'altra chiave. Disinstalla la vecchia app una volta, installa la nuova e rifai l'accesso. Dalla V1.3.1 in poi gli aggiornamenti si installano sopra senza problemi.

### Uscire

Menu rapido → **Log out**: cancella dal telefono credenziali, statistiche e cifre della stima.

La **segnalazione bug** parte solo se la invii tu su WhatsApp. Contiene dati tecnici (versione dell'app, pagina aperta, un breve estratto del testo della pagina, dove può comparire il tuo nome) e le ore e i tipi di giornata del periodo che stai guardando. Non contiene mai la password.

---

Un'app Android non ufficiale, costruita con Python e Flet, nata per rendere piu comodo l'uso quotidiano del portale Geoin ROAD da smartphone.

## Caso Studio

L'idea e nata da un problema molto concreto: il sito Geoin ROAD funzionava, ma per un driver era scomodo da usare ogni giorno. Le informazioni importanti erano sparse tra diario, calendario e rotte assegnate; le statistiche di lavoro richiedevano controlli manuali; alcune azioni frequenti, come ricaricare la pagina, aprire le statistiche o segnalare un problema, non erano immediate da mobile.

L'obiettivo non era riscrivere il portale, ma costruire un wrapper Android leggero intorno al sito esistente:

- accesso automatico con credenziali salvate sul dispositivo;
- WebView a tutto schermo con barra di caricamento superiore rosa;
- menu rapido flottante in basso a sinistra;
- segnalazione bug tramite WhatsApp con report gia compilato;
- dashboard locale con ore e giorni lavorati;
- salvataggio locale dei dati per rendere le statistiche piu veloci;
- tema e splash coerenti con il brand.

## Problema

Il punto piu delicato era il calcolo delle ore lavorate. Il sito espone i dati in piu viste, soprattutto diario e calendario, e non sempre mostra una rotta completa per ogni giorno. Inoltre il calendario puo mostrare turni futuri gia programmati, che non devono essere contati come ore lavorate.

La prima soluzione basata solo sulla pagina corrente non bastava: leggeva bene il giorno visibile, ma non ricostruiva correttamente settimane e mesi.

## Soluzione

La soluzione finale usa una WebView controllata dall'app:

1. L'app effettua il login nel portale.
2. Uno script JavaScript locale legge diario, calendario e righe disponibili dal sito.
3. I dati vengono passati al codice Python tramite bridge.
4. Python normalizza turni, date e durate.
5. I dati vengono salvati in un archivio locale collegato all'account.
6. La dashboard legge prima il database locale, cosi si apre velocemente.

Per evitare conteggi sbagliati, l'app ignora i giorni futuri rispetto al giorno dello scraping, ma mantiene tutti i giorni precedenti e il giorno corrente. In questo modo un turno pianificato per domani non viene sommato alle ore gia lavorate.

## Funzioni Principali

- Login automatico con fallback locale.
- Drawer flottante con ricarica, statistiche lavoro, segnala bug e logout.
- Logout con cancellazione credenziali e dati locali dell'account.
- Statistiche per giorno, settimana Geoin ROAD e mese, con lo storico dei mesi passati scaricato una volta sola.
- Stima lorda del mese con paga, straordinari e diaria inseriti dall'utente.
- Credenziali nel vault protetto del telefono (impronta o PIN), mai in chiaro.
- Conteggio ore in formato orario reale, non decimale.
- Splash screen con logo animato.
- Tasto back Android: indietro nel portale, dalle statistiche torna al diario.
- Test automatici per scraping, dashboard, credenziali, logout e navigazione.

## Stack Tecnico

- Python
- Flet
- Flutter generato da Flet
- WebView Android
- JavaScript injection controllata
- SQLite locale
- unittest

## Avvio in Sviluppo

Installa le dipendenze Python e avvia l'app in debug Flet:

```powershell
.\.uv-venv\Scripts\flet.exe debug android --device-id emulator-5554 --yes --skip-flutter-doctor --no-rich-output .
```

Esegui i test:

```powershell
.\.uv-venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Distribuzione

L'APK viene costruito e pubblicato automaticamente da GitHub Actions a ogni
tag `v*`, con la `v` minuscola (un tag `V1.3.1` maiuscolo non avvia nulla).
Prima di creare il tag, `APP_VERSION` in `app_config.py` e `version` in
`pyproject.toml` devono avere la stessa versione. Per rilasciare:

```bash
git tag v1.4.0
git push origin v1.4.0
```

Dopo circa 20 minuti l'APK compare nella pagina
[Releases](https://github.com/parifede/geoinroad-pro/releases): basta
condividere il link ai colleghi, che possono scaricarlo e installarlo
direttamente (serve consentire l'installazione da origini sconosciute).
Un tag con suffisso, ad esempio `v1.2.0-rc1`, viene pubblicato come
pre-release di prova.

## Note

Questo progetto non e un prodotto ufficiale Geoin ROAD. E un caso studio pratico su come migliorare l'esperienza mobile di un portale gia esistente senza modificarne il backend.
