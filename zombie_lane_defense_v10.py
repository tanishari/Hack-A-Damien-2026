import pygame, random, sys, math, threading, time

try:
    import serial as _serial
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False

# ─── CONFIG ───────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1550, 800
LANES = 4
LANE_HEIGHT = HEIGHT // LANES
FPS = 60

SERIAL_PORT     = "COM11"
SERIAL_BAUD     = 9600
JOY_CENTER      = 512
JOY_DEADZONE    = 150
JOY_FIRE_THRESH = JOY_CENTER + JOY_DEADZONE
JOY_LANE_CD_MAX = 22

MAG_SIZE      = 6
RELOAD_FRAMES = 120
ULT_MAX       = 100.0
ULT_DURATION  = FPS * 5
ULT_HOLD_NEED = 14        # frames to hold diagonal / E for ult activation
SHOP_INTERVAL = 5         # show shop every N waves
BOSS_INTERVAL = 10        # boss wave every N waves

# ── Colours ───────────────────────────────────────────────────────────────────
BG_SKY_TOP=(5,8,18); BG_SKY_BOT=(18,22,42); C_ROAD_LINE=(55,55,68)
C_PLAYER=(0,200,255); C_PLAYER_HL=(120,230,255)
C_BARREL=(140,150,170); C_BARREL_HL=(200,210,230); C_MUZZLE=(255,230,100)
C_STOCK=(100,70,40); C_GRIP=(80,55,30)
C_BULLET=(255,240,80); C_BULLET_GL=(255,200,40)
C_ZOMBIE_EYE=(255,40,40); C_ZOMBIE_HL=(220,255,220); C_SKIN=(180,140,100)
C_SHIRT_N=(40,110,40); C_SHIRT_F=(140,40,40); C_SHIRT_T=(50,50,140); C_PANTS=(60,50,40)
C_BASE=(120,80,30); C_BASE_HL=(180,130,60)
C_HP_BAR_BG=(50,15,15); C_HP_BAR_FG=(210,50,50)
C_AMMO_FULL=(255,220,50); C_AMMO_EMPTY=(55,55,68); C_RELOAD_BAR=(255,160,30)
C_ULT_FILL=(180,60,255); C_ULT_FULL=(255,180,50); C_ULT_ACTIVE=(255,230,80)
C_FIRE1=(255,80,10); C_FIRE2=(255,160,30); C_FIRE3=(255,220,60)
C_EXPLOSION=[(255,200,50),(255,140,30),(255,80,10),(200,200,200)]
C_WHITE=(255,255,255); C_BLACK=(0,0,0); C_UI_BORDER=(60,90,140)

BASE_X=70; BASE_HP_MAX=10

# ─── BOSS DATA (10 unique bosses, repeat after wave 100) ─────────────────────
BOSS_DATA = [
    {"name":"THE BLITZER",   "sub":"Speed Incarnate",    "body":(140,30,20),  "glow":(255,100,40),  "gold":(255,160,40),
     "hp":30,  "speed":0.9,  "abilities":["fast"],                         "perk":"swift_stride",   "perk_name":"Swift Stride",   "perk_desc":"Lane switch 30% faster"},
    {"name":"THE COLOSSUS",  "sub":"Immovable Object",   "body":(60,65,75),   "glow":(130,170,210), "gold":(190,200,220),
     "hp":80,  "speed":0.18, "abilities":["bulwark"],                      "perk":"iron_fortitude", "perk_name":"Iron Fortitude", "perk_desc":"Base max HP +2"},
    {"name":"THE BROODMOTHER","sub":"Spawn of Ruin",     "body":(30,90,30),   "glow":(80,220,80),   "gold":(140,255,100),
     "hp":50,  "speed":0.38, "abilities":["spawn"],                        "perk":"parasite_rounds","perk_name":"Parasite Rounds","perk_desc":"15% kills grant a free shot"},
    {"name":"THE REGENERATOR","sub":"Undying Flesh",     "body":(20,80,100),  "glow":(40,200,220),  "gold":(100,240,255),
     "hp":60,  "speed":0.32, "abilities":["regen"],                        "perk":"vampiric_touch", "perk_name":"Vampiric Touch", "perk_desc":"Every 5 kills heal 1 base HP"},
    {"name":"THE BERSERKER", "sub":"Wrath Unbound",      "body":(160,50,10),  "glow":(255,130,30),  "gold":(255,200,60),
     "hp":55,  "speed":0.42, "abilities":["berserk"],                      "perk":"adrenaline_rush","perk_name":"Adrenaline Rush","perk_desc":"Ult charges 20% faster"},
    {"name":"THE SENTINEL",  "sub":"Guardian of Death",  "body":(20,40,120),  "glow":(80,120,255),  "gold":(160,200,255),
     "hp":65,  "speed":0.28, "abilities":["shield"],                       "perk":"shield_fragment","perk_name":"Shield Fragment","perk_desc":"+1 bullet per magazine"},
    {"name":"THE PHANTOM",   "sub":"Between Worlds",     "body":(70,20,100),  "glow":(180,60,255),  "gold":(220,150,255),
     "hp":70,  "speed":0.4,  "abilities":["phase"],                        "perk":"ghost_protocol", "perk_name":"Ghost Protocol", "perk_desc":"20% shots cost no ammo"},
    {"name":"THE BOMBER",    "sub":"Raining Destruction","body":(100,20,10),  "glow":(255,60,20),   "gold":(255,140,20),
     "hp":75,  "speed":0.32, "abilities":["bomb"],                         "perk":"explosive_rounds","perk_name":"Explosive Rounds","perk_desc":"Bullets splash adjacent lane zombies"},
    {"name":"THE MIMIC",     "sub":"Chaos Given Form",   "body":(80,60,80),   "glow":(200,100,200), "gold":(240,180,240),
     "hp":80,  "speed":0.48, "abilities":["mimic"],                        "perk":"adaptation",     "perk_name":"Adaptation",     "perk_desc":"Power-up duration +50%"},
    {"name":"THE OVERLORD",  "sub":"End of All Things",  "body":(15,10,25),   "glow":(220,180,30),  "gold":(255,220,60),
     "hp":120, "speed":0.28, "abilities":["regen","spawn","shield","bomb"], "perk":"overlord_blessing","perk_name":"Overlord's Blessing","perk_desc":"Start each wave with 25% ult"},
]

# ─── SHOP DATA ────────────────────────────────────────────────────────────────
SHOP_POOL = [
    ("bigger_mag",   "Extended Mag",    "+1 bullet per magazine",        400, 6, "common"),
    ("fast_reload",  "Speed Loader",    "Reload time −20%",              500, 4, "common"),
    ("score_boost",  "Score Surge",     "Score gains +20%",              600, 5, "uncommon"),
    ("base_hp",      "Fortified Base",  "+1 max base HP",                700, 5, "uncommon"),
    ("fire_rate",    "Hair Trigger",    "Fire rate +10%",                500, 5, "common"),
    ("ult_charge",   "Kill Frenzy",     "Ult charges +15% faster",       600, 5, "uncommon"),
    ("powerup_time", "Power Surge",     "Power-up duration +25%",        350, 4, "common"),
    ("pierce_retain","Dense Rounds",    "Sniper pierce loses 10% less",  650, 3, "rare"),
    ("ammo_save",    "Ghost Rounds",    "15% shots cost no ammo",        750, 3, "rare"),
    ("heal_chance",  "Lifesteal",       "2% kills: heal base 1 HP",      900, 3, "rare"),
    ("quick_hands",  "Quick Hands",     "Melee cooldown -25%",           400, 3, "common"),
    ("sweep_strike", "Sweeping Strike", "Melee hits all 4 lanes at once",800, 1, "rare"),
    ("blast_radius", "Blast Radius",    "Grenade explosion +35% radius", 550, 2, "uncommon"),
    ("double_blast", "Double Launcher", "Grenade hits 3 lanes not 2",   700, 1, "rare"),
]
REBIRTH_SHOP = [
    ("rebirth_ammo",  "Eternal Magazine","rt", "+2 bullets per mag",       1),
    ("rebirth_hp",    "Undying Will",    "rt", "+3 max base HP",           1),
    ("rebirth_ult",   "Fury Eternal",    "rt", "Ult charges 50% faster",  2),
    ("rebirth_dmg",   "Ancient Power",   "rt", "All bullet dmg +50%",     2),
    ("rebirth_score", "Plunder",         "rt", "Score multiplier ×2",     2),
]
RARITY_COL = {"common":(80,160,80),"uncommon":(80,80,220),"rare":(200,60,220)}

# ─── PYGAME INIT ──────────────────────────────────────────────────────────────
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DEAD LANES!")
clock = pygame.time.Clock()
try:
    font_big=pygame.font.SysFont("consolas",44,bold=True); font_med=pygame.font.SysFont("consolas",24,bold=True)
    font_sm=pygame.font.SysFont("consolas",16);            font_xs=pygame.font.SysFont("consolas",13)
except:
    font_big=pygame.font.SysFont(None,44); font_med=pygame.font.SysFont(None,24)
    font_sm=pygame.font.SysFont(None,16);  font_xs=pygame.font.SysFont(None,13)

