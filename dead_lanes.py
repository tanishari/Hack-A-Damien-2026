#!/usr/bin/env python3
"""
DEAD LANES — UAlbany Hackathon 2026
Python / Pygame | First-person 5-lane zombie defense

KEYBOARD:
  A / D         → cycle weapon
  ← / → (or Q/E) → switch lane
  SPACE          → shoot  (hold for SMG auto-fire)
  R              → reload
  P / ESC        → pause
  SHOP: 1/2/3=buy   S/ENTER=skip

pip install pygame
Optional gyro: pip install pyserial  (uses gyro_bridge.py WebSocket output)
"""

import pygame, math, random, sys, time, threading, queue

try:
    import serial, serial.tools.list_ports
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
W, H      = 900, 600
HORIZON_Y = int(H * 0.285)
LANE_N    = 5
HRZ_MARG  = W * 0.22
FPS       = 60

SERIAL_PORT = None   # None = auto-detect
SERIAL_BAUD = 9600

# ─── COLOURS ──────────────────────────────────────────────────────────────────
C_SKY_TOP   = (5,   8,  18)
C_SKY_BOT   = (18,  24,  58)
C_GND_TOP   = (20,  20,  30)
C_GND_BOT   = (8,   8,  16)
C_BLD_MARG  = (8,  12,  26)  # horizon margin pillars

C_LANE_LINE = (55,  60,  90)
C_UI_BG     = (8,  12,  24)
C_UI_BORDER = (61,  90, 140)
C_CYAN      = (0,  180, 216)
C_GOLD      = (255, 200,  30)
C_GOLD_HL   = (255, 232, 128)
C_RED       = (204,  34,  34)
C_PURPLE    = (138,  32, 200)
C_PURPLE_GL = (220, 100, 255)
C_GREEN_HUD = (100, 210, 130)
C_WHITE     = (255, 255, 255)
C_BLACK     = (0,   0,   0)

C_SKIN      = (180, 140, 100)
C_SKIN_DK   = (138, 104,  68)
C_BARREL    = (140, 150, 170)
C_BARREL_HL = (200, 210, 230)
C_STOCK     = (100,  60,  30)
C_GRIP      = ( 74,  44,  18)
C_METAL     = ( 90, 100, 114)
C_METAL_HL  = (128, 144, 168)

C_BLOOD     = (120,  18,  18)
C_TEETH     = (200, 178,  65)

# ─── WEAPON DEFS ──────────────────────────────────────────────────────────────
WEAPON_DEFS = [
    dict(name='PISTOL',  dmg=35,  rate=2.2, max_ammo=12, reload_s=1.2, auto=False, pierce=False),
    dict(name='SMG',     dmg=12,  rate=9.0, max_ammo=36, reload_s=1.6, auto=True,  pierce=False),
    dict(name='SNIPER',  dmg=110, rate=0.7, max_ammo=5,  reload_s=2.2, auto=False, pierce=True),
    dict(name='ROCKET',  dmg=200, rate=0.4, max_ammo=4,  reload_s=3.0, auto=False, pierce=False),
    dict(name='SHOTGUN', dmg=80,  rate=1.2, max_ammo=8,  reload_s=2.0, auto=False, pierce=False),
]
SHOP_COSTS = [200, 250, 300]
SHOP_KEYS  = ['ammo', 'dmg', 'rate']

BOSS_DEFS = [
    dict(name='SPECTER',      perk='PERIODIC INVISIBILITY',       col=(120, 120, 255)),
    dict(name='NECROMANCER',  perk='REVIVES FALLEN ZOMBIES',      col=(136,   0, 255)),
    dict(name='IRON GIANT',   perk='REACTIVE ARMOR (50% BLOCK)',  col=(136, 136, 136)),
    dict(name='SPLITTER',     perk='SPLITS INTO CLONES',          col=(  0, 255, 170)),
    dict(name='BERSERKER',    perk='FASTER AS HP DROPS',          col=(255, 102,   0)),
    dict(name='PLAGUE LORD',  perk='BUFFS ALL ZOMBIES',           col=( 68, 255,   0)),
    dict(name='PHANTOM',      perk='TELEPORTS BETWEEN LANES',     col=(  0, 221, 255)),
    dict(name='TITAN SHIELD', perk='GENERATES BLOCKING SHIELDS',  col=(255, 255,   0)),
    dict(name='UNDYING',      perk='RAPID HEALTH REGENERATION',   col=(255, 136, 170)),
    dict(name='APEX PREDATOR',perk:'ALL PREVIOUS BOSS ABILITIES', col=(200,  80, 255)),
]

KILL_STREAKS = [
    (5,  'KILLING SPREE!', (255, 102,  0)),
    (10, 'RAMPAGE!',       (255,  34,  0)),
    (15, 'UNSTOPPABLE!',   (255,   0, 136)),
    (20, 'GODLIKE!',       (255, 221,  0)),
    (25, 'BEYOND HUMAN!',  (200, 212, 232)),
]

# ═══════════════════════════════════════════════════════════════════════════════
#  PYGAME INIT
# ═══════════════════════════════════════════════════════════════════════════════
pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption('DEAD LANES — UAlbany Hackathon 2026')
clock  = pygame.font.init() or pygame.time.Clock()
clock  = pygame.time.Clock()

def _try_font(name, size, bold=False):
    f = pygame.font.SysFont(name, size, bold=bold)
    return f if f else pygame.font.SysFont(None, size, bold=bold)

font_title = _try_font('impact',   72,  bold=True)
font_big   = _try_font('impact',   44,  bold=True)
font_med   = _try_font('consolas', 24,  bold=True)
font_sm    = _try_font('consolas', 16)
font_xs    = _try_font('consolas', 13)

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t

