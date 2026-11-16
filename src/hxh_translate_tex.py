import os
import sys
import struct
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ss_tools import swizzle_psp, unswizzle_psp
from translate_gim_ita import FONT_SANS_BOLD, FONT_SANS_NARROW, load_fitted_font, render_styled_text
from hxh_tools import (
    parse_rhg,
    parse_tex_psp,
    replace_rhg_image,
    replace_rhg_image_keep_palette,
    replace_tex_psp_image,
)

ARENA_RANKS = {
    0: "Dominatore del Cielo",
    1: "Autoproclamato Piu' Forte",
    2: "Maestro di Piano",
    3: "Sfidante Maestro",
    4: "Ricercatore di Nen",
    5: "Principiante di Nen",
    6: "Battezzato",
    7: "Re Nudo",
}


def patch_e3_sub10_tex(tex_bytes: bytes) -> bytes:
    """Translate Japanese sub-labels in Entry 3 sub[10][3] (Pause/GameOver/Result atlas)."""
    im = parse_tex_psp(tex_bytes)[3]["image"].copy()
    draw = ImageDraw.Draw(im)
    # Clear Japanese sub-labels while keeping English titles and buttons untouched
    # 1. "ポーズメニュー" (y=50..64, x=120..235)
    draw.rectangle((120, 50, 235, 64), fill=(0, 0, 0, 0))
    render_styled_text(
        im, (118, 50, 236, 64), "Menu Pausa", FONT_SANS_BOLD,
        (255, 255, 255), (225, 230, 240), (15, 15, 20, 255), align="center"
    )
    # 2. "ゲームオーバー" (y=81..94, x=120..235)
    draw.rectangle((120, 81, 235, 94), fill=(0, 0, 0, 0))
    render_styled_text(
        im, (118, 81, 236, 94), "Game Over", FONT_SANS_BOLD,
        (255, 255, 255), (225, 230, 240), (15, 15, 20, 255), align="center"
    )
    # 3. "リザルトメニュー" (y=179..193, x=20..145)
    draw.rectangle((20, 179, 145, 193), fill=(0, 0, 0, 0))
    render_styled_text(
        im, (20, 179, 145, 193), "Menu Risultati", FONT_SANS_BOLD,
        (255, 255, 255), (225, 230, 240), (15, 15, 20, 255), align="center"
    )
    out = replace_tex_psp_image(tex_bytes, 3, im)

    # [4] 256x32 START! -> VIA!
    im4 = Image.new("RGBA", (256, 32), (0, 0, 0, 0))
    render_styled_text(
        im4, (8, 2, 248, 30), "VIA!", FONT_SANS_BOLD,
        (255, 245, 140), (255, 145, 0), (40, 15, 0, 255), align="center"
    )
    out = replace_tex_psp_image(out, 4, im4)

    # [5] 256x32 FINISH! -> FINE!
    im5 = Image.new("RGBA", (256, 32), (0, 0, 0, 0))
    render_styled_text(
        im5, (8, 2, 248, 30), "FINE!", FONT_SANS_BOLD,
        (255, 210, 170), (235, 55, 15), (40, 5, 0, 255), align="center"
    )
    out = replace_tex_psp_image(out, 5, im5)

    # [7] 256x32 CLEAR! -> COMPLETATO!
    im7 = Image.new("RGBA", (256, 32), (0, 0, 0, 0))
    render_styled_text(
        im7, (8, 2, 248, 30), "COMPLETATO!", FONT_SANS_BOLD,
        (210, 255, 180), (40, 215, 30), (5, 35, 5, 255), align="center"
    )
    out = replace_tex_psp_image(out, 7, im7)
    return out


