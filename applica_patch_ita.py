#!/usr/bin/env python3
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
