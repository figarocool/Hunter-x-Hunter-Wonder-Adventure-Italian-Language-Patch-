import hashlib
import lzma
import os
import struct
import zipfile

ORIG_ISO = "/tmp/hxh_iso/pa-hxhwaj.iso"
ITA_ISO = "/home/stefano/Scaricati/Hunter x Hunter - Wonder Adventure (ITA).iso"
OUT_ZIP = "/home/stefano/Scaricati/Patch_Italiano_Hunter_x_Hunter_PSP.zip"
WORK_DIR = "/tmp/hxh_patch_pkg"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def create_xor_delta(orig_path: str, mod_path: str) -> bytes:
    """Create LZMA-compressed sector XOR delta between orig_path and mod_path."""
    buf = bytearray(b"HXHPATCH1")
    orig_size = os.path.getsize(orig_path)
    mod_size = os.path.getsize(mod_path)
    assert orig_size == mod_size
    buf.extend(struct.pack("<Q", orig_size))

    orig_sha = bytes.fromhex(sha256_file(orig_path))
    mod_sha = bytes.fromhex(sha256_file(mod_path))
    buf.extend(orig_sha)
    buf.extend(mod_sha)

    chunks = []
    with open(orig_path, "rb") as f1, open(mod_path, "rb") as f2:
        offset = 0
        cur_start = None
        cur_xor = bytearray()
        while True:
            b1 = f1.read(2048)
            b2 = f2.read(2048)
            if not b1:
                break
            if b1 != b2:
                if cur_start is None:
                    cur_start = offset
                x = (int.from_bytes(b1, "little") ^ int.from_bytes(b2, "little")).to_bytes(len(b1), "little")
                cur_xor.extend(x)
            else:
                if cur_start is not None:
                    chunks.append((cur_start, bytes(cur_xor)))
                    cur_start = None
                    cur_xor.clear()
            offset += len(b1)
        if cur_start is not None:
            chunks.append((cur_start, bytes(cur_xor)))

    payload = bytearray()
    payload.extend(struct.pack("<I", len(chunks)))
    for off, data in chunks:
        payload.extend(struct.pack("<QI", off, len(data)))
        payload.extend(data)

    buf.extend(lzma.compress(bytes(payload), preset=6))
    return bytes(buf)


APPLY_SCRIPT = r'''#!/usr/bin/env python3
import hashlib
import lzma
import os
import shutil
import struct
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PATCH_FILE = os.path.join(SCRIPT_DIR, "patch_ita.bin")
DEFAULT_ORIG_NAMES = [
    "pa-hxhwaj.iso",
    "Hunter x Hunter - Wonder Adventure (Japan).iso",
    "Hunter x Hunter - Wonder Adventure.iso",
]
OUT_NAME = "Hunter x Hunter - Wonder Adventure (ITA).iso"


def sha256_file(path: str) -> bytes:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.digest()


def find_orig_iso() -> str:
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        return sys.argv[1]
    for name in DEFAULT_ORIG_NAMES:
        p = os.path.join(SCRIPT_DIR, name)
        if os.path.isfile(p):
            return p
    for fn in sorted(os.listdir(SCRIPT_DIR)):
        if fn.lower().endswith(".iso") and "(ita)" not in fn.lower():
            return os.path.join(SCRIPT_DIR, fn)
    return ""


def main():
    print("============================================================")
    print("  Hunter x Hunter: Wonder Adventure - Patch Italiana v1.0")
    print("============================================================")
    if not os.path.isfile(PATCH_FILE):
        print(f"ERRORE: File patch non trovato: {PATCH_FILE}")
        sys.exit(1)

    orig_iso = find_orig_iso()
    if not orig_iso:
        print("ERRORE: ISO originale giapponese non trovata nella cartella!")
        print("Copia la ISO giapponese (NPJH-50624, 882.704.384 byte) in questa cartella")
        print("oppure trascinala su applica_patch_ita.bat.")
        sys.exit(1)

    with open(PATCH_FILE, "rb") as pf:
        magic = pf.read(9)
        if magic != b"HXHPATCH1":
            print("ERRORE: Formato patch_ita.bin non valido!")
            sys.exit(1)
        expected_size = struct.unpack("<Q", pf.read(8))[0]
        orig_sha = pf.read(32)
        mod_sha = pf.read(32)
        comp_payload = pf.read()

    if os.path.getsize(orig_iso) != expected_size:
        print(f"ERRORE: Dimensione ISO errata ({os.path.getsize(orig_iso)} byte, attesi {expected_size} byte).")
        sys.exit(1)

    print("Verifica integrita' ISO originale in corso...")
    if sha256_file(orig_iso) != orig_sha:
        print("ERRORE: La ISO fornita non corrisponde al dump giapponese originale (SHA-256 diverso).")
        sys.exit(1)

    out_iso = os.path.join(SCRIPT_DIR, OUT_NAME)
    print(f"Creazione di '{OUT_NAME}'...")
    shutil.copyfile(orig_iso, out_iso)

    print("Applicazione patch italiana...")
    payload = lzma.decompress(comp_payload)
    num_chunks = struct.unpack_from("<I", payload, 0)[0]
    pos = 4
    with open(out_iso, "r+b") as out_f:
        for _ in range(num_chunks):
            off, sz = struct.unpack_from("<QI", payload, pos)
            pos += 12
            xor_data = payload[pos : pos + sz]
            pos += sz
            out_f.seek(off)
            orig_data = out_f.read(sz)
            patched = (int.from_bytes(orig_data, "little") ^ int.from_bytes(xor_data, "little")).to_bytes(sz, "little")
            out_f.seek(off)
            out_f.write(patched)

    print("Verifica integrita' ISO italiana generata...")
    if sha256_file(out_iso) != mod_sha:
        print("ERRORE: Verifica SHA-256 finale fallita!")
        sys.exit(1)

    print()
    print("COMPLETATO! ISO italiana creata con successo:")
    print(f"  {out_iso}")
    print("Puoi copiarla direttamente su PS Vita (ux0:pspemu/ISO/) o aprirla con PPSSPP.")


if __name__ == "__main__":
    main()
'''