def patch_e3_sub9_tex(tex_bytes: bytes) -> bytes:
    """Translate English labels in Entry 3 sub[9]: TIME, CONNECTING, ABILITY SLOT."""
    imgs = parse_tex_psp(tex_bytes)
    out = tex_bytes

    # [14] 64x32 TIME -> TEMPO
    im14 = imgs[14]["image"].copy()
    d14 = ImageDraw.Draw(im14)
    d14.rectangle((11, 10, 50, 22), fill=(24, 24, 28, 255))
    render_styled_text(
        im14, (11, 9, 51, 23), "TEMPO", FONT_SANS_NARROW,
        (255, 255, 255), (220, 225, 235), (10, 10, 15, 255), align="center"
    )
    out = replace_tex_psp_image(out, 14, im14)

    # [25] 128x32 CONNECTING -> CONNESSIONE
    im25 = Image.new("RGBA", (128, 32), (0, 0, 0, 0))
    render_styled_text(
        im25, (4, 6, 124, 26), "CONNESSIONE", FONT_SANS_NARROW,
        (140, 245, 255), (30, 175, 235), (10, 35, 70, 255), align="center"
    )
    out = replace_tex_psp_image(out, 25, im25)

    # [56] 512x64 ABILITY SLOT -> SLOT ABILITA'
    im56 = imgs[56]["image"].copy()
    d56 = ImageDraw.Draw(im56)
    d56.rectangle((0, 0, 110, 13), fill=(0, 0, 0, 0))
    render_styled_text(
        im56, (2, 0, 108, 13), "SLOT ABILITA'", FONT_SANS_NARROW,
        (255, 255, 255), (220, 225, 235), (10, 10, 15, 255), align="left"
    )
    out = replace_tex_psp_image(out, 56, im56)
    return out


def patch_e6_tex(tex_bytes: bytes) -> bytes:
    """Translate Entry 6[2] ('DATA INSTALL / データインストール') -> 'Installazione Dati'."""
    im = parse_tex_psp(tex_bytes)[2]["image"].copy()
    draw = ImageDraw.Draw(im)
    # Clear lower Japanese subtitle inside the bar (y=34..54, x=140..372)
    draw.rectangle((140, 34, 372, 54), fill=(25, 28, 32, 255))
    render_styled_text(
        im, (140, 34, 372, 54), "Installazione Dati", FONT_SANS_NARROW,
        (240, 240, 245), (190, 200, 215), (10, 10, 15, 255), align="center"
    )
    return replace_tex_psp_image(tex_bytes, 2, im)


def patch_arena_ranks_tex(tex_bytes: bytes, start_idx: int) -> bytes:
    """Translate 8 Heavens Arena rank title textures (256x32)."""
    out = tex_bytes
    for i in range(8):
        im = Image.new("RGBA", (256, 32), (0, 0, 0, 0))
        render_styled_text(
            im, (6, 3, 250, 29), ARENA_RANKS[i], FONT_SANS_BOLD,
            (255, 255, 255), (215, 225, 240), (15, 20, 30, 255), align="center"
        )
        out = replace_tex_psp_image(out, start_idx + i, im)
    return out


