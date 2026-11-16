import io
import os
import struct
import sys
import zlib
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ss_tools import unswizzle_psp, swizzle_psp

PACK_MAGIC = 0x4B636150  # "PacK"
PACK_LBA_DEFAULT = 158832


def compress_gzip_psp(data: bytes) -> bytes:
    """Compress bytes as standard gzip (wbits=31, no mtime)."""
    c = zlib.compressobj(9, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
    return c.compress(data) + c.flush()


def decompress_gzip_psp(data: bytes) -> bytes:
    return zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(data)


def parse_packfile_toc(head: bytes, pack_lba: int = PACK_LBA_DEFAULT):
    magic, cnt = struct.unpack_from("<II", head, 0)
    assert magic == PACK_MAGIC, hex(magic)
    s1 = pack_lba + 0x20
    entries = []
    for i in range(cnt):
        w0, w1, w2, w3 = struct.unpack_from("<4I", head, 16 + i * 16)
        lba = ((w0 ^ PACK_MAGIC) + s1) & 0xFFFFFFFF
        uncomp_sz = w1 ^ i
        comp_sz = (w2 ^ 0xAAAAAAAA) ^ 0xE1C9CBFA
        datainst_off = w3 ^ i
        entries.append({
            "index": i,
            "lba": lba,
            "offset": (lba - pack_lba) * 2048,
            "uncomp_sz": uncomp_sz,
            "comp_sz": comp_sz,
            "datainst_off": datainst_off,
        })
    for i in range(cnt):
        if i + 1 < cnt:
            entries[i]["slot_sz"] = entries[i + 1]["offset"] - entries[i]["offset"]
        else:
            entries[i]["slot_sz"] = 0
    return entries


def encode_packfile_toc_entry(head: bytearray, idx: int, lba: int, uncomp_sz: int, comp_sz: int, datainst_off: int, pack_lba: int = PACK_LBA_DEFAULT):
    s1 = pack_lba + 0x20
    w0 = ((lba - s1) & 0xFFFFFFFF) ^ PACK_MAGIC
    w1 = uncomp_sz ^ idx
    w2 = (comp_sz ^ 0xE1C9CBFA) ^ 0xAAAAAAAA
    w3 = datainst_off ^ idx
    struct.pack_into("<4I", head, 16 + idx * 16, w0, w1, w2, w3)


def parse_container(b: bytes):
    first_off = struct.unpack_from("<I", b, 0)[0] & 0x00FFFFFF
    max_n = first_off // 4
    offs, pads = [], []
    has_end = False
    for i in range(max_n):
        v, = struct.unpack_from("<I", b, i * 4)
        off = v & 0x00FFFFFF
        pad = v >> 24
        if off == len(b):
            has_end = True
            break
        if i > 0 and off == 0:
            break
        offs.append(off)
        pads.append(pad)
    items = []
    for i in range(len(offs)):
        end = offs[i + 1] if i + 1 < len(offs) else len(b)
        items.append(b[offs[i] : end - pads[i]])
    return items, has_end, first_off


def build_container(items, has_end_marker: bool, hdr_sz: int) -> bytes:
    out = bytearray(hdr_sz)
    cur = hdr_sz
    for i, data in enumerate(items):
        pad = (-len(data)) & 0x3F
        struct.pack_into("<I", out, i * 4, cur | (pad << 24))
        out.extend(data)
        out.extend(b"\x00" * pad)
        cur += len(data) + pad
    if has_end_marker:
        struct.pack_into("<I", out, len(items) * 4, cur)
    return bytes(out)


def parse_0x64(b: bytes):
    magic, n = struct.unpack_from("<II", b, 0)
    assert magic == 0x64, hex(magic)
    cnt = n + 1
    hdr48 = b[:0x48]
    ptrs = struct.unpack_from(f"<{cnt}I", b, 0x48)
    strs = []
    for p in ptrs:
        end = b.find(b"\x00\x00", p)
        while end >= 0 and (end - p) % 2 != 0:
            end = b.find(b"\x00\x00", end + 1)
        if end < 0:
            end = len(b)
        strs.append(b[p:end].decode("utf-16le", errors="replace"))
    return hdr48, strs


def build_0x64(hdr48: bytes, strs: list) -> bytes:
    cnt = len(strs)
    pool_start = 0x48 + cnt * 4
    ptrs = []
    pool = bytearray()
    for s in strs:
        ptrs.append(pool_start + len(pool))
        pool.extend(s.encode("utf-16le") + b"\x00\x00")
    out = bytearray(hdr48)
    out.extend(struct.pack(f"<{cnt}I", *ptrs))
    out.extend(pool)
    return bytes(out)


def parse_tex_psp(b: bytes):
    assert b[:16] == b"texture PSP 1.00"
    cnt, = struct.unpack_from("<I", b, 0x18)
    descs = []
    for i in range(cnt):
        pix_off, pal_off, w, h, fmt, u0, u1, u2, u3 = struct.unpack_from("<IIHHIIIII", b, 0x20 + i * 32)
        im = None
        if fmt == 4:
            rb = ((w // 2) + 15) & ~15
            raw_pix = unswizzle_psp(b[pix_off : pix_off + rb * h], rb, h)
            pal = b[pal_off : pal_off + 16 * 4]
            im = Image.new("RGBA", (w, h))
            px = im.load()
            for y in range(h):
                for x in range(w):
                    byte = raw_pix[y * rb + x // 2]
                    ci = (byte & 0x0F) if (x & 1) == 0 else (byte >> 4)
                    px[x, y] = tuple(pal[ci * 4 : ci * 4 + 4])
        elif fmt == 5:
            rb = (w + 15) & ~15
            raw_pix = unswizzle_psp(b[pix_off : pix_off + rb * h], rb, h)
            pal = b[pal_off : pal_off + 256 * 4]
            im = Image.new("RGBA", (w, h))
            px = im.load()
            for y in range(h):
                for x in range(w):
                    ci = raw_pix[y * rb + x]
                    px[x, y] = tuple(pal[ci * 4 : ci * 4 + 4])
        elif fmt == 3:
            rb = (w * 4 + 15) & ~15
            raw_pix = unswizzle_psp(b[pix_off : pix_off + rb * h], rb, h)
            im = Image.new("RGBA", (w, h))
            px = im.load()
            for y in range(h):
                for x in range(w):
                    px[x, y] = tuple(raw_pix[y * rb + x * 4 : y * rb + x * 4 + 4])
        descs.append({
            "index": i,
            "pix_off": pix_off,
            "pal_off": pal_off,
            "width": w,
            "height": h,
            "fmt": fmt,
            "image": im,
        })
    return descs


def replace_tex_psp_image(b: bytes, idx: int, new_img: Image.Image) -> bytes:
    pix_off, pal_off, w, h, fmt, _, _, _, _ = struct.unpack_from("<IIHHIIIII", b, 0x20 + idx * 32)
    im = new_img.convert("RGBA")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    out = bytearray(b)
    if fmt == 3:
        rb = (w * 4 + 15) & ~15
        lin = bytearray(rb * h)
        px = im.load()
        for y in range(h):
            for x in range(w):
                lin[y * rb + x * 4 : y * rb + x * 4 + 4] = bytes(px[x, y])
        sw = swizzle_psp(bytes(lin), rb, h)
        out[pix_off : pix_off + len(sw)] = sw
    elif fmt in (4, 5):
        ncolors = 16 if fmt == 4 else 256
        q = im.quantize(colors=ncolors, method=Image.Quantize.FASTOCTREE)
        pal_rgb = q.getpalette()[: ncolors * 3]
        # Preserve transparency via alpha channel matching
        pal_rgba = bytearray(ncolors * 4)
        for ci in range(ncolors):
            pal_rgba[ci * 4 : ci * 4 + 3] = bytes(pal_rgb[ci * 3 : ci * 3 + 3])
            pal_rgba[ci * 4 + 3] = 255
        # Map transparent pixels to index 0
        src_px = im.load()
        q_px = q.load()
        rb = (((w // 2) + 15) & ~15) if fmt == 4 else ((w + 15) & ~15)
        lin = bytearray(rb * h)
        pal_rgba[3] = 0
        for y in range(h):
            for x in range(w):
                a = src_px[x, y][3]
                ci = 0 if a < 32 else max(1, q_px[x, y]) if pal_rgba[3] == 0 else q_px[x, y]
                if fmt == 4:
                    if (x & 1) == 0:
                        lin[y * rb + x // 2] |= (ci & 0x0F)
                    else:
                        lin[y * rb + x // 2] |= ((ci & 0x0F) << 4)
                else:
                    lin[y * rb + x] = ci
        sw = swizzle_psp(bytes(lin), rb, h)
        out[pix_off : pix_off + len(sw)] = sw
        out[pal_off : pal_off + len(pal_rgba)] = pal_rgba
    return bytes(out)


def parse_rhg(rhg: bytes):
    assert rhg[:4] == b"RHG\x00"
    cnt = struct.unpack_from("<I", rhg, 0x14)[0]
    cnt2 = struct.unpack_from("<I", rhg, 0x1C)[0]
    cnt3 = struct.unpack_from("<I", rhg, 0x24)[0]
    t2_off = (0x30 + cnt * 0x28 + 15) & ~15
    pix_descs = [struct.unpack_from("<9I", rhg, t2_off + i * 0x24) for i in range(cnt2)]
    t3_off = t2_off + cnt2 * 0x24
    pal_descs = [struct.unpack_from("<8I", rhg, t3_off + i * 0x20) for i in range(cnt3)]
    pix_cur = (t3_off + cnt3 * 0x20 + 127) & ~127
    pix_offs = []
    for p in pix_descs:
        pix_offs.append(pix_cur)
        pix_cur += p[5]
    pal_cur = len(rhg) - sum(p[5] for p in pal_descs)
    pal_offs = []
    for p in pal_descs:
        pal_offs.append(pal_cur)
        pal_cur += p[5]

    imgs = []
    for i in range(cnt2):
        _, fmt, w, h, _, psz, rb, _, _ = pix_descs[i]
        raw_pix = unswizzle_psp(rhg[pix_offs[i] : pix_offs[i] + psz], rb, h)
        pal = rhg[pal_offs[i] : pal_offs[i] + pal_descs[i][5]] if i < cnt3 else b""
        im = Image.new("RGBA", (w, h))
        if fmt == 0x12 and pal:
            px = im.load()
            for y in range(h):
                for x in range(w):
                    b = raw_pix[y * rb + x // 2]
                    ci = (b & 0xF) if (x & 1) == 0 else (b >> 4)
                    if ci * 4 + 4 <= len(pal):
                        px[x, y] = tuple(pal[ci * 4 : ci * 4 + 4])
        elif fmt == 0x11 and pal:
            im_p = Image.frombytes("P", (rb, h), raw_pix)
            im_p.putpalette(pal, "RGBA")
            im = im_p.convert("RGBA").crop((0, 0, w, h))
        imgs.append({
            "index": i,
            "fmt": fmt,
            "width": w,
            "height": h,
            "rb": rb,
            "psz": psz,
            "pix_off": pix_offs[i],
            "pal_off": pal_offs[i] if i < cnt3 else 0,
            "pal_sz": pal_descs[i][5] if i < cnt3 else 0,
            "image": im,
        })
    return imgs


def replace_rhg_image(rhg: bytes, idx: int, new_img: Image.Image) -> bytes:
    info = parse_rhg(rhg)[idx]
    w, h, fmt, rb = info["width"], info["height"], info["fmt"], info["rb"]
    im = new_img.convert("RGBA")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    ncolors = 16 if fmt == 0x12 else 256
    # Quantize RGB over a neutral opaque backdrop so transparent pixels don't skew palette
    bg = Image.new("RGB", (w, h), (30, 30, 30))
    bg.paste(im.convert("RGB"), mask=im.split()[3])
    q = bg.quantize(colors=ncolors - 1, method=Image.Quantize.FASTOCTREE)
    pal_rgb = q.getpalette()[: (ncolors - 1) * 3]
    pal_rgba = bytearray(ncolors * 4)
    # Reserve index 0 for full transparency
    for ci in range(1, ncolors):
        pal_rgba[ci * 4 : ci * 4 + 3] = bytes(pal_rgb[(ci - 1) * 3 : (ci - 1) * 3 + 3])
        pal_rgba[ci * 4 + 3] = 255
    src_px = im.load()
    q_px = q.load()
    lin = bytearray(rb * h)
    for y in range(h):
        for x in range(w):
            a = src_px[x, y][3]
            ci = 0 if a < 32 else (q_px[x, y] + 1)
            if fmt == 0x12:
                if (x & 1) == 0:
                    lin[y * rb + x // 2] |= (ci & 0xF)
                else:
                    lin[y * rb + x // 2] |= ((ci & 0xF) << 4)
            else:
                lin[y * rb + x] = ci
    sw = swizzle_psp(bytes(lin), rb, h)
    out = bytearray(rhg)
    out[info["pix_off"] : info["pix_off"] + len(sw)] = sw
    out[info["pal_off"] : info["pal_off"] + len(pal_rgba)] = pal_rgba
    return bytes(out)


def replace_rhg_image_keep_palette(rhg: bytes, idx: int, new_img: Image.Image, pal_idx: int = None) -> bytes:
    """Encode new_img using an existing RHG palette (preserving original CLUT colors/alpha)."""
    if pal_idx is None:
        pal_idx = idx
    infos = parse_rhg(rhg)
    info = infos[idx]
    pinfo = infos[pal_idx]
    w, h, fmt, rb = info["width"], info["height"], info["fmt"], info["rb"]
    pal_bytes = rhg[pinfo["pal_off"] : pinfo["pal_off"] + pinfo["pal_sz"]]
    ncolors = len(pal_bytes) // 4
    pal_rgba = [tuple(pal_bytes[i * 4 : i * 4 + 4]) for i in range(ncolors)]

    im = new_img.convert("RGBA")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    src_px = im.load()

    # Cache nearest color lookup
    cache = {}
    lin = bytearray(rb * h)
    for y in range(h):
        for x in range(w):
            rgba = src_px[x, y]
            ci = cache.get(rgba)
            if ci is None:
                if rgba[3] < 32:
                    ci = next((i for i, c in enumerate(pal_rgba) if c[3] < 32), 0)
                else:
                    r, g, b, a = rgba
                    best_d = 1 << 30
                    best_i = 0
                    for i, (pr, pg, pb, pa) in enumerate(pal_rgba):
                        if pa < 32:
                            continue
                        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2 + (a - pa) ** 2
                        if d < best_d:
                            best_d = d
                            best_i = i
                    ci = best_i
                cache[rgba] = ci
            if fmt == 0x12:
                if (x & 1) == 0:
                    lin[y * rb + x // 2] |= (ci & 0xF)
                else:
                    lin[y * rb + x // 2] |= ((ci & 0xF) << 4)
            else:
                lin[y * rb + x] = ci

    sw = swizzle_psp(bytes(lin), rb, h)
    out = bytearray(rhg)
    out[info["pix_off"] : info["pix_off"] + len(sw)] = sw
    return bytes(out)
