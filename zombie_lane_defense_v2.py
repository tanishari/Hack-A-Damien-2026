import pygame
import random
import sys
import math
import threading

# ── Optional pyserial ─────────────────────────────────────────────────────────
try:
    import serial as _serial
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False

# ─── CONFIG ───────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 900, 600
LANES = 4
LANE_HEIGHT = HEIGHT // LANES
FPS = 60

SERIAL_PORT     = "COM3"
SERIAL_BAUD     = 9600
JOY_CENTER      = 512
JOY_DEADZONE    = 150
JOY_FIRE_THRESH = JOY_CENTER + JOY_DEADZONE
JOY_LANE_CD_MAX = 22

MAG_SIZE      = 6
RELOAD_FRAMES = 120  # 2 seconds

# ── Colours ───────────────────────────────────────────────────────────────────
BG_SKY_TOP  = (5,  8,  18)
BG_SKY_BOT  = (18, 22, 42)
C_ROAD      = (28, 28, 35)
C_ROAD_LINE = (55, 55, 68)
C_LANE_LINE = (50, 60, 90)

C_PLAYER    = (0,  200, 255)
C_PLAYER_HL = (120, 230, 255)
C_BARREL    = (140, 150, 170)
C_BARREL_HL = (200, 210, 230)
C_MUZZLE    = (255, 230, 100)
C_STOCK     = (100, 70,  40)
C_GRIP      = (80,  55,  30)

C_BULLET    = (255, 240,  80)
C_BULLET_GL = (255, 200,  40)

C_ZOMBIE_N  = (60,  160,  60)
C_ZOMBIE_F  = (200,  60,  60)
C_ZOMBIE_T  = (70,   70, 190)
C_ZOMBIE_EYE= (255,  40,  40)
C_ZOMBIE_HL = (220, 255, 220)
C_SKIN      = (180, 140, 100)
C_SHIRT_N   = (40,  110,  40)
C_SHIRT_F   = (140,  40,  40)
C_SHIRT_T   = (50,   50, 140)
C_PANTS     = (60,   50,  40)

C_BASE      = (120,  80,  30)
C_BASE_HL   = (180, 130,  60)
C_HP_BAR_BG = (50,   15,  15)
C_HP_BAR_FG = (210,  50,  50)
C_AMMO_FULL = (255, 220,  50)
C_AMMO_EMPTY= (55,   55,  68)
C_RELOAD_BAR= (255, 160,  30)

C_FIRE1 = (255,  80,  10)
C_FIRE2 = (255, 160,  30)
C_FIRE3 = (255, 220,  60)
C_SMOKE = (80,   80,  90)

C_EXPLOSION = [(255,200,50),(255,140,30),(255,80,10),(200,200,200)]
C_WHITE     = (255, 255, 255)
C_BLACK     = (0,   0,   0)
C_UI_BG     = (10,  14,  28)
C_UI_BORDER = (60,  90, 140)

BASE_X      = 70
BASE_HP_MAX = 10

# ─── PYGAME INIT ──────────────────────────────────────────────────────────────
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ZOMBIE LANE DEFENSE")
clock  = pygame.time.Clock()

try:
    font_big = pygame.font.SysFont("consolas", 44, bold=True)
    font_med = pygame.font.SysFont("consolas", 24, bold=True)
    font_sm  = pygame.font.SysFont("consolas", 16)
    font_xs  = pygame.font.SysFont("consolas", 13)
except Exception:
    font_big = pygame.font.SysFont(None, 44)
    font_med = pygame.font.SysFont(None, 24)
    font_sm  = pygame.font.SysFont(None, 16)
    font_xs  = pygame.font.SysFont(None, 13)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def lane_cy(idx):
    return idx * LANE_HEIGHT + LANE_HEIGHT // 2