def lerp_col(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def get_lane_edges(lane, depth):
    far_w  = (W - HRZ_MARG * 2) / LANE_N
    near_w = W / LANE_N
    lw     = near_w + (far_w - near_w) * depth
    far_l  = HRZ_MARG + lane * far_w
    near_l = lane * near_w
    lx     = near_l + (far_l - near_l) * depth
    cy     = HORIZON_Y + (H - HORIZON_Y) * (1 - depth)
    return dict(left=lx, right=lx+lw, center=lx+lw/2, width=lw, y=cy)

def depth_to_y(d):
    return HORIZON_Y + (H - HORIZON_Y) * (1 - d)

def draw_text(surf, text, font, color, x, y, anchor='topleft', shadow=True):
    if shadow:
        sh = font.render(text, True, C_BLACK)
        r  = sh.get_rect(**{anchor: (x+1, y+1)})
        surf.blit(sh, r)
    lbl = font.render(text, True, color)
    r   = lbl.get_rect(**{anchor: (x, y)})
    surf.blit(lbl, r)

def draw_panel(surf, rect, alpha=200):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    s.fill((*C_UI_BG, alpha))
    surf.blit(s, (rect[0], rect[1]))
    pygame.draw.rect(surf, C_UI_BORDER, rect, 1, border_radius=4)

def get_wep_stat(G, wi, stat):
    d = WEAPON_DEFS[wi]
    u = G['upgrades']
    if stat == 'dmg':      return d['dmg']      * (1 + u['dmg']  * 0.15)
    if stat == 'rate':     return d['rate']      * (1 + u['rate'] * 0.15)
    if stat == 'max_ammo': return int(d['max_ammo'] * (1 + u['ammo'] * 0.15))
    if stat == 'reload_s': return d['reload_s']
    return d.get(stat, False)

# ═══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND (pre-rendered)
# ═══════════════════════════════════════════════════════════════════════════════
_bg_cache = {}
def get_bg(blood_moon=False):
    key = bool(blood_moon)
    if key in _bg_cache:
        return _bg_cache[key]

    surf = pygame.Surface((W, H))

    # Sky gradient
    sky_top = (12,  1,  5) if blood_moon else C_SKY_TOP
    sky_bot = (40,  6,  8) if blood_moon else C_SKY_BOT
    for y in range(HORIZON_Y + 14):
        pygame.draw.line(surf, lerp_col(sky_top, sky_bot, y/(HORIZON_Y+14)), (0,y), (W,y))

    # Moon
    pygame.draw.circle(surf, (221, 220, 160), (720, 44), 24)
    pygame.draw.circle(surf, (200, 198, 140), (710, 38),  7)
    pygame.draw.circle(surf, (200, 198, 140), (730, 54),  4)
    pygame.draw.circle(surf, (200, 198, 140), (715, 56),  3)

    # Stars (seeded)
    rng = random.Random(42)
    for _ in range(130):
        sx = rng.randint(0, W-1)
        sy = rng.randint(0, HORIZON_Y - 4)
        sz = 1 if rng.random() < 0.78 else 2
        br = int((0.35 + rng.random()*0.65) * 255)
        pygame.draw.rect(surf, (br, br, br), (sx, sy, sz, sz))

    # City silhouette
    bld_rng = random.Random(77)
    bx = 8
    while bx < W - 8:
        bw = bld_rng.randint(18, 50)
        bh = bld_rng.randint(22, 80)
        pygame.draw.rect(surf, (8, 12, 26), (bx, HORIZON_Y - bh, bw, bh))
        # A few lit windows
        win_rng = random.Random(bx * 13)
        for wy in range(HORIZON_Y - bh + 5, HORIZON_Y - 5, 9):
            for wx in range(bx + 3, bx + bw - 4, 7):
                if win_rng.random() < 0.35:
                    wc_idx = win_rng.randint(0, 2)
                    wc = [(75,65,35), (35,55,80), (55,45,25)][wc_idx]
                    pygame.draw.rect(surf, wc, (wx, wy, 4, 5))
        bx += bw + bld_rng.randint(3, 11)

    # Ground gradient
    gnd_top = (26, 4, 4) if blood_moon else C_GND_TOP
    gnd_bot = (10, 2, 2) if blood_moon else C_GND_BOT
    for y in range(HORIZON_Y, H):
        t = (y - HORIZON_Y) / (H - HORIZON_Y)
        pygame.draw.line(surf, lerp_col(gnd_top, gnd_bot, t), (0,y), (W,y))

    _bg_cache[key] = surf
    return surf

# ═══════════════════════════════════════════════════════════════════════════════
#  LANE RENDERING
# ═══════════════════════════════════════════════════════════════════════════════
def draw_lanes(surf, G):
    active_lane = G['lane']
    blood_moon  = G['blood_moon']

    far_total_w = W - HRZ_MARG * 2
    near_total_w = W

    for lane in range(LANE_N):
        far_l  = HRZ_MARG  + lane * far_total_w  / LANE_N
        near_l = lane * near_total_w / LANE_N
        far_r  = HRZ_MARG  + (lane+1) * far_total_w  / LANE_N
        near_r = (lane+1) * near_total_w / LANE_N
        pts = [(far_l, HORIZON_Y), (far_r, HORIZON_Y), (near_r, H), (near_l, H)]
        if lane == active_lane:
            c = (0, 26, 52) if not blood_moon else (40, 5, 5)
        else:
            shade = 16 + abs(lane - 2) * 2
            c = (shade, shade, shade + 10)
        pygame.draw.polygon(surf, c, pts)

    # Lane divider lines (converging)
    for lane in range(LANE_N + 1):
        fx = HRZ_MARG + lane * far_total_w / LANE_N
        nx = lane * near_total_w / LANE_N
        lc = (100, 10, 10, 70) if blood_moon else (60, 72, 110, 60)
        # Draw dashed line segments
        for seg in range(8):
            t0 = seg / 8;  t1 = (seg + 0.55) / 8
            y0 = HORIZON_Y + (H - HORIZON_Y) * (1 - (1-t0));  x0 = fx + (nx-fx)*t0
            y1 = HORIZON_Y + (H - HORIZON_Y) * (1 - (1-t1));  x1 = fx + (nx-fx)*t1
            lcc = (100, 10, 10) if blood_moon else (60, 72, 110)
            pygame.draw.line(surf, lcc, (int(x0), int(y0)), (int(x1), int(y1)), 1)

    # Horizontal depth seams (road texture)
    for depth in [0.1, 0.2, 0.33, 0.5, 0.65, 0.78, 0.88, 0.95]:
        y = depth_to_y(depth)
        el = get_lane_edges(0, depth)
        er = get_lane_edges(LANE_N-1, depth)
        alpha = int((1 - depth) * 50)
        lcc = (alpha//2, 0, 0) if blood_moon else (0, 0, alpha//3)
        pygame.draw.line(surf, lerp_col((55,60,90),(0,0,0),depth), (int(el['left']), int(y)), (int(er['right']), int(y)), 1)

    # Horizon fog
    fog = pygame.Surface((W, 40), pygame.SRCALPHA)
    fog_col = (30, 3, 3, 120) if blood_moon else (14, 18, 40, 100)
    for fy in range(40):
        a = int(fog_col[3] * fy / 40)
        pygame.draw.line(fog, (*fog_col[:3], a), (0, fy), (W, fy))
    surf.blit(fog, (0, HORIZON_Y - 10))

# ═══════════════════════════════════════════════════════════════════════════════
#  ZOMBIE DRAWING (proportional helpers)
# ═══════════════════════════════════════════════════════════════════════════════
def _pr(x, y, w, h, fx, fy, fw, fh, r=0):
    """Draw rect from fractional coords within bounding box"""
    px = x + int(fx*w); py = y + int(fy*h)
    pw = max(1, int(fw*w)); ph = max(1, int(fh*h))
    return pygame.Rect(px, py, pw, ph)

def _pe(x, y, w, h, cx_f, cy_f, rx_f, ry_f):
    """Ellipse rect from fractional center + radii"""
    cx = x + int(cx_f*w); cy = y + int(cy_f*h)
    rx = max(1, int(rx_f*w)); ry = max(1, int(ry_f*h))
    return pygame.Rect(cx-rx, cy-ry, rx*2, ry*2)

def _pc(x, y, w, h, fx, fy):
    return (x + int(fx*w), y + int(fy*h))

def _pv(x, y, w, h, pts):
    return [(x + int(p[0]*w), y + int(p[1]*h)) for p in pts]

def draw_zombie_sprite(surf, x, y, w, h, z):
    if w < 6: return
    if w < 18:
        # Too small for detail — just a colored block
        col = (60,154,60) if z['type']=='normal' else (200,60,60) if z['type']=='fast' else (70,70,190)
        if z['type']=='boss': col = BOSS_DEFS[z.get('boss_idx',0)]['col']
        pygame.draw.rect(surf, col, (x, y, w, h))
        return

    hit = z.get('hit_flash', 0) > 0

    if z['type'] == 'boss':
        _draw_boss(surf, x, y, w, h, z, hit)
        return

    _draw_zombie_char(surf, x, y, w, h, z, hit)

def _draw_zombie_char(surf, x, y, w, h, z, hit):
    t = z['type']
    if   t == 'normal': _draw_hanzo(surf, x, y, w, h, hit)
    elif t == 'fast':   _draw_fast(surf, x, y, w, h, hit)
    elif t == 'tank':   _draw_kiriko(surf, x, y, w, h, hit)

    # Hit flash overlay
    if hit and w >= 12:
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill((180, 255, 180, 55))
        surf.blit(ov, (x, y))

def _draw_hanzo(surf, x, y, w, h, hit):
    skin   = (180, 220, 180) if hit else (60, 154, 60)
    skin_dk= (40,  110,  40)
    hair   = (18,  14,  30)
    jacket = (120, 96, 184) if hit else (74, 42, 122)
    j_dark = (88,  70, 140) if hit else (50, 28,  88)
    pants  = (60,  50,  40)
    blood  = C_BLOOD

    # Hair
    pygame.draw.ellipse(surf, hair, _pe(x,y,w,h, 0.5,0.04, 0.24,0.09))
    pygame.draw.polygon(surf, hair, _pv(x,y,w,h,
        [(0.28,0.07),(0.36,-0.02),(0.5,0.03),(0.64,-0.02),(0.72,0.07)]))

    # Head
    pygame.draw.ellipse(surf, skin, _pe(x,y,w,h, 0.5,0.14, 0.22,0.12))

    # Wound
    pygame.draw.ellipse(surf, blood, _pe(x,y,w,h, 0.44,0.08, 0.04,0.02))

    # Eyes
    for ex_f in [0.41, 0.59]:
        pygame.draw.ellipse(surf, (224,224,208), _pe(x,y,w,h, ex_f,0.11, 0.065,0.033))
    pygame.draw.ellipse(surf, (204,  0,  0), _pe(x,y,w,h, 0.42,0.11, 0.033,0.027))
    pygame.draw.ellipse(surf, (204,  0,  0), _pe(x,y,w,h, 0.60,0.11, 0.033,0.027))
    pygame.draw.circle(surf, C_BLACK, _pc(x,y,w,h, 0.42,0.11), max(1,int(w*0.014)))
    pygame.draw.circle(surf, C_BLACK, _pc(x,y,w,h, 0.60,0.11), max(1,int(w*0.014)))

    # Mouth
    pygame.draw.rect(surf, (32, 8, 8), _pr(x,y,w,h, 0.40,0.19,0.20,0.03))
    for i in range(3):
        pygame.draw.rect(surf, C_TEETH, _pr(x,y,w,h, 0.42+i*0.06,0.19,0.04,0.025))

    # Neck
    pygame.draw.rect(surf, skin, _pr(x,y,w,h, 0.43,0.24,0.14,0.05))

    # Jacket torso
    pygame.draw.rect(surf, jacket, _pr(x,y,w,h, 0.22,0.28,0.56,0.34, r=3))
    pygame.draw.polygon(surf, j_dark, _pv(x,y,w,h,[(0.5,0.28),(0.38,0.28),(0.48,0.46)]))
    pygame.draw.polygon(surf, j_dark, _pv(x,y,w,h,[(0.5,0.28),(0.62,0.28),(0.52,0.46)]))
    pygame.draw.ellipse(surf, (120,18,18,180) if True else blood,
        _pe(x,y,w,h, 0.55,0.36,0.07,0.04))

    # Arms
    pygame.draw.rect(surf, jacket, _pr(x,y,w,h, 0.05,0.29,0.16,0.28))
    pygame.draw.rect(surf, jacket, _pr(x,y,w,h, 0.79,0.29,0.16,0.28))
    # Hands
    pygame.draw.rect(surf, skin,   _pr(x,y,w,h, 0.03,0.55,0.19,0.09,r=2))
    pygame.draw.rect(surf, skin,   _pr(x,y,w,h, 0.78,0.55,0.19,0.09,r=2))
    for i in range(3):
        lw2 = max(1, int(w*0.012))
        p1 = _pc(x,y,w,h, 0.06+i*0.06, 0.63)
        p2 = _pc(x,y,w,h, 0.04+i*0.06, 0.70)
        pygame.draw.line(surf, skin_dk, p1, p2, lw2)
        p1 = _pc(x,y,w,h, 0.80+i*0.06, 0.63)
        p2 = _pc(x,y,w,h, 0.80+i*0.06, 0.70)
        pygame.draw.line(surf, skin_dk, p1, p2, lw2)

    # Pants + boots
    pygame.draw.rect(surf, pants, _pr(x,y,w,h, 0.23,0.60,0.22,0.38))
    pygame.draw.rect(surf, pants, _pr(x,y,w,h, 0.55,0.60,0.22,0.38))
    pygame.draw.rect(surf, (30,20,12), _pr(x,y,w,h, 0.21,0.94,0.25,0.06,r=2))
    pygame.draw.rect(surf, (30,20,12), _pr(x,y,w,h, 0.54,0.94,0.25,0.06,r=2))


def _draw_fast(surf, x, y, w, h, hit):
    skin   = (180, 220, 180) if hit else (60, 154, 60)
    shirt  = (200,  96,  96) if hit else (200,  56,  40)
    pants  = (60,  50,  40)
    blood  = C_BLOOD

    # Head (tilted forward)
    pygame.draw.ellipse(surf, (28,16,8), _pe(x,y,w,h, 0.5,0.04,0.16,0.06))
    pygame.draw.ellipse(surf, skin,      _pe(x,y,w,h, 0.5,0.11,0.19,0.10))

    # Angry slanted eyes
    for ex_f, angle_sign in [(0.41,-1),(0.59,1)]:
        pygame.draw.ellipse(surf, (204,0,0), _pe(x,y,w,h, ex_f,0.10,0.052,0.025))
    pygame.draw.ellipse(surf, blood, _pe(x,y,w,h, 0.57,0.14,0.04,0.02))

    # Shirt body (slightly rotated feel via asymmetric shading)
    pygame.draw.rect(surf, shirt, _pr(x,y,w,h, 0.24,0.19,0.52,0.26,r=2))
    # Rips
    lw2 = max(1, int(w*0.013))
    pygame.draw.line(surf, (0,0,0,90), _pc(x,y,w,h, 0.42,0.22), _pc(x,y,w,h, 0.46,0.36), lw2)
    pygame.draw.line(surf, (0,0,0,90), _pc(x,y,w,h, 0.54,0.22), _pc(x,y,w,h, 0.58,0.34), lw2)
    pygame.draw.ellipse(surf, blood, _pe(x,y,w,h, 0.47,0.31,0.05,0.03))

    # Arms (outstretched)
    pygame.draw.rect(surf, shirt, _pr(x,y,w,h, 0.05,0.20,0.18,0.24))
    pygame.draw.rect(surf, shirt, _pr(x,y,w,h, 0.77,0.18,0.18,0.24))
    pygame.draw.rect(surf, skin,  _pr(x,y,w,h, 0.03,0.42,0.20,0.08,r=2))
    pygame.draw.rect(surf, skin,  _pr(x,y,w,h, 0.77,0.39,0.20,0.08,r=2))

    # Pants / legs (running pose asymmetry)
    pygame.draw.rect(surf, pants, _pr(x,y,w,h, 0.23,0.43,0.22,0.38))
    pygame.draw.rect(surf, pants, _pr(x,y,w,h, 0.55,0.46,0.22,0.35))
    pygame.draw.rect(surf, (30,20,12), _pr(x,y,w,h, 0.21,0.78,0.25,0.07,r=2))
    pygame.draw.rect(surf, (30,20,12), _pr(x,y,w,h, 0.54,0.78,0.25,0.07,r=2))


def _draw_kiriko(surf, x, y, w, h, hit):
    skin   = (190, 230, 190) if hit else (60, 154, 60)
    skin_dk= (40,  110,  40)
    hair   = (30,  40,  40)
    haori  = (220, 220, 212) if not hit else (255, 255, 248)
    haori_sh=(180, 180, 172)
    hakama = (165,  48,  52) if hit else (160,  32,  52)
    hak_dk = (112,  20,  32)
    obi    = (200, 170,  52) if hit else (175, 135,  35)
    blood  = C_BLOOD
    teeth  = C_TEETH

    # Hair bun
    pygame.draw.ellipse(surf, hair, _pe(x,y,w,h, 0.5,0.04,0.18,0.08))
    pygame.draw.ellipse(surf, hair, _pe(x,y,w,h, 0.5,0.00,0.07,0.05))
    pygame.draw.rect(surf, hair, _pr(x,y,w,h, 0.28,0.07,0.08,0.13))
    pygame.draw.rect(surf, hair, _pr(x,y,w,h, 0.64,0.07,0.08,0.13))

    # Head (wider)
    pygame.draw.ellipse(surf, skin, _pe(x,y,w,h, 0.5,0.15,0.26,0.13))
    pygame.draw.ellipse(surf, blood, _pe(x,y,w,h, 0.44,0.09,0.05,0.025))

    # Wide frightened eyes
    for ex_f in [0.40, 0.60]:
        pygame.draw.ellipse(surf, (234, 232, 224), _pe(x,y,w,h, ex_f,0.14,0.08,0.04))
    pygame.draw.circle(surf, (10,2,2), _pc(x,y,w,h, 0.41,0.14), max(1,int(w*0.04)))
    pygame.draw.circle(surf, (10,2,2), _pc(x,y,w,h, 0.61,0.14), max(1,int(w*0.04)))
    pygame.draw.circle(surf, C_WHITE,  _pc(x,y,w,h, 0.39,0.13), max(1,int(w*0.015)))
    pygame.draw.circle(surf, C_WHITE,  _pc(x,y,w,h, 0.63,0.13), max(1,int(w*0.015)))

    # Cheek blood
    pygame.draw.ellipse(surf, (*blood,160), _pe(x,y,w,h, 0.30,0.16,0.06,0.025))
    pygame.draw.ellipse(surf, (*blood,140), _pe(x,y,w,h, 0.66,0.175,0.055,0.02))

    # Mouth + teeth
    pygame.draw.rect(surf, (26,6,6), _pr(x,y,w,h, 0.36,0.22,0.28,0.055,r=2))
    pygame.draw.ellipse(surf, blood, _pe(x,y,w,h, 0.36,0.23,0.07,0.04))
    for i in range(4):
        pygame.draw.rect(surf, teeth, _pr(x,y,w,h, 0.39+i*0.06,0.22,0.04,0.04))

    # Neck
    pygame.draw.rect(surf, skin, _pr(x,y,w,h, 0.43,0.27,0.14,0.05))

    # Haori (white kimono top) — wide
    pygame.draw.rect(surf, haori, _pr(x,y,w,h, 0.14,0.31,0.72,0.27,r=3))
    pygame.draw.polygon(surf, haori_sh, _pv(x,y,w,h,[(0.5,0.31),(0.37,0.31),(0.48,0.47)]))
    pygame.draw.polygon(surf, haori_sh, _pv(x,y,w,h,[(0.5,0.31),(0.63,0.31),(0.52,0.47)]))
    pygame.draw.ellipse(surf, (*blood, 140), _pe(x,y,w,h, 0.55,0.43,0.07,0.04))

    # Wide sleeves
    pygame.draw.rect(surf, haori,    _pr(x,y,w,h, 0.02,0.31,0.14,0.21,r=2))
    pygame.draw.rect(surf, haori,    _pr(x,y,w,h, 0.84,0.31,0.14,0.21,r=2))
    pygame.draw.rect(surf, haori_sh, _pr(x,y,w,h, 0.02,0.46,0.14,0.06))
    pygame.draw.rect(surf, haori_sh, _pr(x,y,w,h, 0.84,0.46,0.14,0.06))

    # Hands
    pygame.draw.rect(surf, skin, _pr(x,y,w,h, 0.00,0.51,0.20,0.09,r=2))
    pygame.draw.rect(surf, skin, _pr(x,y,w,h, 0.80,0.51,0.20,0.09,r=2))
    lw2 = max(1, int(w*0.012))
    for i in range(3):
        pygame.draw.line(surf, skin_dk, _pc(x,y,w,h,0.03+i*0.07,0.59), _pc(x,y,w,h,0.01+i*0.07,0.67),lw2)
        pygame.draw.line(surf, skin_dk, _pc(x,y,w,h,0.81+i*0.07,0.59), _pc(x,y,w,h,0.81+i*0.07,0.67),lw2)

    # Obi sash
    pygame.draw.rect(surf, obi,    _pr(x,y,w,h, 0.14,0.57,0.72,0.05))

    # Hakama
    pygame.draw.rect(surf, hakama, _pr(x,y,w,h, 0.15,0.61,0.70,0.17,r=2))
    lw3 = max(1, int(w*0.01))
    for i in range(5):
        p1 = _pc(x,y,w,h, 0.22+i*0.13, 0.61)
        p2 = _pc(x,y,w,h, 0.22+i*0.13, 0.78)
        pygame.draw.line(surf, hak_dk, p1, p2, lw3)

    # Legs / tabi
    pygame.draw.rect(surf, skin,         _pr(x,y,w,h, 0.26,0.77,0.19,0.13))
    pygame.draw.rect(surf, skin,         _pr(x,y,w,h, 0.55,0.77,0.19,0.13))
    pygame.draw.rect(surf, (224,220,210),_pr(x,y,w,h, 0.24,0.88,0.22,0.08,r=1))
    pygame.draw.rect(surf, (224,220,210),_pr(x,y,w,h, 0.54,0.88,0.22,0.08,r=1))


def _draw_boss(surf, x, y, w, h, z, hit):
    bi   = z.get('boss_idx', 0) % len(BOSS_DEFS)
    bdef = BOSS_DEFS[bi]
    col  = bdef['col']
    gold = C_GOLD
    gld_hl = C_GOLD_HL
    armour = (26, 8, 40)
    glow   = (220,100,255) if not hit else (255,200,255)
    teeth  = (200,200,200)
    t_ms   = pygame.time.get_ticks()
    pulse  = (math.sin(t_ms / 400.0) + 1) / 2

    # Aura
    aura_r = int(w * 0.65)
    if aura_r > 2:
        aura_s = pygame.Surface((aura_r*2, aura_r*2), pygame.SRCALPHA)
        aura_a = int((0.12 + pulse*0.10) * 255)
        pygame.draw.circle(aura_s, (*col, aura_a), (aura_r, aura_r), aura_r)
        surf.blit(aura_s, (x + int(w*0.5) - aura_r, y + int(h*0.5) - aura_r))

    # Crown spikes
    spikes_fx = [(-0.30,0.01),(-0.18,-0.06),(-0.08,0.0),(0,-0.08),(0.08,0.0),(0.18,-0.06),(0.30,0.01)]
    for sdx, sdy in spikes_fx:
        pts = _pv(x,y,w,h,[
            (0.5+sdx-0.04, 0.08+sdy),
            (0.5+sdx+0.04, 0.08+sdy),
            (0.5+sdx,      sdy-0.01),
        ])
        pygame.draw.polygon(surf, gold, pts)
        pts2 = _pv(x,y,w,h,[
            (0.5+sdx-0.01, 0.08+sdy),
            (0.5+sdx+0.01, 0.08+sdy),
            (0.5+sdx,      sdy+0.01),
        ])
        pygame.draw.polygon(surf, gld_hl, pts2)

    # Head armour
    pygame.draw.rect(surf, armour,   _pr(x,y,w,h, 0.22,0.08,0.56,0.20,r=3))
    pygame.draw.rect(surf, (46,16,70),_pr(x,y,w,h, 0.24,0.08,0.52,0.08,r=2))
    pygame.draw.rect(surf, glow,     _pr(x,y,w,h, 0.26,0.09,0.48,0.02))

    # 4 eyes
    for ey_f, er_f in [(0.15, 0.056), (0.21, 0.046)]:
        for ex_f in [0.36, 0.64]:
            pygame.draw.circle(surf, (40,0,40),   _pc(x,y,w,h, ex_f, ey_f), max(2,int(er_f*w)+1))
            pygame.draw.circle(surf, (255,0,200),  _pc(x,y,w,h, ex_f, ey_f), max(1,int(er_f*w)))
            pygame.draw.circle(surf, (255,128,238),_pc(x,y,w,h, ex_f, ey_f), max(1,int(er_f*w*0.55)))
    pygame.draw.circle(surf, C_WHITE, _pc(x,y,w,h, 0.38,0.14), max(1,int(w*0.015)))
    pygame.draw.circle(surf, C_WHITE, _pc(x,y,w,h, 0.66,0.14), max(1,int(w*0.015)))

    # Jaw + teeth
    pygame.draw.rect(surf, (22,4,34), _pr(x,y,w,h, 0.30,0.25,0.40,0.05,r=2))
    for i in range(5):
        pygame.draw.rect(surf, teeth, _pr(x,y,w,h, 0.33+i*0.075, 0.25, 0.05, 0.038))

    # Neck
    pygame.draw.rect(surf, col, _pr(x,y,w,h, 0.44,0.29,0.12,0.04))

    # Torso armour
    pygame.draw.rect(surf, armour, _pr(x,y,w,h, 0.17,0.32,0.66,0.32,r=4))
    # Shoulder pads
    pygame.draw.rect(surf, col,  _pr(x,y,w,h, 0.06,0.30,0.14,0.14,r=3))
    pygame.draw.rect(surf, col,  _pr(x,y,w,h, 0.80,0.30,0.14,0.14,r=3))
    pygame.draw.rect(surf, glow, _pr(x,y,w,h, 0.06,0.30,0.14,0.025,r=3))
    pygame.draw.rect(surf, glow, _pr(x,y,w,h, 0.80,0.30,0.14,0.025,r=3))

    # Chest rune
    rune_cx = _pc(x,y,w,h, 0.5,0.50)
    rune_r  = max(4, int(w*0.12))
    pygame.draw.circle(surf, (14,3,24), rune_cx, rune_r+2)
    pygame.draw.circle(surf, col,       rune_cx, rune_r)
    glow_col = tuple(min(255,int(c*(0.7+pulse*0.3))) for c in glow)
    pygame.draw.circle(surf, glow_col, rune_cx, int(rune_r*0.62))
    pygame.draw.circle(surf, C_WHITE,  rune_cx, max(1, int(rune_r*0.24)))
    lw4 = max(1, int(w*0.018))
    for ang in range(0, 360, 60):
        rad = math.radians(ang)
        ex = int(rune_cx[0] + math.cos(rad)*rune_r*0.92)
        ey = int(rune_cx[1] + math.sin(rad)*rune_r*0.92)
        pygame.draw.line(surf, glow_col, rune_cx, (ex,ey), lw4)
    pygame.draw.rect(surf, glow, _pr(x,y,w,h, 0.17,0.32,0.66,0.025,r=4))

    # Arms / gauntlets
    pygame.draw.rect(surf, armour, _pr(x,y,w,h, 0.05,0.34,0.13,0.20,r=2))
    pygame.draw.rect(surf, armour, _pr(x,y,w,h, 0.82,0.34,0.13,0.20,r=2))
    pygame.draw.rect(surf, col,   _pr(x,y,w,h, 0.03,0.53,0.15,0.16,r=2))
    pygame.draw.rect(surf, col,   _pr(x,y,w,h, 0.82,0.53,0.15,0.16,r=2))
    pygame.draw.rect(surf, glow,  _pr(x,y,w,h, 0.03,0.53,0.15,0.025,r=2))
    pygame.draw.rect(surf, glow,  _pr(x,y,w,h, 0.82,0.53,0.15,0.025,r=2))
    for i in range(3):
        sp = _pv(x,y,w,h, [(0.04+i*0.05,0.53),(0.09+i*0.05,0.53),(0.065+i*0.05,0.47)])
        pygame.draw.polygon(surf, gold, sp)
        sp2= _pv(x,y,w,h, [(0.83+i*0.05,0.53),(0.88+i*0.05,0.53),(0.855+i*0.05,0.47)])
        pygame.draw.polygon(surf, gold, sp2)

    # Legs
    pygame.draw.rect(surf, col,  _pr(x,y,w,h, 0.17,0.63,0.28,0.24,r=2))
    pygame.draw.rect(surf, col,  _pr(x,y,w,h, 0.55,0.63,0.28,0.24,r=2))
    pygame.draw.rect(surf, glow, _pr(x,y,w,h, 0.17,0.63,0.28,0.025,r=2))
    pygame.draw.rect(surf, glow, _pr(x,y,w,h, 0.55,0.63,0.28,0.025,r=2))
    # Boots + spikes
    pygame.draw.rect(surf, (14,4,20), _pr(x,y,w,h, 0.15,0.85,0.32,0.10,r=2))
    pygame.draw.rect(surf, (14,4,20), _pr(x,y,w,h, 0.53,0.85,0.32,0.10,r=2))
    pygame.draw.polygon(surf, gold, _pv(x,y,w,h,[(0.16,0.85),(0.23,0.85),(0.195,0.80)]))
    pygame.draw.polygon(surf, gold, _pv(x,y,w,h,[(0.54,0.85),(0.61,0.85),(0.575,0.80)]))

    # Titan shield ring
    if z.get('shield_active', False):
        shield_r = int(w*0.65)
        s_surf = pygame.Surface((shield_r*2, shield_r*2), pygame.SRCALPHA)
        pygame.draw.circle(s_surf, (255,255,0,180), (shield_r,shield_r), shield_r, max(2,int(w*0.025)))
        surf.blit(s_surf, (x+int(w*0.5)-shield_r, y+int(h*0.5)-shield_r))

    if hit:
        ov = pygame.Surface((w,h), pygame.SRCALPHA)
        ov.fill((220,160,255, 55)); surf.blit(ov, (x,y))

# ═══════════════════════════════════════════════════════════════════════════════
#  PLAYER HAND + WEAPON
# ═══════════════════════════════════════════════════════════════════════════════
barrel_tip = [W*0.37, H - 72]   # updated each frame

def draw_player_hand(surf, G, t_ms):
    if G['phase'] != 'game': return

    sway   = math.sin(G['weapon_sway']) * 3
    recoil = G['recoil_offset']
    wst    = G['w_states'][G['weapon_idx']]
    reload_dip = math.sin(wst['reload_prog'] * math.pi) * 22 if wst['reloading'] else 0

    gx = 560
    gy = int(H - 52 + sway + recoil*0.6 + reload_dip)

    # Forearm
    pygame.draw.polygon(surf, C_SKIN, [(gx+60,H),(gx+100,H),(gx+14,gy+12),(gx-10,gy+12)])
    pygame.draw.polygon(surf, C_SKIN_DK, [(gx+60,H),(gx+100,H),(gx+28,gy+12),(gx+14,gy+12)])

    # Palm
    pygame.draw.rect(surf, C_SKIN, (gx-22, gy-8, 60, 28), border_radius=5)
    # Knuckles
    for i in range(4):
        pygame.draw.ellipse(surf, C_SKIN_DK, (gx-14+i*14, gy-13, 10, 8))
    # Thumb
    pygame.draw.ellipse(surf, C_SKIN, (gx+33, gy-4, 18, 13))
    # Finger bands
    for yo in [4, 10, 16]:
        pygame.draw.rect(surf, C_SKIN_DK, (gx-22, gy+yo, 36, 2))

    wi = G['weapon_idx']
    if   wi == 0: _draw_pistol(surf, gx, gy)
    elif wi == 1: _draw_smg(surf, gx, gy)
    elif wi == 2: _draw_sniper(surf, gx, gy)
    elif wi == 3: _draw_rocket(surf, gx, gy)
    elif wi == 4: _draw_shotgun(surf, gx, gy)

    # Muzzle flash
    fl = G['flash']
    if fl > 0.1:
        bx, by = int(barrel_tip[0]), int(barrel_tip[1])
        r  = int(18 * fl)
        if r > 1:
            fs = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
            pygame.draw.circle(fs, (255,240,140, int(220*fl)), (r*2,r*2), r*2)
            pygame.draw.circle(fs, (255,200,60,  int(180*fl)), (r*2,r*2), r)
            surf.blit(fs, (bx-r*2, by-r*2))
            pygame.draw.circle(surf, (255,255,200), (bx,by), max(1,int(r*0.25)))
            # Sparks
            if fl > 0.5:
                for dx, dy in [(-1,-1),(1,-1),(0,-1.5),(-1.4,0),(1.4,0)]:
                    ex = int(bx + dx*r*1.8); ey = int(by + dy*r*1.8)
                    pygame.draw.line(surf, (255,220,80), (bx,by),(ex,ey),2)


def _draw_pistol(surf, gx, gy):
    # Barrel
    pygame.draw.rect(surf, C_BARREL,    (gx-115, gy-14, 100, 8))
    pygame.draw.rect(surf, C_BARREL_HL, (gx-115, gy-14, 100, 3))
    # Slide
    pygame.draw.rect(surf, C_METAL,     (gx-90,  gy-22,  70, 16), border_radius=3)
    pygame.draw.rect(surf, C_METAL_HL,  (gx-88,  gy-22,  66,  4))
    pygame.draw.rect(surf, C_BLACK,     (gx-68,  gy-20,  22,  8))
    # Sights
    pygame.draw.rect(surf, C_BARREL,    (gx-112, gy-18,   4,  6))
    pygame.draw.rect(surf, C_BARREL,    (gx-28,  gy-24,  14,  4))
    pygame.draw.rect(surf, C_BLACK,     (gx-25,  gy-24,   8,  4))
    # Grip
    pygame.draw.rect(surf, C_GRIP,      (gx-18,  gy-6,   18, 32), border_radius=3)
    pygame.draw.rect(surf, lerp_col(C_GRIP,C_BLACK,0.3),(gx-17,gy-2,16,4))
    # Trigger guard
    pygame.draw.arc(surf,  C_METAL, pygame.Rect(gx-32,gy+2,24,20), 0, math.pi, 2)
    barrel_tip[0] = gx-118; barrel_tip[1] = gy-10


def _draw_smg(surf, gx, gy):
    pygame.draw.rect(surf, C_BARREL,    (gx-130, gy-14,  80,  8))
    pygame.draw.rect(surf, C_BARREL_HL, (gx-130, gy-14,  80,  3))
    for i in range(6):
        pygame.draw.rect(surf, C_BLACK, (gx-128+i*11, gy-11, 6, 5))
    pygame.draw.rect(surf, C_METAL,     (gx-100, gy-20,  80, 18), border_radius=3)
    pygame.draw.rect(surf, C_METAL_HL,  (gx-98,  gy-20,  76,  4))
    # Drum mag
    pygame.draw.circle(surf, C_METAL,   (gx-52,  gy+22), 18)
    pygame.draw.circle(surf, (58,64,76),(gx-52,  gy+22), 12)
    pygame.draw.circle(surf, C_METAL_HL,(gx-52,  gy+22),  5)
    # Stock
    pygame.draw.rect(surf, C_STOCK,     (gx-24,  gy-16,  16, 24), border_radius=3)
    pygame.draw.rect(surf, C_GRIP,      (gx-18,  gy-4,   14, 28), border_radius=3)
    pygame.draw.arc(surf,  C_METAL, pygame.Rect(gx-30,gy+2,20,18), 0, math.pi, 2)
    barrel_tip[0] = gx-133; barrel_tip[1] = gy-10


def _draw_sniper(surf, gx, gy):
    pygame.draw.rect(surf, C_BARREL,    (gx-240, gy-14, 195,  8))
    pygame.draw.rect(surf, C_BARREL_HL, (gx-240, gy-14, 195,  3))
    pygame.draw.rect(surf, (106,112,128),(gx-240,gy-17,  18, 14), border_radius=2)
    for i in range(4):
        pygame.draw.rect(surf, C_BARREL_HL,(gx-238+i*4,gy-15, 2, 10))
    # Bipod
    pygame.draw.line(surf, C_BARREL, (gx-180,gy-6),(gx-175,gy+16), 2)
    pygame.draw.line(surf, C_BARREL, (gx-158,gy-6),(gx-163,gy+16), 2)
    # Receiver
    pygame.draw.rect(surf, C_METAL,    (gx-85,  gy-22,  62, 18), border_radius=3)
    pygame.draw.rect(surf, C_METAL_HL, (gx-83,  gy-22,  58,  4))
    # Scope
    pygame.draw.rect(surf, (42,44,48),  (gx-80,  gy-32,  52, 13), border_radius=4)
    pygame.draw.rect(surf, (60,64,80),  (gx-78,  gy-30,  48,  4))
    pygame.draw.circle(surf,(18,24,30), (gx-76,  gy-26),  6)
    pygame.draw.circle(surf,(42,64,96), (gx-76,  gy-26),  4)
    pygame.draw.circle(surf,(80,120,200,128),(gx-74,gy-28),2)
    # Stock
    pygame.draw.rect(surf, C_STOCK,    (gx-26,  gy-14,  26, 12), border_radius=3)
    pygame.draw.rect(surf, C_STOCK,    (gx-26,  gy- 2,  26, 10), border_radius=3)
    pygame.draw.rect(surf, C_GRIP,     (gx-18,  gy- 6,  14, 30), border_radius=3)
    barrel_tip[0] = gx-243; barrel_tip[1] = gy-10


def _draw_rocket(surf, gx, gy):
    pygame.draw.rect(surf, C_STOCK,    (gx-20,  gy-28,  22, 38), border_radius=4)
    # Tube
    pygame.draw.rect(surf, C_METAL,    (gx-155, gy-22, 130, 32), border_radius=6)
    pygame.draw.rect(surf, C_BARREL_HL,(gx-153, gy-22, 126,  5))
    # Warhead
    pygame.draw.polygon(surf,(204,48,16),[(gx-155,gy-22),(gx-155,gy+10),(gx-175,gy-6)])
    pygame.draw.polygon(surf,(255,96,64),[(gx-155,gy-22),(gx-155,gy-10),(gx-166,gy-16)])
    # Optic
    pygame.draw.rect(surf, (58,48,64), (gx-120, gy-34,  40, 14), border_radius=3)
    pygame.draw.circle(surf,(30,40,60),(gx-100,  gy-27),  5)
    pygame.draw.circle(surf,(80,160,200,150),(gx-100,gy-27),3)
    # Back cone
    pygame.draw.polygon(surf,(42,48,58),[(gx-25,gy-22),(gx-25,gy+10),(gx+20,gy+18),(gx+20,gy-28)])
    pygame.draw.rect(surf, C_GRIP,     (gx-18,  gy+ 8,  16, 30), border_radius=3)
    pygame.draw.arc(surf,  C_METAL, pygame.Rect(gx-30,gy+12,22,20),0,math.pi,2)
    barrel_tip[0] = gx-178; barrel_tip[1] = gy-6


def _draw_shotgun(surf, gx, gy):
    pygame.draw.rect(surf, C_BARREL,    (gx-168, gy-16, 140, 10), border_radius=2)
    pygame.draw.rect(surf, C_BARREL_HL, (gx-167, gy-16, 138,  4))
    pygame.draw.rect(surf, C_METAL,     (gx-148, gy- 4, 110,  7), border_radius=2)
    pygame.draw.rect(surf, C_METAL_HL,  (gx-146, gy- 4, 106,  2))
    # Pump foregrip
    pygame.draw.rect(surf, (90,56,34),  (gx-128, gy-18,  26, 24), border_radius=4)
    for ry in [gy-14, gy-8, gy-2]:
        pygame.draw.rect(surf,(70,42,24),(gx-126,   ry, 22,  2))
    # Receiver
    pygame.draw.rect(surf, C_METAL,    (gx-68,  gy-22,  50, 18), border_radius=3)
    pygame.draw.rect(surf, C_METAL_HL, (gx-66,  gy-22,  46,  4))
    pygame.draw.rect(surf, C_BLACK,    (gx-62,  gy-18,  20, 10))
    # Wood stock
    pygame.draw.rect(surf, C_STOCK,    (gx-24,  gy-14,  24, 12), border_radius=3)
    pygame.draw.rect(surf, C_STOCK,    (gx-24,  gy- 2,  24, 10), border_radius=3)
    pygame.draw.rect(surf, lerp_col(C_STOCK,C_BLACK,0.3),(gx-22,gy-10,20,3))
    pygame.draw.rect(surf, C_GRIP,     (gx-18,  gy- 4,  14, 28), border_radius=3)
    barrel_tip[0] = gx-171; barrel_tip[1] = gy-11

# ═══════════════════════════════════════════════════════════════════════════════
#  PARTICLES
# ═══════════════════════════════════════════════════════════════════════════════
class Particle:
    def __init__(self, px, py, col):
        self.x, self.y = float(px), float(py)
        self.vx = random.uniform(-4,4)
        self.vy = random.uniform(-5,2)
        self.life = random.uniform(0.4, 0.9)
        self.max_life = self.life
        self.col = col

    def update(self, dt):
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy += 200 * dt
        self.life -= dt

    def draw(self, surf):
        a = self.life / self.max_life
        r = max(1, int(4 * a))
        c = lerp_col((20,20,20), self.col, a)
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), r)