BAT_SCRIPT = """@echo off
python "%~dp0applica_patch_ita.py" %*
pause
"""

SH_SCRIPT = """#!/bin/bash
cd "$(dirname "$0")"
python3 applica_patch_ita.py "$@"
"""

README_TXT = """====================================================================
  HUNTER x HUNTER: WONDER ADVENTURE (PSP) - PATCH ITALIANA v1.0
====================================================================

Questa patch converte la ISO originale giapponese di Hunter x Hunter:
Wonder Adventure (NPJH-50624) in una ISO giocabile in italiano,
compatibile con PS Vita (Adrenaline), PSP e PPSSPP.

CONTENUTO TRADOTTO:
- Tutti i menu, sottomenu, opzioni, abilita' Nen, missioni e obiettivi
- Messaggi di sistema, salvataggio, installazione dati e avvisi
- Tutti gli 89 capitoli della Modalita' Storia ed eventi con terminologia
  fedele all'anime italiano (Hunter, Esame per Hunter, Nen, Ten/Zetsu/
  Ren/Hatsu, Jajanken, Jenny, Arena Celeste, Isola Balena, ecc.)
- Grafiche UI tradotte (Menu Pausa, Game Over, Menu Risultati, Installazione)
- Menu di uscita PSP/Adrenaline (Si/No) impostato in italiano

COME APPLICARE LA PATCH:
1. Estrai tutti i file di questo archivio in una cartella.
2. Copia nella stessa cartella la tua ISO originale giapponese:
   "pa-hxhwaj.iso" oppure "Hunter x Hunter - Wonder Adventure (Japan).iso"
   (dimensione esatta: 882.704.384 byte)
3. Avvia la patch:
   - Su Windows: doppio click su "applica_patch_ita.bat"
     (oppure trascina la ISO su applica_patch_ita.bat; richiede Python 3)
   - Su Linux / macOS: esegui "./applica_patch_ita.sh"
     (oppure "python3 applica_patch_ita.py percorso/della/iso.iso")
4. Verra' creata la ISO:
   "Hunter x Hunter - Wonder Adventure (ITA).iso"
5. Copia la ISO su PS Vita in "ux0:pspemu/ISO/" e gioca con Adrenaline!
"""


def main():
    os.makedirs(WORK_DIR, exist_ok=True)
    print("Generating XOR binary delta...")
    delta = create_xor_delta(ORIG_ISO, ITA_ISO)
    patch_path = os.path.join(WORK_DIR, "patch_ita.bin")
    with open(patch_path, "wb") as f:
        f.write(delta)
    print(f"patch_ita.bin size: {len(delta) / (1024 * 1024):.2f} MB")

    apply_py = os.path.join(WORK_DIR, "applica_patch_ita.py")
    with open(apply_py, "w", encoding="utf-8") as f:
        f.write(APPLY_SCRIPT)
    os.chmod(apply_py, 0o755)

    apply_bat = os.path.join(WORK_DIR, "applica_patch_ita.bat")
    with open(apply_bat, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(BAT_SCRIPT)

    apply_sh = os.path.join(WORK_DIR, "applica_patch_ita.sh")
    with open(apply_sh, "w", encoding="utf-8") as f:
        f.write(SH_SCRIPT)
    os.chmod(apply_sh, 0o755)

    readme_path = os.path.join(WORK_DIR, "LEGGIMI.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(README_TXT)

    # Test applying the patch right now
    import subprocess
    test_orig = os.path.join(WORK_DIR, "pa-hxhwaj.iso")
    os.symlink(ORIG_ISO, test_orig)
    subprocess.run(["python3", apply_py], check=True)
    out_test = os.path.join(WORK_DIR, "Hunter x Hunter - Wonder Adventure (ITA).iso")
    assert sha256_file(out_test) == sha256_file(ITA_ISO), "Self-test SHA256 mismatch!"
    os.remove(test_orig)
    os.remove(out_test)

    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fn in ["patch_ita.bin", "applica_patch_ita.py", "applica_patch_ita.bat", "applica_patch_ita.sh", "LEGGIMI.txt"]:
            zf.write(os.path.join(WORK_DIR, fn), arcname=fn)

    print(f"Created distributable patch package: {OUT_ZIP} ({os.path.getsize(OUT_ZIP) / (1024 * 1024):.2f} MB)")


if __name__ == "__main__":
    main()