# ─── SOUND MANAGER ────────────────────────────────────────────────────────────
class SoundManager:
    """Procedurally synthesises every sound effect using numpy + pygame.sndarray.
    Falls back silently if numpy is unavailable or the mixer cannot init."""

    SR = 44100  # sample rate

    def __init__(self):
        self._ok = False
        try:
            import numpy as _np
            self._np = _np
            pygame.mixer.init()
            self._sounds   = {}
            self._last_ms  = {}   # rate-limit map  {name: last_play_ticks}
            self._fire_ch  = None
            self._shop_ch  = None
            self._build_all()
            self._ok = True
        except Exception as _e:
            print(f"[SoundManager] disabled: {_e}")

    # ── low-level helpers ────────────────────────────────────────────────────
    def _t(self, dur):
        return self._np.linspace(0, dur, int(self.SR * dur), endpoint=False)

    def _to_snd(self, arr):
        np = self._np
        arr = np.clip(arr, -1.0, 1.0)
        a16 = (arr * 32767).astype(np.int16)
        stereo = np.column_stack([a16, a16])
        return pygame.sndarray.make_sound(stereo)

    def _env(self, sig, atk=0.02, dec=0.15, sus=0.6, rel=0.3):
        np = self._np; n = len(sig)
        a = max(1, int(atk*n)); d = max(1, int(dec*n))
        r = max(1, int(rel*n)); s = max(0, n-a-d-r)
        e = np.zeros(n)
        e[:a]           = np.linspace(0,   1,   a)
        e[a:a+d]        = np.linspace(1,   sus, d)
        e[a+d:a+d+s]    = sus
        e[a+d+s:]       = np.linspace(sus, 0,   max(1, n-a-d-s))
        return sig * e

    def _noise(self, dur, amp=0.5):
        np = self._np; n = int(self.SR*dur)
        return amp * (2*np.random.random(n) - 1)

    def _can_play(self, name, ms_cd=60):
        now = pygame.time.get_ticks()
        if now - self._last_ms.get(name, 0) < ms_cd:
            return False
        self._last_ms[name] = now
        return True

    # ── sound builders ───────────────────────────────────────────────────────
    def _build_all(self):
        np = self._np; SR = self.SR; s = self._sounds

        # ── Shoot: Normal ──
        def gun_normal():
            t = self._t(0.13)
            n = self._noise(0.13, 0.75)
            sig = n * np.exp(-t * 32)
            return self._env(sig, atk=0.001, dec=0.05, sus=0.0, rel=0.95)
        s['shoot_normal'] = self._to_snd(gun_normal())

        # ── Shoot: Rapid (SMG – snappier, higher) ──
        def gun_rapid():
            t = self._t(0.07)
            n = self._noise(0.07, 0.68)
            tone = 0.18 * np.sin(2*np.pi*900*t) * np.exp(-t*60)
            return self._env((n + tone) * np.exp(-t*50), atk=0.001, dec=0.02, sus=0.0, rel=0.97)
        s['shoot_rapid'] = self._to_snd(gun_rapid())

        # ── Shoot: Pierce (sniper – deeper, longer boom) ──
        def gun_pierce():
            t = self._t(0.20)
            n = self._noise(0.20, 0.55)
            bass = 0.32 * np.sin(2*np.pi*100*t) * np.exp(-t*18)
            sig = (n * np.exp(-t*20) + bass)
            return self._env(sig, atk=0.001, dec=0.09, sus=0.1, rel=0.85)
        s['shoot_pierce'] = self._to_snd(gun_pierce())

        # ── Shoot: Ultimate (energy zap) ──
        def gun_ult():
            t = self._t(0.11)
            freq = 700 + 2200*(t/t[-1])**0.5
            ph = np.cumsum(2*np.pi*freq/SR)
            sig = 0.6*np.sin(ph)*np.exp(-t*12)
            n = self._noise(0.11, 0.22) * np.exp(-t*28)
            return self._env(sig+n, atk=0.001, dec=0.04, sus=0.0, rel=0.96)
        s['shoot_ultimate'] = self._to_snd(gun_ult())

        # ── Zombie Spawn (low groaning moan) ──
        def z_spawn():
            t = self._t(0.60)
            vib = 1 + 0.04*np.sin(2*np.pi*5.5*t)
            ph = np.cumsum(2*np.pi*115*vib/SR)
            sig = 0.38*np.sin(ph) + 0.14*np.sin(2*ph) + 0.08*np.sin(3*ph)
            n = self._noise(0.60, 0.07)
            return self._env(sig+n, atk=0.10, dec=0.25, sus=0.50, rel=0.15)
        s['zombie_spawn'] = self._to_snd(z_spawn())

        # ── Zombie Death (descending gurgle) ──
        def z_death():
            t = self._t(0.45)
            freq = 270 * np.exp(-t*3.8)
            ph = np.cumsum(2*np.pi*freq/SR)
            sig = 0.34*np.sin(ph)
            n = self._noise(0.45, 0.32) * np.exp(-t*4.2)
            return self._env(sig+n, atk=0.005, dec=0.20, sus=0.18, rel=0.30)
        s['zombie_death'] = self._to_snd(z_death())

        # ── Grenade Toss (whoosh + fuse whistle) ──
        def gren_toss():
            t = self._t(0.32)
            n = self._noise(0.32, 0.38)
            env_shape = np.sin(np.pi*t/t[-1])
            whistle = 0.13*np.sin(2*np.pi*(380 + 820*t/t[-1])*t)
            return self._env((n*env_shape + whistle), atk=0.06, dec=0.50, sus=0.20, rel=0.20)
        s['grenade_toss'] = self._to_snd(gren_toss())

        # ── Grenade Explosion (big boom) ──
        def explosion():
            t = self._t(0.95)
            bass  = 0.60*np.sin(2*np.pi*52*t)*np.exp(-t*4.2)
            bass2 = 0.28*np.sin(2*np.pi*88*t)*np.exp(-t*6.0)
            n = self._noise(0.95, 0.58) * np.exp(-t*5.0)
            crack_n = int(0.028*SR)
            crack = np.zeros(len(t))
            crack[:crack_n] = (2*np.random.random(crack_n)-1)*0.72
            return np.clip(bass+bass2+n+crack, -1.0, 1.0)
        s['explosion'] = self._to_snd(explosion())

        # ── Knife Slash (blade swoosh) ──
        def slash():
            t = self._t(0.24)
            n = self._noise(0.24, 0.50)
            sweep = np.sin(2*np.pi*np.linspace(500,2600,len(t))*t)
            impact = 0.30*(2*np.random.random(len(t))-1)*np.exp(-t*30)
            sig = n*sweep*0.50 + impact
            return self._env(sig, atk=0.004, dec=0.14, sus=0.08, rel=0.28)
        s['slash'] = self._to_snd(slash())

        # ── Boss Spawn (ominous low horn + rumble) ──
        def boss_spawn():
            dur = 2.0; t = self._t(dur)
            fund = 72
            horn  = 0.36*np.sin(2*np.pi*fund*t)
            horn += 0.18*np.sin(2*np.pi*fund*2*t)
            horn += 0.10*np.sin(2*np.pi*fund*3*t)
            horn += 0.06*np.sin(2*np.pi*fund*4*t)
            trem = 1 + 0.16*np.sin(2*np.pi*6.5*t)
            horn *= trem
            rumble = 0.09*(2*np.random.random(len(t))-1)*np.exp(-np.abs(t-0.08)*3)
            sig = horn + rumble
            a2 = int(0.06*SR); d2 = int(0.30*SR); r2 = int(0.55*SR)
            s2 = max(0, len(t)-a2-d2-r2)
            e2 = np.zeros(len(t))
            e2[:a2]           = np.linspace(0, 1, a2)
            e2[a2:a2+d2]      = np.linspace(1, 0.75, d2)
            e2[a2+d2:a2+d2+s2]= 0.75
            e2[a2+d2+s2:]     = np.linspace(0.75, 0, max(1,r2))
            return np.clip(sig*e2, -1.0, 1.0)
        s['boss_spawn'] = self._to_snd(boss_spawn())

        # ── Bullet Impact (tick click) ──
        def bullet_impact():
            t = self._t(0.06)
            n = self._noise(0.06, 0.50)
            return n * np.exp(-t*85)
        s['bullet_impact'] = self._to_snd(bullet_impact())

        # ── Ultimate Activate (power surge sweep) ──
        def ult_snd():
            dur = 1.05; t = self._t(dur)
            freq = 180 + 1100*(t/dur)**0.65
            ph = np.cumsum(2*np.pi*freq/SR)
            sig = 0.45*np.sin(ph) + 0.20*np.sin(2*ph)
            n = self._noise(dur, 0.14) * np.sin(np.pi*t/dur)
            pk = int(0.68*len(t)); pl = int(0.16*SR)
            pulse = np.zeros(len(t))
            if pk+pl < len(t):
                pulse[pk:pk+pl] = np.sin(np.linspace(0,np.pi,pl))*0.42
            env = np.sin(np.pi*t/dur)**0.4
            return np.clip((sig+n+pulse)*env, -1.0, 1.0)
        s['ult'] = self._to_snd(ult_snd())

        # ── Game Over (four descending notes) ──
        def game_over():
            nd = 0.42; gap = 0.055
            freqs = [440, 370, 294, 220]
            parts = []
            for freq in freqs:
                t = self._t(nd)
                note = 0.52*np.sin(2*np.pi*freq*t) + 0.18*np.sin(2*np.pi*freq*2*t)
                note *= np.exp(-t*4.5)
                parts.append(note)
                parts.append(np.zeros(int(gap*SR)))
            return np.concatenate(parts)
        s['game_over'] = self._to_snd(game_over())

        # ── Reload (two mechanical clicks) ──
        def reload_snd():
            cd = 0.042; gp = 0.085
            t1 = self._t(cd)
            c1 = (2*np.random.random(len(t1))-1) * np.exp(-t1*65)*0.52
            t2 = self._t(cd)
            c2 = (2*np.random.random(len(t2))-1) * np.exp(-t2*65)*0.42
            return np.concatenate([c1, np.zeros(int(gp*SR)), c2])
        s['reload'] = self._to_snd(reload_snd())

        # ── Fire Burning (crackling loop) ──
        def fire_loop():
            dur = 1.6; t = self._t(dur)
            n = self._noise(dur, 0.28)
            am = 0.50 + 0.50*np.sin(2*np.pi*8*t + (2*np.random.random(len(t))-1)*0.6)
            pops = np.zeros(len(t))
            for _ in range(int(dur*14)):
                idx = random.randint(0, len(t)-1)
                pl = random.randint(80, 380); ei = min(len(t), idx+pl)
                pt = np.arange(ei-idx)/SR
                pops[idx:ei] += (2*np.random.random(ei-idx)-1)*np.exp(-pt*55)*0.28
            sig = n*am + pops
            return np.clip(sig, -1.0, 1.0)
        s['fire_loop'] = self._to_snd(fire_loop())
        s['fire_loop'].set_volume(0.35)

        # ── Power Up (ascending chime arpeggio) ──
        def powerup():
            freqs = [523, 659, 784, 1047]   # C5 E5 G5 C6
            nd = 0.16; gp = 0.022
            parts = []
            for freq in freqs:
                t = self._t(nd)
                note = 0.42*np.sin(2*np.pi*freq*t) + 0.15*np.sin(2*np.pi*freq*2*t)
                note *= np.exp(-t*8)
                parts.append(note)
                parts.append(np.zeros(int(gp*SR)))
            return np.concatenate(parts)
        s['powerup'] = self._to_snd(powerup())

        # ── Shoot: SMG (tight mechanical rattle, higher pitch, very short) ──
        def gun_smg():
            t = self._t(0.06)
            n = self._noise(0.06, 0.55)
            # Mechanical click transient at front
            click = 0.35 * np.sin(2*np.pi*1400*t) * np.exp(-t*120)
            # Mid-range chamber rattle
            rattle = 0.20 * np.sin(2*np.pi*620*t) * np.exp(-t*70)
            sig = (n * np.exp(-t*80) + click + rattle)
            return self._env(sig, atk=0.001, dec=0.012, sus=0.0, rel=0.98)
        s['shoot_smg'] = self._to_snd(gun_smg())

        # ── Shoot: Sniper (deep crack + echo tail) ──
        def gun_sniper():
            dur = 0.55; t = self._t(dur)
            # Sharp crack burst
            crack_n = int(0.018 * SR)
            crack = np.zeros(len(t))
            crack[:crack_n] = (2*np.random.random(crack_n)-1) * 0.85
            crack[:crack_n] *= np.linspace(1, 0, crack_n)
            # Deep subsonic bass thump
            bass = 0.45 * np.sin(2*np.pi*68*t) * np.exp(-t*9)
            bass2 = 0.22 * np.sin(2*np.pi*130*t) * np.exp(-t*14)
            # Noise body decaying slowly (the "rifle boom")
            n = self._noise(dur, 0.40) * np.exp(-t*7)
            # Echo: delayed quieter copy
            echo_delay = int(0.11 * SR)
            echo = np.zeros(len(t))
            echo[echo_delay:] = (n[:len(t)-echo_delay] * 0.28)
            sig = crack + bass + bass2 + n + echo
            e = np.zeros(len(t))
            a2 = max(1, int(0.001*SR)); r2 = int(0.45*SR); s2 = max(0, len(t)-a2-r2)
            e[:a2] = np.linspace(0, 1, a2)
            e[a2:a2+s2] = 1.0
            e[a2+s2:] = np.linspace(1.0, 0, max(1, len(t)-a2-s2))
            return np.clip(sig * e, -1.0, 1.0)
        s['shoot_sniper'] = self._to_snd(gun_sniper())

        # ── Knife Slash (realistic blade swoosh + flesh impact) ──
        def knife_slash():
            dur = 0.38; t = self._t(dur)
            # Air whoosh — filtered noise sweeping high→low
            whoosh_env = np.sin(np.pi * t / dur) ** 0.6
            n1 = self._noise(dur, 0.38)
            # Frequency-band filtering via additive: emphasise 800-3000 Hz range
            sweep_hz = np.linspace(3200, 900, len(t))
            modulator = np.sin(2*np.pi*sweep_hz*t / SR) * 0.5 + 0.5
            whoosh = n1 * modulator * whoosh_env
            # Sharp impact transient at ~40% through the swing
            impact_idx = int(0.38 * len(t))
            impact_len = int(0.035 * SR)
            impact = np.zeros(len(t))
            it = np.arange(impact_len) / SR
            impact[impact_idx:impact_idx+impact_len] = (
                (2*np.random.random(impact_len)-1) * np.exp(-it*110) * 0.62
                + 0.28 * np.sin(2*np.pi*280*it) * np.exp(-it*80)
            )
            # Metallic ring (blade resonance)
            ring = 0.10 * np.sin(2*np.pi*2800*t) * np.exp(-t*28)
            sig = whoosh * 0.65 + impact + ring
            return self._env(sig, atk=0.003, dec=0.18, sus=0.05, rel=0.25)
        s['slash'] = self._to_snd(knife_slash())   # replaces old slash

        # ── Take Damage (punchy hit + low grunt) ──
        def take_damage():
            dur = 0.35; t = self._t(dur)
            # Heavy thud
            thud = 0.55 * np.sin(2*np.pi*90*t) * np.exp(-t*18)
            thud += 0.25 * np.sin(2*np.pi*55*t) * np.exp(-t*12)
            # Distorted noise burst (impact crunch)
            n = self._noise(dur, 0.50) * np.exp(-t*22)
            crack_n = int(0.010*SR)
            crack = np.zeros(len(t))
            crack[:crack_n] = (2*np.random.random(crack_n)-1) * 0.70
            # Low grunt tone
            grunt = 0.18 * np.sin(2*np.pi*160*t) * np.exp(-t*10)
            sig = thud + n + crack + grunt
            return self._env(sig, atk=0.001, dec=0.08, sus=0.05, rel=0.55)
        s['take_damage'] = self._to_snd(take_damage())

        # ── Shop Ambient (eerie cash-register ding + low drone hum) ──
        def shop_ambient():
            dur = 3.2; t = self._t(dur)
            # Dark drone: two detuned low tones
            drone1 = 0.18 * np.sin(2*np.pi*82*t)
            drone2 = 0.14 * np.sin(2*np.pi*82.8*t)   # slight detune → beating
            drone3 = 0.09 * np.sin(2*np.pi*164.5*t)  # octave shimmer
            drone = (drone1 + drone2 + drone3) * np.sin(np.pi*t/dur)**0.3
            # Distant metallic ding (register bell)
            ding_t = self._t(0.90)
            ding = 0.38 * np.sin(2*np.pi*1080*ding_t) * np.exp(-ding_t*4.5)
            ding += 0.15 * np.sin(2*np.pi*2160*ding_t) * np.exp(-ding_t*7)
            ding_arr = np.zeros(len(t))
            ding_arr[:len(ding_t)] = ding
            # Second quieter ding mid-way
            mid = int(1.5 * SR)
            ding2 = ding * 0.45
            if mid + len(ding2) < len(t):
                ding_arr[mid:mid+len(ding2)] += ding2
            # Subtle high-frequency shimmer (coins/chains)
            shimmer = self._noise(dur, 0.06) * (0.5 + 0.5*np.sin(2*np.pi*2.5*t))
            sig = drone + ding_arr + shimmer
            return np.clip(sig, -1.0, 1.0)
        s['shop_ambient'] = self._to_snd(shop_ambient())
        s['shop_ambient'].set_volume(0.55)

        # bg_music is handled via pygame.mixer.music (file streaming), not sndarray

    # ── public play API ──────────────────────────────────────────────────────
    def play_zombie_spawn(self):
        if not self._ok or not self._can_play('zombie_spawn', 280): return
        self._sounds['zombie_spawn'].play()

    def play_zombie_death(self):
        if not self._ok or not self._can_play('zombie_death', 45): return
        self._sounds['zombie_death'].play()

    def play_grenade_toss(self):
        if not self._ok: return
        self._sounds['grenade_toss'].play()

    def play_explosion(self):
        if not self._ok: return
        self._sounds['explosion'].play()

    def play_slash(self):
        if not self._ok: return
        self._sounds['slash'].play()

    def play_boss_spawn(self):
        if not self._ok: return
        self._sounds['boss_spawn'].play()

    def play_bullet_impact(self):
        if not self._ok or not self._can_play('bullet_impact', 75): return
        self._sounds['bullet_impact'].play()

    def play_ult(self):
        if not self._ok: return
        self._sounds['ult'].play()

    def play_game_over(self):
        if not self._ok: return
        self._sounds['game_over'].play()

    def play_reload(self):
        if not self._ok: return
        self._sounds['reload'].play()

    def start_fire_loop(self):
        if not self._ok: return
        if self._fire_ch is None or not self._fire_ch.get_busy():
            self._fire_ch = self._sounds['fire_loop'].play(loops=-1)

    def stop_fire_loop(self):
        if not self._ok: return
        if self._fire_ch and self._fire_ch.get_busy():
            self._fire_ch.stop(); self._fire_ch = None

    def play_powerup(self):
        if not self._ok: return
        self._sounds['powerup'].play()

    def play_take_damage(self):
        if not self._ok or not self._can_play('take_damage', 120): return
        self._sounds['take_damage'].play()

    def play_shoot(self, weapon="normal"):
        if not self._ok: return
        if weapon == 'rapid':
            self._sounds['shoot_smg'].play(); return
        if weapon == 'pierce':
            self._sounds['shoot_sniper'].play(); return
        key = f'shoot_{weapon}' if f'shoot_{weapon}' in self._sounds else 'shoot_normal'
        self._sounds[key].play()

    # ── Volume control ───────────────────────────────────────────────────────
    _music_vol = 0.6   # class-level defaults
    _sfx_vol   = 0.8

    def set_music_volume(self, v):
        self._music_vol = max(0.0, min(1.0, v))
        pygame.mixer.music.set_volume(self._music_vol)

    def set_sfx_volume(self, v):
        self._sfx_vol = max(0.0, min(1.0, v))
        for name, snd in self._sounds.items():
            # shop_ambient has its own baseline; scale around it
            if name == 'shop_ambient':
                snd.set_volume(self._sfx_vol * 0.55)
            elif name == 'fire_loop':
                snd.set_volume(self._sfx_vol * 0.35)
            else:
                snd.set_volume(self._sfx_vol)

    def get_music_volume(self): return self._music_vol
    def get_sfx_volume(self):   return self._sfx_vol

    # ── Background music (file-based via pygame.mixer.music) ─────────────────
    def load_music(self, path):
        """Load an audio file as the background music track."""
        try:
            pygame.mixer.music.load(path)
            self._music_loaded = True
        except Exception as e:
            print(f"[SoundManager] Could not load music '{path}': {e}")
            self._music_loaded = False

    def start_bg_music(self):
        if not self._ok: return
        if not getattr(self, '_music_loaded', False): return
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(self._music_vol)
            pygame.mixer.music.play(loops=-1)

    def pause_bg_music(self):
        if not self._ok: return
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()

    def resume_bg_music(self):
        if not self._ok: return
        if not getattr(self, '_music_loaded', False): return
        pygame.mixer.music.unpause()
        if not pygame.mixer.music.get_busy():
            self.start_bg_music()

    def stop_bg_music(self):
        if not self._ok: return
        pygame.mixer.music.stop()

    # ── Shop ambient ─────────────────────────────────────────────────────────
    def start_shop_ambient(self):
        if not self._ok: return
        if self._shop_ch is None or not self._shop_ch.get_busy():
            self._shop_ch = self._sounds['shop_ambient'].play(loops=-1)

    def stop_shop_ambient(self):
        if not self._ok: return
        if self._shop_ch and self._shop_ch.get_busy():
            self._shop_ch.stop(); self._shop_ch = None

sfx = SoundManager()

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def lane_cy(idx): return idx*LANE_HEIGHT+LANE_HEIGHT//2
def lerp_colour(c1,c2,t):
    t=max(0.0,min(1.0,t)); return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))
def draw_text(surf,text,font,colour,x,y,anchor="topleft",shadow=True):
    if shadow:
        sh=font.render(text,True,(0,0,0)); r=sh.get_rect(**{anchor:(x,y)}); surf.blit(sh,r.move(2,2))
    lbl=font.render(text,True,colour); r=lbl.get_rect(**{anchor:(x,y)}); surf.blit(lbl,r)
def draw_panel(surf,rect,alpha=200,border=True,col=(10,14,28)):
    s=pygame.Surface((rect[2],rect[3]),pygame.SRCALPHA); s.fill((*col,alpha)); surf.blit(s,(rect[0],rect[1]))
    if border: pygame.draw.rect(surf,C_UI_BORDER,rect,1,border_radius=4)

# ─── GAME STATE ───────────────────────────────────────────────────────────────
class GameState:
    def __init__(self):
        self.rebirth=0; self.rebirth_tokens=0
        self.perks=set(); self.upgrades={}
        self.shop_shown_wave=0; self.vampire_kills=0
        self._compute()

    def add_upgrade(self,uid): self.upgrades[uid]=self.upgrades.get(uid,0)+1; self._compute()
    def add_perk(self,pid):    self.perks.add(pid); self._compute()

    def _compute(self):
        u=self.upgrades; p=self.perks
        self.mag_bonus      = u.get("bigger_mag",0)+u.get("rebirth_ammo",0)*2+(1 if "shield_fragment" in p else 0)
        self.reload_mult    = max(0.25,1.0-u.get("fast_reload",0)*0.20)
        self.score_mult     = (1.0+u.get("score_boost",0)*0.20)*(2.0 if "rebirth_score" in p else 1.0)
        self.hp_bonus       = u.get("base_hp",0)+u.get("rebirth_hp",0)*3+(2 if "iron_fortitude" in p else 0)
        self.fire_rate_mult = max(0.3,1.0-u.get("fire_rate",0)*0.10)
        self.ult_charge_mult= 1.0+u.get("ult_charge",0)*0.15+(0.5 if "rebirth_ult" in p else 0)+(0.2 if "adrenaline_rush" in p else 0)
        self.pu_dur_mult    = 1.0+u.get("powerup_time",0)*0.25+(0.5 if "adaptation" in p else 0)
        self.pierce_retain  = min(0.88,0.50+u.get("pierce_retain",0)*0.10)
        self.ammo_save      = min(0.50,u.get("ammo_save",0)*0.15+(0.20 if "ghost_protocol" in p else 0))
        self.heal_chance    = min(0.15,u.get("heal_chance",0)*0.02)
        self.splash         = "explosive_rounds" in p
        self.swift_stride   = "swift_stride" in p
        self.parasite       = "parasite_rounds" in p
        self.vampiric       = "vampiric_touch"  in p
        self.wave_start_ult = 0.25 if "overlord_blessing" in p else 0.0
        self.dmg_mult       = 1.5  if "rebirth_dmg" in p else 1.0
        # Melee + grenade
        self.melee_cd_mult   = max(0.25, 1.0 - u.get("quick_hands",0)*0.25)
        self.melee_aoe       = "sweep_strike" in u and u["sweep_strike"]>0
        self.grenade_radius  = 70*(1.0+u.get("blast_radius",0)*0.35)
        self.grenade_lanes   = 3 if ("double_blast" in u and u["double_blast"]>0) else 2

    def difficulty_mult(self,wave):
        return (1.0+max(0,wave-1)*0.025)*(1.0+self.rebirth*0.35)

    def apply_to_player(self,player):
        player.mag_size       = max(1,MAG_SIZE+self.mag_bonus)
        player.ammo           = player.mag_size
        player.reload_duration= max(40,int(RELOAD_FRAMES*self.reload_mult))
        player.ult_charge     = min(ULT_MAX,self.wave_start_ult*ULT_MAX)
        player.ammo_save      = self.ammo_save
        player.fire_rate_mult = self.fire_rate_mult
        player.dmg_mult       = self.dmg_mult
        player.parasite       = self.parasite
        player.pierce_retain  = self.pierce_retain
        player.melee_cd_max   = max(8, int(30*self.melee_cd_mult))
        player.melee_aoe      = self.melee_aoe
        player.grenade_radius = self.grenade_radius
        player.grenade_lanes  = self.grenade_lanes

# ─── SPRITE FACTORIES ─────────────────────────────────────────────────────────
def make_gun_sprite(weapon="normal"):
    w,h=72,28; surf=pygame.Surface((w,h),pygame.SRCALPHA)
    if weapon=="pierce":
        pygame.draw.rect(surf,C_BARREL,(0,10,66,6)); pygame.draw.rect(surf,C_BARREL_HL,(0,10,66,2))
        pygame.draw.rect(surf,(55,60,80),(28,4,18,9),border_radius=2); pygame.draw.rect(surf,(90,130,170),(30,5,14,4))
        pygame.draw.circle(surf,(200,220,255),(37,7),2)
        pygame.draw.rect(surf,C_BARREL,(38,8,28,14),border_radius=2)
        pygame.draw.rect(surf,C_STOCK,(58,8,12,18),border_radius=2)
        pygame.draw.rect(surf,lerp_colour(C_STOCK,(0,0,0),0.3),(58,8,12,5),border_radius=2)
        pygame.draw.rect(surf,C_GRIP,(50,16,8,10),border_radius=2)
        pygame.draw.arc(surf,C_BARREL,pygame.Rect(47,14,10,10),math.pi,math.pi*2,2)
        pygame.draw.line(surf,C_BARREL,(10,16),(7,24),2); pygame.draw.line(surf,C_BARREL,(14,16),(17,24),2)
        for my in [10,13,16]: pygame.draw.rect(surf,C_BARREL_HL,(0,my,3,2))
    elif weapon=="rapid":
        pygame.draw.rect(surf,C_BARREL,(0,10,42,7)); pygame.draw.rect(surf,C_BARREL_HL,(0,10,42,2))
        pygame.draw.rect(surf,(90,100,120),(4,10,18,7))
        for rx in range(6,22,4): pygame.draw.line(surf,(110,120,140),(rx,10),(rx,17),1)
        pygame.draw.rect(surf,C_BARREL,(30,6,30,16),border_radius=3)
        pygame.draw.rect(surf,C_STOCK,(54,4,16,20),border_radius=3)
        pygame.draw.circle(surf,(65,70,90),(44,25),8); pygame.draw.circle(surf,(85,90,110),(44,25),6)
        pygame.draw.rect(surf,C_GRIP,(46,18,7,10),border_radius=2)
        pygame.draw.arc(surf,C_BARREL,pygame.Rect(43,14,10,10),math.pi,math.pi*2,2)
        for my in [10,14,18]: pygame.draw.rect(surf,C_BARREL_HL,(0,my,3,2))
    elif weapon=="ultimate":
        pygame.draw.rect(surf,(180,140,20),(0,10,60,8)); pygame.draw.rect(surf,(255,220,60),(0,10,60,3))
        pygame.draw.rect(surf,(120,100,20),(4,10,20,8))
        for rx in range(6,24,4): pygame.draw.line(surf,(220,180,40),(rx,10),(rx,18),1)
        pygame.draw.rect(surf,(160,120,20),(30,5,32,18),border_radius=3)
        pygame.draw.rect(surf,(255,200,40),(30,5,32,4),border_radius=3)
        pygame.draw.rect(surf,(100,70,15),(55,5,14,22),border_radius=3)
        pygame.draw.rect(surf,(100,70,15),(46,18,8,10),border_radius=2)
        pygame.draw.arc(surf,(180,140,20),pygame.Rect(43,14,10,10),math.pi,math.pi*2,2)
        pygame.draw.circle(surf,(255,220,60),(36,14),4); pygame.draw.circle(surf,(255,255,150),(36,14),2)
        for my in [9,13,17]: pygame.draw.rect(surf,(255,230,60),(0,my,4,2))
    else:
        pygame.draw.rect(surf,C_BARREL,(0,11,54,6)); pygame.draw.rect(surf,C_BARREL_HL,(0,11,54,2))
        pygame.draw.rect(surf,(95,105,125),(4,10,22,8))
        for rx in range(6,26,5): pygame.draw.line(surf,(115,125,145),(rx,10),(rx,18),1)
        pygame.draw.rect(surf,C_BARREL,(34,7,32,16),border_radius=3)
        pygame.draw.rect(surf,(75,85,105),(38,3,16,7),border_radius=2); pygame.draw.rect(surf,(55,65,85),(40,3,4,4))
        pygame.draw.rect(surf,C_STOCK,(58,7,12,10),border_radius=2); pygame.draw.rect(surf,C_STOCK,(58,15,12,8),border_radius=2)
        pygame.draw.rect(surf,(65,75,95),(43,20,8,12),border_radius=2); pygame.draw.rect(surf,(85,95,115),(43,21,8,3))
        pygame.draw.rect(surf,C_GRIP,(50,18,7,10),border_radius=2)
        pygame.draw.arc(surf,C_BARREL,pygame.Rect(47,14,10,10),math.pi,math.pi*2,2)
        pygame.draw.rect(surf,C_BARREL_HL,(0,12,4,4)); pygame.draw.rect(surf,C_BARREL_HL,(0,10,3,2)); pygame.draw.rect(surf,C_BARREL_HL,(0,16,3,2))
    return surf