# ═══════════════════════════════════════════════════════════════════════════════
#  GAME STATE
# ═══════════════════════════════════════════════════════════════════════════════
def init_G():
    return dict(
        phase='title',  wave=0, score=0, pts=0,
        hp=100, max_hp=100, lane=2, weapon_idx=0,
        upgrades=dict(ammo=0, dmg=0, rate=0),
        total_kills=0, kill_streak=0, combo_mult=1.0, combo_timer=0.0,
        w_states=[dict(ammo=d['max_ammo'], reloading=False, reload_prog=0.0) for d in WEAPON_DEFS],
        zombies=[], projectiles=[], particles=[],
        wave_active=False, wave_timer=0.0, spawn_queue=[], wave_total=0, wave_kills=0,
        boss_active=False, boss=None, boss_idx=0,
        blood_moon=False, blood_moon_timer=0.0,
        last_fire=[0.0]*len(WEAPON_DEFS),
        shake=0.0, flash=0.0,
        fire_held=False,
        prev_lane_t=0.0, prev_weap_t=0.0,
        recoil_offset=0.0, weapon_sway=0.0,
        boss_dead_zombies=[], plague_active=False, phantom_timer=0.0,
        shield_active=False, necro_timer=0.0,
        announce_text='', announce_col=(255,255,255), announce_timer=0.0,
        wave_ann_text='', wave_ann_timer=0.0,
        boss_intro_active=False, boss_intro_timer=0.0, boss_intro_idx=0,
        shop_open=False,
        pause_menu_sel=0,
    )

