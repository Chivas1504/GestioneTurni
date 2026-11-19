## Aggiornamento TV 1.1.0: collegamento automatico

L’APK attuale è `android-tv/output/GestioneTurniTV-1.1.0.apk`.
Installarlo sulla TV sopra la versione 1.0.0, senza disinstallarla: la firma è
la stessa e gli indirizzi manuali precedenti vengono conservati. Per questa
funzione non serve aggiornare i PC già dotati del protocollo di ricerca
(versione 1.10.2 dello studio compresa).

All’apertura la TV cerca automaticamente il server dello studio tramite UDP
50555, poi verifica il display HTTP sulla porta 8080. Non occorre digitare un
indirizzo. Se i PC sono spenti, attende e riprova; se il PC collegato diventa
irraggiungibile, ripete la ricerca. La ricerca non accende i PC o la TV.
TV e PC devono essere nella stessa rete, senza isolamento tra dispositivi.

L’ultimo indirizzo funzionante viene ricordato. Nelle impostazioni restano due
indirizzi manuali facoltativi e la possibilità di disattivare la ricerca automatica.
Le operazioni di rete avvengono fuori dal thread dell’interfaccia. La protezione
dello schermo resta invariata.

Prove da effettuare sulla Xiaomi:
1. Aprire l’app TV con un PC acceso: deve collegarsi senza inserire indirizzi.
2. Aprire la TV prima dei PC, poi avviare Gestione Turni sul PC: deve collegarsi.
3. Con due PC già collegati tra loro, spegnere quello server: attendere
   l’elezione del sostituto e controllare che la TV riprenda gli aggiornamenti.
4. Chiudere e riaprire l’app TV il giorno seguente.

Verifiche locali: 12 test Java superati, compilazione APK riuscita e firma
v1/v2/v3, manifest e allineamento verificati. La prova sulla rete dello studio
e sulla Xiaomi resta necessaria. Nessuna nuova release è stata pubblicata.

---

# Gestione Turni 1.10.2 e app Android TV 1.0.0

## Stato della consegna

Il programma Windows è stato corretto. Il progetto Android TV è nella cartella
`android-tv`. Dopo l'installazione di Microsoft JDK 21 è stato generato l'APK
firmato `android-tv/output/GestioneTurniTV-1.0.0.apk`. La compilazione diretta
usa JDK, D8, AAPT2 e APK Signer degli strumenti Android già presenti sul PC e
non richiede il daemon Gradle, bloccato dalle restrizioni di rete dell'ambiente.
Sono passati i 3 test Java; firma APK v1/v2/v3, integrità ZIP, allineamento e
manifest sono stati verificati. Non è stata effettuata la prova con un emulatore
o con la Xiaomi. Il workflow GitHub è preparato, ma non è stato pubblicato o eseguito.

Installer locale generato: `Installer/Setup_GestioneTurni_v1.10.2.exe`. È stato
verificato l'avvio dell'eseguibile compilato con dati isolati, senza installarlo
sopra la versione già presente sul PC. Non è stata pubblicata una release GitHub.

## Aggiornare i PC dello studio

1. Conservare una copia della cartella dei dati già in uso. Il percorso predefinito
   è `%USERPROFILE%\GestioneTurniData`; un'eventuale variabile
   `GESTIONE_TURNI_DATA_DIR` può cambiarlo.
2. Chiudere Gestione Turni e installare la versione 1.10.2 su tutti i PC dello studio,
   compresi quelli delle segretarie. Le versioni 1.10.0 e 1.10.1 richiedevano un
   codice di collegamento e vanno aggiornate per tornare al collegamento automatico.
3. Collegare i PC alla stessa rete locale e avviare Gestione Turni. Il primo PC
   disponibile gestisce la condivisione; gli altri lo trovano automaticamente.
4. Accedere ai rispettivi account con le password abituali. Ogni segretaria può
   accedere all'account del medico che gestisce. Non serve copiare alcun codice.
5. Verificare che una chiamata del medico o della segretaria aggiorni gli altri PC
   dello stesso account e il display. Le code dei due medici rimangono distinte.

Il pulsante **Collegamento tra PC** è stato rimosso. Eventuali vecchi file
`network.key` non vengono più letti e non richiedono alcun intervento. Account,
impostazioni, turni e timer non vengono eliminati. La TV continua a usare
l'indirizzo mostrato nel programma e non richiede nessun codice.

## Generare l'APK

### APK già pronto e compilazione diretta

Per installare la versione preparata utilizzare
`android-tv/output/GestioneTurniTV-1.0.0.apk`.

Per ricompilarla sullo stesso PC, dal progetto:

```powershell
python -B android-tv/build_apk.py --java-home "C:\Users\matti\AppData\Local\Programs\Microsoft\jdk-21.0.13.102-hotspot"
```

Lo script esegue compilazione delle risorse e del Java, i 3 test JUnit, conversione
DEX, packaging, allineamento, firma e verifica. Usa gli SDK e le dipendenze già
presenti nella cache locale, senza scaricare nulla. Il lint Gradle non viene
eseguito da questo metodo.

La firma stabile generata per questa applicazione è conservata in
`android-tv/private-signing`, esclusa da Git. Conservare una copia privata di
questa cartella insieme al backup del progetto per poter firmare i successivi
aggiornamenti con la stessa identità. Non inviarla alla dottoressa e non
pubblicarla: sulla TV serve solo l'APK.

### Android Studio

1. Installare Android Studio sul proprio PC, senza coinvolgere la dottoressa.
2. Aprire la cartella `android-tv` come progetto.
3. Lasciare che scarichi gli strumenti Android e sincronizzi il progetto.
4. Eseguire **Build APK(s)** per la variante debug.
5. Recuperare `android-tv/app/build/outputs/apk/debug/app-debug.apk`.

È un APK di prova, adatto al collaudo locale. Per distribuire aggiornamenti nel
tempo, generare un APK release firmato e conservare la stessa chiave di firma.
Il progetto accetta `TV_KEYSTORE`, `TV_STORE_PASSWORD`, `TV_KEY_ALIAS` e
`TV_KEY_PASSWORD` come variabili d'ambiente; nessuna chiave è inclusa nel repository.

È disponibile anche `android-tv/Build-AndroidTV.ps1`: richiede JDK 17/21,
Android SDK e Gradle 9.4.1. Esegue compilazione, lint e test, quindi copia l'APK
in `android-tv/output`. Non scarica o installa silenziosamente programmi.

### GitHub (alternativa senza Android Studio)

Dopo aver portato le modifiche nel repository GitHub, aprire **Actions → Compila
e verifica app Android TV → Run workflow**. Il workflow manuale compila, esegue
lint e test e rende disponibile l'APK di prova come artifact. Non pubblica una
release. Ogni esecuzione usa una firma debug temporanea: tra build differenti
potrebbe essere necessario disinstallare l'APK precedente (gli indirizzi salvati
vanno reinseriti). Per l'uso continuativo scegliere una firma release stabile.

## Installazione sulla Xiaomi

1. Trasferire l'APK alla TV tramite chiavetta USB oppure un'app di trasferimento
   disponibile su entrambi i dispositivi. Disponibilità e voci dei menu dipendono
   dal modello Xiaomi: non è stato verificato uno specifico file manager.
2. Aprire il file con il gestore file della TV. Autorizzare, se richiesto,
   l'installazione da quella fonte. Dopo l'installazione si può revocare l'autorizzazione.
3. Aprire **Gestione Turni TV** dall'elenco delle app.
4. Inserire l'indirizzo TV mostrato nel programma Windows. Sono accettati
   indirizzi IPv4 locali, per esempio `192.168.1.10` oppure
   `http://192.168.1.10:8080/`. Non inventare l'indirizzo: copiarlo dal PC.
5. Se ci sono due PC, inserire anche il secondo indirizzo, facoltativo. L'app li
   ricorda e li riprova quando la pagina iniziale non è raggiungibile.
6. Premere **Salva e apri**. Per cambiare indirizzi usare **Impostazioni**.
   **MENU** o **Indietro** apre le opzioni, incluso **Esci**.

La TV e i PC devono essere sulla stessa rete. Le prenotazioni DHCP nel router
evitano che cambino gli indirizzi dopo un riavvio. Il programma PC deve rimanere
aperto e raggiungibile sulla porta 8080.

## Prova da fare prima dell'uso con i pazienti

Usare dati fittizi:

1. Verificare la comparsa di una coda, un incremento, un cognome, l'audio e la
   scomparsa della coda quando viene terminata.
2. Con due PC aggiornati e collegati, verificare entrambe le code e il cambio
   server quando il primo programma viene chiuso. Provare anche ad aprire l'app
   TV quando il primo PC è già spento, avendo impostato il secondo indirizzo.
3. Interrompere e ripristinare la rete: il display deve mostrare la disconnessione
   e riprendersi senza riscrivere l'indirizzo.
4. Lasciare la TV sulla coda per almeno 60–120 minuti senza toccare il telecomando.
   Verificare anche un intero orario di ambulatorio.
5. Premere Home e controllare che, uscendo dall'app, il normale risparmio
   energetico torni a funzionare.

