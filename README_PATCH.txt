Gestione Turni v1.6.6 - Dashboard adattiva

Base: v1.6.5. Questa patch NON include ancora il suono Smart TV.

Modifiche:
- Dashboard adattata all'area realmente disponibile dello schermo.
- Ridotta la dimensione minima della finestra per PC con scaling Windows 125%/150%.
- Contenuto Dashboard inserito in area scorrevole verticale.
- I pulsanti Aggiorna, Storico completo e Chiudi restano sempre visibili in basso.
- Nessuna modifica a statistiche, storico, code, Server/Client o display TV.

Copia i file nel progetto v1.6.5 mantenendo le cartelle, poi ricrea build/dist con PyInstaller e compila Installer.iss con Inno Setup.

Il precedente pacchetto 1.6.6 Audio Smart TV NON va applicato insieme a questo: il suono verra integrato nella successiva v1.6.7 dopo aver verificato la Dashboard.