# ═══════════════════════════════════════════════════════════════════════════════
#  WAVE / SPAWN
# ═══════════════════════════════════════════════════════════════════════════════
def build_wave(G):
    wave = G['wave']
    count  = min(int(6 + wave*2.5), 100)
    diff   = 1.13 ** (wave-1)
    bm_spd = 1.6 if G['blood_moon'] else 1.0
    pl_buf = 1.25 if G['plague_active'] else 1.0
    queue  = []
    for i in range(count):
        r = random.random()
        if   wave < 3:   ztype = 'normal'
        elif wave < 6:   ztype = 'fast' if r < 0.25 else 'normal'
        elif wave < 12:  ztype = 'fast' if r < 0.35 else ('tank' if r < 0.5 else 'normal')
        else:            ztype = 'fast' if r < 0.35 else ('tank' if r < 0.55 else 'normal')
        base_spd = 14 if ztype=='fast' else (5 if ztype=='tank' else 9)
        base_hp  = 220 if ztype=='tank' else (60 if ztype=='fast' else 100)
        queue.append(dict(
            id=random.random(), type=ztype, lane=random.randint(0,LANE_N-1),
            dist=100.0, hp=base_hp*diff*pl_buf, max_hp=base_hp*diff*pl_buf,
            speed=base_spd*(1.08**(wave-1))*bm_spd*pl_buf,
            alive=True, hit_flash=0, invisible=False,
            spawn_delay=i*max(0.3, 2.0-wave*0.06), spawned=False,
            specter_timer=0.0, boss_idx=None, pulse_timer=0.0,
            shield_active=False,
        ))
    return queue