def _draw_angled_ribbon_label(base_im: Image.Image, center_xy: tuple[int, int], text: str, angle_deg: float, ribbon_w: int = 210, ribbon_h: int = 34):
    """Overlay an angled ribbon + Italian label cleanly over Japanese panel text."""
    ov = Image.new("RGBA", (ribbon_w, ribbon_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle((1, 1, ribbon_w - 2, ribbon_h - 2), radius=8, fill=(20, 18, 28, 220), outline=(220, 30, 85, 255), width=2)
    render_styled_text(
        ov, (8, 3, ribbon_w - 8, ribbon_h - 3), text, FONT_SANS_BOLD,
        (255, 255, 255), (245, 235, 240), (185, 15, 65, 255), align="center"
    )
    rot = ov.rotate(angle_deg, resample=Image.BICUBIC, expand=True)
    x0 = center_xy[0] - rot.width // 2
    y0 = center_xy[1] - rot.height // 2
    base_im.alpha_composite(rot, (x0, y0))


def patch_e7_rhg_title(rhg: bytes) -> bytes:
    """Translate Title Screen RHG (Entry 7 sub[2]): PRESS START / CONTINUE / NEW GAME."""
    imgs = parse_rhg(rhg)
    out = rhg
    # s2[0]: 256x32 "PRESS START BUTTON" -> "PREMI IL TASTO START"
    im0 = Image.new("RGBA", (256, 32), (0, 0, 0, 0))
    render_styled_text(
        im0, (8, 4, 248, 28), "PREMI IL TASTO START", FONT_SANS_BOLD,
        (255, 245, 210), (245, 195, 70), (20, 15, 5, 255), align="center"
    )
    out = replace_rhg_image(out, 0, im0)

    # s2[1]: 256x32 "CONTINUE" -> "CONTINUA"
    im1 = imgs[1]["image"].copy()
    d1 = ImageDraw.Draw(im1)
    d1.rectangle((55, 4, 200, 28), fill=(18, 18, 22, 230))
    render_styled_text(
        im1, (55, 4, 200, 28), "CONTINUA", FONT_SANS_BOLD,
        (255, 255, 255), (220, 230, 245), (15, 15, 25, 255), align="center"
    )
    out = replace_rhg_image(out, 1, im1)

    # s2[2]: 256x32 "NEW GAME" -> "NUOVA PARTITA"
    im2 = imgs[2]["image"].copy()
    d2 = ImageDraw.Draw(im2)
    d2.rectangle((45, 4, 210, 28), fill=(18, 18, 22, 230))
    render_styled_text(
        im2, (45, 4, 210, 28), "NUOVA PARTITA", FONT_SANS_BOLD,
        (255, 255, 255), (220, 230, 245), (15, 15, 25, 255), align="center"
    )
    out = replace_rhg_image(out, 2, im2)
    return out


def patch_e7_rhg_mainmenu(rhg: bytes) -> bytes:
    """Translate Main Menu RHG (Entry 7 sub[4]): MAIN MENU header + mode panels."""
    imgs = parse_rhg(rhg)
    out = rhg

    # s4[0] & s4[1]: 128x128 "ショップ" -> crisp bilevel white+pink outlined "Negozio" (1px outline)
    ov_shop = Image.new("RGBA", (116, 36), (0, 0, 0, 0))
    f_shop, _ = load_fitted_font(FONT_SANS_BOLD, "Negozio", 104, 28, start_size=24, min_size=12)
    m_fill = Image.new("1", (116, 36), 0)
    md = ImageDraw.Draw(m_fill)
    bb = md.textbbox((0, 0), "Negozio", font=f_shop)
    tx = (116 - (bb[2] - bb[0])) // 2 - bb[0]
    ty = (36 - (bb[3] - bb[1])) // 2 - bb[1]
    md.text((tx, ty), "Negozio", font=f_shop, fill=1)
    mpx = m_fill.load()
    opx = ov_shop.load()
    for yy in range(36):
        for xx in range(116):
            if mpx[xx, yy]:
                opx[xx, yy] = (255, 255, 255, 255)
            else:
                hit = any(
                    0 <= xx + dx < 116 and 0 <= yy + dy < 36 and mpx[xx + dx, yy + dy]
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                )
                if hit:
                    opx[xx, yy] = (185, 15, 65, 255)

    rot0 = ov_shop.rotate(28.0, resample=Image.NEAREST, expand=True)
    im0 = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    im0.alpha_composite(rot0, (62 - rot0.width // 2, 68 - rot0.height // 2))

    rot1 = ov_shop.rotate(20.0, resample=Image.NEAREST, expand=True)
    im1 = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    im1.alpha_composite(rot1, (74 - rot1.width // 2, 60 - rot1.height // 2))
    out = replace_rhg_image(out, 1, im1)
    out = replace_rhg_image(out, 0, im0)

    # s4[2]: 256x64 "MAIN MENU / メインメニュー" -> white top bar (bg=18, fg=55), black bottom bar (bg=55, fg=18)
    # Clear everything outside the slanted banner parallelogram to idx=0 with alpha=0 so zero dark border remains
    out = _patch_rhg_luma_indices(out, 2, [
        ((22, 6, 182, 23), "MENU PRINCIPALE", FONT_SANS_NARROW, 18, 55),
        ((22, 26, 176, 38), "Menu Principale", FONT_SANS_NARROW, 55, 18),
    ])
    d2_info = parse_rhg(out)[2]
    px2_raw = bytearray(unswizzle_psp(out[d2_info["pix_off"] : d2_info["pix_off"] + d2_info["psz"]], d2_info["rb"], d2_info["height"]))
    for yy in range(64):
        x_lim = 197 - int(max(0, yy - 4) * 0.55)
        for xx in range(256):
            if yy < 4 or yy > 45 or xx < 3 or xx > x_lim:
                px2_raw[yy * 256 + xx] = 0
    sw2 = swizzle_psp(bytes(px2_raw), d2_info["rb"], d2_info["height"])
    out_ba = bytearray(out)
    out_ba[d2_info["pix_off"] : d2_info["pix_off"] + len(sw2)] = sw2
    pal_off_2 = d2_info["pal_off"]
    out_ba[pal_off_2 + 0 * 4 + 3] = 0
    out = bytes(out_ba)

    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

    # s4[4]: 512x512 Story Mode (2-panel)
    im4 = Image.open(os.path.join(assets_dir, "s4_4.png")).convert("RGBA")
    out = replace_rhg_image(out, 4, im4)

    # s4[8]: 512x512 Story Mode (4-panel)
    im8 = Image.open(os.path.join(assets_dir, "s4_8.png")).convert("RGBA")
    out = replace_rhg_image(out, 8, im8)

    # s4[10]: 512x512 Mission Mode (4-panel)
    im10 = Image.open(os.path.join(assets_dir, "s4_10.png")).convert("RGBA")
    out = replace_rhg_image(out, 10, im10)

    # s4[12]: 512x256 Shop (4-panel)
    im12 = Image.open(os.path.join(assets_dir, "s4_12.png")).convert("RGBA")
    out = replace_rhg_image(out, 12, im12)

    # s4[14]: 512x512 Heavens Arena (4-panel)
    im14 = imgs[14]["image"].copy()
    _draw_angled_ribbon_label(im14, (328, 94), "Arena Celeste", 21.0, ribbon_w=170, ribbon_h=38)
    out = replace_rhg_image(out, 14, im14)

    return out


def _patch_rhg_luma_indices(rhg: bytes, idx: int, regions: list) -> bytes:
    """Patch grayscale/CLUT-indexed RHG texture in-place by sampling exact bg/fg indices.
    regions: list of (box=(x0,y0,x1,y1), text, font_path, bg_sample_xy, fg_val)
    """
    cnt = struct.unpack_from("<I", rhg, 0x14)[0]
    cnt2 = struct.unpack_from("<I", rhg, 0x1C)[0]
    cnt3 = struct.unpack_from("<I", rhg, 0x24)[0]
    t2_off = (0x30 + cnt * 0x28 + 15) & ~15
    pix_descs = [struct.unpack_from("<9I", rhg, t2_off + i * 0x24) for i in range(cnt2)]
    t3_off = t2_off + cnt2 * 0x24
    pix_cur = (t3_off + cnt3 * 0x20 + 127) & ~127
    pix_offs = []
    for p in pix_descs:
        pix_offs.append(pix_cur)
        pix_cur += p[5]

    _, fmt, w, h, _, psz, rb, _, _ = pix_descs[idx]
    rp = bytearray(unswizzle_psp(rhg[pix_offs[idx] : pix_offs[idx] + psz], rb, h))
    im = Image.frombytes("L", (rb, h), bytes(rp))
    px = im.load()

    for (x0, y0, x1, y1), text, font_path, bg_src, fg_idx in regions:
        bg_idx = bg_src if isinstance(bg_src, int) else px[bg_src[0], bg_src[1]]
        draw = ImageDraw.Draw(im)
        draw.rectangle((x0, y0, x1, y1), fill=bg_idx)
        font, _ = load_fitted_font(font_path, text, x1 - x0 - 6, y1 - y0 - 2, start_size=24, min_size=9)
        # Render onto 1-bit mask (no anti-aliasing) so indexed CLUT has zero speckled edges
        mask = Image.new("1", (x1 - x0, y1 - y0), 0)
        md = ImageDraw.Draw(mask)
        bbox = md.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = ((x1 - x0) - tw) // 2 - bbox[0]
        ty = ((y1 - y0) - th) // 2 - bbox[1]
        md.text((tx, ty), text, font=font, fill=1)
        mpx = mask.load()
        for yy in range(y1 - y0):
            for xx in range(x1 - x0):
                if mpx[xx, yy]:
                    px[x0 + xx, y0 + yy] = fg_idx

    sw = swizzle_psp(im.tobytes(), rb, h)
    out = bytearray(rhg)
    out[pix_offs[idx] : pix_offs[idx] + len(sw)] = sw
    return bytes(out)


def patch_e5_charselect(rhg: bytes) -> bytes:
    """Translate Character Select RHG (Entry 5 sub[7]): GON/KILLUA/KURAPIKA/LEORIO + header."""
    out = rhg
    cards = [
        (0, "GON", 2, 125),
        (1, "KILLUA", 2, 104),
        (2, "KURAPIKA", 2, 97),
        (3, "LEORIO", 2, 40),
    ]
    for i, name, bg_i, fg_i in cards:
        out = _patch_rhg_luma_indices(out, i, [
            ((16, 156, 112, 188), name, FONT_SANS_BOLD, bg_i, fg_i),
        ])
    # E5s7[10]: 512x64 "CHARACTER SELECT / キャラクターセレクト"
    out = _patch_rhg_luma_indices(out, 10, [
        ((24, 3, 255, 23), "SELEZIONE PERSONAGGIO", FONT_SANS_NARROW, 15, 37),
        ((24, 26, 238, 44), "Seleziona Personaggio", FONT_SANS_NARROW, 125, 37),
    ])
    return out


def patch_e5_customize(rhg: bytes) -> bytes:
    """Translate Customize header RHG (Entry 5 sub[9][9]): CUSTOMIZE / カスタマイズ."""
    imgs = parse_rhg(rhg)
    im = imgs[9]["image"].copy()
    d = ImageDraw.Draw(im)
    d.rectangle((22, 4, 180, 26), fill=(255, 195, 40, 255))
    render_styled_text(
        im, (24, 4, 180, 26), "PERSONALIZZA", FONT_SANS_NARROW,
        (255, 255, 255), (255, 235, 160), (20, 15, 5, 255), align="left"
    )
    d.rectangle((22, 30, 170, 44), fill=(18, 18, 22, 255))
    render_styled_text(
        im, (24, 30, 170, 44), "Personalizza", FONT_SANS_NARROW,
        (255, 255, 255), (225, 230, 240), (10, 10, 15, 255), align="left"
    )
    return replace_rhg_image(rhg, 9, im)


def patch_e8_story_hdr(rhg: bytes) -> bytes:
    """Translate Story Mode header RHG (Entry 8 sub[2][14])."""
    return _patch_rhg_luma_indices(rhg, 14, [
        ((20, 4, 230, 26), "MODALITA' STORIA", FONT_SANS_NARROW, (215, 14), 37),
        ((20, 26, 215, 46), "Modalita' Storia", FONT_SANS_NARROW, (200, 36), 37),
    ])


def patch_e9_mission_hdr(rhg: bytes, idx: int) -> bytes:
    """Translate Mission Mode header RHG (Entry 9 sub[2][11] and Entry 12 sub[1][19])."""
    return _patch_rhg_luma_indices(rhg, idx, [
        ((20, 4, 230, 26), "MODALITA' MISSIONE", FONT_SANS_NARROW, (215, 14), 37),
        ((20, 26, 215, 46), "Modalita' Missione", FONT_SANS_NARROW, (200, 36), 37),
    ])


def patch_e8_chapters(tex_bytes: bytes) -> bytes:
    """Translate CHAPTER 01..08 -> CAPITOLO 01..08 in Entry 8 sub[3][8..15]."""
    out = tex_bytes
    for n in range(1, 9):
        idx = 7 + n
        im = Image.new("RGBA", (256, 32), (0, 0, 0, 0))
        render_styled_text(
            im, (6, 2, 204, 30), f"CAPITOLO {n:02d}", FONT_SANS_BOLD,
            (255, 255, 255), (245, 240, 245), (190, 20, 75, 255), align="left"
        )
        out = replace_tex_psp_image(out, idx, im)
    return out


def patch_e9_locations(tex_bytes: bytes) -> bytes:
    """Translate LOCATION 01..09 -> LUOGO 01..09 in Entry 9 sub[3][9..17]."""
    out = tex_bytes
    for n in range(1, 10):
        idx = 8 + n
        im = Image.new("RGBA", (256, 32), (0, 0, 0, 0))
        render_styled_text(
            im, (6, 2, 204, 30), f"LUOGO {n:02d}", FONT_SANS_BOLD,
            (255, 255, 255), (245, 240, 245), (190, 20, 75, 255), align="left"
        )
        out = replace_tex_psp_image(out, idx, im)
    return out