def make_zombie_sprite(ztype="normal",hit=False):
    sw,sh=48,72; surf=pygame.Surface((sw,sh),pygame.SRCALPHA); cx=sw//2
    z_skin=(180,225,180) if hit else (120,180,110); z_skin_d=(80,130,70); white_eye=(230,240,230) if hit else (220,230,220)
    if ztype=="normal":
        pygame.draw.polygon(surf,(22,18,14),[(cx-2,0),(cx+4,0),(cx+1,-1),(cx,8)])
        pygame.draw.ellipse(surf,(28,20,14),(cx-12,2,26,16))
        pygame.draw.polygon(surf,(22,16,10),[(cx-13,6),(cx-18,2),(cx-10,10)])
        pygame.draw.polygon(surf,(22,16,10),[(cx+12,8),(cx+18,4),(cx+10,12)])
        pygame.draw.ellipse(surf,z_skin,(cx-13,6,26,22))
        pygame.draw.ellipse(surf,(140,30,30),(cx-2,8,6,4)); pygame.draw.ellipse(surf,(180,60,60),(cx-1,9,4,2))
        pygame.draw.ellipse(surf,white_eye,(cx-11,13,10,9)); pygame.draw.ellipse(surf,white_eye,(cx+1,13,10,9))
        pygame.draw.circle(surf,(8,5,5),(cx-7,17),4); pygame.draw.circle(surf,(40,20,20),(cx+5,17),3)
        pygame.draw.circle(surf,(255,255,255),(cx-5,15),1)
        pygame.draw.ellipse(surf,(15,8,8),(cx-12,12,11,10),2)
        pygame.draw.line(surf,(30,15,5),(cx-11,12),(cx-4,14),2); pygame.draw.line(surf,(30,15,5),(cx+2,13),(cx+10,11),2)
        pygame.draw.ellipse(surf,(18,5,5),(cx-8,22,16,8))
        pygame.draw.rect(surf,(210,195,100),(cx-6,22,5,5),border_radius=1); pygame.draw.rect(surf,(195,180,85),(cx+1,23,5,4),border_radius=1)
        pygame.draw.rect(surf,z_skin,(cx-4,27,8,5))
        jacket=(90,40,130) if not hit else (140,100,180)
        pygame.draw.rect(surf,jacket,(cx-14,30,28,24),border_radius=3)
        pygame.draw.polygon(surf,lerp_colour(jacket,(0,0,0),0.25),[(cx,30),(cx-6,30),(cx-2,40)])
        pygame.draw.polygon(surf,lerp_colour(jacket,(0,0,0),0.25),[(cx,30),(cx+6,30),(cx+2,40)])
        shirt_c=(70,90,170) if not hit else (130,150,220)
        pygame.draw.polygon(surf,shirt_c,[(cx-5,32),(cx+5,32),(cx+3,54),(cx-3,54)])
        pygame.draw.ellipse(surf,(110,20,20),(cx-3,40,8,6))
        pygame.draw.rect(surf,jacket,(cx-22,30,10,18),border_radius=3); pygame.draw.ellipse(surf,z_skin,(cx-24,45,14,10))
        for fi,fd in enumerate([-6,-3,0,3]):
            pygame.draw.line(surf,z_skin,(cx-18+fd,52),(cx-20+fd+fi,62),2)
            pygame.draw.line(surf,(150,210,150),(cx-20+fd+fi,62),(cx-21+fd+fi,66),1)
        pygame.draw.rect(surf,jacket,(cx+12,30,10,18),border_radius=3); pygame.draw.ellipse(surf,z_skin,(cx+10,45,14,10))
        for fi,fd in enumerate([-3,0,3,6]):
            pygame.draw.line(surf,z_skin,(cx+14+fd,52),(cx+15+fd-fi,62),2)
            pygame.draw.line(surf,(150,210,150),(cx+15+fd-fi,62),(cx+16+fd-fi,66),1)
        pygame.draw.rect(surf,(55,75,150),(cx-11,54,10,16),border_radius=2); pygame.draw.rect(surf,(55,75,150),(cx+1,54,10,16),border_radius=2)
        pygame.draw.ellipse(surf,(100,15,15),(cx-4,58,5,4))
        pygame.draw.rect(surf,(90,48,28),(cx-13,67,13,7),border_radius=2); pygame.draw.rect(surf,(90,48,28),(cx+1,68,13,6),border_radius=2)
    elif ztype=="tank":
        hair_c=(40,80,75) if not hit else (80,140,130); hair_cd=(25,55,50)
        pygame.draw.circle(surf,hair_c,(cx,5),8); pygame.draw.circle(surf,hair_cd,(cx,5),5)
        pygame.draw.ellipse(surf,hair_c,(cx-16,4,32,20))
        for hx in range(cx-10,cx+10,4): pygame.draw.line(surf,lerp_colour(hair_c,(180,220,210),0.3),(hx,5),(hx+2,18),1)
        pygame.draw.ellipse(surf,z_skin,(cx-14,10,28,24))
        pygame.draw.ellipse(surf,(130,25,25),(cx+5,18,6,4))
        pygame.draw.ellipse(surf,white_eye,(cx-12,17,11,9)); pygame.draw.ellipse(surf,white_eye,(cx+1,17,11,9))
        pygame.draw.circle(surf,(20,8,8),(cx-7,21),3); pygame.draw.circle(surf,(20,8,8),(cx+6,21),3)
        pygame.draw.circle(surf,(255,255,255),(cx-6,19),1); pygame.draw.circle(surf,(255,255,255),(cx+7,19),1)
        pygame.draw.line(surf,(20,10,5),(cx-11,16),(cx-4,18),2); pygame.draw.line(surf,(20,10,5),(cx+4,17),(cx+11,15),2)
        pygame.draw.ellipse(surf,(14,5,5),(cx-8,26,16,7))
        pygame.draw.rect(surf,(200,185,90),(cx-6,26,4,5),border_radius=1); pygame.draw.rect(surf,(185,170,80),(cx-1,27,4,4),border_radius=1); pygame.draw.rect(surf,(200,185,90),(cx+4,26,4,5),border_radius=1)
        pygame.draw.rect(surf,z_skin,(cx-5,33,10,5))
        haori=(220,220,215) if not hit else (255,255,250); haori_d=(170,170,165)
        pygame.draw.rect(surf,haori,(cx-16,36,32,22),border_radius=4)
        pygame.draw.polygon(surf,(180,110,100),[(cx,36),(cx-5,36),(cx,46)]); pygame.draw.polygon(surf,(180,110,100),[(cx,36),(cx+5,36),(cx,46)])
        pygame.draw.line(surf,haori_d,(cx-14,36),(cx-10,58),1); pygame.draw.line(surf,haori_d,(cx+14,36),(cx+10,58),1)
        pygame.draw.ellipse(surf,(120,20,20),(cx-4,44,9,7)); pygame.draw.ellipse(surf,(100,15,15),(cx+5,50,4,4))
        pygame.draw.rect(surf,haori_d,(cx-16,36,4,22),border_radius=2); pygame.draw.rect(surf,haori_d,(cx+12,36,4,22),border_radius=2)
        pygame.draw.ellipse(surf,z_skin,(cx-20,52,12,10)); pygame.draw.ellipse(surf,z_skin,(cx+8,52,12,10))
        for fi in [-3,0,3]:
            pygame.draw.line(surf,z_skin,(cx-15+fi,60),(cx-16+fi,67),2); pygame.draw.line(surf,z_skin,(cx+13+fi,60),(cx+14+fi,67),2)
        hakama=(180,40,50) if not hit else (220,100,110); hakama_d=(130,25,35)
        pygame.draw.rect(surf,hakama,(cx-14,58,28,14),border_radius=3)
        for px in range(cx-10,cx+12,5): pygame.draw.line(surf,hakama_d,(px,58),(px,72),1)
        pygame.draw.polygon(surf,hakama,[(cx-14,68),(cx-18,72),(cx+18,72),(cx+14,68)])
        pygame.draw.rect(surf,(210,215,210),(cx-13,70,12,8),border_radius=2); pygame.draw.rect(surf,(210,215,210),(cx+2,70,12,8),border_radius=2)
    else:  # fast (Rein)
        robe_c=(28,28,32) if not hit else (70,70,80); hood_c=(105,105,110) if not hit else (160,160,170); hood_d=(70,70,75)
        dk_skin=(55,105,55) if not hit else (100,170,100)
        pygame.draw.ellipse(surf,hood_c,(cx-17,2,34,32)); pygame.draw.ellipse(surf,hood_d,(cx-13,5,26,26))
        pygame.draw.polygon(surf,hood_c,[(cx-8,28),(cx+8,28),(cx+6,36),(cx-6,36)])
        pygame.draw.ellipse(surf,dk_skin,(cx-11,10,22,22))
        pygame.draw.line(surf,(35,70,35),(cx-1,12),(cx,22),1); pygame.draw.line(surf,(35,70,35),(cx+3,13),(cx+4,21),1)
        pygame.draw.ellipse(surf,white_eye,(cx-10,17,9,6)); pygame.draw.ellipse(surf,white_eye,(cx+1,17,9,6))
        pygame.draw.ellipse(surf,dk_skin,(cx-11,15,11,5)); pygame.draw.ellipse(surf,dk_skin,(cx+0,15,11,5))
        pygame.draw.circle(surf,(15,50,15),(cx-6,20),2); pygame.draw.circle(surf,(190,195,195),(cx+5,20),3)
        pygame.draw.rect(surf,(15,40,15),(cx-11,15,10,3),border_radius=1); pygame.draw.rect(surf,(15,40,15),(cx+1,15,10,3),border_radius=1)
        pygame.draw.ellipse(surf,lerp_colour(dk_skin,(0,0,0),0.2),(cx-7,24,14,5))
        pygame.draw.rect(surf,(18,6,6),(cx-6,25,12,5))
        pygame.draw.rect(surf,(205,190,95),(cx-5,25,4,4),border_radius=1); pygame.draw.rect(surf,(195,178,85),(cx-1,26,4,3),border_radius=1); pygame.draw.rect(surf,(205,190,95),(cx+3,25,4,4),border_radius=1)
        pygame.draw.rect(surf,hood_c,(cx-5,30,10,6))
        pygame.draw.polygon(surf,hood_c,[(cx-14,28),(cx+14,28),(cx+10,40),(cx-10,40)])
        pygame.draw.line(surf,hood_d,(cx-12,30),(cx+12,30),1)
        pygame.draw.rect(surf,robe_c,(cx-18,36,36,28),border_radius=5)
        pygame.draw.line(surf,(15,15,18),(cx-14,40),(cx-10,64),1); pygame.draw.line(surf,(15,15,18),(cx+14,40),(cx+10,64),1)
        wisp=(80,160,80) if not hit else (140,220,140); wisp2=(50,120,50)
        pygame.draw.ellipse(surf,wisp2,(cx-26,38,16,12)); pygame.draw.ellipse(surf,wisp,(cx-24,40,12,9))
        for fi,ang in enumerate([-5,-2,2,5]):
            px2=cx-22+ang; py2=48+fi*2
            pygame.draw.line(surf,wisp,(px2,py2),(px2+ang-3,py2+10),2)
            pygame.draw.line(surf,wisp2,(px2+ang-3,py2+10),(px2+ang-4,py2+15),1)
        pygame.draw.ellipse(surf,wisp2,(cx+10,38,16,12)); pygame.draw.ellipse(surf,wisp,(cx+12,40,12,9))
        for fi,ang in enumerate([-5,-2,2,5]):
            px2=cx+18+ang; py2=48+fi*2
            pygame.draw.line(surf,wisp,(px2,py2),(px2+ang+3,py2+10),2)
            pygame.draw.line(surf,wisp2,(px2+ang+3,py2+10),(px2+ang+4,py2+15),1)
        pygame.draw.rect(surf,robe_c,(cx-12,62,10,10),border_radius=2); pygame.draw.rect(surf,robe_c,(cx+2,62,10,10),border_radius=2)
        pygame.draw.rect(surf,(18,18,20),(cx-14,69,13,7),border_radius=2); pygame.draw.rect(surf,(18,18,20),(cx+2,69,13,7),border_radius=2)
    return surf

def make_boss_sprite(btype=0,hit=False):
    bd=BOSS_DATA[btype]; sw,sh=64,96; surf=pygame.Surface((sw,sh),pygame.SRCALPHA); cx=sw//2
    body_c =lerp_colour(bd["body"],C_WHITE,0.4) if hit else bd["body"]
    armour_c=lerp_colour(bd["body"],C_WHITE,0.15) if hit else lerp_colour(bd["body"],C_WHITE,0.1)
    glow_c =bd["glow"]; gold_c=bd["gold"]
    n_spikes=[4,8,6,5,8,4,6,4,6,12][btype]
    for i in range(n_spikes):
        a=math.pi+i*math.pi*2/n_spikes; r1=14; r2=22
        sx2=int(cx+math.cos(a)*r1); sy2=int(16+math.sin(a)*8)
        ex=int(cx+math.cos(a)*r2); ey=int(16+math.sin(a)*14)
        pygame.draw.line(surf,gold_c,(sx2,sy2),(ex,ey),3)
        pygame.draw.circle(surf,glow_c,(ex,ey),3)
    pygame.draw.rect(surf,body_c,(cx-13,14,26,22),border_radius=4)
    pygame.draw.rect(surf,armour_c,(cx-12,14,24,8),border_radius=3)
    pygame.draw.rect(surf,glow_c,(cx-10,15,20,3))
    for ey2,er,ec in [(24,4,glow_c),(28,3,lerp_colour(glow_c,C_WHITE,0.4))]:
        for ex2 in [cx-7,cx+7]:
            pygame.draw.circle(surf,(20,5,20),(ex2,ey2),er+1)
            pygame.draw.circle(surf,ec,(ex2,ey2),er)
    pygame.draw.circle(surf,C_WHITE,(cx-6,23),1); pygame.draw.circle(surf,C_WHITE,(cx+8,23),1)
    pygame.draw.rect(surf,(25,5,35),(cx-10,31,20,6),border_radius=2)
    for tx in range(cx-9,cx+9,4): pygame.draw.rect(surf,(210,200,200),(tx,31,3,4))
    pygame.draw.rect(surf,body_c,(cx-6,36,12,6))
    pygame.draw.rect(surf,armour_c,(cx-20,42,40,30),border_radius=5)
    for ox in [cx-26,cx+12]:
        pygame.draw.rect(surf,lerp_colour(bd["body"],C_WHITE,0.2),(ox,40,14,12),border_radius=4)
        pygame.draw.rect(surf,glow_c,(ox,40,14,3),border_radius=4)
    pygame.draw.circle(surf,(20,5,30),(cx,56),10); pygame.draw.circle(surf,bd["body"],(cx,56),8)
    pygame.draw.circle(surf,glow_c,(cx,56),5); pygame.draw.circle(surf,C_WHITE,(cx,56),2)
    for ang2 in range(0,360,60):
        rad=math.radians(ang2)
        pygame.draw.line(surf,glow_c,(cx,56),(int(cx+math.cos(rad)*9),int(56+math.sin(rad)*9)),1)
    pygame.draw.rect(surf,glow_c,(cx-20,42,40,3),border_radius=5)
    for ox in [cx-30,cx+18]:
        pygame.draw.rect(surf,armour_c,(ox,44,12,20),border_radius=3)
        pygame.draw.rect(surf,lerp_colour(bd["body"],C_BLACK if not hit else C_WHITE,0.2),(ox,62,14,16),border_radius=3)
        pygame.draw.rect(surf,glow_c,(ox,62,14,3),border_radius=3)
    for sp in [-3,1,5]:
        pygame.draw.polygon(surf,gold_c,[(cx-31+sp,62),(cx-31+sp+4,62),(cx-31+sp+2,56)])
        pygame.draw.polygon(surf,gold_c,[(cx+19+sp,62),(cx+19+sp+4,62),(cx+19+sp+2,56)])
    for ly in range(50,62,5):
        pygame.draw.circle(surf,gold_c,(cx-25,ly),3,1); pygame.draw.circle(surf,gold_c,(cx+25,ly),3,1)
    pygame.draw.rect(surf,lerp_colour(bd["body"],C_WHITE,0.1),(cx-18,72,14,22),border_radius=3)
    pygame.draw.rect(surf,lerp_colour(bd["body"],C_WHITE,0.1),(cx+4,72,14,22),border_radius=3)
    pygame.draw.rect(surf,glow_c,(cx-18,72,14,3),border_radius=3); pygame.draw.rect(surf,glow_c,(cx+4,72,14,3),border_radius=3)
    pygame.draw.rect(surf,(18,5,25),(cx-19,88,16,8),border_radius=2); pygame.draw.rect(surf,(18,5,25),(cx+3,88,16,8),border_radius=2)
    pygame.draw.polygon(surf,gold_c,[(cx-18,88),(cx-14,88),(cx-16,83)]); pygame.draw.polygon(surf,gold_c,[(cx+5,88),(cx+9,88),(cx+7,83)])
    # Unique badge per type
    labels=["BLZ","COL","BRD","REG","BSK","SEN","PHN","BMB","MMC","OVR"]
    lbl=font_xs.render(labels[btype],True,gold_c)
    surf.blit(lbl,lbl.get_rect(center=(cx,28)))
    return surf

