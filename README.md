# Geoin ROAD Pro

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
- Statistiche per giorno, settimana Geoin ROAD e mese corrente.
- Conteggio ore in formato orario reale, non decimale.
- Splash screen con logo animato.
- Blocco del tasto back Android sulle viste principali.
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

## Note

Questo progetto non e un prodotto ufficiale Geoin ROAD. E un caso studio pratico su come migliorare l'esperienza mobile di un portale gia esistente senza modificarne il backend.
