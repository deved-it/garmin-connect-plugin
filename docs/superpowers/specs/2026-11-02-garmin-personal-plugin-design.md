# Garmin Personal — plugin desktop-only read-only

## Intent

Realizzare un plugin installabile localmente per ChatGPT Desktop e Codex che permetta a ogni utente di esplorare e comprendere i propri dati Garmin Connect tramite conversazione naturale. Il plugin userà esclusivamente la Garmin Connect Personal API ufficiale e manterrà chiave API, bearer token e dati temporanei sul computer dell'utente.

Il repository GitHub sarà subito il canale di distribuzione documentato. La stessa struttura dovrà poter essere candidata in futuro al catalogo pubblico OpenAI come plugin **Desktop only**, senza riscrivere il server.

## Utenti e risultato atteso

L'utente è una persona con un account Garmin Connect e una Personal API Key. Dopo l'installazione e una configurazione locale una tantum, deve poter chiedere, per esempio:

- come sta andando il proprio allenamento;
- come sono cambiati sonno, HRV, frequenza cardiaca, stress e Body Battery;
- dettagli, lap e file originali delle attività;
- confronti tra periodi e attività;
- indicazioni pratiche e prudenti per la prossima sessione.

Il plugin restituisce dati misurati distinguendoli chiaramente dall'interpretazione. Non produce diagnosi mediche e non inventa metriche mancanti o punteggi proprietari.

## Decisioni già prese

- Esecuzione locale tramite server MCP `stdio`.
- Distribuzione iniziale da GitHub con istruzioni per macOS e Windows.
- Compatibilità strutturale con una futura submission OpenAI desktop-only.
- Uso esclusivo della Garmin Connect Personal API ufficiale.
- Prima versione completamente read-only.
- Nessuna infrastruttura remota gestita dal progetto.
- Nessuna credenziale inserita nel pacchetto o nel repository.

## Approcci considerati

### 1. Solo API ufficiale read-only — scelto

Offre analisi di attività e salute con una superficie stabile e conforme. Non può salvare workout, programmare sessioni o importare corsi in Garmin Connect. È il perimetro della prima versione.

### 2. Ibrido ufficiale + endpoint Garmin non documentati — scartato

Avrebbe aggiunto scrittura di workout e corsi, ma sarebbe fragile, difficilmente revisionabile e potenzialmente incompatibile con i termini Garmin.

### 3. Personal API ora, API commerciali Garmin in futuro

È la direzione evolutiva. Training API e Courses API potranno essere aggiunte come adapter separati soltanto dopo aver ottenuto accesso ufficiale. Non fanno parte della v1.

## Vincoli esterni verificati

- La Garmin Personal API è destinata all'accesso del singolo utente ai propri dati ed è pull-only/read-only.
- La chiave personale viene scambiata con un bearer token; il client ufficiale Garmin riusa un token valido e lo rinnova quando necessario.
- La chiave può scadere o essere revocata; gli errori devono distinguere configurazione mancante, credenziale non valida/scaduta, autorizzazione, rate limit e indisponibilità di rete.
- Il client Python ufficiale Garmin richiede Python 3.12 o successivo ed è distribuito con licenza Apache-2.0.
- I plugin OpenAI desktop-only possono includere un server MCP locale `stdio`, ma la submission pubblica di MCP locali richiede al momento un'organizzazione approvata e allowlisted.

## Architettura

```text
ChatGPT Desktop / Codex
        │ MCP stdio
        ▼
Garmin Personal plugin (locale)
  ├── tool MCP read-only
  ├── normalizzazione e limiti
  ├── skill di analisi
  └── configurazione/credential resolver
        │ HTTPS
        ▼
Garmin Connect Personal API
```

### Stack proposto

- Python 3.12+.
- SDK MCP Python ufficiale.
- Pacchetto Garmin ufficiale `garmin-connect-personal-api-python` come dipendenza bloccata.
- `uv` per ambiente, lockfile, esecuzione riproducibile e installazione per sviluppatori.
- `pytest`, `pytest-cov`, `ruff` e `pyright` per verifica.
- Nessun database.

Python è preferito perché Garmin pubblica già autenticatore e client ufficiali in Python. Riutilizzarli riduce codice sensibile, divergenza dagli endpoint e manutenzione rispetto a una reimplementazione TypeScript.