def do_start_wave(G):
    G['wave'] += 1
    G['wave_kills'] = 0
    G['blood_moon'] = (G['wave'] % 7 == 0)
    if G['blood_moon']:
        G['blood_moon_timer'] = 40.0
        show_announce(G, '🩸 BLOOD MOON RISES! 🩸', C_RED)
    if G['wave'] % 10 == 0:
        bi = G['wave']//10 - 1
        G['boss_intro_active'] = True
        G['boss_intro_timer']  = 3.2
        G['boss_intro_idx']    = bi
        return
    if G['wave'] > 1 and G['wave'] % 5 == 0:
        G['shop_open'] = True
        G['phase']     = 'shop'
        return
    _launch_wave(G)

def _launch_wave(G):
    G['wave_active'] = True
    G['wave_timer']  = 0.0
    G['spawn_queue'] = build_wave(G)
    G['wave_total']  = len(G['spawn_queue'])
    G['wave_kills']  = 0
    G['wave_ann_text']  = f'BOSS WAVE {G["wave"]}' if G.get("incoming_boss") else f'WAVE {G["wave"]}'
    G['wave_ann_timer'] = 2.2

def launch_boss_wave(G, bi):
    G['boss_active']   = True
    G['wave_active']   = True
    G['wave_kills']    = 0
    G['spawn_queue']   = []
    G['wave_total']    = 1
    G['plague_active'] = False
    G['shield_active'] = False
    G['phantom_timer'] = 0.0
    G['necro_timer']   = 0.0
    diff = 1.13 ** (G['wave']-1)
    boss = dict(
        id='boss', type='boss', boss_idx=bi,
        lane=2, dist=100.0, hp=1500*diff, max_hp=1500*diff,
        speed=3.5*(1.06**(G['wave']-1)),
        alive=True, hit_flash=0, invisible=False,
        specter_timer=0.0, pulse_timer=0.0, shield_active=False,
    )
    G['boss'] = boss
    G['zombies'].append(boss)
    G['wave_ann_text']  = f'⚠ BOSS WAVE {G["wave"]} ⚠'
    G['wave_ann_timer'] = 2.2