L'app imposta `FLAG_KEEP_SCREEN_ON` mentre è in primo piano, anche durante le
riconnessioni, e lo rilascia quando si esce. Non simula pressioni del telecomando,
non cambia impostazioni di sistema e non richiede root.

**Questo non garantisce l'eliminazione di qualsiasi standby Xiaomi.** Android 11+
può applicare un distinto `attentive_timeout` che prevale anche su questo flag.
Se la prova fallisce, annotare il tempo preciso, se compare un avviso e cosa
mostra la TV al risveglio. Per una diagnosi tecnica, con ADB già autorizzato,
`adb shell settings get secure attentive_timeout` legge l'eventuale impostazione;
un risultato `null` non esclude un valore predefinito del produttore. Non viene
modificata automaticamente alcuna impostazione.

Riferimenti ufficiali:

- https://developer.android.com/develop/background-work/background-tasks/awake/screen-on
- https://source.android.com/docs/core/power/tv-standby

## Correzioni nel programma Windows

- Ripristinata la ricerca automatica dei PC sulla rete locale, senza codici o
  abbinamento. La password di accesso agli account continua a funzionare.
- Rimossa la cifratura introdotta insieme al codice di collegamento. Il trasporto
  usa nuovamente JSON sulla rete locale, come nelle versioni iniziali.
- Lettura completa dei messaggi TCP anche se frammentati, fino a 4 MiB, senza
  considerare una singola lettura come un messaggio completo. Sono accettati
  anche i messaggi JSON originali senza newline finale.
- Ripristino degli aggiornamenti in uscita in caso di risposta non valida e
  deduplicazione delle ritrasmissioni dotate di identificatore di consegna.
- Il server applica gli aggiornamenti prima di rispondere, evitando di confermare
  immediatamente uno stato precedente.
- Conservate le correzioni di timer, pausa, lettura dei turni, modalità cognome,
  orologio del display, aggiornamento del contenuto e controllo SHA-256 installer.
- Record account identici non vengono riscritti a ogni heartbeat; versioni di
  protocollo malformate vengono rifiutate senza eccezioni.
- La compilazione Windows esclude librerie ICU estranee trovate nel PATH, che
  altrimenti possono impedire l'importazione di QtCore nell'eseguibile.

## Verifica ripetibile

In un ambiente Python con le dipendenze di `requirements.txt`:

```powershell
python -B -m unittest discover -s tests -v
node tests/test_display.cjs
```

I test usano cartelle temporanee nel progetto, dati fittizi e Qt senza finestre.
Non leggono i dati reali della dottoressa. I test di rete reali vengono saltati
quando l'ambiente blocca le connessioni loopback; i test del flusso JSON e degli
handler HTTP senza socket vengono comunque eseguiti. I test Android sono nel
progetto Gradle e richiedono la toolchain Android.

Esito della verifica locale: 22 test Python, 20 superati e 2 saltati perché il
sandbox impedisce le connessioni loopback; 9 scenari JavaScript superati. I test
includono chiamata numerica, timer, mancato salvataggio, messaggi oltre 64 KiB,
discovery automatico di quattro PC, assenza di codici, ritrasmissione,
deduplicazione, conferma dopo applicazione sul thread Qt e checksum installer.
Anche il Java Android e le risorse sono stati compilati e i 3 test JUnit Android
sono passati; firma, integrità e allineamento del pacchetto sono validi.
Lint Gradle, prova nell'emulatore e collaudo sulla TV rimangono da completare.

## Correzione timer 1.10.2

- In modalità numero, premere Inizia coda avvia subito il timer del numero
  corrente; +1 conclude il precedente e riparte da zero.
- In modalità cognome, il timer parte premendo Chiama. Una nuova chiamata
  con lo stesso cognome riavvia il conteggio. Cancellare il cognome lo ferma.
- La pausa viene salvata e ripristinata dopo la riapertura; il tempo trascorso
  in pausa non viene sommato alla visita quando si riprende.
- Il salvataggio delle impostazioni ritenta in caso di un blocco temporaneo
  del file, senza interrompere subito l'avvio o la pausa del timer.
- Termina coda ferma il timer. Per provare la correzione dopo l'aggiornamento,
  terminare un'eventuale coda già attiva e avviarne una nuova.
- Aggiunti test dei pulsanti reali della finestra, dell'avanzamento del testo
  del timer, del cambio paziente, della pausa al riavvio e dei cognomi uguali.

La 1.10.2 conserva tutte le correzioni del timer ma torna alla condivisione LAN
automatica senza codici. L'APK TV 1.0.0 già preparato rimane utilizzabile e non
deve essere ricompilato per questa modifica.
