# Hunter x Hunter: Wonder Adventure - Patch Italiana (PSP)

Traduzione amatoriale completa in italiano per **Hunter x Hunter: Wonder Adventure** (PSP, `NPJH-50624`).

## Caratteristiche della Patch v1.0
- **2.386 stringhe di testo tradotte** in italiano (storia, dialoghi, menu, missioni, oggetti, abilita', tutorial e descrizioni) con terminologia fedele all'anime.
- **Menu e grafiche UI localizzate**: Schermata Titolo, Menu Principale, Selezione Personaggio, Personalizzazione, Modalita' Storia/Missione, Capitoli (`CAPITOLO 01..08`), Luoghi (`LUOGO 01..09`), HUD di battaglia e schermata di avviso iniziale.
- **Menu di sistema PSP / uscita gioco (`HOME`) forzato in italiano** (`sceImposeSetLanguageMode` -> Italiano).
- **Patch binaria XOR leggera (`8.07 MB`)** con verifica SHA-256 automatica della ISO originale e di quella generata.

## Come Applicare la Patch

1. Scarica **`Patch_Italiano_Hunter_x_Hunter_PSP.zip`** dalla sezione **[Releases](https://github.com/figarocool/Hunter-x-Hunter-Wonder-Adventure-Italian-Language-Patch-/releases)** ed estrailo in una cartella.
2. Copia nella stessa cartella la tua ISO originale giapponese (`NPJH-50624`, `882.704.384` byte).
3. Avvia lo script:
   - **Windows**: doppio clic su `applica_patch_ita.bat` (richiede Python 3)
   - **Linux / macOS**: `./applica_patch_ita.sh` oppure `python3 applica_patch_ita.py`
4. Verranno verificati gli hash e creata automaticamente la ISO **`Hunter x Hunter - Wonder Adventure (ITA).iso`**.
5. Copia la ISO generata su **PS Vita** (`ux0:pspemu/ISO/`) per **Adrenaline**, su PSP (`ms0:/ISO/`), oppure aprila con **PPSSPP**.

## Note
- Questo repository contiene esclusivamente gli strumenti di patching e i sorgenti di traduzione; **non include** file protetti da copyright o ISO di gioco.