def show_announce(G, text, col, dur=1.8):
    G['announce_text']  = text
    G['announce_col']   = col
    G['announce_timer'] = dur

# ═══════════════════════════════════════════════════════════════════════════════
#  COMBAT
# ═══════════════════════════════════════════════════════════════════════════════
def try_fire(G, now):
    ws = G['w_states'][G['weapon_idx']]
    if ws['reloading']: return
    if ws['ammo'] <= 0: trigger_reload(G); return
    cd = 1.0 / get_wep_stat(G, G['weapon_idx'], 'rate')
    if now - G['last_fire'][G['weapon_idx']] < cd: return
    G['last_fire'][G['weapon_idx']] = now
    ws['ammo'] -= 1
    G['flash'] = 1.0
    G['recoil_offset'] = 18
    wi = G['weapon_idx']
    if   wi == 3: _fire_rocket(G)
    elif wi == 4: _fire_shotgun(G)
    else:         _spawn_proj(G, G['lane'], wi)

def _spawn_proj(G, lane, wi, dmg=None, pierce=None):
    G['projectiles'].append(dict(
        id=random.random(), lane=lane, wi=wi, dist=0.0, speed=80.0,
        pierce=pierce if pierce is not None else get_wep_stat(G, wi, 'pierce'),
        dmg=dmg if dmg is not None else get_wep_stat(G, wi, 'dmg'),
        alive=True, hit=[],
    ))

def _fire_rocket(G):
    for dl in [-1,0,1]:
        tl = G['lane']+dl
        if 0 <= tl < LANE_N: _spawn_proj(G, tl, 3, dmg=get_wep_stat(G,3,'dmg'))
    G['shake'] = 14
    _add_explosion_particles(G, G['lane'])

def _fire_shotgun(G):
    for _ in range(6): _spawn_proj(G, G['lane'], 4)

def trigger_reload(G):
    ws = G['w_states'][G['weapon_idx']]
    if ws['reloading']: return
    if ws['ammo'] >= get_wep_stat(G, G['weapon_idx'], 'max_ammo'): return
    ws['reloading'] = True; ws['reload_prog'] = 0.0

def kill_zombie(G, z):
    z['alive'] = False
    G['total_kills'] += 1; G['wave_kills'] += 1; G['kill_streak'] += 1
    for n, msg, col in KILL_STREAKS:
        if G['kill_streak'] == n: show_announce(G, msg, col)
    if z['type'] == 'tank':
        G['w_states'][G['weapon_idx']]['ammo'] = min(
            get_wep_stat(G, G['weapon_idx'], 'max_ammo'),
            G['w_states'][G['weapon_idx']]['ammo'] + 4)
        show_announce(G, '+4 AMMO', C_CYAN)
    G['combo_mult'] = min(8.0, G['combo_mult'] + 0.5)
    G['combo_timer'] = 3.0
    pts = 1000 if z['type']=='boss' else (150 if z['type']=='tank' else (80 if z['type']=='fast' else 50))
    n   = int(pts * G['combo_mult'])
    G['score'] += n; G['pts'] += n
    if z['type'] != 'boss': G['boss_dead_zombies'].append(dict(**z))
    _add_blood_particles(G, z['lane'], z['dist'])

def _add_blood_particles(G, lane, dist):
    depth = 1 - dist/100
    e = get_lane_edges(lane, 1-depth)
    for _ in range(8):
        cx = e['center'] + random.uniform(-1,1)*e['width']*0.4
        cy = e['y'] - e['width']*0.4*random.random()
        G['particles'].append(Particle(cx, cy, C_BLOOD))

def _add_explosion_particles(G, lane):
    e = get_lane_edges(lane, 0.1)
    cols = [(255,200,50),(255,128,0),(255,64,16),(200,200,200)]
    for _ in range(26):
        G['particles'].append(Particle(
            e['center'] + random.uniform(-80,80),
            H - 80 + random.uniform(-30,30),
            random.choice(cols)))

# ═══════════════════════════════════════════════════════════════════════════════
#  UPDATE
# ═══════════════════════════════════════════════════════════════════════════════
def update(G, dt, now):
    if G['phase'] not in ('game',): return

    G['weapon_sway']   += dt * 0.9
    G['recoil_offset']  = max(0, G['recoil_offset'] - 220*dt)
    G['shake']          = max(0, G['shake']  - 28*dt)
    G['flash']          = max(0, G['flash']  - 4*dt)

    if G['combo_timer'] > 0:
        G['combo_timer'] -= dt
        if G['combo_timer'] <= 0: G['combo_mult'] = 1.0

    if G['blood_moon'] and G['blood_moon_timer'] > 0:
        G['blood_moon_timer'] -= dt
        if G['blood_moon_timer'] <= 0: G['blood_moon'] = False

    G['announce_timer']   = max(0, G['announce_timer']   - dt)
    G['wave_ann_timer']   = max(0, G['wave_ann_timer']   - dt)

    # Boss intro countdown
    if G['boss_intro_active']:
        G['boss_intro_timer'] -= dt
        if G['boss_intro_timer'] <= 0:
            G['boss_intro_active'] = False
            launch_boss_wave(G, G['boss_intro_idx'])
        return

    # Reload
    ws = G['w_states'][G['weapon_idx']]
    if ws['reloading']:
        rt = get_wep_stat(G, G['weapon_idx'], 'reload_s')
        ws['reload_prog'] += dt / rt
        if ws['reload_prog'] >= 1.0:
            ws['reloading'] = False; ws['reload_prog'] = 0.0
            ws['ammo'] = get_wep_stat(G, G['weapon_idx'], 'max_ammo')

    # Auto-fire SMG
    if G['fire_held'] and WEAPON_DEFS[G['weapon_idx']]['auto']:
        try_fire(G, now)

    # Spawn queue
    G['wave_timer'] += dt
    for s in G['spawn_queue']:
        if not s['spawned'] and G['wave_timer'] >= s['spawn_delay']:
            s['spawned'] = True; G['zombies'].append(s)
    G['spawn_queue'] = [s for s in G['spawn_queue'] if not s['spawned']]

    # Projectile update
    for p in G['projectiles']:
        if not p['alive']: continue
        p['dist'] += p['speed'] * dt
        if p['dist'] > 110: p['alive'] = False; continue
        for z in G['zombies']:
            if not z['alive'] or z['invisible'] or z['id'] in p['hit'] or z['lane'] != p['lane']: continue
            if G['shield_active'] and z is G.get('boss'): continue
            if abs(p['dist'] - (100 - z['dist'])) < 9:
                dmg = p['dmg']
                if p['wi'] == 4: dmg *= (0.08 + 0.92*(100-z['dist'])/100)  # shotgun falloff
                if z['type']=='boss' and z['boss_idx'] in (2,9) and random.random()<0.5:
                    dmg=0; show_announce(G,'BLOCKED!', (136,136,136))
                if random.random() < 0.05:
                    dmg *= 2; show_announce(G, 'CRITICAL!', C_GOLD)
                z['hp'] -= dmg; z['hit_flash'] = 10
                _add_blood_particles(G, z['lane'], z['dist'])
                p['hit'].append(z['id'])
                if not p['pierce']: p['alive'] = False
                if z['hp'] <= 0: kill_zombie(G, z)
    G['projectiles'] = [p for p in G['projectiles'] if p['alive']]

    # Zombie update
    for z in G['zombies']:
        if not z['alive']: continue
        if z['hit_flash'] > 0: z['hit_flash'] -= 1
        spd = z['speed']
        if z['type']=='boss':
            z['pulse_timer'] += dt
            bi = z['boss_idx']
            if bi in (4,9): spd *= (1 + (1-z['hp']/z['max_hp'])*2.5)
            if bi in (0,9): z['specter_timer']+=dt; z['invisible']=int(z['specter_timer']/2.0)%2==1
            if bi in (6,9): G['phantom_timer']+=dt; (z.update({'lane':random.randint(0,LANE_N-1)}) if G['phantom_timer']>3.0 else None); G['phantom_timer']=0 if G['phantom_timer']>3.0 else G['phantom_timer']
            if bi in (8,9): z['hp']=min(z['max_hp'], z['hp']+4*dt)
            if bi in (5,9): G['plague_active']=True
            if bi in (7,9) and not G['shield_active'] and z['hp']<z['max_hp']*0.7:
                G['shield_active']=True; show_announce(G,'SHIELD!',C_GOLD)
            z['shield_active'] = G['shield_active'] and z is G.get('boss')
        z['dist'] -= spd * dt
        if z['dist'] <= 0:
            z['alive'] = False
            G['hp'] -= 50 if z['type']=='boss' else (25 if z['type']=='tank' else 10)
            G['hp'] = max(0, G['hp']); G['shake']=20; G['kill_streak']=0
            if G['hp'] <= 0: G['phase']='gameover'; return

    # Necromancer
    if G.get('boss') and G['boss'] and G['boss']['alive'] and G['boss']['boss_idx'] in (1,9):
        G['necro_timer'] += dt
        if G['necro_timer'] > 8.0 and G['boss_dead_zombies']:
            G['necro_timer'] = 0.0
            rv = G['boss_dead_zombies'].pop(); rv['alive']=True; rv['hp']=rv['max_hp']*0.5; rv['dist']=95.0
            G['zombies'].append(rv); show_announce(G,'REVIVED!', (136,0,255))

    G['zombies'] = [z for z in G['zombies'] if z['alive']]

    # Particles
    for p in G['particles']: p.update(dt)
    G['particles'] = [p for p in G['particles'] if p.life > 0]

    # Wave clear
    if G['wave_active'] and not G['zombies'] and not G['spawn_queue'] and not G['boss_intro_active']:
        G['wave_active'] = False
        if G['boss_active']:
            G['boss_active']=False; G['boss']=None; G['plague_active']=False; G['shield_active']=False
            for lane in range(LANE_N): _add_explosion_particles(G, lane)
            G['shake']=26; G['flash']=1.8
            G['score']+=2000; G['pts']+=2000
            G['phase']='wave_clear'  # brief pause then next wave
        else:
            bonus = G['wave']*50; G['score']+=bonus; G['pts']+=bonus
            show_announce(G, f'WAVE CLEAR  +{bonus}', C_GREEN_HUD)
            G['phase']='wave_clear'