def lerp_colour(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def draw_text(surf, text, font, colour, x, y, anchor="topleft", shadow=True):
    if shadow:
        sh = font.render(text, True, (0, 0, 0))
        r  = sh.get_rect(**{anchor: (x, y)})
        surf.blit(sh, r.move(2, 2))
    lbl = font.render(text, True, colour)
    r   = lbl.get_rect(**{anchor: (x, y)})
    surf.blit(lbl, r)

def draw_panel(surf, rect, alpha=200, border=True):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    s.fill((10, 14, 28, alpha))
    surf.blit(s, (rect[0], rect[1]))
    if border:
        pygame.draw.rect(surf, C_UI_BORDER, rect, 1, border_radius=4)

# ─── SPRITE FACTORIES ─────────────────────────────────────────────────────────

def make_gun_sprite(weapon="normal"):
    """Pixel-art side-view gun.  No external files needed."""
    w, h = 72, 28
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    if weapon == "pierce":
        # ── Sniper rifle ──────────────────────────────────────────────
        pygame.draw.rect(surf, C_BARREL,    (0,  10, 66, 6))
        pygame.draw.rect(surf, C_BARREL_HL, (0,  10, 66, 2))
        # Scope
        pygame.draw.rect(surf, (55, 60, 80), (28,  4, 18, 9), border_radius=2)
        pygame.draw.rect(surf, (90,130,170), (30,  5, 14, 4))
        # Scope cross-hair dots
        pygame.draw.circle(surf, (200,220,255), (37,  7), 2)
        # Receiver body
        pygame.draw.rect(surf, C_BARREL,   (38,  8, 28, 14), border_radius=2)
        # Stock
        pygame.draw.rect(surf, C_STOCK,    (58,  8, 12, 18), border_radius=2)
        pygame.draw.rect(surf, lerp_colour(C_STOCK,(0,0,0),0.3),(58,8,12,5),border_radius=2)
        # Grip
        pygame.draw.rect(surf, C_GRIP,     (50, 16,  8, 10), border_radius=2)
        # Trigger guard
        pygame.draw.arc(surf, C_BARREL, pygame.Rect(47,14,10,10), math.pi, math.pi*2, 2)
        # Bipod legs
        pygame.draw.line(surf, C_BARREL, (10,16),(7,24),2)
        pygame.draw.line(surf, C_BARREL, (14,16),(17,24),2)
        # Muzzle brake
        for my in [10,13,16]:
            pygame.draw.rect(surf, C_BARREL_HL, (0,my,3,2))

    elif weapon == "rapid":
        # ── SMG ───────────────────────────────────────────────────────
        pygame.draw.rect(surf, C_BARREL,    ( 0, 10, 42,  7))
        pygame.draw.rect(surf, C_BARREL_HL, ( 0, 10, 42,  2))
        # Handguard
        pygame.draw.rect(surf, (90,100,120),( 4, 10, 18,  7))
        for rail_x in range(6,22,4):
            pygame.draw.line(surf,(110,120,140),(rail_x,10),(rail_x,17),1)
        # Receiver
        pygame.draw.rect(surf, C_BARREL,   (30,  6, 30, 16), border_radius=3)
        # Stock (folded)
        pygame.draw.rect(surf, C_STOCK,    (54,  4, 16, 20), border_radius=3)
        # Drum magazine
        pygame.draw.circle(surf, (65,70,90), (44, 25), 8)
        pygame.draw.circle(surf, (85,90,110),(44, 25), 6)
        pygame.draw.circle(surf, (110,115,135),(44,25), 3)
        # Grip
        pygame.draw.rect(surf, C_GRIP,     (46, 18,  7, 10), border_radius=2)
        # Trigger guard
        pygame.draw.arc(surf, C_BARREL, pygame.Rect(43,14,10,10), math.pi, math.pi*2, 2)
        # Muzzle flash guard slots
        for my in [10,14,18]:
            pygame.draw.rect(surf, C_BARREL_HL,(0,my,3,2))

    else:
        # ── Assault rifle ─────────────────────────────────────────────
        pygame.draw.rect(surf, C_BARREL,    ( 0, 11, 54,  6))
        pygame.draw.rect(surf, C_BARREL_HL, ( 0, 11, 54,  2))
        # Handguard with rails
        pygame.draw.rect(surf, (95,105,125),( 4, 10, 22,  8))
        for rail_x in range(6,26,5):
            pygame.draw.line(surf,(115,125,145),(rail_x,10),(rail_x,18),1)
        # Receiver body
        pygame.draw.rect(surf, C_BARREL,   (34,  7, 32, 16), border_radius=3)
        # Carry handle / iron sight
        pygame.draw.rect(surf, (75,85,105),(38,  3, 16,  7), border_radius=2)
        pygame.draw.rect(surf, (55,65,85), (40,  3,  4,  4))
        # Stock
        pygame.draw.rect(surf, C_STOCK,    (58,  7, 12, 10), border_radius=2)
        pygame.draw.rect(surf, C_STOCK,    (58, 15, 12,  8), border_radius=2)
        pygame.draw.line(surf, lerp_colour(C_STOCK,(0,0,0),0.3),(58,14),(70,14),1)
        # Magazine
        pygame.draw.rect(surf, (65,75, 95),(43, 20,  8, 12), border_radius=2)
        pygame.draw.rect(surf, (85,95,115),(43, 21,  8,  3))
        # Grip
        pygame.draw.rect(surf, C_GRIP,     (50, 18,  7, 10), border_radius=2)
        pygame.draw.arc(surf, C_BARREL, pygame.Rect(47,14,10,10), math.pi, math.pi*2, 2)
        # Muzzle
        pygame.draw.rect(surf, C_BARREL_HL,(0,12,4,4))
        pygame.draw.rect(surf, C_BARREL_HL,(0,10,3,2))
        pygame.draw.rect(surf, C_BARREL_HL,(0,16,3,2))

    return surf


def make_zombie_sprite(ztype="normal", hit=False):
    """48×72 SRCALPHA pixel-art zombie sprite."""
    sw, sh = 48, 72
    surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    cx = sw // 2

    skin  = C_ZOMBIE_HL if hit else C_SKIN
    shirt_base = {"normal": C_SHIRT_N, "fast": C_SHIRT_F, "tank": C_SHIRT_T}[ztype]
    shirt = lerp_colour(shirt_base, C_WHITE, 0.5) if hit else shirt_base

    if ztype == "tank":
        # ── Tank zombie: wide, hunched, armoured scraps ────────────────
        # Head
        pygame.draw.rect(surf, skin,  (cx-11, 2, 22, 20), border_radius=5)
        pygame.draw.rect(surf, (40,30,20),(cx-11,2,22,6))      # matted hair
        # Scar
        pygame.draw.line(surf,(80,40,40),(cx-7,6),(cx-3,14),1)
        # Eyes – glowing red
        pygame.draw.circle(surf, (30,0,0),  (cx-5,11), 5)
        pygame.draw.circle(surf, (30,0,0),  (cx+5,11), 5)
        pygame.draw.circle(surf, C_ZOMBIE_EYE,(cx-5,11),3)
        pygame.draw.circle(surf, C_ZOMBIE_EYE,(cx+5,11),3)
        pygame.draw.circle(surf, (255,120,120),(cx-5,11),1)
        pygame.draw.circle(surf, (255,120,120),(cx+5,11),1)
        # Exposed teeth
        pygame.draw.rect(surf, (60,20,20),(cx-6,17,12,4))
        for tx in range(cx-5,cx+5,3):
            pygame.draw.rect(surf,(220,210,200),(tx,17,2,3))
        # Neck
        pygame.draw.rect(surf, skin,  (cx-6,20, 12, 6))
        # Torso wide
        pygame.draw.rect(surf, shirt, (cx-18,24, 36, 26), border_radius=4)
        # Armour scraps
        pygame.draw.polygon(surf,(60,60,70),[(cx-18,24),(cx-12,24),(cx-18,34)])
        pygame.draw.polygon(surf,(60,60,70),[(cx+18,24),(cx+12,24),(cx+18,34)])
        # Belt
        pygame.draw.rect(surf,(45,32,18),(cx-18,46,36,5))
        pygame.draw.rect(surf,(100,80,40),(cx-3,46,6,5))
        # Arms – thick
        pygame.draw.rect(surf, shirt,(cx-24,24,8,22),border_radius=3)
        pygame.draw.rect(surf, shirt,(cx+16,24,8,22),border_radius=3)
        pygame.draw.rect(surf, skin, (cx-24,42,8, 8),border_radius=2)
        pygame.draw.rect(surf, skin, (cx+16,42,8, 8),border_radius=2)
        # Claws
        for dx in [-23,-20,-17]:
            pygame.draw.line(surf,(130,100,70),(cx+dx+2,50),(cx+dx,56),1)
        for dx in [17,20,23]:
            pygame.draw.line(surf,(130,100,70),(cx+dx-2,50),(cx+dx-1,56),1)
        # Legs – wide
        pygame.draw.rect(surf,C_PANTS,(cx-16,50,13,22),border_radius=3)
        pygame.draw.rect(surf,C_PANTS,(cx+3, 50,13,22),border_radius=3)
        # Boots
        pygame.draw.rect(surf,(28,22,18),(cx-17,68,15,8),border_radius=2)
        pygame.draw.rect(surf,(28,22,18),(cx+2, 68,15,8),border_radius=2)
        # "TANK" nametag badge
        pygame.draw.rect(surf,(20,20,60),(cx-12,24,24,8),border_radius=2)
        lbl = font_xs.render("TANK",True,(180,180,255))
        surf.blit(lbl, lbl.get_rect(center=(cx,28)))

    elif ztype == "fast":
        # ── Fast zombie: lean, forward-leaning, arms outstretched ─────
        # Head tilted fwd
        pygame.draw.ellipse(surf, skin,  (cx-7, 0,16,16))
        pygame.draw.ellipse(surf, (40,25,15),(cx-7,0,16,5))   # hair
        # Eyes
        pygame.draw.circle(surf,(20,0,0),(cx-2,7),3)
        pygame.draw.circle(surf,(20,0,0),(cx+5,6),3)
        pygame.draw.circle(surf,C_ZOMBIE_EYE,(cx-2,7),2)
        pygame.draw.circle(surf,C_ZOMBIE_EYE,(cx+5,6),2)
        # Slash-mouth
        pygame.draw.line(surf,(80,30,30),(cx-3,12),(cx+5,11),1)
        # Torso – leaning fwd, torn shirt
        pygame.draw.rect(surf, shirt,(cx-8,14,18,22),border_radius=2)
        # Rips
        pygame.draw.line(surf,lerp_colour(shirt,(0,0,0),0.35),(cx-4,16),(cx+2,28),1)
        pygame.draw.line(surf,lerp_colour(shirt,(0,0,0),0.35),(cx+1,14),(cx+6,24),1)
        # Arms stretched fwd
        pygame.draw.rect(surf,shirt,(cx-14,14,8,16),border_radius=2)
        pygame.draw.rect(surf,shirt,(cx+6, 12,8,18),border_radius=2)
        pygame.draw.rect(surf,skin, (cx-14,28,8, 6),border_radius=2)
        pygame.draw.rect(surf,skin, (cx+6, 28,8, 6),border_radius=2)
        # Claws reaching
        for dx in [-14,-11,-8]:
            pygame.draw.line(surf,(140,110,80),(cx+dx+2,34),(cx+dx-1,40),1)
        for dx in [6,9,12]:
            pygame.draw.line(surf,(140,110,80),(cx+dx+2,34),(cx+dx+4,40),1)
        # Legs running pose
        pygame.draw.rect(surf,C_PANTS,(cx-9,34, 9,24),border_radius=2)
        pygame.draw.rect(surf,C_PANTS,(cx+1, 36, 9,22),border_radius=2)
        # Shoes
        pygame.draw.rect(surf,(40,33,26),(cx-10,54,11,8),border_radius=2)
        pygame.draw.rect(surf,(40,33,26),(cx+1,  56,11,7),border_radius=2)

    else:
        # ── Normal zombie: classic shuffler ───────────────────────────
        # Head
        pygame.draw.rect(surf, skin, (cx-9, 2,18,20),border_radius=5)
        # Messy hair
        pygame.draw.rect(surf,(40,28,18),(cx-9,2,18,6))
        pygame.draw.rect(surf,(40,28,18),(cx-9,2,5,10))
        pygame.draw.rect(surf,(40,28,18),(cx+5,2,4,8))
        # Eyes
        pygame.draw.circle(surf,(20,0,0),(cx-3,11),4)
        pygame.draw.circle(surf,(20,0,0),(cx+5,11),4)
        pygame.draw.circle(surf,C_ZOMBIE_EYE,(cx-3,11),3)
        pygame.draw.circle(surf,C_ZOMBIE_EYE,(cx+5,11),3)
        pygame.draw.circle(surf,(255,110,110),(cx-3,11),1)
        pygame.draw.circle(surf,(255,110,110),(cx+5,11),1)
        # Grimace
        pygame.draw.line(surf,(80,35,35),(cx-4,17),(cx+6,17),2)
        pygame.draw.line(surf,(80,35,35),(cx-4,17),(cx-5,19),1)
        pygame.draw.line(surf,(80,35,35),(cx+6,17),(cx+7,19),1)
        # Visible teeth
        for tx in range(cx-3,cx+5,3):
            pygame.draw.rect(surf,(210,200,190),(tx,17,2,2))
        # Neck
        pygame.draw.rect(surf, skin, (cx-4,20,8,5))
        # Torso
        pygame.draw.rect(surf, shirt,(cx-11,24,22,22),border_radius=2)
        pygame.draw.line(surf,lerp_colour(shirt,(0,0,0),0.3),(cx-5,26),(cx+2,40),1)
        # Arms outstretched
        pygame.draw.rect(surf,shirt,(cx-17,24,8,18),border_radius=2)
        pygame.draw.rect(surf,shirt,(cx+9, 24,8,18),border_radius=2)
        pygame.draw.rect(surf,skin, (cx-17,38,8,6),border_radius=2)
        pygame.draw.rect(surf,skin, (cx+9, 38,8,6),border_radius=2)
        # Claws
        for dx in [-17,-14,-11]:
            pygame.draw.line(surf,(120,95,70),(cx+dx+2,44),(cx+dx,50),1)
        for dx in [9,12,15]:
            pygame.draw.line(surf,(120,95,70),(cx+dx-2,44),(cx+dx-1,50),1)
        # Legs
        pygame.draw.rect(surf,C_PANTS,(cx-10,46,10,24),border_radius=2)
        pygame.draw.rect(surf,C_PANTS,(cx+1, 46,10,24),border_radius=2)
        # Shoes
        pygame.draw.rect(surf,(34,27,20),(cx-11,66,12,8),border_radius=2)
        pygame.draw.rect(surf,(34,27,20),(cx+1,  67,12,7),border_radius=2)

    return surf


# Pre-render caches
_zombie_cache = {}
def get_zombie_sprite(ztype, hit=False):
    key = (ztype, hit)
    if key not in _zombie_cache:
        _zombie_cache[key] = make_zombie_sprite(ztype, hit)
    return _zombie_cache[key]

_gun_cache = {}
def get_gun_sprite(weapon="normal"):
    if weapon not in _gun_cache:
        _gun_cache[weapon] = make_gun_sprite(weapon)
    return _gun_cache[weapon]


# ─── BACKGROUND ───────────────────────────────────────────────────────────────

class BurningCar:
    def __init__(self, x, lane):
        self.x    = x
        self.lane = lane
        self.fire  = []
        self.smoke = []
        self.tick  = random.uniform(0, math.pi * 2)
        self.body_col = random.choice([(55,28,18),(38,38,42),(48,33,18)])

    def update(self):
        self.tick += 0.14
        if random.random() < 0.45:
            self.fire.append({
                'x': self.x + random.randint(-22,22),
                'y': lane_cy(self.lane) - 18,
                'vx': random.uniform(-0.5, 0.5),
                'vy': random.uniform(-2.6,-1.0),
                'life': random.randint(18,38),
                'max': 38,
                'r': random.randint(4,11),
            })
        if random.random() < 0.14:
            self.smoke.append({
                'x': self.x + random.randint(-14,14),
                'y': lane_cy(self.lane) - 32,
                'vx': random.uniform(-0.3,0.3),
                'vy': random.uniform(-1.0,-0.5),
                'life': random.randint(40,80),
                'max': 80,
                'r': random.randint(7,16),
            })
        for lst in (self.fire, self.smoke):
            for p in lst:
                p['x'] += p['vx']; p['y'] += p['vy']; p['life'] -= 1
        self.fire  = [p for p in self.fire  if p['life']>0]
        self.smoke = [p for p in self.smoke if p['life']>0]

    def draw(self, surf):
        cy = lane_cy(self.lane)
        # Smoke (back layer)
        for p in self.smoke:
            a = p['life'] / p['max']
            r = max(1, int(p['r'] * (1 + (1-a)*0.6)))
            c = lerp_colour((18,18,22),(65,65,75),a)
            s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*c, int(70*a)),(r,r),r)
            surf.blit(s,(int(p['x'])-r, int(p['y'])-r))
        # Glow pool
        gr = int(34 + math.sin(self.tick)*5)
        gs = pygame.Surface((gr*2,gr*2), pygame.SRCALPHA)
        pygame.draw.circle(gs,(255,90,20,38),(gr,gr),gr)
        surf.blit(gs,(self.x-gr, cy-gr+12))
        # Car chassis
        cw,ch = 82,28
        pygame.draw.rect(surf,self.body_col,(self.x-cw//2,cy-ch//2+4,cw,ch),border_radius=4)
        # Cabin
        cab = lerp_colour(self.body_col,(0,0,0),0.3)
        pygame.draw.rect(surf,cab,(self.x-28,cy-ch//2-14,54,20),border_radius=6)
        # Shattered windows
        pygame.draw.rect(surf,(14,9,5),(self.x-24,cy-ch//2-12,22,14),border_radius=3)
        pygame.draw.rect(surf,(14,9,5),(self.x+2,  cy-ch//2-12,22,14),border_radius=3)
        # Crack lines on windows
        pygame.draw.line(surf,(30,20,10),(self.x-22,cy-ch//2-10),(self.x-12,cy-ch//2-2),1)
        pygame.draw.line(surf,(30,20,10),(self.x+5,cy-ch//2-10),(self.x+18,cy-ch//2-4),1)
        # Wheels
        for wx in [self.x-30, self.x+30]:
            pygame.draw.circle(surf,(18,18,18),(wx,cy+ch//2+2),10)
            pygame.draw.circle(surf,(32,32,32),(wx,cy+ch//2+2),6)
            pygame.draw.circle(surf,(50,50,50),(wx,cy+ch//2+2),2)
        # Fire (front layer)
        for p in self.fire:
            a = p['life'] / p['max']
            r = max(1,int(p['r']*a))
            t = 1-a
            c = lerp_colour(C_FIRE3, lerp_colour(C_FIRE2,C_FIRE1,t), t)
            s = pygame.Surface((r*2,r*2),pygame.SRCALPHA)
            pygame.draw.circle(s,(*c,int(200*a)),(r,r),r)
            surf.blit(s,(int(p['x'])-r,int(p['y'])-r))


def build_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    # Sky gradient
    for y in range(HEIGHT):
        t = y / HEIGHT
        c = lerp_colour(BG_SKY_TOP, BG_SKY_BOT, t)
        pygame.draw.line(bg, c, (0,y),(WIDTH,y))
    # Moon
    pygame.draw.circle(bg,(220,220,180),(815,58),34)
    pygame.draw.circle(bg,(205,205,165),(815,58),32)
    for cx,cy,cr in [(803,50,7),(828,72,5),(812,74,4),(832,52,3)]:
        pygame.draw.circle(bg,(188,188,148),(cx,cy),cr)
    # Moon glow halo
    ms = pygame.Surface((120,120),pygame.SRCALPHA)
    pygame.draw.circle(ms,(220,220,160,18),(60,60),60)
    bg.blit(ms,(755,0))
    # Stars
    random.seed(99)
    for _ in range(140):
        sx = random.randint(0,WIDTH)
        sy = random.randint(0,HEIGHT//2)
        sr = random.choice([1,1,1,1,2])
        bright = random.randint(140,255)
        pygame.draw.circle(bg,(bright,bright,bright),(sx,sy),sr)
    random.seed()
    # Distant city silhouette
    horizon_y = HEIGHT // 2 - 10
    bld_data = [
        (80,50),(115,65),(155,42),(195,70),(235,52),(275,78),(315,44),(355,60),
        (395,72),(435,40),(475,58),(515,48),(555,75),(595,38),(635,60),(675,46),
        (715,68),(755,42),(795,55),(840,38),(885,55),
    ]
    random.seed(77)
    for bx,bh in bld_data:
        pygame.draw.rect(bg,(11,13,20),(bx-14,horizon_y-bh,28,bh))
        # Windows
        for wy in range(horizon_y-bh+5,horizon_y-5,9):
            for wxi in range(bx-10,bx+10,7):
                if random.random()<0.3:
                    wc = random.choice([(75,65,35),(35,55,80),(55,45,25)])
                    pygame.draw.rect(bg,wc,(wxi,wy,4,5))
    random.seed()
    # Road surfaces
    for i in range(LANES):
        y0 = i * LANE_HEIGHT
        road_c = (22+i*2, 23+i*2, 30)
        pygame.draw.rect(bg,road_c,(BASE_X,y0,WIDTH-BASE_X,LANE_HEIGHT))
        # Road texture (subtle)
        for tx in range(BASE_X,WIDTH,60):
            pygame.draw.line(bg,lerp_colour(road_c,(0,0,0),0.07),(tx,y0),(tx,y0+LANE_HEIGHT),1)
        # Lane divider dashes
        if i < LANES-1:
            yl = (i+1)*LANE_HEIGHT
            for dx in range(BASE_X+10,WIDTH,32):
                pygame.draw.rect(bg,C_ROAD_LINE,(dx,yl-1,18,2))
    # Fortification wall (left side)
    pygame.draw.rect(bg,(28,18,8),(0,0,BASE_X,HEIGHT))
    pygame.draw.rect(bg,(44,28,12),(BASE_X-5,0,6,HEIGHT))
    # Sandbag rows
    for i in range(LANES):
        for j in range(3):
            by = i*LANE_HEIGHT + 10 + j*18
            pygame.draw.ellipse(bg,(68,48,22),(4,by,44,14))
            pygame.draw.ellipse(bg,(84,58,28),(4,by,44,6))
            pygame.draw.ellipse(bg,(52,36,16),(44,by+4,6,6))
    return bg

_BG = None
def get_bg():
    global _BG
    if _BG is None:
        _BG = build_background()
    return _BG


# ─── ARDUINO JOYSTICK ─────────────────────────────────────────────────────────

class JoystickController:
    def __init__(self, port=SERIAL_PORT, baud=SERIAL_BAUD):
        self.connected  = False
        self._lock      = threading.Lock()
        self._x         = JOY_CENTER
        self._y         = JOY_CENTER
        self._btn       = 0
        self._btn_event = False
        if not _SERIAL_AVAILABLE:
            return
        try:
            self._ser = _serial.Serial(port, baud, timeout=1)
            self.connected = True
            threading.Thread(target=self._read_loop, daemon=True).start()
        except Exception as e:
            print(f"[Arduino] {e} – keyboard only.")

    def _read_loop(self):
        prev = 0
        while self.connected:
            try:
                raw = self._ser.readline().decode("utf-8", errors="ignore").strip()
                parts = raw.split(",")
                if len(parts) != 3: continue
                x,y,btn = int(parts[0]),int(parts[1]),int(parts[2])
                with self._lock:
                    self._x,self._y,self._btn = x,y,btn
                    if btn==1 and prev==0: self._btn_event = True
                prev = btn
            except: pass

    def get_axes(self):
        with self._lock: return self._x, self._y
    def consume_btn_event(self):
        with self._lock:
            e = self._btn_event; self._btn_event = False; return e
    def btn_held(self):
        with self._lock: return self._btn == 1
    def close(self):
        self.connected = False
        if hasattr(self,"_ser"):
            try: self._ser.close()
            except: pass


# ─── PARTICLES ────────────────────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, colour):
        self.x,self.y = float(x),float(y)
        self.vx = random.uniform(-4,4)
        self.vy = random.uniform(-5,2)
        self.life = random.randint(15,35)
        self.max_life = self.life
        self.r = random.randint(3,8)
        self.colour = colour

    def update(self):
        self.x+=self.vx; self.y+=self.vy; self.vy+=0.25; self.life-=1

    def draw(self, surf):
        a = self.life / self.max_life
        c = lerp_colour((20,20,20), self.colour, a)
        r = max(1, int(self.r*a))
        pygame.draw.circle(surf, c, (int(self.x),int(self.y)), r)


class MuzzleFlash:
    def __init__(self, x, y):
        self.x,self.y = x,y; self.life = 5
    def update(self): self.life -= 1
    def draw(self, surf):
        if self.life <= 0: return
        r = self.life * 5
        s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
        pygame.draw.circle(s,(*C_MUZZLE,int(200*(self.life/5))),(r,r),r)
        surf.blit(s,(self.x-r,self.y-r))
        pygame.draw.circle(surf,C_WHITE,(self.x,self.y),r//3)


# ─── BULLET ───────────────────────────────────────────────────────────────────

class Bullet:
    def __init__(self, lane_idx, speed=15, damage=1, pierce=False):
        self.lane   = lane_idx
        self.x      = float(BASE_X + 44)
        self.speed  = speed
        self.damage = damage
        self.pierce = pierce
        self.alive  = True
        self.trail  = []

    def update(self):
        self.trail.append((self.x, lane_cy(self.lane)))
        if len(self.trail) > 10: self.trail.pop(0)
        self.x += self.speed
        if self.x > WIDTH + 20: self.alive = False

    def draw(self, surf):
        cy = lane_cy(self.lane)
        for i,(tx,ty) in enumerate(self.trail):
            a = i / len(self.trail)
            c = lerp_colour(BG_SKY_TOP, C_BULLET_GL, a)
            pygame.draw.circle(surf,c,(int(tx),ty),max(1,int(4*a)))
        pygame.draw.circle(surf,C_BULLET,(int(self.x),cy),6)
        pygame.draw.circle(surf,C_WHITE, (int(self.x),cy),3)


# ─── ZOMBIE ───────────────────────────────────────────────────────────────────
# HP tuned for 6-shot mag: normal takes 3 shots, fast 2, tank needs ~full mag + reload

ZOMBIE_TYPES = {
    "normal": dict(hp=3,  speed=1.1,  size=28, score=10),
    "fast"  : dict(hp=2,  speed=2.55, size=22, score=15),
    "tank"  : dict(hp=8,  speed=0.55, size=36, score=35),
}

class Zombie:
    def __init__(self, lane_idx, ztype="normal"):
        self.lane   = lane_idx
        self.ztype  = ztype
        cfg = ZOMBIE_TYPES[ztype]
        self.hp      = cfg["hp"]
        self.max_hp  = cfg["hp"]
        self.speed   = cfg["speed"]
        self.size    = cfg["size"]
        self.score_val = cfg["score"]
        self.x       = float(WIDTH + cfg["size"] + 10)
        self.alive   = True
        self.hit_flash = 0
        self.wobble    = random.uniform(0, math.pi*2)
        self._spr      = get_zombie_sprite(ztype, False)
        self._spr_hit  = get_zombie_sprite(ztype, True)

    def update(self):
        self.x -= self.speed
        self.wobble += 0.18
        if self.hit_flash > 0: self.hit_flash -= 1
        if self.x < BASE_X - self.size:
            self.alive = False
            return "breach"

    def take_damage(self, dmg):
        self.hp -= dmg
        self.hit_flash = 8
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surf):
        cy  = lane_cy(self.lane)
        sx  = int(self.x)
        bob = int(math.sin(self.wobble) * 2)
        spr = self._spr_hit if self.hit_flash > 0 else self._spr
        sw,sh = spr.get_size()
        scale = self.size / 28
        if abs(scale-1.0) > 0.01:
            nw,nh = int(sw*scale), int(sh*scale)
            spr = pygame.transform.scale(spr,(nw,nh))
            sw,sh = nw,nh
        surf.blit(spr,(sx-sw//2, cy-sh//2+bob))
        # HP bar
        if self.hp < self.max_hp:
            bw = sw+8; bh = 4
            bx = sx-bw//2
            by = cy-sh//2-8+bob
            pygame.draw.rect(surf,C_HP_BAR_BG,(bx,by,bw,bh))
            fw = int(bw*self.hp/self.max_hp)
            hc = lerp_colour((210,50,50),(50,200,80),self.hp/self.max_hp)
            pygame.draw.rect(surf,hc,(bx,by,fw,bh))


# ─── PLAYER ───────────────────────────────────────────────────────────────────

class Player:
    def __init__(self):
        self.lane         = 0
        self.target_y     = float(lane_cy(0))
        self.y            = float(lane_cy(0))
        self.shoot_cd     = 0
        self.base_hp      = BASE_HP_MAX
        self.weapon       = "normal"
        self.weapon_timer = 0
        self.muzzle_flash = None
        self.ammo         = MAG_SIZE
        self.reloading    = False
        self.reload_timer = 0

    def set_lane(self, idx):
        self.lane = max(0, min(LANES-1, idx))
        self.target_y = float(lane_cy(self.lane))

    def start_reload(self):
        if not self.reloading and self.ammo < MAG_SIZE:
            self.reloading    = True
            self.reload_timer = RELOAD_FRAMES

    def update(self):
        self.y += (self.target_y - self.y) * 0.22
        if self.shoot_cd > 0: self.shoot_cd -= 1
        if self.weapon_timer > 0:
            self.weapon_timer -= 1
            if self.weapon_timer == 0: self.weapon = "normal"
        if self.muzzle_flash:
            self.muzzle_flash.update()
            if self.muzzle_flash.life <= 0: self.muzzle_flash = None
        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self.ammo      = MAG_SIZE
                self.reloading = False

    def shoot(self):
        if self.reloading: return None
        if self.ammo <= 0:
            self.start_reload()
            return None
        cd_map = {"normal":18,"rapid":7,"pierce":24}
        if self.shoot_cd > 0: return None
        self.shoot_cd = cd_map.get(self.weapon,18)
        self.ammo -= 1
        if self.ammo == 0: self.start_reload()
        cx,cy = BASE_X+44, int(self.y)
        self.muzzle_flash = MuzzleFlash(cx,cy)
        if self.weapon == "rapid":
            return Bullet(self.lane, speed=18, damage=1)
        elif self.weapon == "pierce":
            return Bullet(self.lane, speed=14, damage=99, pierce=True)
        else:
            return Bullet(self.lane, speed=15, damage=1)

    def draw(self, surf):
        cy = int(self.y)
        x  = BASE_X
        # Lane glow strip
        hs = pygame.Surface((12,LANE_HEIGHT), pygame.SRCALPHA)
        hs.fill((0,200,255,22))
        surf.blit(hs,(0, self.lane*LANE_HEIGHT))
        # Turret base
        pygame.draw.rect(surf,C_BASE,   (x-30,cy-28,62,56),border_radius=6)
        pygame.draw.rect(surf,C_BASE_HL,(x-30,cy-28,62, 9),border_radius=6)
        # Detail rivets
        for ry in [cy-22,cy,cy+22]:
            pygame.draw.circle(surf,(90,60,24),(x-24,ry),3)
            pygame.draw.circle(surf,(90,60,24),(x+24,ry),3)
        # Sphere
        pygame.draw.circle(surf,C_PLAYER_HL,(x,cy),18)
        pygame.draw.circle(surf,C_PLAYER,   (x,cy),14)
        pygame.draw.circle(surf,C_WHITE,    (x,cy), 5)
        # Gun sprite
        gspr = get_gun_sprite(self.weapon)
        gw,gh = gspr.get_size()
        if self.reloading:
            t     = 1 - self.reload_timer/RELOAD_FRAMES
            angle = math.sin(t*math.pi)*-14
            rot   = pygame.transform.rotate(gspr, angle)
            rr    = rot.get_rect(midleft=(x+12,cy))
            surf.blit(rot,rr)
        else:
            surf.blit(gspr,(x+12,cy-gh//2))
        # Muzzle flash
        if self.muzzle_flash:
            self.muzzle_flash.draw(surf)
        # Weapon badge
        if self.weapon != "normal":
            secs = math.ceil(self.weapon_timer/FPS)
            wc   = (255,220,0) if self.weapon=="rapid" else (100,160,255)
            nm   = {"rapid":"SMG","pierce":"SNP"}[self.weapon]
            draw_text(surf,f"{nm} {secs}s",font_xs,wc,x,cy-46,"midtop")


# ─── POWERUP ──────────────────────────────────────────────────────────────────

POWERUP_TYPES = ["rapid","pierce","heal"]

class PowerUp:
    def __init__(self):
        self.kind   = random.choice(POWERUP_TYPES)
        self.lane   = random.randint(0,LANES-1)
        self.x      = float(WIDTH+20)
        self.alive  = True
        self.pulse  = 0
        self.colour = {"rapid":(255,220,0),"pierce":(100,160,255),"heal":(80,220,80)}[self.kind]

    def update(self):
        self.x -= 1.5; self.pulse += 0.1
        if self.x < BASE_X-20: self.alive = False

    def draw(self, surf):
        cy = lane_cy(self.lane)
        r  = 18+int(math.sin(self.pulse)*3)
        gs = pygame.Surface((r*4,r*4),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*self.colour,55),(r*2,r*2),r*2)
        surf.blit(gs,(int(self.x)-r*2,cy-r*2))
        pygame.draw.circle(surf,self.colour,(int(self.x),cy),r)
        pygame.draw.circle(surf,C_WHITE,(int(self.x),cy),r-5,2)
        labels={"rapid":"SMG","pierce":"SNP","heal":"HP+"}
        lbl = font_xs.render(labels[self.kind],True,C_BLACK)
        surf.blit(lbl,lbl.get_rect(center=(int(self.x),cy)))


# ─── WAVE MANAGER ─────────────────────────────────────────────────────────────

class WaveManager:
    def __init__(self):
        self.wave        = 1
        self.spawn_timer = 0
        self.in_break    = False
        self.break_timer = 0
        self.spawned     = 0
        self.total       = self._count()

    def _count(self):
        # Slightly fewer per wave than original since ammo is gated
        return 4 + self.wave * 3

    def _interval(self):
        # Slower spawn early; tighter as waves progress
        return max(28, 105 - self.wave * 6)

    def _type(self):
        r = random.random()
        if self.wave >= 5 and r < 0.25: return "tank"
        if self.wave >= 3 and r < 0.40: return "fast"
        return "normal"

    def update(self, zombies):
        if self.in_break:
            self.break_timer -= 1
            if self.break_timer <= 0:
                self.in_break = False
                self.wave    += 1
                self.spawned  = 0
                self.total    = self._count()
            return None
        self.spawn_timer += 1
        if self.spawn_timer >= self._interval() and self.spawned < self.total:
            self.spawn_timer = 0
            self.spawned    += 1
            return Zombie(random.randint(0,LANES-1), self._type())
        if self.spawned >= self.total and not zombies:
            self.in_break    = True
            self.break_timer = FPS * 5
        return None


# ─── HUD ──────────────────────────────────────────────────────────────────────

def draw_hud(surf, score, player, wave_mgr, joy):
    # ── Top bar ───────────────────────────────────────────────────────────────
    draw_panel(surf,(0,0,WIDTH,44),alpha=215)

    draw_text(surf,f"SCORE  {score:06d}",font_med,C_WHITE,12,8)

    wave_txt = f"WAVE  {wave_mgr.wave}"
    if wave_mgr.in_break:
        secs = math.ceil(wave_mgr.break_timer/FPS)
        wave_txt += f"   NEXT IN {secs}s"
    draw_text(surf,wave_txt,font_med,(255,200,80),WIDTH//2,8,"midtop")

    # Base HP bar (top right)
    bw=150; bx=WIDTH-bw-10; by=8
    pygame.draw.rect(surf,C_HP_BAR_BG,(bx,by,bw,26),border_radius=4)
    frac = max(0,player.base_hp/BASE_HP_MAX)
    hpc  = lerp_colour((210,50,50),(50,210,80),frac)
    pygame.draw.rect(surf,hpc,(bx,by,int(bw*frac),26),border_radius=4)
    pygame.draw.rect(surf,C_UI_BORDER,(bx,by,bw,26),1,border_radius=4)
    # HP hearts
    for i in range(BASE_HP_MAX//2):
        hx = bx+5+i*14
        hc = (200,50,50) if (i*2)<player.base_hp else (50,50,60)
        draw_text(surf,"v",font_xs,hc,hx,by+6,shadow=False)
    draw_text(surf,f"BASE HP {player.base_hp}/{BASE_HP_MAX}",font_xs,C_WHITE,bx+bw//2,by+2,"midtop",shadow=False)

    # ── Bottom HUD bar ────────────────────────────────────────────────────────
    ph = 50
    draw_panel(surf,(0,HEIGHT-ph,WIDTH,ph),alpha=215)

    # Ammo pips
    px0 = BASE_X+8
    draw_text(surf,"AMMO",font_xs,(150,170,200),px0,HEIGHT-ph+8)
    for i in range(MAG_SIZE):
        c = C_AMMO_FULL if i < player.ammo else C_AMMO_EMPTY
        bpx = px0+48+i*23
        bpy = HEIGHT-ph+7
        # Shell body
        pygame.draw.rect(surf,c,(bpx,bpy+4,14,22),border_radius=3)
        # Shell tip
        pygame.draw.ellipse(surf,lerp_colour(c,C_WHITE,0.35),(bpx,bpy,14,10))
        # Base rim
        if i < player.ammo:
            pygame.draw.rect(surf,(180,140,30),(bpx-1,bpy+23,16,4),border_radius=1)

    # Reload bar
    if player.reloading:
        rb_x=px0; rb_w=212
        rb_y=HEIGHT-12
        pygame.draw.rect(surf,(38,28,8),(rb_x,rb_y,rb_w,8),border_radius=4)
        prog = 1 - player.reload_timer/RELOAD_FRAMES
        pygame.draw.rect(surf,C_RELOAD_BAR,(rb_x,rb_y,int(rb_w*prog),8),border_radius=4)
        pygame.draw.rect(surf,(200,120,20),(rb_x,rb_y,rb_w,8),2,border_radius=4)
        secs_left = math.ceil(player.reload_timer/FPS)
        draw_text(surf,f"RELOADING  {secs_left}s",font_xs,(255,180,40),rb_x+rb_w+8,rb_y-2,shadow=False)
    elif player.ammo == 0:
        draw_text(surf,"PRESS [R] TO RELOAD",font_xs,(255,70,70),px0,HEIGHT-16)

    # Weapon timer (center bottom)
    if player.weapon != "normal":
        secs = math.ceil(player.weapon_timer/FPS)
        wc   = (255,220,0) if player.weapon=="rapid" else (100,160,255)
        nm   = {"rapid":"SMG MODE","pierce":"SNIPER MODE"}[player.weapon]
        draw_text(surf,f"{nm}  {secs}s",font_sm,wc,WIDTH//2,HEIGHT-ph+12,"midtop")

    # Lane numbers
    for i in range(LANES):
        cy = lane_cy(i)
        c  = (120,200,255) if i==player.lane else (65,85,105)
        lbl = font_xs.render(f"[{i+1}]",True,c)
        surf.blit(lbl,lbl.get_rect(midright=(BASE_X-4,cy)))

    # Arduino dot (bottom right)
    if joy.connected:
        jx,jy = joy.get_axes()
        dc = (50,230,50)
        dl = f"JOY  X:{jx:4d}  Y:{jy:4d}"
    else:
        dc = (180,60,60)
        dl = "KB ONLY"
    pygame.draw.circle(surf,dc,(WIDTH-100,HEIGHT-ph+15),5)
    draw_text(surf,dl,font_xs,dc,WIDTH-92,HEIGHT-ph+8,shadow=False)


# ─── PAUSE MENU ───────────────────────────────────────────────────────────────

class PauseMenu:
    OPTIONS  = ["RESUME","RESTART","QUIT"]
    COLOURS  = {"RESUME":(70,215,100),"RESTART":(255,200,55),"QUIT":(220,65,55)}

    def __init__(self):
        self.selected = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected-1)%len(self.OPTIONS)
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected+1)%len(self.OPTIONS)
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.OPTIONS[self.selected].lower()
            if event.key in (pygame.K_p, pygame.K_ESCAPE):
                return "resume"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i,opt in enumerate(self.OPTIONS):
                if self._btn_rect(i).collidepoint(event.pos):
                    return opt.lower()
        return None

    def handle_joy(self, jy, btn_ev, joy_cd):
        """Returns (action|None, new_joy_cd)"""
        action = None
        if btn_ev:
            action = self.OPTIONS[self.selected].lower()
        if joy_cd > 0:
            return action, joy_cd-1
        if jy < JOY_CENTER - JOY_DEADZONE:
            self.selected = (self.selected-1)%len(self.OPTIONS)
            return action, JOY_LANE_CD_MAX
        if jy > JOY_CENTER + JOY_DEADZONE:
            self.selected = (self.selected+1)%len(self.OPTIONS)
            return action, JOY_LANE_CD_MAX
        return action, joy_cd

    def _btn_rect(self, idx):
        bw,bh = 290,52
        cx = WIDTH//2
        cy = HEIGHT//2 - 30 + idx*(bh+16)
        return pygame.Rect(cx-bw//2, cy-bh//2, bw, bh)

    def draw(self, surf):
        # Dim overlay
        ov = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        ov.fill((0,0,0,170))
        surf.blit(ov,(0,0))

        # Panel
        pw,ph = 380,320
        px,py = WIDTH//2-pw//2, HEIGHT//2-ph//2
        draw_panel(surf,(px,py,pw,ph),alpha=235)
        # Panel top accent bar
        pygame.draw.rect(surf,(255,200,60),(px,py,pw,4),border_radius=4)

        draw_text(surf,"PAUSED",font_big,(255,215,70),WIDTH//2,py+16,"midtop")
        draw_text(surf,"W/S  or  UP/DOWN  to navigate    ENTER  to select",
                  font_xs,(130,150,175),WIDTH//2,py+70,"midtop",shadow=False)

        mx,my = pygame.mouse.get_pos()
        for i,opt in enumerate(self.OPTIONS):
            r    = self._btn_rect(i)
            sel  = (i == self.selected)
            hov  = r.collidepoint(mx,my)
            base = self.COLOURS[opt]

            if sel:
                pygame.draw.rect(surf,lerp_colour((10,14,28),base,0.18),r,border_radius=8)
                pygame.draw.rect(surf,base,r,2,border_radius=8)
                # Selection arrows
                draw_text(surf,">>",font_sm,base,r.left-34,r.centery,"midleft",shadow=False)
                draw_text(surf,"<<",font_sm,base,r.right+34,r.centery,"midright",shadow=False)
            elif hov:
                pygame.draw.rect(surf,lerp_colour((10,14,28),base,0.10),r,border_radius=8)
                pygame.draw.rect(surf,lerp_colour(base,(60,80,110),0.5),r,1,border_radius=8)
            else:
                pygame.draw.rect(surf,(18,22,38),r,border_radius=8)
                pygame.draw.rect(surf,(48,62,88),r,1,border_radius=8)

            tc = base if sel else lerp_colour(base,(150,160,180),0.55)
            draw_text(surf,opt,font_med,tc,r.centerx,r.centery,"center")


# ─── SCREENS ──────────────────────────────────────────────────────────────────

def screen_menu(joy):
    t = 0
    while True:
        t += 1
        screen.blit(get_bg(),(0,0))
        ov = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        ov.fill((0,0,0,130)); screen.blit(ov,(0,0))

        # Pulsing title
        tc = lerp_colour((60,180,60),(120,255,120),(math.sin(t*0.05)+1)/2)
        draw_text(screen,"ZOMBIE LANE DEFENSE",font_big,tc,WIDTH//2,78,"midtop")

        # Info panel
        draw_panel(screen,(WIDTH//2-285,152,570,348),alpha=215)
        pygame.draw.rect(screen,(80,200,80),(WIDTH//2-285,152,570,4),border_radius=4)

        rows = [
            ("── KEYBOARD ──────────────────────────────────",(90,115,145)),
            ("[1-4]  Switch lane    [SPACE]  Fire    [R]  Reload",(175,195,175)),
            ("[P]  Pause / unpause  [ESC]  Quit to score",(175,195,175)),
            ("",(0,0,0)),
            ("── ARDUINO JOYSTICK ───────────────────────────",(90,115,145)),
            ("Stick LEFT/RIGHT → Lane    Pull BACK → Fire",(175,195,175)),
            ("Push FWD → Reload          Click → Pause",(175,195,175)),
            ("",(0,0,0)),
            ("── MECHANICS ──────────────────────────────────",(90,115,145)),
            ("6 bullets per magazine  –  reload between waves!",(210,185,95)),
            ("Collect glowing power-ups for SMG or Sniper mode",(175,195,175)),
            ("Tanks need 8 shots – plan your reloads carefully",(175,195,175)),
            ("",(0,0,0)),
            ("Press  ENTER  or  joystick button  to  START",(255,220,60)),
        ]
        for j,(l,c) in enumerate(rows):
            if l: draw_text(screen,l,font_xs,c,WIDTH//2,168+j*22,"midtop",shadow=False)

        # Connection status
        sc = (50,230,50) if joy.connected else (200,70,70)
        st = f"  Arduino: {'CONNECTED' if joy.connected else 'NOT FOUND  (keyboard only)'}"
        pygame.draw.circle(screen,sc,(WIDTH//2-148,HEIGHT-27),5)
        draw_text(screen,st,font_xs,sc,WIDTH//2-140,HEIGHT-34,shadow=False)

        pygame.display.flip()
        clock.tick(60)
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_RETURN: return
        if joy.consume_btn_event(): return


def screen_game_over(score, wave):
    while True:
        screen.blit(get_bg(),(0,0))
        ov = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        ov.fill((0,0,0,160)); screen.blit(ov,(0,0))
        draw_panel(screen,(WIDTH//2-210,138,420,278),alpha=235)
        pygame.draw.rect(screen,(220,50,50),(WIDTH//2-210,138,420,4),border_radius=4)
        draw_text(screen,"GAME OVER",font_big,(220,50,50),WIDTH//2,155,"midtop")
        draw_text(screen,f"SCORE    {score:06d}",font_med,C_WHITE,WIDTH//2,228,"midtop")
        draw_text(screen,f"WAVES    {wave}",font_med,(255,200,80),WIDTH//2,262,"midtop")
        draw_text(screen,"ENTER → Play Again          ESC → Quit",
                  font_sm,(155,175,155),WIDTH//2,336,"midtop")
        pygame.display.flip()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_RETURN: return True
                if ev.key==pygame.K_ESCAPE: return False
        clock.tick(30)


# ─── MAIN GAME LOOP ───────────────────────────────────────────────────────────

def run_game(joy):
    # Burning cars placed across all lanes
    car_positions = [(260,0),(460,1),(680,2),(800,3),(370,1),(580,0),(750,3),(430,2)]
    cars      = [BurningCar(x,l) for x,l in car_positions]
    player    = Player()
    bullets   = []
    zombies   = []
    particles = []
    powerups  = []
    wave_mgr  = WaveManager()
    score     = 0
    pu_timer  = 0
    holding_fire = False
    paused    = False
    pm        = PauseMenu()
    joy_cd    = 0
    bg        = get_bg()

    while True:
        clock.tick(FPS)

        # ── EVENTS ────────────────────────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                joy.close(); pygame.quit(); sys.exit()

            if paused:
                action = pm.handle_event(ev)
                if action == "resume":
                    paused = False
                elif action == "restart":
                    return None          # None = restart signal
                elif action == "quit":
                    return score, wave_mgr.wave
                continue                 # swallow all other events while paused

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_1: player.set_lane(0)
                if ev.key == pygame.K_2: player.set_lane(1)
                if ev.key == pygame.K_3: player.set_lane(2)
                if ev.key == pygame.K_4: player.set_lane(3)
                if ev.key == pygame.K_p:
                    paused = True; pm.selected = 0
                if ev.key == pygame.K_ESCAPE:
                    return score, wave_mgr.wave
                if ev.key == pygame.K_SPACE: holding_fire = True
                if ev.key == pygame.K_r:     player.start_reload()
            if ev.type == pygame.KEYUP:
                if ev.key == pygame.K_SPACE: holding_fire = False

        # ── JOYSTICK ──────────────────────────────────────────────────────────
        if joy.connected:
            jx,jy  = joy.get_axes()
            btn_ev = joy.consume_btn_event()

            if paused:
                action, joy_cd = pm.handle_joy(jy, btn_ev, joy_cd)
                if action == "resume":  paused = False
                elif action == "restart": return None
                elif action == "quit":    return score, wave_mgr.wave
            else:
                if btn_ev: paused=True; pm.selected=0
                if joy_cd>0: joy_cd-=1
                else:
                    if jx < JOY_CENTER-JOY_DEADZONE:
                        player.set_lane(player.lane-1); joy_cd=JOY_LANE_CD_MAX
                    elif jx > JOY_CENTER+JOY_DEADZONE:
                        player.set_lane(player.lane+1); joy_cd=JOY_LANE_CD_MAX
                if jy > JOY_FIRE_THRESH:
                    b = player.shoot()
                    if b: bullets.append(b)
                # Forward push = reload
                if jy < JOY_CENTER - JOY_DEADZONE - 80:
                    player.start_reload()

        # ── PAUSE: render frozen frame + overlay, skip sim ────────────────────
        if paused:
            screen.blit(bg,(0,0))
            for c in cars:     c.draw(screen)
            for p in particles: p.draw(screen)
            for pu in powerups: pu.draw(screen)
            for b in bullets:   b.draw(screen)
            for z in zombies:   z.draw(screen)
            player.draw(screen)
            draw_hud(screen,score,player,wave_mgr,joy)
            pm.draw(screen)
            pygame.display.flip()
            continue

        # ── KEYBOARD FIRE ─────────────────────────────────────────────────────
        if holding_fire:
            b = player.shoot()
            if b: bullets.append(b)

        # ── UPDATE ────────────────────────────────────────────────────────────
        player.update()
        for c  in cars:      c.update()
        for b  in bullets:   b.update()
        for p  in particles: p.update()
        for pu in powerups:  pu.update()

        new_z = wave_mgr.update([z for z in zombies if z.alive])
        if new_z: zombies.append(new_z)

        game_over = False
        for z in zombies:
            result = z.update()
            if result == "breach":
                player.base_hp -= 1
                for _ in range(14):
                    particles.append(Particle(BASE_X, lane_cy(z.lane),(220,55,55)))
                if player.base_hp <= 0: game_over = True

        # Bullet/zombie collisions
        for b in bullets:
            if not b.alive: continue
            for z in zombies:
                if not z.alive: continue
                if b.lane == z.lane and abs(b.x-z.x) < z.size+8:
                    killed = z.take_damage(b.damage)
                    if not b.pierce: b.alive = False
                    if killed:
                        score += z.score_val
                        for _ in range(20):
                            particles.append(Particle(z.x,lane_cy(z.lane),
                                                      random.choice(C_EXPLOSION)))
                    break

        # Player/powerup collisions
        for pu in powerups:
            if not pu.alive: continue
            if pu.lane==player.lane and abs(pu.x-BASE_X)<46:
                pu.alive = False
                if pu.kind == "heal":
                    player.base_hp = min(BASE_HP_MAX, player.base_hp+2)
                else:
                    player.weapon       = pu.kind
                    player.weapon_timer = FPS*15
                score += 50

        # Powerup spawning
        pu_timer += 1
        if pu_timer > FPS * random.randint(12,20):
            pu_timer = 0
            powerups.append(PowerUp())

        # Cleanup dead objects
        bullets   = [b  for b  in bullets   if b.alive]
        zombies   = [z  for z  in zombies   if z.alive]
        particles = [p  for p  in particles if p.life > 0]
        powerups  = [pu for pu in powerups  if pu.alive]

        # ── DRAW ──────────────────────────────────────────────────────────────
        screen.blit(bg,(0,0))
        for c  in cars:      c.draw(screen)
        for p  in particles: p.draw(screen)
        for pu in powerups:  pu.draw(screen)
        for b  in bullets:   b.draw(screen)
        for z  in zombies:   z.draw(screen)
        player.draw(screen)
        draw_hud(screen,score,player,wave_mgr,joy)

        # Wave clear banner
        if wave_mgr.in_break:
            secs = math.ceil(wave_mgr.break_timer/FPS)
            btxt = f"  WAVE {wave_mgr.wave} CLEARED!   Next wave in {secs}s  "
            bs   = font_big.render(btxt,True,(255,220,80))
            bw,bh = bs.get_size()
            draw_panel(screen,(WIDTH//2-bw//2-12,HEIGHT//2-bh//2-8,bw+24,bh+16))
            screen.blit(bs,(WIDTH//2-bw//2,HEIGHT//2-bh//2))

        pygame.display.flip()

        if game_over:
            return score, wave_mgr.wave


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def main():
    joy = JoystickController(port=SERIAL_PORT, baud=SERIAL_BAUD)
    get_bg()           # pre-build static background
    # Pre-cache all sprites
    for wt in ("normal","rapid","pierce"): get_gun_sprite(wt)
    for zt in ("normal","fast","tank"):
        get_zombie_sprite(zt,False)
        get_zombie_sprite(zt,True)

    screen_menu(joy)

    while True:
        result = run_game(joy)
        if result is None:
            continue       # Restart chosen from pause menu
        score, wave = result
        again = screen_game_over(score, wave)
        if not again:
            break

    joy.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