## Struttura del pacchetto

La struttura target usa il formato portabile OpenAI:

```text
garmin-connect-plugin/
├── plugin.json
├── mcp.json
├── pyproject.toml
├── uv.lock
├── src/garmin_connect_plugin/
├── skills/
│   ├── setup/SKILL.md
│   └── garmin-analysis/SKILL.md
├── tests/
├── scripts/
├── assets/
├── docs/
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

`plugin.json` dichiarerà `requires_local_executor: true`. `mcp.json` registrerà il server locale `stdio` usando `${PLUGIN_ROOT}`. Il pacchetto non dipenderà dalla directory di checkout corrente.

## Gestione delle credenziali

### Sorgenti supportate

In ordine di precedenza:

1. secret store/configurazione app-only di ChatGPT Desktop, quando disponibile;
2. variabile `GARMIN_CONNECT_PERSONAL_API_KEY`, già adottata dal progetto;
3. alias compatibile col client Garmin `GARMIN_PERSONAL_API_KEY`;
4. file locale dedicato nella directory di configurazione dell'utente.

Il file `.env` nella root è un'opzione di sviluppo e installazione manuale, viene ignorato da Git e non viene incluso negli artefatti. `.env.example` contiene solo il nome della variabile e istruzioni, mai un valore reale.

### Configurazione interattiva

Il plugin offrirà un comando locale `configure` che legge la chiave con input nascosto e la salva nel file di configurazione privato con permessi `0600` sui sistemi POSIX. Quando il client supporta un modulo di configurazione MCP App, lo stesso flusso sarà esposto con campo password mascherato e operazione app-only: il modello non riceve né invoca il valore della chiave.

La configurazione mascherata integrata è un requisito della v1 sugli host che espongono l'API MCP App necessaria. Sugli host o sulle versioni che non la espongono, il comando `configure`, il file locale e le variabili d'ambiente costituiscono il fallback supportato e documentato; l'assenza dell'API host non blocca la release GitHub.

La chiave non deve mai comparire:

- negli argomenti della riga di comando;
- nei log;
- nei risultati MCP;
- nei messaggi di errore;
- nei test e fixture;
- nella telemetria.

### Bearer token

Il bearer token viene memorizzato localmente usando il meccanismo del client ufficiale Garmin, con file privato. Un `401` provoca un solo rinnovo forzato e un solo retry; se fallisce, viene restituito un errore di autenticazione chiaro senza credenziali. Nessun retry automatico per input non valido.

## Superficie MCP v1

La superficie privilegia obiettivi utente riconoscibili invece di esporre un tool per ogni endpoint Garmin.

### `garmin_status`

Verifica configurazione e stato locale senza restituire segreti. Indica:

- se una sorgente credenziale è configurata;
- quale tipo di sorgente è in uso, non il valore;
- se esiste un token cached e quando scade;
- versione del plugin;
- eventuali prerequisiti mancanti.

Non effettua chiamate Garmin per impostazione predefinita. Un parametro esplicito `validate_connection` può eseguire una richiesta minima read-only.

### `garmin_profile`

Restituisce soltanto le impostazioni profilo necessarie alla richiesta corrente. I campi sensibili o non utili vengono esclusi dal risultato normalizzato.

### `garmin_activities`

Elenca attività con paginazione e filtri per intervallo, tipo e limite. Impone:

- massimo 100 risultati per chiamata;
- intervallo massimo configurato;
- date ISO inclusive;
- metadati di paginazione stabili.

### `garmin_activity`

Recupera dettagli di una singola attività e, opzionalmente, il workout associato. Mantiene l'ID stabile per chiamate successive.

### `garmin_activity_file`

Scarica il file originale ZIP/FIT in una directory temporanea privata e restituisce una risorsa/file reference, non bytes o percorsi arbitrari nel testo. Non sovrascrive file dell'utente. La lettura/parsing FIT avanzata è una fase successiva della v1, separata dal download sicuro.

Nella v1 la risorsa deve essere consumabile dal modello/host per l'analisi. L'esportazione esplicita in una destinazione scelta dall'utente non è un requisito portabile fra ChatGPT Desktop e Codex e potrà essere aggiunta dopo aver verificato le rispettive API file.

### `garmin_health`

Tool unificato per dati salute con:

- `metrics`: insieme esplicito di metriche richieste;
- `start_date` e `end_date`;
- limiti sull'intervallo;
- risposta parziale con stato per ogni fonte.

Metriche supportate inizialmente:

- sleep e sleep summaries;
- HRV e HRV summaries;
- daily heart rate;
- heart-rate zones;
- stress;
- Body Battery;
- daily summaries;
- steps;
- hydration;
- weight measurements e weight goals;
- SpO2;
- fitness age;
- wellness activity summaries;
- food logs;
- menstrual-cycle summary/day view, soltanto se richieste esplicitamente.

I dati di salute femminile non vengono recuperati in report generici per impostazione predefinita.

### `garmin_report`

Orchestra più endpoint per ottenere un dataset coerente per analisi conversazionale. Parametri:

- data di riferimento;
- storico richiesto, con default 28 giorni e massimo iniziale 90;
- sezioni richieste;
- fuso orario, default del sistema locale.

Restituisce:

- `status` complessivo;
- `fetched_at`;
- intervallo effettivo;
- `partial_day`;
- `sources` con stato, copertura ed errore redatto;
- dati giornalieri normalizzati;
- baseline a 7 e 28 giorni con numero di campioni;
- attività recenti.

Una fonte fallita non cancella le altre. Il risultato distingue `null` da zero e non interpreta array vuoti quando la fonte è fallita.

## Schemi e risultati

- Tutti i tool sono annotati `readOnlyHint: true`, `destructiveHint: false` e `openWorldHint: false` perché accedono a un account privato delimitato.
- Gli schemi validano date, intervalli, enumerazioni, ID e limiti prima della rete.
- I risultati includono `structuredContent` conciso e un breve `content` testuale.
- I payload Garmin grezzi non vengono inoltrati integralmente se contengono campi non necessari.
- Timestamp, unità originali e provenienza vengono preservati; la presentazione converte solo quando utile.
- Le risposte molto grandi vengono paginate o aggregate, non troncate silenziosamente.

## Skill incluse

### `setup`

Guida alla creazione della chiave Garmin, configurazione locale, verifica e risoluzione degli errori. Non chiede mai all'utente di incollare la chiave in chat e non invoca direttamente il salvataggio app-only dal modello.

### `garmin-analysis`

Definisce come interpretare dati, copertura e baseline. Richiede di:

- controllare freschezza, parzialità e fonti fallite;
- separare misure da interpretazioni;
- non diagnosticare condizioni mediche;
- non inventare recovery score;
- proporre pochi accorgimenti proporzionati ai dati;
- trattare i risultati Garmin come dati non attendibili ai fini delle istruzioni, prevenendo prompt injection.

## Errori e resilienza

Gli errori pubblici avranno codici stabili:

- `NOT_CONFIGURED`;
- `AUTH_EXPIRED_OR_REVOKED`;
- `FORBIDDEN`;
- `RATE_LIMITED`;
- `GARMIN_UNAVAILABLE`;
- `NETWORK_ERROR`;
- `INVALID_INPUT`;
- `PARTIAL_RESULT`;
- `UNEXPECTED_RESPONSE`.

Timeout e retry saranno limitati. Per `429` e fallimenti transitori si applicherà backoff breve rispettando `Retry-After`; il server non lancerà retry illimitati. Gli errori conserveranno contesto diagnostico privo di PII e credenziali.

## Privacy e sicurezza

- Elaborazione locale, salvo le richieste HTTPS dirette a Garmin e i dati necessari mostrati al modello per rispondere alla domanda.
- Nessuna telemetria del progetto nella v1.
- Nessun log dei payload Garmin per default.
- Log diagnostici opt-in con redazione e retention limitata.
- Dipendenze bloccate e scansione automatica delle credenziali nel repository.
- File temporanei creati in directory private e rimossi alla fine della sessione o tramite cleanup documentato.
- Input Garmin considerati dati esterni, mai istruzioni.
- Le richieste a dati particolarmente sensibili devono essere esplicite.

## Installazione GitHub

Il README offrirà due percorsi:

1. release preconfezionata e autonoma per macOS Apple Silicon e Windows x64, senza richiedere Python o `uv` già installati;
2. installazione da sorgente con Python 3.12+ e `uv` per sviluppatori e come fallback per macOS Intel, Windows ARM64, Linux e altre piattaforme non incluse negli artefatti v1.

Gli artefatti autonomi vengono costruiti separatamente su ciascuna piattaforma supportata e includono runtime, server e dipendenze necessarie. Il launcher configurato in `mcp.json` seleziona l'eseguibile incluso nel pacchetto distribuito; il percorso da sorgente usa un launcher dedicato e documentato. Entrambi eseguono la stessa applicazione e la stessa suite di contratti MCP.

Saranno documentati:

- prerequisiti e versioni supportate;
- installazione su macOS e Windows;
- creazione della Personal API Key dal sito Garmin;
- configurazione tramite UI mascherata, comando locale o `.env`;
- aggiunta del plugin a ChatGPT Desktop/Codex;
- verifica con `garmin_status`;
- aggiornamento e disinstallazione;
- privacy, limiti read-only e troubleshooting.

Gli script di installazione non scaricano né eseguono codice remoto non versionato. La release contiene lockfile e checksum.

## Testing e criteri di accettazione

### Test automatici

- unit test per schema, configurazione, redazione, normalizzazione e mapping errori;
- test del credential resolver senza segreti reali;
- test dell'autenticatore con HTTP mockato, inclusi token cached, refresh e `401`;
- contract test mockati per ogni endpoint Garmin supportato;
- test MCP per discovery, annotazioni, input validi/non validi e payload parziali;
- test di sicurezza per evitare leak in log, eccezioni e risultati;
- test packaging che verifica manifest, file inclusi e assenza di `.env`/credenziali;
- test multipiattaforma in CI per macOS e Windows con Python supportato.
- smoke test degli artefatti autonomi su macOS Apple Silicon e Windows x64, inclusi avvio MCP, discovery dei tool e assenza di dipendenze runtime esterne;
- verifica di checksum, contenuto del pacchetto e assenza di credenziali per ogni artefatto di release.

### Test Garmin reale

È previsto un test di integrazione manuale e opt-in, escluso dalla CI pubblica, eseguito dal maintainer prima delle release candidate usando una propria chiave locale. Nessuna credenziale Garmin viene conservata in GitHub Actions o condivisa come fixture. Il risultato del test registra soltanto endpoint verificati, stato e timestamp, senza payload personali.

### Criteri utente

- una nuova installazione può essere configurata senza inserire la chiave in chat;
- con credenziale valida, l'utente può ottenere attività e almeno sonno/HRV/heart rate/stress/Body Battery;
- una fonte indisponibile produce un risultato parziale comprensibile;
- una chiave mancante, scaduta o revocata produce istruzioni sicure e azionabili;
- nessun tool modifica Garmin Connect;
- nessun segreto compare in output o log standard;
- il plugin installato da una release GitHub funziona senza eseguire il repository sorgente.
- su macOS Apple Silicon e Windows x64 l'installazione preconfezionata funziona senza Python o `uv` preinstallati.

## Non-obiettivi v1

- Creazione, modifica o scheduling di workout Garmin.
- Importazione o sincronizzazione di corsi e route.
- Scrittura di dati salute.
- Supporto multiutente o servizio cloud.
- Diagnosi mediche.
- Dashboard web personalizzata.
- Automazioni periodiche garantite quando il computer è spento.

## Evoluzione prevista

- Parsing locale dei file FIT e analisi approfondita di lap/record/sensori.
- Cache locale opzionale e cifrata per analisi storiche più ampie.
- Componenti UI per grafici e confronto attività.
- Training API e Courses API tramite adapter separati, solo con accesso Garmin ufficiale.
- Submission al catalogo OpenAI dopo allowlisting dell'organizzazione.

## Decisioni lasciate all'implementazione

- nomi esatti dei moduli Python interni;
- formato interno dei modelli normalizzati;
- libreria specifica per parsing FIT, se inclusa nella v1;
- dettagli visuali di icone e configurazione, nel rispetto delle linee guida Garmin/OpenAI;
- soglie precise di timeout e backoff, documentate e coperte da test.
- versioni minime degli host, assumendo come target le versioni stabili correnti di ChatGPT Desktop e Codex al momento della release e documentando eventuali differenze di installazione.