# ═══════════════════════════════════════════════════════════════════════════════
#  RENDERING
# ═══════════════════════════════════════════════════════════════════════════════
def draw_game(surf, G, t_ms):
    surf.blit(get_bg(G['blood_moon']), (0,0))
    draw_lanes(surf, G)

    # Zombies (furthest first)
    for z in sorted(G['zombies'], key=lambda z: -z['dist']):
        if not z['alive']: continue
        depth = 1 - z['dist']/100
        e = get_lane_edges(z['lane'], 1-depth)
        zW = max(6, int(e['width'] * 0.80))
        zH = max(10, int(zW * 1.65))
        zX = int(e['center'] - zW/2)
        zY = int(e['y'] - zH)
        alpha = 26 if z['invisible'] else 255
        if alpha < 255:
            tmp = pygame.Surface((zW, zH), pygame.SRCALPHA)
            draw_zombie_sprite(tmp, 0, 0, zW, zH, z)
            tmp.set_alpha(alpha)
            surf.blit(tmp, (zX, zY))
        else:
            draw_zombie_sprite(surf, zX, zY, zW, zH, z)
        # HP bar
        if z['type'] != 'boss':
            hf = max(0, z['hp']/z['max_hp'])
            pygame.draw.rect(surf, (14,5,5),   (zX, zY-7, zW, 4))
            hc = lerp_col((204,32,32),(50,200,80),hf)
            pygame.draw.rect(surf, hc, (zX, zY-7, int(zW*hf), 4))

    # Projectiles
    for p in G['projectiles']:
        depth = p['dist']/100
        e = get_lane_edges(p['lane'], depth)
        px, py = int(e['center']), int(e['y'])
        sz = max(2, int(3 + depth*8))
        if p['wi']==2:  # sniper tracer
            pygame.draw.line(surf,(100,180,255,200),(px,int(depth_to_y(0))),(px,py),max(1,sz//2))
        elif p['wi']==3:  # rocket
            pygame.draw.circle(surf,(255,136,0),(px,py),int(sz*1.6))
            pygame.draw.circle(surf,(255,200,64),(px,py),int(sz*0.7))
        elif p['wi']==1:  # SMG fast
            pygame.draw.rect(surf,(255,240,80),(px-2,py,4,min(20,int(sz*3))))
            pygame.draw.rect(surf,(255,248,192),(px-2,py-3,5,5))
        else:
            pygame.draw.circle(surf,(255,240,80),(px,py),sz)
            pygame.draw.circle(surf,C_WHITE,(px,py),max(1,sz//3))

    # Particles
    for p in G['particles']: p.draw(surf)

    # Vignette
    vig = pygame.Surface((W,H), pygame.SRCALPHA)
    for r_frac in range(10):
        r = int(H*(0.25 + r_frac*0.065))
        alpha = int(r_frac * 7)
        pygame.draw.circle(vig, (0,0,0,alpha), (W//2,H//2), r, max(1,int(H*0.065)))
    pygame.draw.rect(vig,(0,0,0,140),(0,0,W,H),int(W*0.06))
    surf.blit(vig, (0,0))

    draw_player_hand(surf, G, t_ms)
    draw_hud(surf, G, t_ms)
    draw_overlays(surf, G, t_ms)

# ═══════════════════════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════════════════════
def draw_hud(surf, G, t_ms):
    # Bottom HUD panel
    panel_h = 56
    draw_panel(surf, (0, H-panel_h, W, panel_h), alpha=210)

    # HP
    hp_frac = max(0, G['hp']/G['max_hp'])
    hp_c = lerp_col(C_RED, C_GREEN_HUD, hp_frac)
    pygame.draw.rect(surf, (20,5,5),  (10, H-panel_h+8, 170, 10), border_radius=4)
    pygame.draw.rect(surf, hp_c,      (10, H-panel_h+8, int(170*hp_frac), 10), border_radius=4)
    pygame.draw.rect(surf, C_UI_BORDER,(10,H-panel_h+8,170,10),1,border_radius=4)
    draw_text(surf, f'HP  {int(G["hp"])}',font_xs,C_WHITE,12,H-panel_h+20,shadow=False)

    # Wave + score
    wave_c = (255,80,255) if G['wave']%10==0 else C_GREEN_HUD
    draw_text(surf, f'WAVE {G["wave"]}',font_sm, wave_c, W//2, H-panel_h+6, 'midtop')
    draw_text(surf, f'SCORE  {G["score"]:06d}', font_sm, C_GOLD, W//2, H-panel_h+26,'midtop')

    # Weapon + ammo (right side)
    wi  = G['weapon_idx']
    wst = G['w_states'][wi]
    max_a = get_wep_stat(G, wi, 'max_ammo')
    draw_text(surf, WEAPON_DEFS[wi]['name'], font_med, C_CYAN, W-12, H-panel_h+4, 'topright')
    ammo_col = C_GOLD if wst['ammo'] > max_a*0.25 else C_RED
    draw_text(surf, f'{wst["ammo"]} / {max_a}', font_sm, ammo_col, W-12, H-panel_h+30, 'topright', shadow=False)

    # Lane dots
    for i in range(LANE_N):
        c = C_CYAN if i==G['lane'] else C_UI_BORDER
        px = W//2 - LANE_N*14//2 + i*14
        pygame.draw.circle(surf, c, (px, H-8), 5)

    # Combo
    if G['combo_mult'] > 1.0:
        cmb_c = lerp_col(C_GOLD,(255,80,0),min(1,(G['combo_mult']-1)/7))
        draw_text(surf, f'x{G["combo_mult"]:.1f} COMBO', font_sm, cmb_c, 12, H-panel_h-24, shadow=False)

    # Reload progress bar
    if wst['reloading']:
        pygame.draw.rect(surf,(38,28,8),(W//2-80,H-panel_h-14,160,8),border_radius=4)
        pygame.draw.rect(surf,(255,160,30),(W//2-80,H-panel_h-14,int(160*wst['reload_prog']),8),border_radius=4)
        pygame.draw.rect(surf,C_UI_BORDER,(W//2-80,H-panel_h-14,160,8),1,border_radius=4)
        draw_text(surf,'RELOADING',font_xs,(255,180,40),W//2,H-panel_h-26,'midtop',shadow=False)

    # Boss HP bar (top)
    if G['boss_active'] and G.get('boss') and G['boss']['alive']:
        bi   = G['boss']['boss_idx']
        bdef = BOSS_DEFS[bi]
        pygame.draw.rect(surf,(14,3,22),(int(W*0.1),8,int(W*0.8),16),border_radius=3)
        hf = max(0, G['boss']['hp']/G['boss']['max_hp'])
        bc = bdef['col']
        pygame.draw.rect(surf, bc, (int(W*0.1),8,int(W*0.8*hf),16),border_radius=3)
        pygame.draw.rect(surf,C_PURPLE,(int(W*0.1),8,int(W*0.8),16),1,border_radius=3)
        draw_text(surf, bdef['name'], font_xs, bc, W//2, 6, 'midtop', shadow=False)


def draw_overlays(surf, G, t_ms):
    # Kill / streak announcement
    if G['announce_timer'] > 0:
        a = min(1.0, G['announce_timer'])
        txt = font_big.render(G['announce_text'], True, G['announce_col'])
        txt.set_alpha(int(a*255))
        r = txt.get_rect(midtop=(W//2, int(H*0.24)))
        surf.blit(txt, r)

    # Wave announce
    if G['wave_ann_timer'] > 0:
        a = min(1.0, G['wave_ann_timer'])
        txt = font_title.render(G['wave_ann_text'], True, C_RED)
        txt.set_alpha(int(a*255))
        r = txt.get_rect(center=(W//2, int(H*0.40)))
        surf.blit(txt, r)

    # Blood moon banner
    if G['blood_moon'] and G['blood_moon_timer'] > 36:
        txt = font_big.render('🩸 BLOOD MOON 🩸', True, C_RED)
        r = txt.get_rect(midtop=(W//2, 54))
        surf.blit(txt, r)

    # Boss intro
    if G['boss_intro_active']:
        ov = pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,230)); surf.blit(ov,(0,0))
        bdef = BOSS_DEFS[G['boss_intro_idx']]
        # Flashing warning
        if (t_ms//300)%2==0:
            draw_text(surf,'⚠ BOSS INCOMING ⚠',font_med,C_PURPLE,W//2,H//2-80,'center')
        draw_text(surf, bdef['name'], font_title, C_WHITE, W//2, H//2-30, 'center')
        draw_text(surf, bdef['perk'], font_sm,    (120,100,140), W//2, H//2+52, 'center', shadow=False)

# ═══════════════════════════════════════════════════════════════════════════════
#  SCREENS
# ═══════════════════════════════════════════════════════════════════════════════
def screen_title(surf, t_ms):
    surf.blit(get_bg(False),(0,0))
    ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,140)); surf.blit(ov,(0,0))
    tc = lerp_col((180,20,20),(255,80,80),(math.sin(t_ms/600)+1)/2)
    draw_text(surf, 'DEAD LANES', font_title, tc, W//2, 60, 'midtop')
    draw_text(surf, 'UALBANY HACKATHON 2026', font_xs, C_UI_BORDER, W//2, 140, 'midtop', shadow=False)
    draw_panel(surf,(W//2-280,165,560,310),alpha=215)
    pygame.draw.rect(surf,C_UI_BORDER,(W//2-280,165,560,4),border_radius=4)
    rows = [
        ('─── KEYBOARD CONTROLS ──────────────────────', (90,115,145)),
        ('A / D               →  cycle weapon',         C_CYAN),
        ('← →  (or Q / E)    →  switch lane',          C_CYAN),
        ('SPACE               →  shoot  (hold for SMG)',(210,190,100)),
        ('R                   →  reload',               (210,190,100)),
        ('P / ESC             →  pause',                (210,190,100)),
        ('',                                            C_BLACK),
        ('─── SHOP (every 5th wave) ──────────────────',(90,115,145)),
        ('1 / 2 / 3  →  buy upgrade     S  →  skip',   C_GREEN_HUD),
        ('',                                            C_BLACK),
        ('─── GYROSCOPE (optional) ───────────────────',(90,115,145)),
        ('Run gyro_bridge.py with Arduino connected',   (130,130,160)),
        ('',                                            C_BLACK),
        ('PRESS  ENTER  TO  START',                     C_GOLD),
    ]
    for i,(line,col) in enumerate(rows):
        if line: draw_text(surf,line,font_xs,col,W//2,180+i*20,'midtop',shadow=False)


def draw_shop(surf, G):
    ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,220)); surf.blit(ov,(0,0))
    draw_text(surf,'UPGRADE STATION',font_title,C_GOLD,W//2,40,'midtop')
    draw_text(surf,f'POINTS: {G["pts"]}',font_sm,C_UI_BORDER,W//2,116,'midtop',shadow=False)
    names  = ['AMMO CAP','DAMAGE AMP','FIRE RATE']
    icons  = ['📦','💀','⚡']
    keys   = SHOP_KEYS
    costs  = SHOP_COSTS
    effs   = [lambda lv:f'+{lv*15}% capacity',lambda lv:f'+{lv*15}% damage',lambda lv:f'+{lv*15}% fire rate']
    for i in range(3):
        lv   = G['upgrades'][keys[i]]
        cost = costs[i]*(lv+1)
        can  = lv<10 and G['pts']>=cost
        rx   = W//2 - 280 + i*195
        col  = C_CYAN if can else (60,60,80)
        draw_panel(surf,(rx,144,180,200),alpha=220)
        if can: pygame.draw.rect(surf,C_UI_BORDER,(rx,144,180,200),1,border_radius=4)
        draw_text(surf,icons[i],font_big,C_WHITE,rx+90,154,'midtop',shadow=False)
        draw_text(surf,names[i],font_sm,C_WHITE,rx+90,198,'midtop',shadow=False)
        draw_text(surf,f'LV {lv}/10',font_xs,C_UI_BORDER,rx+90,220,'midtop',shadow=False)
        draw_text(surf,effs[i](lv),font_xs,C_GREEN_HUD,rx+90,238,'midtop',shadow=False)
        price_txt = 'MAXED' if lv>=10 else f'{cost} PTS'
        draw_text(surf,price_txt,font_sm,col,rx+90,268,'midtop',shadow=False)
        draw_text(surf,f'[{i+1}]',font_xs,col,rx+90,290,'midtop',shadow=False)
    draw_text(surf,'S / ENTER → SKIP',font_sm,C_UI_BORDER,W//2,358,'midtop',shadow=False)


def draw_pause(surf, G):
    ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,170)); surf.blit(ov,(0,0))
    pw,ph=340,260; px,py=W//2-pw//2,H//2-ph//2
    draw_panel(surf,(px,py,pw,ph),alpha=235)
    pygame.draw.rect(surf,C_GOLD,(px,py,pw,4),border_radius=4)
    draw_text(surf,'PAUSED',font_big,C_GOLD,W//2,py+18,'midtop')
    opts   = ['RESUME','RESTART','QUIT']
    cols_o = [C_GREEN_HUD,(255,200,55),(220,65,55)]
    sel    = G['pause_menu_sel']
    for i,(opt,oc) in enumerate(zip(opts,cols_o)):
        ry = py+70+i*58
        if i==sel:
            pygame.draw.rect(surf,lerp_col(C_UI_BG,oc,0.18),(px+20,ry,pw-40,44),border_radius=6)
            pygame.draw.rect(surf,oc,(px+20,ry,pw-40,44),2,border_radius=6)
        draw_text(surf,opt,font_med,oc if i==sel else lerp_col(oc,(100,110,130),0.5),W//2,ry+10,'midtop')
    draw_text(surf,'↑↓ navigate   ENTER select',font_xs,(80,90,110),W//2,py+ph-22,'midtop',shadow=False)


def draw_gameover(surf, G):
    surf.blit(get_bg(False),(0,0))
    ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,180)); surf.blit(ov,(0,0))
    draw_panel(surf,(W//2-220,120,440,260),alpha=235)
    pygame.draw.rect(surf,C_RED,(W//2-220,120,440,4),border_radius=4)
    draw_text(surf,'GAME OVER',font_title,C_RED,W//2,136,'midtop')
    draw_text(surf,f'WAVE     {G["wave"]}',font_med,C_WHITE,W//2,220,'midtop')
    draw_text(surf,f'SCORE    {G["score"]:06d}',font_med,C_GOLD,W//2,252,'midtop')
    draw_text(surf,f'KILLS    {G["total_kills"]}',font_med,C_GREEN_HUD,W//2,284,'midtop')
    draw_text(surf,'ENTER → Play Again      ESC → Quit',font_xs,(130,150,130),W//2,334,'midtop',shadow=False)

# ═══════════════════════════════════════════════════════════════════════════════
#  OPTIONAL SERIAL / GYROSCOPE
# ═══════════════════════════════════════════════════════════════════════════════
gyro_queue   = queue.Queue()
gyro_running = False

def start_gyro_thread(port=None, baud=9600):
    global gyro_running
    if not SERIAL_OK: return
    gyro_running = True
    t = threading.Thread(target=_gyro_reader, args=(port, baud), daemon=True)
    t.start()

def _gyro_reader(port, baud):
    global gyro_running
    try:
        if port is None:
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                if any(k in (p.description or '').lower() for k in ['arduino','ch340','cp210','ftdi']):
                    port = p.device; break
            if port is None and ports: port = ports[0].device
        if port is None: return
        ser = serial.Serial(port, baud, timeout=1)
        print(f'[GYRO] Connected on {port}')
        _state = dict(shooting=False, last_lane=0.0, last_weap=0.0, last_reload=0.0)
        UP_T=30; DOWN_T=-30; LEFT_T=-40; RIGHT_T=40; LEAN_L=-40; LEAN_R=40; FLIP_T=150
        while gyro_running:
            raw = ser.readline().decode('utf-8','ignore').strip()
            parts = raw.split(',')
            if len(parts) < 3: continue
            try: roll,pitch,yaw = float(parts[0]),float(parts[1]),float(parts[2])
            except: continue
            now = time.time()
            if abs(roll) > FLIP_T:
                if now - _state.get('last_pause',0) > 1.5:
                    _state['last_pause'] = now; gyro_queue.put('pause')
                continue
            if pitch > UP_T:
                if not _state['shooting']: _state['shooting']=True; gyro_queue.put('shoot')
                else: gyro_queue.put('shoot')
            else:
                if _state['shooting']: _state['shooting']=False; gyro_queue.put('shoot_release')
            if pitch < DOWN_T:
                if now - _state['last_reload'] > 0.8: _state['last_reload']=now; gyro_queue.put('reload')
            if yaw < LEFT_T:
                if now - _state['last_lane'] > 0.25: _state['last_lane']=now; gyro_queue.put('lane_left')
            elif yaw > RIGHT_T:
                if now - _state['last_lane'] > 0.25: _state['last_lane']=now; gyro_queue.put('lane_right')
            if abs(pitch) < 20:
                if roll < LEAN_L:
                    if now - _state['last_weap'] > 0.3: _state['last_weap']=now; gyro_queue.put('weapon_prev')
                elif roll > LEAN_R:
                    if now - _state['last_weap'] > 0.3: _state['last_weap']=now; gyro_queue.put('weapon_next')
    except Exception as e:
        print(f'[GYRO] Error: {e}')

def handle_gyro_action(G, action, now):
    if G['phase'] == 'shop':
        if action=='lane_left':  shop_buy(G,0)
        if action=='lane_right': shop_buy(G,1)
        if action=='shoot':      shop_buy(G,2)
        if action=='reload':     shop_skip(G)
        return
    if G['phase'] == 'pause':
        if action=='pause': G['phase']='game'
        return
    if G['phase'] != 'game': return
    if action=='lane_left':
        if now-G['prev_lane_t']>0.2: G['lane']=max(0,G['lane']-1); G['prev_lane_t']=now
    if action=='lane_right':
        if now-G['prev_lane_t']>0.2: G['lane']=min(LANE_N-1,G['lane']+1); G['prev_lane_t']=now
    if action=='weapon_prev':
        if now-G['prev_weap_t']>0.25: G['weapon_idx']=(G['weapon_idx']-1)%len(WEAPON_DEFS); G['prev_weap_t']=now
    if action=='weapon_next':
        if now-G['prev_weap_t']>0.25: G['weapon_idx']=(G['weapon_idx']+1)%len(WEAPON_DEFS); G['prev_weap_t']=now
    if action=='shoot':      G['fire_held']=True; try_fire(G,now)
    if action=='shoot_release': G['fire_held']=False
    if action=='reload':     trigger_reload(G)
    if action=='pause':      G['phase']='pause'

# ═══════════════════════════════════════════════════════════════════════════════
#  SHOP LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def shop_buy(G, i):
    k = SHOP_KEYS[i]; lv = G['upgrades'][k]
    if lv >= 10: return
    cost = SHOP_COSTS[i]*(lv+1)
    if G['pts'] < cost: return
    G['pts'] -= cost; G['upgrades'][k] += 1
    if i==0:
        for wi in range(len(WEAPON_DEFS)):
            G['w_states'][wi]['ammo'] = get_wep_stat(G,wi,'max_ammo')

def shop_skip(G):
    G['shop_open'] = False
    G['phase']     = 'game'
    if G['wave'] % 10 == 0:
        bi = G['wave']//10 - 1
        G['boss_intro_active']=True; G['boss_intro_timer']=3.2; G['boss_intro_idx']=bi
    else:
        _launch_wave(G)