_zombie_cache={}
def get_zombie_sprite(zt,hit=False):
    k=(zt,hit)
    if k not in _zombie_cache: _zombie_cache[k]=make_zombie_sprite(zt,hit)
    return _zombie_cache[k]
_boss_cache={}
def get_boss_sprite(btype,hit=False):
    k=(btype,hit)
    if k not in _boss_cache: _boss_cache[k]=make_boss_sprite(btype,hit)
    return _boss_cache[k]
_gun_cache={}
def get_gun_sprite(w):
    if w not in _gun_cache: _gun_cache[w]=make_gun_sprite(w)
    return _gun_cache[w]

# ─── BACKGROUND ───────────────────────────────────────────────────────────────
class BurningCar:
    def __init__(self,x,lane):
        self.x=x; self.lane=lane; self.fire=[]; self.smoke=[]
        self.tick=random.uniform(0,math.pi*2); self.body_col=random.choice([(55,28,18),(38,38,42),(48,33,18)])
    def update(self):
        self.tick+=0.14
        if random.random()<0.45:
            self.fire.append({'x':self.x+random.randint(-22,22),'y':lane_cy(self.lane)-18,
                              'vx':random.uniform(-0.5,0.5),'vy':random.uniform(-2.6,-1.0),'life':random.randint(18,38),'max':38,'r':random.randint(4,11)})
        if random.random()<0.14:
            self.smoke.append({'x':self.x+random.randint(-14,14),'y':lane_cy(self.lane)-32,
                               'vx':random.uniform(-0.3,0.3),'vy':random.uniform(-1.0,-0.5),'life':random.randint(40,80),'max':80,'r':random.randint(7,16)})
        for lst in (self.fire,self.smoke):
            for p in lst: p['x']+=p['vx']; p['y']+=p['vy']; p['life']-=1
        self.fire=[p for p in self.fire if p['life']>0]; self.smoke=[p for p in self.smoke if p['life']>0]
    def draw(self,surf):
        cy=lane_cy(self.lane)
        for p in self.smoke:
            a=p['life']/p['max']; r=max(1,int(p['r']*(1+(1-a)*0.6))); c=lerp_colour((18,18,22),(65,65,75),a)
            s=pygame.Surface((r*2,r*2),pygame.SRCALPHA); pygame.draw.circle(s,(*c,int(70*a)),(r,r),r); surf.blit(s,(int(p['x'])-r,int(p['y'])-r))
        gr=int(34+math.sin(self.tick)*5); gs2=pygame.Surface((gr*2,gr*2),pygame.SRCALPHA)
        pygame.draw.circle(gs2,(255,90,20,38),(gr,gr),gr); surf.blit(gs2,(self.x-gr,cy-gr+12))
        cw,ch=82,28; pygame.draw.rect(surf,self.body_col,(self.x-cw//2,cy-ch//2+4,cw,ch),border_radius=4)
        cab=lerp_colour(self.body_col,(0,0,0),0.3)
        pygame.draw.rect(surf,cab,(self.x-28,cy-ch//2-14,54,20),border_radius=6)
        pygame.draw.rect(surf,(14,9,5),(self.x-24,cy-ch//2-12,22,14),border_radius=3)
        pygame.draw.rect(surf,(14,9,5),(self.x+2,cy-ch//2-12,22,14),border_radius=3)
        for wx in [self.x-30,self.x+30]:
            pygame.draw.circle(surf,(18,18,18),(wx,cy+ch//2+2),10); pygame.draw.circle(surf,(32,32,32),(wx,cy+ch//2+2),6)
        for p in self.fire:
            a=p['life']/p['max']; r=max(1,int(p['r']*a)); t2=1-a
            c=lerp_colour(C_FIRE3,lerp_colour(C_FIRE2,C_FIRE1,t2),t2)
            s=pygame.Surface((r*2,r*2),pygame.SRCALPHA); pygame.draw.circle(s,(*c,int(200*a)),(r,r),r); surf.blit(s,(int(p['x'])-r,int(p['y'])-r))

def build_background():
    bg=pygame.Surface((WIDTH,HEIGHT))
    SKY_TOP=(4,5,14); SKY_MID=(22,12,38); SKY_HOR=(55,22,18)
    for y in range(HEIGHT):
        t=y/HEIGHT
        c=lerp_colour(SKY_TOP,SKY_MID,t/0.45) if t<0.45 else lerp_colour(SKY_MID,SKY_HOR,(t-0.45)/0.55)
        pygame.draw.line(bg,c,(0,y),(WIDTH,y))
    for r2,c2 in [(38,(90,55,20)),(36,(130,85,30)),(34,(170,115,45)),(32,(195,140,60))]:
        pygame.draw.circle(bg,c2,(820,62),r2)
    for mx,my,mr in [(808,54,6),(834,76,4),(817,78,3),(838,56,3)]: pygame.draw.circle(bg,(150,100,35),(mx,my),mr)
    for gr,ga in [(70,12),(55,20),(42,35)]:
        hs=pygame.Surface((gr*2,gr*2),pygame.SRCALPHA); pygame.draw.circle(hs,(200,120,40,ga),(gr,gr),gr); bg.blit(hs,(820-gr,62-gr))
    random.seed(99)
    for _ in range(200):
        sx=random.randint(0,WIDTH); sy=random.randint(0,int(HEIGHT*0.52)); sr=random.choice([1,1,1,1,1,2,2]); bright=random.randint(120,255)
        tint=random.choice([(bright,bright,bright),(bright,bright,int(bright*0.7)),(int(bright*0.7),int(bright*0.8),bright)])
        pygame.draw.circle(bg,tint,(sx,sy),sr)
    for _ in range(12):
        sx=random.randint(0,WIDTH); sy=random.randint(0,int(HEIGHT*0.4))
        pygame.draw.circle(bg,(255,240,200),(sx,sy),2)
        hs2=pygame.Surface((8,8),pygame.SRCALPHA); pygame.draw.circle(hs2,(255,220,150,40),(4,4),4); bg.blit(hs2,(sx-4,sy-4))
    random.seed()
    horizon_y=HEIGHT//2-5
    bld_back=[(70,38),(100,52),(140,30),(180,55),(220,42),(260,60),(300,34),(340,48),(380,58),(420,32),(460,44),(500,36),(540,58),(580,30),(620,50),(660,36),(700,54),(740,34),(780,44),(820,30),(870,42),(895,38)]
    random.seed(88)
    for bx,bh in bld_back:
        pygame.draw.rect(bg,(8,10,16),(bx-12,horizon_y-bh,24,bh))
        if random.random()<0.4: pygame.draw.rect(bg,(30,15,10),(bx-12,horizon_y-bh,24,2))
    bld_front=[(85,50),(125,68),(165,44),(205,72),(250,56),(290,80),(330,46),(370,62),(415,75),(455,42),(500,60),(545,50),(590,78),(630,40),(670,62),(715,48),(760,70),(800,44),(845,58),(885,40)]
    for bx,bh in bld_front:
        pygame.draw.rect(bg,(11,13,22),(bx-15,horizon_y-bh,30,bh))
        for wy in range(horizon_y-bh+5,horizon_y-6,10):
            for wxi in range(bx-12,bx+12,8):
                if random.random()<0.35: pygame.draw.rect(bg,random.choice([(80,65,28),(28,50,90),(65,40,15),(20,45,80)]),(wxi,wy,5,6))
        if random.random()<0.3:
            pygame.draw.line(bg,(18,20,30),(bx,horizon_y-bh),(bx,horizon_y-bh-12),1)
            pygame.draw.circle(bg,(25,25,35),(bx,horizon_y-bh-12),2)
    for bx,bh in random.sample(bld_front,6):
        for gr,ga,gc in [(28,30,(255,80,10)),(18,50,(255,130,20)),(10,70,(255,180,40))]:
            hs=pygame.Surface((gr*2,gr*2),pygame.SRCALPHA); pygame.draw.circle(hs,(*gc,ga),(gr,gr),gr); bg.blit(hs,(bx-gr,horizon_y-bh-gr+4))
    random.seed()
    for y in range(horizon_y-8,horizon_y+12):
        t=(y-(horizon_y-8))/20; alp=int((1-abs(t*2-1))*80*0.55)
        haze_c=lerp_colour((60,20,8),(30,10,50),t)
        hs=pygame.Surface((WIDTH,1),pygame.SRCALPHA); hs.fill((*haze_c,alp)); bg.blit(hs,(0,y))
    for i in range(LANES):
        y0=i*LANE_HEIGHT; road_c=(20+i*3,20+i*2,28+i*2)
        pygame.draw.rect(bg,road_c,(BASE_X,y0,WIDTH-BASE_X,LANE_HEIGHT))
        for tx in range(BASE_X,WIDTH,48): pygame.draw.line(bg,lerp_colour(road_c,(0,0,0),0.10),(tx,y0),(tx+8,y0+LANE_HEIGHT),1)
        if i<LANES-1:
            yl=(i+1)*LANE_HEIGHT
            for dx in range(BASE_X+10,WIDTH,36): pygame.draw.rect(bg,(90,80,20),(dx,yl-1,22,2))
            pygame.draw.line(bg,(40,40,50),(BASE_X,yl),(WIDTH,yl),1)
        random.seed(i*13+77)
        for _ in range(4):
            cx2=random.randint(BASE_X+60,WIDTH-60); cy2=y0+random.randint(10,LANE_HEIGHT-10)
            pygame.draw.line(bg,lerp_colour(road_c,(0,0,0),0.15),(cx2,cy2),(cx2+random.randint(10,40),cy2+random.randint(-8,8)),1)
        random.seed()
    pygame.draw.rect(bg,(22,14,6),(0,0,BASE_X,HEIGHT))
    for y in range(0,HEIGHT,24): pygame.draw.line(bg,(30,20,10),(0,y),(BASE_X,y),1)
    pygame.draw.rect(bg,(38,24,10),(BASE_X-7,0,8,HEIGHT)); pygame.draw.line(bg,(55,38,16),(BASE_X-2,0),(BASE_X-2,HEIGHT),1)
    for i in range(LANES):
        for j in range(3):
            bsy=i*LANE_HEIGHT+8+j*20
            pygame.draw.ellipse(bg,(72,52,24),(3,bsy,44,15)); pygame.draw.ellipse(bg,(88,62,28),(3,bsy,44,6))
            pygame.draw.line(bg,(55,38,16),(8,bsy+7),(38,bsy+7),1)
    return bg

_BG=None
def get_bg():
    global _BG
    if _BG is None: _BG=build_background()
    return _BG

# ─── ARDUINO ──────────────────────────────────────────────────────────────────
class JoystickController:
    """
    Gesture map (no extra hardware needed):
      Short button press  (< 15 frames)  →  MELEE
      Long  button press  (≥ 15 frames)  →  PAUSE
      Double Y-forward tap within 0.4 s  →  GRENADE
    """
    LONG_PRESS_FRAMES = 15                              # ~300 ms at 50 Hz sampling
    DOUBLE_TAP_WINDOW = 0.40                            # seconds
    Y_FWD_THRESH      = JOY_CENTER - JOY_DEADZONE - 80 # same as reload zone

    def __init__(self, port=SERIAL_PORT, baud=SERIAL_BAUD):
        self.connected       = False
        self._lock           = threading.Lock()
        self._x              = JOY_CENTER
        self._y              = JOY_CENTER
        self._btn            = 0
        self._pause_event    = False   # long press
        self._melee_event    = False   # short press
        self._grenade_event  = False   # double Y-fwd tap
        if not _SERIAL_AVAILABLE: return
        try:
            self._ser = _serial.Serial(port, baud, timeout=1)
            self.connected = True
            threading.Thread(target=self._read_loop, daemon=True).start()
        except Exception as e:
            print(f"[Arduino] {e} – keyboard only.")

    def _read_loop(self):
        prev_btn    = 0
        btn_held    = 0      # consecutive frames button is pressed
        y_was_fwd   = False  # was Y in forward zone last sample
        y_tap_count = 0      # how many forward taps recorded
        y_tap_time  = 0.0    # time.monotonic() of most recent tap

        while self.connected:
            try:
                raw   = self._ser.readline().decode("utf-8", errors="ignore").strip()
                parts = raw.split(",")
                if len(parts) != 3: continue
                x, y, btn = int(parts[0]), int(parts[1]), int(parts[2])
                now = time.monotonic()

                with self._lock:
                    self._x, self._y, self._btn = x, y, btn

                # ── Button gesture ────────────────────────────────────────────
                if btn == 1:
                    btn_held += 1
                elif btn == 0 and prev_btn == 1:
                    with self._lock:
                        if btn_held < self.LONG_PRESS_FRAMES:
                            self._melee_event = True   # quick tap → melee
                        else:
                            self._pause_event = True   # held long  → pause
                    btn_held = 0
                prev_btn = btn

                # ── Y-forward double-tap → grenade ────────────────────────────
                y_fwd = (y < self.Y_FWD_THRESH)
                if y_fwd and not y_was_fwd:
                    # Rising edge into forward zone
                    if y_tap_count == 1 and (now - y_tap_time) < self.DOUBLE_TAP_WINDOW:
                        with self._lock: self._grenade_event = True
                        y_tap_count = 0
                    else:
                        y_tap_count = 1
                        y_tap_time  = now
                elif not y_fwd:
                    # Outside forward zone: expire old tap if window passed
                    if y_tap_count == 1 and (now - y_tap_time) >= self.DOUBLE_TAP_WINDOW:
                        y_tap_count = 0
                y_was_fwd = y_fwd

            except Exception:
                pass

    # ── Public API ────────────────────────────────────────────────────────────
    def get_axes(self):
        with self._lock: return self._x, self._y

    def consume_btn_event(self):
        """Long press → pause (keeps original call-site name)."""
        with self._lock:
            e = self._pause_event; self._pause_event = False; return e

    def consume_melee_event(self):
        """Short press → melee."""
        with self._lock:
            e = self._melee_event; self._melee_event = False; return e

    def consume_grenade_event(self):
        """Double Y-forward tap → grenade."""
        with self._lock:
            e = self._grenade_event; self._grenade_event = False; return e

    def btn_held(self):
        with self._lock: return self._btn == 1

    def send_ammo(self, count):
        if self.connected:
            try: self._ser.write(f"A{count}\n".encode())
            except: pass

    def send_wave_beep(self):
        """Tell the Arduino to play the wave-start E5 beep."""
        if self.connected:
            try: self._ser.write(b"W\n")
            except: pass

    def close(self):
        self.connected = False
        if hasattr(self, "_ser"):
            try: self._ser.close()
            except: pass

# ─── PARTICLES ────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self,x,y,col):
        self.x,self.y=float(x),float(y); self.vx=random.uniform(-4,4); self.vy=random.uniform(-5,2)
        self.life=random.randint(15,35); self.max_life=self.life; self.r=random.randint(3,8); self.col=col
    def update(self): self.x+=self.vx; self.y+=self.vy; self.vy+=0.25; self.life-=1
    def draw(self,surf):
        a=self.life/self.max_life; c=lerp_colour((20,20,20),self.col,a); r=max(1,int(self.r*a))
        pygame.draw.circle(surf,c,(int(self.x),int(self.y)),r)

class MuzzleFlash:
    def __init__(self,x,y,colour=None): self.x,self.y=x,y; self.life=5; self.colour=colour or C_MUZZLE
    def update(self): self.life-=1
    def draw(self,surf):
        if self.life<=0: return
        r=self.life*5; s=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
        pygame.draw.circle(s,(*self.colour,int(200*(self.life/5))),(r,r),r); surf.blit(s,(self.x-r,self.y-r))
        pygame.draw.circle(surf,C_WHITE,(self.x,self.y),r//3)

# ─── BULLET ───────────────────────────────────────────────────────────────────
class Bullet:
    def __init__(self,lane,speed=15,base_damage=1,pierce=False,colour=None,pierce_retain=0.5):
        self.lane=lane; self.x=float(BASE_X+44); self.speed=speed
        self.base_damage=base_damage; self.pierce=pierce; self.pierce_hits=0
        self.pierce_retain=pierce_retain; self.alive=True; self.trail=[]
        self.colour=colour or C_BULLET
    @property
    def damage(self):
        if self.pierce: return self.base_damage*(self.pierce_retain**self.pierce_hits)
        return self.base_damage
    def update(self):
        self.trail.append((self.x,lane_cy(self.lane)))
        if len(self.trail)>10: self.trail.pop(0)
        self.x+=self.speed
        if self.x>WIDTH+20: self.alive=False
    def draw(self,surf):
        cy=lane_cy(self.lane); bx=int(self.x); is_ult=(self.base_damage>1)
        for i,(tx,ty) in enumerate(self.trail):
            a=i/max(len(self.trail),1); r=max(1,int((6 if is_ult else 4)*a))
            c=lerp_colour(BG_SKY_TOP,self.colour,a); ts=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
            pygame.draw.circle(ts,(*c,int(160*a)),(r,r),r); surf.blit(ts,(int(tx)-r,ty-r))
        bw=18 if is_ult else 14; bh=7 if is_ult else 5
        if is_ult: cas_c=(255,200,40); cas_d=(200,140,10); cas_hl=(255,240,130); tip_c=(255,220,60)
        else: cas_c=(210,170,50); cas_d=(150,110,20); cas_hl=(240,210,100); tip_c=(195,195,195)
        cw=int(bw*0.62); cx2=bx-bw+2; cy2=cy-bh//2
        pygame.draw.rect(surf,cas_c,(cx2,cy2,cw,bh),border_radius=2)
        pygame.draw.rect(surf,cas_hl,(cx2+1,cy2,cw-2,bh//3))
        pygame.draw.rect(surf,cas_d,(cx2+1,cy2+bh-bh//3,cw-2,bh//3))
        pygame.draw.circle(surf,cas_c,(cx2,cy),bh//2)
        tip_pts=[(cx2+cw,cy-bh//2),(bx,cy),(cx2+cw,cy+bh//2)]
        pygame.draw.polygon(surf,tip_c,tip_pts)
        pygame.draw.line(surf,lerp_colour(tip_c,C_WHITE,0.4),(cx2+cw,cy-bh//2+1),(bx-3,cy),1)
        if is_ult:
            gs3=pygame.Surface((14,14),pygame.SRCALPHA); pygame.draw.circle(gs3,(255,220,60,80),(7,7),7); surf.blit(gs3,(bx-7,cy-7))

# ─── MELEE SLASH ──────────────────────────────────────────────────────────────
MELEE_RANGE = 90   # px from BASE_X

class MeleeSlash:
    """Visual-only slash effect. Damage is applied immediately on creation."""
    def __init__(self, lane, aoe=False):
        self.lane=lane; self.aoe=aoe; self.life=12; self.max_life=12
    def update(self): self.life-=1
    def draw(self, surf):
        t=self.life/self.max_life
        lanes=range(LANES) if self.aoe else [self.lane]
        for l in lanes:
            cy=lane_cy(l); alpha=int(240*t)
            c1=lerp_colour((80,180,255),(255,255,255),t)
            c2=lerp_colour((40,100,200),(200,220,255),t)
            x0=BASE_X+5; x1=BASE_X+MELEE_RANGE+10
            w=max(1,int(4*t))
            pygame.draw.line(surf,c1,(x0,cy-int(24*t)),(x1,cy+int(24*t)),w)
            pygame.draw.line(surf,c2,(x0,cy-int(14*t)),(x1-8,cy+int(32*t)),max(1,w-1))
            pygame.draw.line(surf,c1,(x0+8,cy-int(30*t)),(x1,cy+int(16*t)),max(1,w-1))
            # Impact flash at tip
            if t>0.6:
                flash=pygame.Surface((20,20),pygame.SRCALPHA)
                pygame.draw.circle(flash,(200,240,255,int(180*t)),(10,10),int(10*t))
                surf.blit(flash,(x1-10,cy-10))

# ─── GRENADE PROJECTILE ───────────────────────────────────────────────────────
class GrenadeProjectile:
    """Arcs forward, explodes dealing damage to zombies across 2-3 lanes."""
    TARGET_X = BASE_X + int((WIDTH - BASE_X) * 0.55)

    def __init__(self, lane, radius=70, lanes_hit=2):
        self.lane=lane; self.radius=int(radius); self.lanes_hit=lanes_hit
        self.x=float(BASE_X+55); self.alive=True
        self.exploded=False; self.exp_timer=0; self.exp_max=22
        self.spin=0.0

    def get_hit_lanes(self):
        l=self.lane; n=self.lanes_hit
        if n>=LANES: return list(range(LANES))
        if l+n-1<LANES: return list(range(l,l+n))
        return list(range(LANES-n,LANES))

    def update(self):
        if not self.exploded:
            self.x+=10; self.spin+=0.3
            if self.x>=self.TARGET_X: self.exploded=True
        else:
            self.exp_timer+=1
            if self.exp_timer>=self.exp_max: self.alive=False

    def draw(self, surf):
        if not self.exploded:
            cy=lane_cy(self.lane)
            # Arcing trajectory: slight Y bob
            t=max(0,(self.x-BASE_X-55)/max(1,self.TARGET_X-BASE_X-55))
            arc_y=int(-20*math.sin(t*math.pi)); gy=cy+arc_y
            # Shadow
            pygame.draw.ellipse(surf,(20,20,20),(int(self.x)-10,cy-3,20,6))
            # Grenade body
            pygame.draw.circle(surf,(70,100,55),(int(self.x),gy),9)
            pygame.draw.circle(surf,(100,140,80),(int(self.x),gy),7)
            # Spin stripe
            sx2=int(self.x+math.cos(self.spin)*7); sy2=int(gy+math.sin(self.spin)*7)
            pygame.draw.line(surf,(140,200,110),(int(self.x),gy),(sx2,sy2),2)
            # Fuse spark
            pygame.draw.circle(surf,(255,200,50),(int(self.x)-4,gy-8),3)
            pygame.draw.circle(surf,(255,120,20),(int(self.x)-4,gy-8),2)
        else:
            t=self.exp_timer/self.exp_max
            for l in self.get_hit_lanes():
                cy=lane_cy(l)
                r=int(self.radius*(0.4+t*0.6))
                # Outer blast ring
                es=pygame.Surface((r*2+8,r*2+8),pygame.SRCALPHA)
                c1=lerp_colour((255,220,80),(255,60,10),t)
                pygame.draw.circle(es,(*c1,int(200*(1-t))),(r+4,r+4),r)
                surf.blit(es,(int(self.TARGET_X)-r-4,cy-r-4))
                # Inner bright core
                cr=max(1,int(r*0.35*(1-t)))
                pygame.draw.circle(surf,(255,240,180),(int(self.TARGET_X),cy),cr)
                # Shockwave ring
                pygame.draw.circle(surf,(255,180,60),(int(self.TARGET_X),cy),r,max(1,int(3*(1-t))))

# ─── ZOMBIE ───────────────────────────────────────────────────────────────────
ZOMBIE_TYPES={"normal":dict(hp=3,speed=1.1,size=28,score=10,ult_charge=8),
              "fast":dict(hp=2,speed=2.55,size=22,score=15,ult_charge=12),
              "tank":dict(hp=8,speed=0.55,size=36,score=35,ult_charge=22)}

class Zombie:
    def __init__(self,lane,ztype="normal",diff=1.0):
        self.lane=lane; self.ztype=ztype; cfg=ZOMBIE_TYPES[ztype]
        self.hp=max(1,int(cfg["hp"]*diff)); self.max_hp=self.hp
        self.speed=cfg["speed"]*(0.85+diff*0.15)
        self.size=cfg["size"]; self.score_val=cfg["score"]; self.ult_charge=cfg["ult_charge"]
        self.x=float(WIDTH+cfg["size"]+10); self.alive=True; self.hit_flash=0; self.wobble=random.uniform(0,math.pi*2)
        self._spr=get_zombie_sprite(ztype,False); self._spr_hit=get_zombie_sprite(ztype,True)
    def update(self):
        self.x-=self.speed; self.wobble+=0.18
        if self.hit_flash>0: self.hit_flash-=1
        if self.x<BASE_X-self.size: self.alive=False; return [("breach",)]
        return []
    def take_damage(self,dmg):
        self.hp-=dmg; self.hit_flash=8
        if self.hp<=0: self.alive=False; return True
        return False
    def draw(self,surf):
        cy=lane_cy(self.lane); sx=int(self.x); bob=int(math.sin(self.wobble)*2)
        spr=self._spr_hit if self.hit_flash>0 else self._spr; sw,sh=spr.get_size()
        scale=self.size/28
        if abs(scale-1.0)>0.01:
            nw,nh=int(sw*scale),int(sh*scale); spr=pygame.transform.scale(spr,(nw,nh)); sw,sh=nw,nh
        surf.blit(spr,(sx-sw//2,cy-sh//2+bob))
        if self.hp<self.max_hp:
            bw=sw+8; bh=4; bx=sx-bw//2; by=cy-sh//2-8+bob
            pygame.draw.rect(surf,C_HP_BAR_BG,(bx,by,bw,bh))
            pygame.draw.rect(surf,lerp_colour((210,50,50),(50,200,80),self.hp/self.max_hp),(bx,by,int(bw*self.hp/self.max_hp),bh))

# ─── BOSS ZOMBIE ──────────────────────────────────────────────────────────────
class BossZombie:
    ULT_REWARD=55
    def __init__(self,lane,wave,gs):
        self.lane=lane; self.wave=wave
        tidx=(wave//BOSS_INTERVAL-1)%10; self.tidx=tidx; self.bd=BOSS_DATA[tidx]
        cycle=(wave//BOSS_INTERVAL-1)//10
        hp_scale=self.bd["hp"]+cycle*25
        self.hp=max(1,int(hp_scale*gs.difficulty_mult(wave))); self.max_hp=self.hp
        self.speed=self.bd["speed"]; self.size=52
        self.score_val=300+wave*15; self.ult_charge=self.ULT_REWARD
        self.x=float(WIDTH+90); self.alive=True; self.hit_flash=0; self.wobble=0; self.pulse=0
        self.abilities=self.bd["abilities"]
        # Timers per ability
        self.spawn_timer=0; self.bomb_timer=0; self.phase_timer=0; self.phase_invuln=False; self.phase_cd=0
        self.shield_hp=8 if "shield" in self.abilities else 0; self.shield_max=self.shield_hp
        self.regen_acc=0.0
        self.mimic_timer=0; self.mimic_ability=None
        self._spr=get_boss_sprite(tidx,False); self._spr_hit=get_boss_sprite(tidx,True)
    def _active_abilities(self):
        if "mimic" in self.abilities and self.mimic_ability:
            return [self.mimic_ability]
        return self.abilities
    def update(self):
        events=[]
        self.wobble+=0.10; self.pulse+=0.07
        if self.hit_flash>0: self.hit_flash-=1
        ab=self._active_abilities()
        # Regen
        if "regen" in ab:
            self.regen_acc+=0.025
            if self.regen_acc>=1.0: self.regen_acc-=1.0; self.hp=min(self.max_hp,self.hp+1)
        # Spawn
        if "spawn" in ab:
            self.spawn_timer+=1
            if self.spawn_timer>=480: self.spawn_timer=0; events.append(("boss_spawn",self.lane))
        # Bomb
        if "bomb" in ab:
            self.bomb_timer+=1
            if self.bomb_timer>=300: self.bomb_timer=0; events.append(("boss_bomb",self.lane))
        # Berserk
        if "berserk" in ab:
            self.speed=self.bd["speed"]*(2.0 if self.hp<self.max_hp*0.5 else 1.0)
        # Fast
        if "fast" in ab: self.speed=max(self.speed,self.bd["speed"]*1.8)
        # Phase
        if "phase" in ab:
            self.phase_timer+=1
            if not self.phase_invuln and self.phase_timer>=360:
                self.phase_timer=0; self.phase_invuln=True
            elif self.phase_invuln and self.phase_timer>=120:
                self.phase_timer=0; self.phase_invuln=False
        # Mimic
        if "mimic" in self.abilities:
            self.mimic_timer+=1
            if self.mimic_timer>=360:
                self.mimic_timer=0
                self.mimic_ability=random.choice(["fast","regen","spawn","berserk","bomb"])
        self.x-=self.speed
        if self.x<BASE_X-self.size: self.alive=False; events.append(("breach",)); return events
        return events
    def take_damage(self,dmg):
        if self.phase_invuln: return False
        if self.shield_hp>0:
            self.shield_hp=max(0,self.shield_hp-1); self.hit_flash=5; return False
        self.hp-=dmg; self.hit_flash=10
        if self.hp<=0: self.alive=False; return True
        return False
    def draw(self,surf):
        cy=lane_cy(self.lane); sx=int(self.x); bob=int(math.sin(self.wobble)*3)
        spr=self._spr_hit if self.hit_flash>0 else self._spr; sw,sh=spr.get_size()
        # Phase: blink
        if self.phase_invuln and (pygame.time.get_ticks()//100)%2==0: return
        # Aura
        ar=int(sw//2+14+math.sin(self.pulse)*4); aura=pygame.Surface((ar*2,ar*2),pygame.SRCALPHA)
        pygame.draw.circle(aura,(*self.bd["glow"],30),(ar,ar),ar); surf.blit(aura,(sx-ar,cy-ar+bob))
        surf.blit(spr,(sx-sw//2,cy-sh//2+bob))
        # Shield ring
        if self.shield_hp>0:
            sf=self.shield_hp/self.shield_max; sc=self.bd["glow"]
            pygame.draw.circle(surf,sc,(sx,cy+bob),sw//2+10,2)
            pygame.draw.circle(surf,lerp_colour(sc,C_WHITE,0.4),(sx,cy+bob),sw//2+10,1)
        # HP bar
        bw=sw+16; bh=7; bx2=sx-bw//2; by2=cy-sh//2-18+bob
        pygame.draw.rect(surf,(30,5,40),(bx2,by2,bw,bh))
        pygame.draw.rect(surf,lerp_colour(self.bd["glow"],(210,30,30),1-self.hp/self.max_hp),(bx2,by2,int(bw*max(0,self.hp/self.max_hp)),bh))
        pygame.draw.rect(surf,self.bd["glow"],(bx2,by2,bw,bh),1)
        draw_text(surf,f"{self.bd['name']}",font_xs,self.bd["gold"],sx,by2-14,"midtop")

# ─── BOSS PROJECTILE (bomb ability) ───────────────────────────────────────────
class BossProjectile:
    def __init__(self,lane):
        self.lane=lane; self.x=float(WIDTH//2); self.alive=True; self.pulse=0
    def update(self):
        self.x-=6; self.pulse+=0.2
        if self.x<BASE_X: self.alive=False; return True  # hit base
        return False
    def draw(self,surf):
        cy=lane_cy(self.lane); sx=int(self.x); r=int(8+math.sin(self.pulse)*2)
        gs4=pygame.Surface((r*3,r*3),pygame.SRCALPHA); pygame.draw.circle(gs4,(255,80,10,80),(r,r),r*2); surf.blit(gs4,(sx-r,cy-r))
        pygame.draw.circle(surf,(255,100,20),(sx,cy),r); pygame.draw.circle(surf,(255,200,80),(sx,cy),r//2)

# ─── PLAYER ───────────────────────────────────────────────────────────────────
class Player:
    def __init__(self):
        self.lane=0; self.target_y=float(lane_cy(0)); self.y=float(lane_cy(0))
        self.shoot_cd=0; self.base_hp=BASE_HP_MAX; self.max_hp=BASE_HP_MAX
        self.weapon="normal"; self.weapon_timer=0; self.muzzle_flash=None
        self.mag_size=MAG_SIZE; self.ammo=MAG_SIZE
        self.reloading=False; self.reload_timer=0; self.reload_duration=RELOAD_FRAMES
        self.ult_charge=0.0; self.ult_active=False; self.ult_timer=0
        self.ult_hold=0      # frames E/diagonal held
        self._joy=None
        # From GameState
        self.ammo_save=0.0; self.fire_rate_mult=1.0; self.dmg_mult=1.0
        self.parasite=False; self.pierce_retain=0.5
        self.melee_cd=0; self.melee_cd_max=30     # 0.5s default
        self.melee_aoe=False
        self.grenade_cd=0; self.grenade_cd_max=90  # 1.5s
        self.grenade_radius=70; self.grenade_lanes=2

    def set_lane(self,idx): self.lane=max(0,min(LANES-1,idx)); self.target_y=float(lane_cy(self.lane))
    def charge_ult(self,amt,gs):
        if not self.ult_active: self.ult_charge=min(ULT_MAX,self.ult_charge+amt*gs.ult_charge_mult)

    def try_activate_ult(self):
        if self.ult_charge>=ULT_MAX and not self.ult_active:
            self.ult_active=True; self.ult_timer=ULT_DURATION; self.ult_charge=0.0
            self.reloading=False; self.ammo=self.mag_size
            if self._joy: self._joy.send_ammo(self.ammo)
            self.ult_hold=0; sfx.play_ult(); return True
        return False

    def start_reload(self):
        # Does NOT activate ult — reload is always just reload
        if not self.reloading and not self.ult_active and self.ammo<self.mag_size:
            self.reloading=True; self.reload_timer=self.reload_duration
            sfx.play_reload()

    def update(self):
        self.y+=(self.target_y-self.y)*0.22
        if self.shoot_cd>0: self.shoot_cd-=1
        if self.weapon_timer>0:
            self.weapon_timer-=1
            if self.weapon_timer==0: self.weapon="normal"
        if self.muzzle_flash:
            self.muzzle_flash.update()
            if self.muzzle_flash.life<=0: self.muzzle_flash=None
        if self.reloading:
            self.reload_timer-=1
            if self.reload_timer<=0:
                self.ammo=self.mag_size; self.reloading=False
                if self._joy: self._joy.send_ammo(self.ammo)
        if self.ult_active:
            self.ult_timer-=1
            if self.ult_timer<=0: self.ult_active=False; self.weapon="normal"
        if self.melee_cd>0: self.melee_cd-=1
        if self.grenade_cd>0: self.grenade_cd-=1

    def shoot(self):
        if self.ult_active:
            if self.shoot_cd>0: return None
            self.shoot_cd=4
            cx2,cy2=BASE_X+44,int(self.y)
            self.muzzle_flash=MuzzleFlash(cx2,cy2,colour=(255,220,50))
            sfx.play_shoot("ultimate")
            return Bullet(self.lane,speed=22,base_damage=int(3*self.dmg_mult),pierce=True,colour=(255,220,50),pierce_retain=self.pierce_retain)
        if self.reloading: return None
        if self.ammo<=0: self.start_reload(); return None
        cd_map={"normal":int(18*self.fire_rate_mult),"rapid":int(7*self.fire_rate_mult),"pierce":int(24*self.fire_rate_mult)}
        if self.shoot_cd>0: return None
        self.shoot_cd=cd_map.get(self.weapon,int(18*self.fire_rate_mult))
        # Ghost rounds: skip ammo decrement
        if random.random()>=self.ammo_save:
            self.ammo-=1
            if self._joy: self._joy.send_ammo(self.ammo)
        if self.ammo==0: self.start_reload()
        cx2,cy2=BASE_X+44,int(self.y)
        self.muzzle_flash=MuzzleFlash(cx2,cy2)
        dmg=int(self.dmg_mult)
        if self.weapon=="rapid":
            sfx.play_shoot("rapid")
            return Bullet(self.lane,speed=18,base_damage=dmg,pierce_retain=self.pierce_retain)
        if self.weapon=="pierce":
            sfx.play_shoot("pierce")
            return Bullet(self.lane,speed=14,base_damage=dmg,pierce=True,pierce_retain=self.pierce_retain)
        sfx.play_shoot("normal")
        return Bullet(self.lane,speed=15,base_damage=dmg,pierce_retain=self.pierce_retain)

    def draw(self,surf):
        cy=int(self.y); x=BASE_X
        hs=pygame.Surface((12,LANE_HEIGHT),pygame.SRCALPHA)
        hs.fill((255,200,30,30) if self.ult_active else (0,200,255,22)); surf.blit(hs,(0,self.lane*LANE_HEIGHT))
        if self.ult_active:
            ar=int(44+math.sin(pygame.time.get_ticks()*0.01)*6)
            aura=pygame.Surface((ar*2,ar*2),pygame.SRCALPHA)
            pygame.draw.circle(aura,(*lerp_colour((255,180,0),(255,100,0),1-self.ult_timer/ULT_DURATION),55),(ar,ar),ar)
            surf.blit(aura,(x-ar,cy-ar))
        base_c=lerp_colour(C_BASE,(140,100,10),0.6) if self.ult_active else C_BASE
        base_hl=lerp_colour(C_BASE_HL,(255,200,30),0.6) if self.ult_active else C_BASE_HL
        pygame.draw.rect(surf,base_c,(x-30,cy-28,62,56),border_radius=6); pygame.draw.rect(surf,base_hl,(x-30,cy-28,62,9),border_radius=6)
        for ry in [cy-22,cy,cy+22]:
            pygame.draw.circle(surf,(90,60,24),(x-24,ry),3); pygame.draw.circle(surf,(90,60,24),(x+24,ry),3)
        sc=lerp_colour(C_PLAYER,(255,200,0),0.7) if self.ult_active else C_PLAYER
        sh_c=lerp_colour(C_PLAYER_HL,(255,240,80),0.7) if self.ult_active else C_PLAYER_HL
        pygame.draw.circle(surf,sh_c,(x,cy),18); pygame.draw.circle(surf,sc,(x,cy),14); pygame.draw.circle(surf,C_WHITE,(x,cy),5)
        gspr=get_gun_sprite("ultimate" if self.ult_active else self.weapon); gw,gh=gspr.get_size()
        if self.reloading:
            t2=1-self.reload_timer/self.reload_duration; angle=math.sin(t2*math.pi)*-14
            rot=pygame.transform.rotate(gspr,angle); rr=rot.get_rect(midleft=(x+12,cy)); surf.blit(rot,rr)
        else: surf.blit(gspr,(x+12,cy-gh//2))
        if self.muzzle_flash: self.muzzle_flash.draw(surf)

# ─── POWERUP ──────────────────────────────────────────────────────────────────
class PowerUp:
    def __init__(self):
        self.kind=random.choice(["rapid","pierce","heal"]); self.lane=random.randint(0,LANES-1)
        self.x=float(WIDTH+20); self.alive=True; self.pulse=0
        self.colour={"rapid":(255,220,0),"pierce":(100,160,255),"heal":(80,220,80)}[self.kind]
    def update(self): self.x-=1.5; self.pulse+=0.1; self.alive=self.x>BASE_X-20
    def draw(self,surf):
        cy=lane_cy(self.lane); r=18+int(math.sin(self.pulse)*3)
        gs5=pygame.Surface((r*4,r*4),pygame.SRCALPHA); pygame.draw.circle(gs5,(*self.colour,55),(r*2,r*2),r*2); surf.blit(gs5,(int(self.x)-r*2,cy-r*2))
        pygame.draw.circle(surf,self.colour,(int(self.x),cy),r); pygame.draw.circle(surf,C_WHITE,(int(self.x),cy),r-5,2)
        lbl=font_xs.render({"rapid":"SMG","pierce":"SNP","heal":"HP+"}[self.kind],True,C_BLACK)
        surf.blit(lbl,lbl.get_rect(center=(int(self.x),cy)))

# ─── WAVE MANAGER ─────────────────────────────────────────────────────────────
class WaveManager:
    def __init__(self,gs):
        self.gs=gs; self.wave=1; self.spawn_timer=0; self.in_break=False
        self.break_timer=0; self.spawned=0; self.total=self._count()
        self.boss_spawned=False; self.just_entered_break=False

    def is_boss_wave(self): return self.wave%BOSS_INTERVAL==0
    def _count(self): return max(1,4+self.wave*3-self.wave//5)  # slightly curve off
    def _interval(self): return max(20,105-self.wave*5)
    def _type(self):
        d=self.gs.difficulty_mult(self.wave); r=random.random()
        if self.wave>=5 and r<min(0.35,0.05+self.wave*0.025): return "tank"
        if self.wave>=3 and r<min(0.55,0.15+self.wave*0.03): return "fast"
        return "normal"
    def _diff(self): return self.gs.difficulty_mult(self.wave)

    def update(self,zombies):
        self.just_entered_break=False
        if self.in_break:
            self.break_timer-=1
            if self.break_timer<=0:
                self.in_break=False; self.wave+=1; self.spawned=0
                self.total=self._count(); self.boss_spawned=False
            return None
        # Boss spawning
        if self.is_boss_wave() and not self.boss_spawned:
            self.boss_spawned=True
            return BossZombie(random.randint(0,LANES-1),self.wave,self.gs)
        # Regular spawning
        self.spawn_timer+=1
        if self.spawn_timer>=self._interval() and self.spawned<self.total:
            self.spawn_timer=0; self.spawned+=1
            return Zombie(random.randint(0,LANES-1),self._type(),self._diff())
        if self.spawned>=self.total and not zombies:
            self.in_break=True; self.break_timer=FPS*5; self.just_entered_break=True
        return None

# ─── HUD ──────────────────────────────────────────────────────────────────────
def draw_hud(surf,score,player,wave_mgr,joy,gs,boss_alive=False):
    # ── TOP BAR (44px) ────────────────────────────────────────────────────────
    draw_panel(surf,(0,0,WIDTH,44),alpha=220)
    draw_text(surf,f"SCORE  {int(score):07d}",font_med,C_WHITE,10,8)
    # Wave center
    wc=(255,100,255) if wave_mgr.is_boss_wave() else (255,200,80)
    wt=f"WAVE  {wave_mgr.wave}"
    if wave_mgr.in_break: wt+=f"   NEXT IN {math.ceil(wave_mgr.break_timer/FPS)}s"
    draw_text(surf,wt,font_med,wc,WIDTH//2,8,"midtop")
    if wave_mgr.is_boss_wave() and not wave_mgr.in_break:
        t=((pygame.time.get_ticks()//400)%2); draw_text(surf,"BOSS WAVE",font_xs,(255,80,255) if t else (200,40,200),WIDTH//2,30,"midtop",shadow=False)
    # Rebirth badge
    if gs.rebirth>0: draw_text(surf,f"REB {gs.rebirth}",font_xs,(255,180,40),WIDTH-8,8,"topright",shadow=False)
    # HP segmented (top right)
    max_hp=BASE_HP_MAX+gs.hp_bonus; seg_w=16; seg_h=22; gap=3; total_w=max_hp*(seg_w+gap)-gap
    hpx=WIDTH-total_w-10; hpy=10
    for i in range(max_hp):
        filled=i<player.base_hp; fc=(200,50,50) if filled else (40,20,20)
        sx2=hpx+i*(seg_w+gap)
        pygame.draw.rect(surf,fc,(sx2,hpy,seg_w,seg_h),border_radius=3)
        if filled: pygame.draw.rect(surf,lerp_colour(fc,C_WHITE,0.3),(sx2,hpy,seg_w,4),border_radius=3)
    draw_text(surf,f"HP {player.base_hp}/{max_hp}",font_xs,C_WHITE,WIDTH-total_w-12,34,"topright",shadow=False)

    # ── BOTTOM BAR (65px) ─────────────────────────────────────────────────────
    bh=65; by=HEIGHT-bh
    draw_panel(surf,(0,by,WIDTH,bh),alpha=220)

    # AMMO (left block)
    ax=10; draw_text(surf,"AMMO",font_xs,(140,160,200),ax,by+6,shadow=False)
    for i in range(player.mag_size):
        ult_on=player.ult_active
        c=C_ULT_ACTIVE if ult_on else (C_AMMO_FULL if i<player.ammo else C_AMMO_EMPTY)
        bpx=ax+48+i*20; bpy=by+5
        pygame.draw.rect(surf,c,(bpx,bpy+4,13,20),border_radius=3)
        pygame.draw.ellipse(surf,lerp_colour(c,C_WHITE,0.35),(bpx,bpy,13,10))
        if i<player.ammo or ult_on: pygame.draw.rect(surf,(170,130,25),(bpx-1,bpy+21,15,4),border_radius=1)

    # Reload bar (left block, below shells)
    if player.reloading:
        rb_x=ax; rb_w=ax+50+player.mag_size*20
        ry=by+bh-14; prog=1-player.reload_timer/player.reload_duration
        pygame.draw.rect(surf,(38,28,8),(rb_x,ry,rb_w,8),border_radius=4)
        pygame.draw.rect(surf,C_RELOAD_BAR,(rb_x,ry,int(rb_w*prog),8),border_radius=4)
        pygame.draw.rect(surf,(200,120,20),(rb_x,ry,rb_w,8),2,border_radius=4)
        draw_text(surf,f"RELOADING {math.ceil(player.reload_timer/FPS)}s",font_xs,(255,180,40),rb_x+rb_w+6,ry-2,shadow=False)
    elif player.ammo==0 and not player.reloading and not player.ult_active:
        draw_text(surf,"PRESS [R] TO RELOAD",font_xs,(255,70,70),ax,by+bh-16,shadow=False)

    # ULTIMATE meter (center block)
    ux=290; uw=240; uy=by+10
    draw_text(surf,"ULTIMATE",font_xs,(160,100,255),ux,uy,shadow=False)
    if player.ult_active:
        prog=player.ult_timer/ULT_DURATION; t2=(pygame.time.get_ticks()//150)%2
        bc=(255,220,60) if t2 else (255,160,20)
        pygame.draw.rect(surf,(40,30,10),(ux,uy+16,uw,10),border_radius=4)
        pygame.draw.rect(surf,bc,(ux,uy+16,int(uw*prog),10),border_radius=4)
        pygame.draw.rect(surf,(220,180,40),(ux,uy+16,uw,10),1,border_radius=4)
        draw_text(surf,f"ACTIVE  {math.ceil(player.ult_timer/FPS)}s",font_xs,C_ULT_ACTIVE,ux+uw+6,uy+14,shadow=False)
    else:
        frac=player.ult_charge/ULT_MAX; full=(frac>=1.0)
        fc=lerp_colour((60,20,100),(255,180,50),frac) if not full else (255,200,50)
        pygame.draw.rect(surf,(25,15,40),(ux,uy+16,uw,10),border_radius=4)
        pygame.draw.rect(surf,fc,(ux,uy+16,int(uw*frac),10),border_radius=4)
        if full:
            t3=(pygame.time.get_ticks()//350)%2
            pygame.draw.rect(surf,(255,200,40) if t3 else (180,140,20),(ux,uy+16,uw,10),2,border_radius=4)
            draw_text(surf,"HOLD [E] TO ACTIVATE",font_xs,(255,200,40),ux+uw+6,uy+14,shadow=False)
            # Hold indicator bar
            if player.ult_hold>0:
                hfrac=player.ult_hold/ULT_HOLD_NEED
                pygame.draw.rect(surf,(80,50,0),(ux,uy+28,uw,6),border_radius=3)
                pygame.draw.rect(surf,(255,200,40),(ux,uy+28,int(uw*hfrac),6),border_radius=3)
        else:
            pygame.draw.rect(surf,(80,50,120),(ux,uy+16,uw,10),1,border_radius=4)
            draw_text(surf,f"{int(player.ult_charge)}%",font_xs,(140,90,200),ux+uw+6,uy+14,shadow=False)

    # STATUS right block — weapon timer + melee + grenade
    sx3=555
    if player.weapon!="normal" and not player.ult_active:
        secs=math.ceil(player.weapon_timer/FPS); wc2=(255,220,0) if player.weapon=="rapid" else (100,160,255)
        nm={"rapid":"SMG MODE","pierce":"SNP MODE"}[player.weapon]
        draw_text(surf,f"{nm}  {secs}s",font_sm,wc2,sx3,by+6)

    # Melee cooldown indicator
    mx3=sx3; my3=by+26
    m_rdy=player.melee_cd==0
    mc=(80,200,255) if m_rdy else (50,70,100)
    draw_text(surf,"[F]",font_xs,(140,200,255),mx3,my3,shadow=False)
    draw_text(surf,"MELEE",font_xs,mc,mx3+26,my3,shadow=False)
    if not m_rdy:
        mbar_w=70; mbar_x=mx3+80; mbar_y=my3+1
        prog=1-player.melee_cd/player.melee_cd_max
        pygame.draw.rect(surf,(30,30,45),(mbar_x,mbar_y,mbar_w,8),border_radius=3)
        pygame.draw.rect(surf,(80,160,220),(mbar_x,mbar_y,int(mbar_w*prog),8),border_radius=3)
    else:
        draw_text(surf,"READY",font_xs,(80,220,120),mx3+80,my3,shadow=False)

    # Grenade cooldown indicator
    gx3=sx3; gy3=by+42
    g_rdy=player.grenade_cd==0
    gc2=(255,180,60) if g_rdy else (100,80,40)
    draw_text(surf,"[G]",font_xs,(255,180,60),gx3,gy3,shadow=False)
    draw_text(surf,"NADE",font_xs,gc2,gx3+26,gy3,shadow=False)
    if not g_rdy:
        gbar_w=70; gbar_x=gx3+80; gbar_y=gy3+1
        prog2=1-player.grenade_cd/player.grenade_cd_max
        pygame.draw.rect(surf,(40,30,15),(gbar_x,gbar_y,gbar_w,8),border_radius=3)
        pygame.draw.rect(surf,(220,140,40),(gbar_x,gbar_y,int(gbar_w*prog2),8),border_radius=3)
    else:
        draw_text(surf,"READY",font_xs,(80,220,120),gx3+80,gy3,shadow=False)

    # Active perks (truncated to avoid right-edge overlap)
    px2=sx3+165; py2=by+8
    for perk in sorted(gs.perks):
        short=perk[:4].upper(); draw_text(surf,f"[{short}]",font_xs,(160,180,140),px2,py2,shadow=False); px2+=48
        if px2>WIDTH-80: break

    # Joy dot (far right)
    if joy.connected:
        jx,jy=joy.get_axes(); dc=(50,230,50); dl=f"JOY {jx},{jy}"
    else:
        dc=(180,60,60); dl="KB"
    pygame.draw.circle(surf,dc,(WIDTH-38,by+24),5)
    draw_text(surf,dl,font_xs,dc,WIDTH-30,by+17,shadow=False)

    # Boss warning strip (below top bar)
    if boss_alive and not wave_mgr.in_break:
        t4=(pygame.time.get_ticks()//200)%2
        st=pygame.Surface((WIDTH,16),pygame.SRCALPHA); st.fill((60,5,80,180) if t4 else (40,3,55,180)); surf.blit(st,(0,44))
        draw_text(surf,"⚠  BOSS ACTIVE  ⚠",font_xs,(255,80,255),WIDTH//2,47,"midtop",shadow=False)

    # Lane labels (left column)
    for i in range(LANES):
        c=(120,200,255) if i==player.lane else (65,85,105)
        lbl=font_xs.render(f"[{i+1}]",True,c); surf.blit(lbl,lbl.get_rect(midright=(BASE_X-4,lane_cy(i))))

# ─── SHOP SCREEN ──────────────────────────────────────────────────────────────
def screen_shop(gs, score, joy):
    """Blocking shop. Returns new score.
    Joystick controls:
      X left/right  → navigate between cards
      Y pull back   → buy highlighted card  (rising edge)
      Short press   → buy highlighted card
      Long press    → skip shop
      Y push fwd    → toggle rebirth shop
    """
    # ── Card selection ────────────────────────────────────────────────────────
    weights={"common":4,"uncommon":2,"rare":1}
    available=[(uid,n,d,c,mx,r) for uid,n,d,c,mx,r in SHOP_POOL if gs.upgrades.get(uid,0)<mx]
    pool=[]
    for item in available: pool.extend([item]*weights[item[5]])
    random.shuffle(pool)
    seen=set(); cards=[]
    for item in pool:
        if item[0] not in seen: seen.add(item[0]); cards.append(item)
        if len(cards)==3: break
    while len(cards)<3 and available:
        item=random.choice(available)
        if item[0] not in seen: seen.add(item[0]); cards.append(item)

    rebirth_cards=[]
    if gs.rebirth_tokens>0:
        rebirth_cards=[u for u in REBIRTH_SHOP if gs.upgrades.get(u[0],0)==0]

    selected=-1; show_rebirth=False; msg=""
    cw=240; ch=200; gap=16
    total_cw=len(cards)*cw+(len(cards)-1)*gap
    cx_start=(WIDTH-total_cw)//2; cy_cards=170

    # Joystick state
    joy_cursor   = 0      # which card the stick is on
    joy_nav_cd   = 0      # X-axis navigation cooldown (frames)
    joy_fire_prev= False  # previous frame Y-pull state (rising-edge buy)

    def _try_buy(idx):
        """Attempt to buy card at index idx. Updates score, msg, cards in place."""
        nonlocal score, msg
        if idx<0 or idx>=len(cards): return
        uid,name,desc,cost,mx2,rarity=cards[idx]
        stacks=gs.upgrades.get(uid,0)
        actual_cost=int(cost*(1+stacks*0.5))
        if score>=actual_cost and stacks<mx2:
            score-=actual_cost; gs.add_upgrade(uid)
            msg=f"Bought {name}!"; cards.pop(idx)
        else:
            msg="Not enough score!" if score<actual_cost else "Already maxed!"

    def _try_buy_rebirth(idx):
        nonlocal msg, show_rebirth
        if idx<0 or idx>=len(rebirth_cards): return
        ru=rebirth_cards[idx]
        if gs.rebirth_tokens>=ru[4]:
            gs.rebirth_tokens-=ru[4]; gs.add_upgrade(ru[0])
            msg=f"Bought {ru[1]}!"; show_rebirth=False
        else:
            msg="Not enough tokens!"

    clock2=pygame.time.Clock()
    while True:
        clock2.tick(60)
        mx,my=pygame.mouse.get_pos()

        # Clamp cursor in case cards shrink after a purchase
        max_cursor=(len(rebirth_cards[:3])-1) if show_rebirth else (len(cards)-1)
        joy_cursor=max(0,min(joy_cursor,max(0,max_cursor)))

        # ── Keyboard / mouse events ───────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key in (pygame.K_1,pygame.K_KP1): selected=0
                if ev.key in (pygame.K_2,pygame.K_KP2): selected=1
                if ev.key in (pygame.K_3,pygame.K_KP3): selected=2
                if ev.key in (pygame.K_ESCAPE,pygame.K_s): return score
                if ev.key==pygame.K_r and gs.rebirth_tokens>0:
                    show_rebirth=not show_rebirth; joy_cursor=0
                if ev.key==pygame.K_LEFT:  joy_cursor=max(0,joy_cursor-1)
                if ev.key==pygame.K_RIGHT: joy_cursor=min(max_cursor,joy_cursor+1)
                if ev.key==pygame.K_RETURN or ev.key==pygame.K_SPACE:
                    if not show_rebirth: selected=joy_cursor
                    else: _try_buy_rebirth(joy_cursor)
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                skip_r=pygame.Rect(WIDTH//2-60,HEIGHT-55,120,36)
                if skip_r.collidepoint(mx,my): return score
                for i,card in enumerate(cards):
                    r=pygame.Rect(cx_start+i*(cw+gap),cy_cards,cw,ch)
                    if r.collidepoint(mx,my): selected=i
                if gs.rebirth_tokens>0:
                    rb=pygame.Rect(WIDTH//2-80,HEIGHT-100,160,30)
                    if rb.collidepoint(mx,my): show_rebirth=not show_rebirth; joy_cursor=0
                if show_rebirth:
                    for i,ru in enumerate(rebirth_cards[:3]):
                        rr=pygame.Rect(cx_start+i*(cw+gap),cy_cards,cw,100)
                        if rr.collidepoint(mx,my): _try_buy_rebirth(i)

        # ── Joystick input ────────────────────────────────────────────────────
        if joy.connected:
            jx,jy=joy.get_axes()

            # X-axis: navigate left / right between cards
            if joy_nav_cd>0:
                joy_nav_cd-=1
            else:
                if jx<JOY_CENTER-JOY_DEADZONE:
                    joy_cursor=max(0,joy_cursor-1); joy_nav_cd=18
                elif jx>JOY_CENTER+JOY_DEADZONE:
                    joy_cursor=min(max_cursor,joy_cursor+1); joy_nav_cd=18

            # Y pull-back rising edge → buy
            joy_fire_now=(jy>JOY_FIRE_THRESH)
            if joy_fire_now and not joy_fire_prev:
                if not show_rebirth: selected=joy_cursor
                else: _try_buy_rebirth(joy_cursor)
            joy_fire_prev=joy_fire_now

            # Short press (melee event) → buy highlighted card
            if joy.consume_melee_event():
                if not show_rebirth: selected=joy_cursor
                else: _try_buy_rebirth(joy_cursor)

            # Long press (pause event) → skip shop
            if joy.consume_btn_event():
                return score

            # Y forward push → toggle rebirth shop
            if joy.consume_grenade_event():
                if gs.rebirth_tokens>0:
                    show_rebirth=not show_rebirth; joy_cursor=0

        # ── Process keyboard/mouse card purchase ──────────────────────────────
        if selected>=0:
            _try_buy(selected); selected=-1

        # ── DRAW ──────────────────────────────────────────────────────────────
        screen.blit(get_bg(),(0,0))
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,160)); screen.blit(ov,(0,0))

        # Header
        draw_panel(screen,(WIDTH//2-340,22,680,118),alpha=230)
        pygame.draw.rect(screen,(255,180,40),(WIDTH//2-340,22,680,4),border_radius=4)
        draw_text(screen,"SHOP",font_big,(255,200,60),WIDTH//2,30,"midtop")
        draw_text(screen,f"Score: {int(score):,}   Tokens: {gs.rebirth_tokens}",font_sm,(180,200,180),WIDTH//2,82,"midtop",shadow=False)
        if joy.connected:
            draw_text(screen,"Stick L/R: navigate   Y-pull / short-press: buy   Long-press: skip",
                      font_xs,(100,160,200),WIDTH//2,104,"midtop",shadow=False)
        else:
            draw_text(screen,"[1][2][3] buy   Arrow keys navigate   ENTER buy   [S]/[ESC] skip   [R] rebirth shop",
                      font_xs,(120,140,160),WIDTH//2,104,"midtop",shadow=False)

        if not show_rebirth:
            for i,card in enumerate(cards):
                uid,name,desc,cost,mx2,rarity=card
                stacks=gs.upgrades.get(uid,0); actual_cost=int(cost*(1+stacks*0.5))
                cx_c=cx_start+i*(cw+gap); rc=pygame.Rect(cx_c,cy_cards,cw,ch)
                hover=rc.collidepoint(mx,my)
                joy_sel=(i==joy_cursor and joy.connected)

                # Panel background — brighter for joystick or mouse selection
                draw_panel(screen,(cx_c,cy_cards,cw,ch),alpha=230 if joy_sel else (210 if hover else 190))
                # Rarity top stripe
                pygame.draw.rect(screen,RARITY_COL[rarity],(cx_c,cy_cards,cw,5),border_radius=4)

                # Border: gold pulsing for joystick selection, normal for hover
                if joy_sel:
                    t_pulse=(pygame.time.get_ticks()//250)%2
                    border_c=(255,220,60) if t_pulse else (200,160,30)
                    pygame.draw.rect(screen,border_c,rc,3,border_radius=4)
                    # Joystick cursor arrow at bottom of card
                    ax=cx_c+cw//2; ay=cy_cards+ch+6
                    pygame.draw.polygon(screen,(255,220,60),[(ax-10,ay),(ax+10,ay),(ax,ay+8)])
                elif hover:
                    pygame.draw.rect(screen,RARITY_COL[rarity],rc,2,border_radius=4)
                else:
                    pygame.draw.rect(screen,RARITY_COL[rarity],rc,1,border_radius=4)

                draw_text(screen,f"[{i+1}] {name}",font_sm,C_WHITE,cx_c+12,cy_cards+14)
                draw_text(screen,rarity.upper(),font_xs,RARITY_COL[rarity],cx_c+cw-10,cy_cards+14,"topright",shadow=False)
                # Description word-wrap
                words=desc.split(); lines2=[]; line2=""
                for w in words:
                    if font_xs.size(line2+" "+w)[0]>cw-20: lines2.append(line2); line2=w
                    else: line2=(line2+" "+w).strip()
                if line2: lines2.append(line2)
                for li,l in enumerate(lines2): draw_text(screen,l,font_xs,(180,200,180),cx_c+12,cy_cards+44+li*18,shadow=False)
                if stacks>0: draw_text(screen,f"Owned: {stacks}/{mx2}",font_xs,(150,170,150),cx_c+12,cy_cards+ch-54,shadow=False)
                can_buy=score>=actual_cost and stacks<mx2
                bc=(70,180,70) if (can_buy and joy_sel) else ((50,140,50) if can_buy else (60,60,70))
                pygame.draw.rect(screen,bc,(cx_c+12,cy_cards+ch-38,cw-24,28),border_radius=5)
                btxt=f"BUY  {actual_cost:,}" if stacks<mx2 else "MAXED"
                draw_text(screen,btxt,font_sm,(230,255,230) if can_buy else (100,100,110),cx_c+cw//2,cy_cards+ch-30,"midtop",shadow=False)
        else:
            draw_text(screen,"REBIRTH UPGRADES",font_med,(255,180,40),WIDTH//2,cy_cards-30,"midtop")
            for i,ru in enumerate(rebirth_cards[:3]):
                cxr=cx_start+i*(cw+gap); rr2=pygame.Rect(cxr,cy_cards,cw,100)
                joy_sel=(i==joy_cursor and joy.connected)
                draw_panel(screen,(cxr,cy_cards,cw,100),alpha=230 if joy_sel else 210)
                pygame.draw.rect(screen,(255,150,30),(cxr,cy_cards,cw,4),border_radius=4)
                if joy_sel:
                    t_p=(pygame.time.get_ticks()//250)%2
                    pygame.draw.rect(screen,(255,200,40) if t_p else (200,150,20),rr2,3,border_radius=4)
                    ax2=cxr+cw//2; ay2=cy_cards+102
                    pygame.draw.polygon(screen,(255,200,40),[(ax2-10,ay2),(ax2+10,ay2),(ax2,ay2+8)])
                else:
                    pygame.draw.rect(screen,(180,100,20),rr2,1,border_radius=4)
                draw_text(screen,ru[1],font_sm,(255,200,80),cxr+12,cy_cards+10)
                draw_text(screen,ru[3],font_xs,(180,200,180),cxr+12,cy_cards+36,shadow=False)
                draw_text(screen,f"Cost: {ru[4]} token(s)",font_xs,(255,180,40),cxr+12,cy_cards+56,shadow=False)
                can=gs.rebirth_tokens>=ru[4]; bc=(70,140,70) if can else (50,50,60)
                pygame.draw.rect(screen,bc,(cxr+12,cy_cards+76,cw-24,20),border_radius=4)
                draw_text(screen,"REDEEM" if can else "NEED TOKENS",font_xs,(220,255,220) if can else (100,100,110),cxr+cw//2,cy_cards+78,"midtop",shadow=False)

        # Skip button
        skip_r=pygame.Rect(WIDTH//2-60,HEIGHT-55,120,36)
        pygame.draw.rect(screen,(50,60,80),skip_r,border_radius=6)
        pygame.draw.rect(screen,C_UI_BORDER,skip_r,1,border_radius=6)
        draw_text(screen,"SKIP",font_sm,(160,180,200),WIDTH//2,HEIGHT-48,"midtop")
        if gs.rebirth_tokens>0:
            rb2=pygame.Rect(WIDTH//2-90,HEIGHT-100,180,30)
            pygame.draw.rect(screen,(70,50,20),rb2,border_radius=5)
            draw_text(screen,f"[R] REBIRTH SHOP  [{gs.rebirth_tokens} tokens]",font_xs,(255,200,60),WIDTH//2,HEIGHT-97,"midtop",shadow=False)
        if msg:
            mc2=(100,255,100) if "Bought" in msg else (255,100,100)
            ms=font_sm.render(msg,True,mc2)
            screen.blit(ms,ms.get_rect(center=(WIDTH//2,HEIGHT-130)))

        pygame.display.flip()

# ─── PERK AWARD SCREEN ────────────────────────────────────────────────────────
def screen_perk_award(bd,gs):
    if bd["perk"] in gs.perks: return  # already have it
    timer=FPS*5
    while timer>0:
        timer-=1
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_RETURN,pygame.K_SPACE): timer=0
        screen.blit(get_bg(),(0,0))
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,170)); screen.blit(ov,(0,0))
        draw_panel(screen,(WIDTH//2-280,160,560,260),alpha=240)
        pygame.draw.rect(screen,bd["gold"],(WIDTH//2-280,160,560,5),border_radius=4)
        draw_text(screen,"BOSS DEFEATED!",font_big,bd["gold"],WIDTH//2,172,"midtop")
        draw_text(screen,f"PERK UNLOCKED: {bd['perk_name']}",font_med,bd["glow"],WIDTH//2,232,"midtop")
        draw_text(screen,bd["perk_desc"],font_sm,(200,220,200),WIDTH//2,268,"midtop",shadow=False)
        draw_text(screen,"ENTER to continue",font_xs,(140,160,140),WIDTH//2,312,"midtop",shadow=False)
        pygame.display.flip(); clock.tick(60)
    gs.add_perk(bd["perk"])

# ─── PAUSE MENU ───────────────────────────────────────────────────────────────
class PauseMenu:
    BASE_OPTS=["RESUME","VOLUME","RESTART","QUIT"]
    REBIRTH_OPT="REBIRTH"
    COLOURS={"RESUME":(70,215,100),"VOLUME":(100,180,255),"RESTART":(255,200,55),"QUIT":(220,65,55),"REBIRTH":(255,140,30)}
    def __init__(self): self.selected=0; self.can_rebirth=False
    @property
    def options(self): return self.BASE_OPTS[:2]+([self.REBIRTH_OPT] if self.can_rebirth else [])+self.BASE_OPTS[2:]
    def _btn_rect(self,idx):
        opts=self.options; bw,bh=350,40; cy2=HEIGHT//2-20+idx*(bh+14)
        return pygame.Rect(WIDTH//2-bw//2,cy2-bh//2,bw,bh)
    def handle_event(self,ev):
        opts=self.options
        if ev.type==pygame.KEYDOWN:
            if ev.key in (pygame.K_UP,pygame.K_w): self.selected=(self.selected-1)%len(opts)
            if ev.key in (pygame.K_DOWN,pygame.K_s): self.selected=(self.selected+1)%len(opts)
            if ev.key in (pygame.K_RETURN,pygame.K_SPACE): return opts[self.selected].lower()
            if ev.key in (pygame.K_p,pygame.K_ESCAPE): return "resume"
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            for i,opt in enumerate(opts):
                if self._btn_rect(i).collidepoint(ev.pos): return opt.lower()
        return None
    def handle_joy(self,jy,btn_ev,joy_cd):
        opts=self.options; action=None
        if btn_ev: action=opts[self.selected].lower()
        if joy_cd>0: return action,joy_cd-1
        if jy<JOY_CENTER-JOY_DEADZONE: self.selected=(self.selected-1)%len(opts); return action,JOY_LANE_CD_MAX
        if jy>JOY_CENTER+JOY_DEADZONE: self.selected=(self.selected+1)%len(opts); return action,JOY_LANE_CD_MAX
        return action,joy_cd
    def draw(self,surf):
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,175)); surf.blit(ov,(0,0))
        opts=self.options; ph=80+len(opts)*66; pw=420; px2=WIDTH//2-pw//2; py2=HEIGHT//2-ph//2
        draw_panel(surf,(px2,py2,pw,ph),alpha=240)
        pygame.draw.rect(surf,(255,200,60),(px2,py2,pw,4),border_radius=4)
        draw_text(surf,"PAUSED",font_big,(255,215,70),WIDTH//2,py2+12,"midtop")
        draw_text(surf,"W/S  navigate    ENTER  select",font_xs,(130,150,175),WIDTH//2,py2+58,"midtop",shadow=False)
        mx,my=pygame.mouse.get_pos()
        for i,opt in enumerate(opts):
            r=self._btn_rect(i); sel=(i==self.selected); hov=r.collidepoint(mx,my)
            base=self.COLOURS.get(opt,(180,180,180))
            if sel: pygame.draw.rect(surf,lerp_colour((10,14,28),base,0.2),r,border_radius=8); pygame.draw.rect(surf,base,r,2,border_radius=8)
            elif hov: pygame.draw.rect(surf,lerp_colour((10,14,28),base,0.1),r,border_radius=8); pygame.draw.rect(surf,lerp_colour(base,(60,80,110),0.5),r,1,border_radius=8)
            else: pygame.draw.rect(surf,(18,22,38),r,border_radius=8); pygame.draw.rect(surf,(48,62,88),r,1,border_radius=8)
            tc=base if sel else lerp_colour(base,(150,160,180),0.55)
            draw_text(surf,opt,font_med,tc,r.centerx,r.centery,"center")

# ─── SCREENS ──────────────────────────────────────────────────────────────────
def screen_volume(joy):
    """Blocking volume settings overlay. [V] or ESC to close."""
    SLIDER_W = 320; SLIDER_H = 14; KNOB_R = 10
    labels  = ["MUSIC VOLUME", "SFX VOLUME"]
    getters = [sfx.get_music_volume, sfx.get_sfx_volume]
    setters = [sfx.set_music_volume, sfx.set_sfx_volume]
    dragging = None   # index of slider being dragged

    def slider_rect(i):
        cx = WIDTH // 2; y = 400 + i * 100
        return pygame.Rect(cx - SLIDER_W // 2, y, SLIDER_W, SLIDER_H)

    clock2 = pygame.time.Clock()
    while True:
        clock2.tick(60)
        mx, my = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_v, pygame.K_ESCAPE, pygame.K_p): return
                # Arrow keys tweak focused slider (music = up/down cycle, both = left/right)
                for i, (g, s) in enumerate(zip(getters, setters)):
                    if ev.key == pygame.K_LEFT:  s(g() - 0.05)
                    if ev.key == pygame.K_RIGHT: s(g() + 0.05)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i in range(2):
                    r = slider_rect(i)
                    hit = r.inflate(0, KNOB_R * 4)
                    if hit.collidepoint(mx, my):
                        dragging = i
                        v = max(0.0, min(1.0, (mx - r.x) / r.w))
                        setters[i](v)
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                dragging = None
            if ev.type == pygame.MOUSEMOTION and dragging is not None:
                r = slider_rect(dragging)
                v = max(0.0, min(1.0, (mx - r.x) / r.w))
                setters[dragging](v)

        # ── Draw ─────────────────────────────────────────────────────────────
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 190)); screen.blit(ov, (0, 0))

        pw, ph = 480, 340; px2 = WIDTH // 2 - pw // 2; py2 = HEIGHT // 2 - ph // 2
        draw_panel(screen, (px2, py2, pw, ph), alpha=245)
        pygame.draw.rect(screen, (255, 200, 60), (px2, py2, pw, 4), border_radius=4)
        draw_text(screen, "VOLUME SETTINGS", font_big, (255, 200, 60), WIDTH // 2, py2 + 14, "midtop")
        draw_text(screen, "Drag sliders  ·  ← → adjust  ·  [V] / [ESC] close",
                  font_xs, (120, 140, 160), WIDTH // 2, py2 + 62, "midtop", shadow=False)

        for i, (label, getter) in enumerate(zip(labels, getters)):
            vol = getter(); r = slider_rect(i)
            draw_text(screen, label, font_sm, (200, 220, 200), WIDTH // 2, r.y - 30, "midtop", shadow=False)
            # Track
            pygame.draw.rect(screen, (40, 40, 55), r, border_radius=7)
            filled = pygame.Rect(r.x, r.y, int(r.w * vol), r.h)
            fc = (100, 200, 100) if i == 0 else (100, 160, 255)
            pygame.draw.rect(screen, fc, filled, border_radius=7)
            pygame.draw.rect(screen, lerp_colour(fc, C_WHITE, 0.3), r, 1, border_radius=7)
            # Knob
            kx = r.x + int(r.w * vol); ky = r.centery
            pygame.draw.circle(screen, C_WHITE, (kx, ky), KNOB_R)
            pygame.draw.circle(screen, fc, (kx, ky), KNOB_R - 3)
            # Percentage label
            draw_text(screen, f"{int(vol * 100)}%", font_sm, C_WHITE,
                      r.right + 18, r.centery, "midleft", shadow=False)

        draw_text(screen, "[V] to close", font_xs, (100, 120, 140),
                  WIDTH // 2, py2 + ph - 28, "midtop", shadow=False)
        pygame.display.flip()

def screen_menu(joy):
    t=0
    while True:
        t+=1; screen.blit(get_bg(),(0,0))
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,135)); screen.blit(ov,(0,0))
        tc=lerp_colour((60,180,60),(120,255,120),(math.sin(t*0.05)+1)/2)
        draw_text(screen,"DEAD LANES!",font_big,tc,WIDTH//2,72,"midtop")
        draw_panel(screen,(WIDTH//2-295,148,590,386),alpha=215)
        pygame.draw.rect(screen,(80,200,80),(WIDTH//2-295,148,590,4),border_radius=4)
        rows=[
            ("── KEYBOARD ────────────────────────────────────",(90,115,145)),
            ("[1-4] Lane    [SPACE] Fire    [R] Reload    [E] HOLD for Ult",( 175,195,175)),
            ("[F] Melee    [G] Grenade (2-lane)    [P] Pause    [V] Volume    [ESC] Quit",(175,195,175)),("",C_BLACK),
            ("── ARDUINO JOYSTICK ─────────────────────────────",(90,115,145)),
            ("LEFT/RIGHT → Lane    Pull BACK → Fire    FWD → Reload",(175,195,175)),
            ("HOLD DIAGONAL → Ultimate    Click → Pause",(175,195,175)),("",C_BLACK),
            ("── MECHANICS ────────────────────────────────────",(90,115,145)),
            ("6-bullet mag — auto-reloads on empty",(210,185,95)),
            ("Kill zombies to charge ULTIMATE → HOLD [E] to activate",(175,195,175)),
            ("Sniper: piercing but damage decays each zombie hit",(175,195,175)),
            ("Shop every 5 waves — spend score for upgrades",(255,200,100)),
            ("Boss every 10 waves — defeat for a permanent perk!",(255,100,255)),
            ("Rebirth after wave 100 for tokens & scaled power",(255,140,30)),("",C_BLACK),
            ("Press  ENTER  or  joystick  to  START",(255,220,60)),
        ]
        for j,(l,c) in enumerate(rows):
            if l: draw_text(screen,l,font_xs,c,WIDTH//2,164+j*21,"midtop",shadow=False)
        sc=(50,230,50) if joy.connected else (200,70,70)
        pygame.draw.circle(screen,sc,(WIDTH//2-152,HEIGHT-26),5)
        draw_text(screen,f"  Arduino: {'CONNECTED' if joy.connected else 'NOT FOUND (keyboard only)'}",font_xs,sc,WIDTH//2-144,HEIGHT-34,shadow=False)
        pygame.display.flip(); clock.tick(60)
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_RETURN: return
        if joy.consume_btn_event(): return

def screen_game_over(score,wave,gs):
    while True:
        screen.blit(get_bg(),(0,0))
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,165)); screen.blit(ov,(0,0))
        draw_panel(screen,(WIDTH//2-220,130,440,310),alpha=240)
        pygame.draw.rect(screen,(220,50,50),(WIDTH//2-220,130,440,4),border_radius=4)
        draw_text(screen,"GAME OVER",font_big,(220,50,50),WIDTH//2,148,"midtop")
        draw_text(screen,f"SCORE    {int(score):,}",font_med,C_WHITE,WIDTH//2,218,"midtop")
        draw_text(screen,f"WAVE     {wave}",font_med,(255,200,80),WIDTH//2,252,"midtop")
        draw_text(screen,f"REBIRTHS {gs.rebirth}",font_med,(255,140,30),WIDTH//2,286,"midtop")
        draw_text(screen,"ENTER → Play Again          ESC → Quit",font_sm,(155,175,155),WIDTH//2,340,"midtop")
        pygame.display.flip()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_RETURN: return True
                if ev.key==pygame.K_ESCAPE: return False
        clock.tick(30)

# ─── MAIN GAME LOOP ───────────────────────────────────────────────────────────
def run_game(joy,gs):
    car_positions=[(260,0),(460,1),(680,2),(800,3),(370,1),(580,0),(750,3),(430,2)]
    cars=[BurningCar(x,l) for x,l in car_positions]
    player=Player(); gs.apply_to_player(player)
    player._joy=joy; player.base_hp=BASE_HP_MAX+gs.hp_bonus; player.max_hp=player.base_hp
    joy.send_ammo(player.mag_size)
    bullets=[]; zombies=[]; particles=[]; powerups=[]; boss_projs=[]
    slashes=[]; grenades=[]
    wave_mgr=WaveManager(gs)
    score=0; pu_timer=0; holding_fire=False; paused=False
    pm=PauseMenu(); joy_cd=0; do_melee=False; do_grenade=False
    prev_wave=0      # tracks wave changes for buzzer beep
    ult_hold=0       # frames E or diagonal held
    boss_alive=False; boss_banner=0; boss_kill_flash=0
    perk_to_award=None   # bd dict, shown after frame
    bg=get_bg()
    sfx.load_music("deadLanesScore.mp3")
    sfx.start_bg_music()   # begin background music

    while True:
        clock.tick(FPS)

        # ── EVENTS ────────────────────────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: joy.close(); pygame.quit(); sys.exit()
            if paused:
                action=pm.handle_event(ev)
                if action=="resume": paused=False
                elif action=="volume": screen_volume(joy)
                elif action=="restart": return None,gs
                elif action=="rebirth":
                    gs.rebirth+=1; gs.rebirth_tokens+=1; gs.shop_shown_wave=0; return None,gs
                elif action=="quit": return score,gs
                continue
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_1: player.set_lane(0)
                if ev.key==pygame.K_2: player.set_lane(1)
                if ev.key==pygame.K_3: player.set_lane(2)
                if ev.key==pygame.K_4: player.set_lane(3)
                if ev.key==pygame.K_p: paused=True; pm.selected=0
                if ev.key==pygame.K_v: sfx.pause_bg_music(); screen_volume(joy); sfx.resume_bg_music()
                if ev.key==pygame.K_ESCAPE: return score,gs
                if ev.key==pygame.K_SPACE: holding_fire=True
                if ev.key==pygame.K_r: player.start_reload()
                if ev.key==pygame.K_f: do_melee=True
                if ev.key==pygame.K_g: do_grenade=True
            if ev.type==pygame.KEYUP:
                if ev.key==pygame.K_SPACE: holding_fire=False

        # ── JOYSTICK ──────────────────────────────────────────────────────────
        if joy.connected:
            jx,jy=joy.get_axes(); btn_ev=joy.consume_btn_event()
            melee_ev=joy.consume_melee_event(); grenade_ev=joy.consume_grenade_event()
            if paused:
                action,joy_cd=pm.handle_joy(jy,btn_ev,joy_cd)
                if action=="resume": paused=False
                elif action=="volume": screen_volume(joy)
                elif action=="restart": return None,gs
                elif action=="rebirth": gs.rebirth+=1; gs.rebirth_tokens+=1; gs.shop_shown_wave=0; return None,gs
                elif action=="quit": return score,gs
            else:
                if btn_ev: paused=True; pm.selected=0
                if melee_ev: do_melee=True
                if grenade_ev: do_grenade=True
                if joy_cd>0: joy_cd-=1
                else:
                    if jx<JOY_CENTER-JOY_DEADZONE: player.set_lane(player.lane-1); joy_cd=JOY_LANE_CD_MAX
                    elif jx>JOY_CENTER+JOY_DEADZONE: player.set_lane(player.lane+1); joy_cd=JOY_LANE_CD_MAX
                if jy>JOY_FIRE_THRESH:
                    b=player.shoot()
                    if b: bullets.append(b)
                if jy<JOY_CENTER-JOY_DEADZONE-80: player.start_reload()
                # Diagonal hold → ult
                diag=(abs(jx-JOY_CENTER)>JOY_DEADZONE+30 and abs(jy-JOY_CENTER)>JOY_DEADZONE+30)
                if diag and player.ult_charge>=ULT_MAX: ult_hold+=1
                else: ult_hold=max(0,ult_hold-2)

        # ── PAUSE ─────────────────────────────────────────────────────────────
        pm.can_rebirth=(wave_mgr.wave>100)
        if paused:
            screen.blit(bg,(0,0)); [c.draw(screen) for c in cars]
            [p.draw(screen) for p in particles]; [pu.draw(screen) for pu in powerups]
            [bp.draw(screen) for bp in boss_projs]; [b.draw(screen) for b in bullets]
            [sl.draw(screen) for sl in slashes]; [gr.draw(screen) for gr in grenades]
            [z.draw(screen) for z in zombies]; player.draw(screen)
            draw_hud(screen,score,player,wave_mgr,joy,gs,boss_alive)
            pm.draw(screen); pygame.display.flip(); do_melee=False; do_grenade=False; continue

        # ── E KEY — ult hold ──────────────────────────────────────────────────
        keys=pygame.key.get_pressed()
        if keys[pygame.K_e] and player.ult_charge>=ULT_MAX: ult_hold+=1
        elif not joy.connected: ult_hold=max(0,ult_hold-2)
        player.ult_hold=ult_hold
        if ult_hold>=ULT_HOLD_NEED: player.try_activate_ult(); ult_hold=0

        # ── MELEE [F] ─────────────────────────────────────────────────────────
        if do_melee and player.melee_cd==0:
            player.melee_cd=player.melee_cd_max
            slashes.append(MeleeSlash(player.lane, aoe=player.melee_aoe))
            sfx.play_slash()
            hit_lanes=range(LANES) if player.melee_aoe else [player.lane]
            for z in zombies:
                if not z.alive: continue
                if z.lane in hit_lanes and z.x<BASE_X+MELEE_RANGE:
                    dmg=int(3*player.dmg_mult)
                    killed=z.take_damage(dmg)
                    if killed:
                        sfx.play_zombie_death()
                        score+=int(z.score_val*gs.score_mult)
                        player.charge_ult(z.ult_charge,gs)
                        exp_c=C_BOSS_EXPLOSION if isinstance(z,BossZombie) else [(100,200,255),(150,220,255),(200,240,255),(80,160,220)]
                        for _ in range(14): particles.append(Particle(z.x,lane_cy(z.lane),random.choice(exp_c)))
                        if isinstance(z,BossZombie): perk_to_award=z.bd; boss_kill_flash=14
        do_melee=False

        # ── GRENADE [G] ───────────────────────────────────────────────────────
        if do_grenade and player.grenade_cd==0:
            player.grenade_cd=player.grenade_cd_max
            grenades.append(GrenadeProjectile(player.lane,radius=player.grenade_radius,lanes_hit=player.grenade_lanes))
            sfx.play_grenade_toss()
        do_grenade=False

        # ── KEYBOARD FIRE ─────────────────────────────────────────────────────
        if holding_fire:
            b=player.shoot()
            if b: bullets.append(b)

        # ── UPDATE ────────────────────────────────────────────────────────────
        player.update(); [c.update() for c in cars]; [b2.update() for b2 in bullets]
        [p.update() for p in particles]; [pu.update() for pu in powerups]
        [sl.update() for sl in slashes]
        # Fire-burning loop: runs while ultimate is active
        if player.ult_active: sfx.start_fire_loop()
        else: sfx.stop_fire_loop()
        # Grenade update + zombie damage on explosion
        for gr in grenades:
            was_exploded=gr.exploded
            gr.update()
            if gr.exploded and not was_exploded:
                sfx.play_explosion()
                # First frame of explosion: deal damage
                for z in zombies:
                    if not z.alive: continue
                    if z.lane in gr.get_hit_lanes() and abs(z.x-gr.TARGET_X)<gr.radius:
                        dmg=int(4*player.dmg_mult)
                        killed=z.take_damage(dmg)
                        if killed:
                            sfx.play_zombie_death()
                            score+=int(z.score_val*gs.score_mult)
                            player.charge_ult(z.ult_charge,gs)
                            exp_c=C_BOSS_EXPLOSION if isinstance(z,BossZombie) else C_EXPLOSION
                            for _ in range(20): particles.append(Particle(z.x,lane_cy(z.lane),random.choice(exp_c)))
                            if isinstance(z,BossZombie): perk_to_award=z.bd; boss_kill_flash=14

        # Boss projectiles
        for bp in boss_projs:
            hit_base=bp.update()
            if hit_base:
                player.base_hp-=1
                sfx.play_take_damage()
                for _ in range(10): particles.append(Particle(BASE_X,lane_cy(bp.lane),(255,80,20)))
                if player.base_hp<=0: return score,gs
        boss_projs=[bp for bp in boss_projs if bp.alive]

        # Wave manager
        new_z=wave_mgr.update([z for z in zombies if z.alive])
        if new_z:
            zombies.append(new_z)
            if isinstance(new_z,BossZombie):
                sfx.play_boss_spawn()
                if boss_banner==0: boss_banner=FPS*3
            else:
                sfx.play_zombie_spawn()

        # Wave-start buzzer beep
        if wave_mgr.wave != prev_wave:
            joy.send_wave_beep()
            prev_wave = wave_mgr.wave

        # Shop trigger
        if wave_mgr.just_entered_break and wave_mgr.wave%SHOP_INTERVAL==0 and gs.shop_shown_wave!=wave_mgr.wave:
            gs.shop_shown_wave=wave_mgr.wave
            sfx.pause_bg_music()
            sfx.start_shop_ambient()
            score=screen_shop(gs,score,joy)
            sfx.stop_shop_ambient()
            sfx.resume_bg_music()
            gs.apply_to_player(player); player.base_hp=min(player.base_hp,BASE_HP_MAX+gs.hp_bonus); player.max_hp=BASE_HP_MAX+gs.hp_bonus

        boss_alive=any(isinstance(z,BossZombie) and z.alive for z in zombies)
        pu_interval=FPS*random.randint(4,8) if boss_alive else FPS*random.randint(12,20)

        game_over=False
        for z in zombies:
            evts=z.update()
            for ev2 in evts:
                if ev2[0]=="breach":
                    player.base_hp-=1
                    sfx.play_take_damage()
                    dc=(180,20,220) if isinstance(z,BossZombie) else (220,55,55)
                    for _ in range(16 if isinstance(z,BossZombie) else 12): particles.append(Particle(BASE_X,lane_cy(z.lane),dc))
                    if player.base_hp<=0: game_over=True
                elif ev2[0]=="boss_spawn":
                    diff=gs.difficulty_mult(wave_mgr.wave)
                    zombies.append(Zombie(ev2[1],"fast",diff)); zombies.append(Zombie(ev2[1],"normal",diff))
                elif ev2[0]=="boss_bomb":
                    boss_projs.append(BossProjectile(z.lane))

        # Bullet ↔ zombie
        for b2 in bullets:
            if not b2.alive: continue
            for z in zombies:
                if not z.alive: continue
                if b2.lane==z.lane and abs(b2.x-z.x)<z.size+8:
                    killed=z.take_damage(b2.damage)
                    if b2.pierce: b2.pierce_hits+=1
                    else: b2.alive=False
                    if killed:
                        sfx.play_zombie_death()
                        pts=int(z.score_val*gs.score_mult); score+=pts
                        player.charge_ult(z.ult_charge,gs)
                        if gs.vampiric: gs.vampire_kills+=1
                        if gs.vampiric and gs.vampire_kills>=5:
                            gs.vampire_kills=0; player.base_hp=min(player.max_hp,player.base_hp+1)
                        exp_c=C_BOSS_EXPLOSION if isinstance(z,BossZombie) else C_EXPLOSION
                        cnt=40 if isinstance(z,BossZombie) else 18
                        for _ in range(cnt): particles.append(Particle(z.x,lane_cy(z.lane),random.choice(exp_c)))
                        if isinstance(z,BossZombie):
                            boss_kill_flash=14; score+=z.score_val; perk_to_award=z.bd
                        # Splash perk
                        if gs.splash:
                            for z2 in zombies:
                                if z2 is not z and z2.alive and z2.lane==z.lane and abs(z2.x-z.x)<40:
                                    z2.take_damage(1)
                        # Parasite perk
                        if gs.parasite and random.random()<0.15:
                            player.ammo=min(player.mag_size,player.ammo+1)
                            if player._joy: player._joy.send_ammo(player.ammo)
                    else:
                        sfx.play_bullet_impact()
                    break

        # Player ↔ powerup
        for pu in powerups:
            if not pu.alive: continue
            if pu.lane==player.lane and abs(pu.x-BASE_X)<46:
                pu.alive=False
                sfx.play_powerup()
                if pu.kind=="heal": player.base_hp=min(player.max_hp,player.base_hp+2)
                else: player.weapon=pu.kind; player.weapon_timer=int(FPS*15*gs.pu_dur_mult)
                score+=int(50*gs.score_mult)

        # Powerup spawn
        pu_timer+=1
        if pu_timer>pu_interval: pu_timer=0; powerups.append(PowerUp())

        # Timers
        if boss_banner>0: boss_banner-=1
        if boss_kill_flash>0: boss_kill_flash-=1

        # Cleanup
        bullets=[b2 for b2 in bullets if b2.alive]
        zombies=[z for z in zombies if z.alive]
        particles=[p for p in particles if p.life>0]
        powerups=[pu for pu in powerups if pu.alive]
        slashes=[sl for sl in slashes if sl.life>0]
        grenades=[gr for gr in grenades if gr.alive]

        # ── DRAW ──────────────────────────────────────────────────────────────
        screen.blit(bg,(0,0))
        if boss_kill_flash>0:
            t5=boss_kill_flash/14; fl=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            fl.fill((180,30,220,int(120*t5))); screen.blit(fl,(0,0))
        [c.draw(screen) for c in cars]
        [p.draw(screen) for p in particles]
        [pu.draw(screen) for pu in powerups]
        [bp.draw(screen) for bp in boss_projs]
        [gr.draw(screen) for gr in grenades]
        [b2.draw(screen) for b2 in bullets]
        [z.draw(screen) for z in zombies]
        [sl.draw(screen) for sl in slashes]
        player.draw(screen)
        draw_hud(screen,score,player,wave_mgr,joy,gs,boss_alive)

        if boss_banner>0:
            bt2=(pygame.time.get_ticks()//300)%2; bc2=(255,80,255) if bt2 else (200,20,200)
            btxt2="  ⚠  BOSS INCOMING  ⚠  "
            bs=font_big.render(btxt2,True,bc2); bw2,bh2=bs.get_size()
            draw_panel(screen,(WIDTH//2-bw2//2-12,HEIGHT//2-bh2//2-8,bw2+24,bh2+16),alpha=210)
            pygame.draw.rect(screen,bc2,(WIDTH//2-bw2//2-12,HEIGHT//2-bh2//2-8,bw2+24,bh2+16),2,border_radius=4)
            screen.blit(bs,(WIDTH//2-bw2//2,HEIGHT//2-bh2//2))

        if wave_mgr.in_break:
            secs=math.ceil(wave_mgr.break_timer/FPS)
            btxt3=f"  WAVE {wave_mgr.wave} CLEARED!   Next in {secs}s  "
            bs2=font_big.render(btxt3,True,(255,220,80)); bw3,bh3=bs2.get_size()
            draw_panel(screen,(WIDTH//2-bw3//2-12,HEIGHT//2-bh3//2-8,bw3+24,bh3+16))
            screen.blit(bs2,(WIDTH//2-bw3//2,HEIGHT//2-bh3//2))

        pygame.display.flip()
        # Music control: pause during wave break, resume during active combat
        if wave_mgr.in_break or paused:
            sfx.pause_bg_music()
        else:
            sfx.resume_bg_music()
        if game_over:
            sfx.stop_fire_loop()
            sfx.stop_bg_music()
            sfx.play_game_over()
            pygame.time.wait(int(4 * 0.42 * 1000 + 300))   # let the 4-note sequence finish
            return score,gs

        # Perk award (after frame drawn)
        if perk_to_award:
            screen_perk_award(perk_to_award,gs); perk_to_award=None
            gs.apply_to_player(player); player.base_hp=min(player.base_hp,BASE_HP_MAX+gs.hp_bonus); player.max_hp=BASE_HP_MAX+gs.hp_bonus

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
def main():
    joy=JoystickController(port=SERIAL_PORT,baud=SERIAL_BAUD)
    get_bg()
    for wt in ("normal","rapid","pierce","ultimate"): get_gun_sprite(wt)
    for zt in ("normal","fast","tank"):
        get_zombie_sprite(zt,False); get_zombie_sprite(zt,True)
    for bi in range(10):
        get_boss_sprite(bi,False); get_boss_sprite(bi,True)

    gs=GameState()
    screen_menu(joy)

    while True:
        result,gs=run_game(joy,gs)
        if result is None: continue  # restart / rebirth
        score=result
        again=screen_game_over(score,gs.rebirth,gs)
        if not again: break
        # Reset wave progress but keep gs (upgrades, perks persist)
        gs.shop_shown_wave=0

    joy.close(); pygame.quit(); sys.exit()

if __name__=="__main__": main()
