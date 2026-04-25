import pygame
import random
import sys
import math

# ─── CONFIG ───────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 900, 600
LANES = 4
LANE_HEIGHT = HEIGHT // LANES
FPS = 60

# Colours
BG_DARK      = (8,  12,  20)
BG_LANE      = (12, 18,  30)
LANE_LINE    = (40, 55,  80)
GRASS_DARK   = (15, 35,  15)
GRASS_LIGHT  = (20, 45,  20)

C_PLAYER     = (0,  200, 255)
C_PLAYER_HL  = (120, 230, 255)
C_BARREL     = (180, 180, 200)
C_MUZZLE     = (255, 230, 100)

C_BULLET     = (255, 240,  80)
C_BULLET_GL  = (255, 200,  40)

C_ZOMBIE_N   = (60,  180,  60)   # normal
C_ZOMBIE_F   = (180,  60,  60)   # fast
C_ZOMBIE_T   = (80,   80, 180)   # tank
C_ZOMBIE_EYE = (255,  40,  40)
C_ZOMBIE_HL  = (200, 255, 200)

C_BASE       = (160, 100,  40)
C_BASE_HL    = (200, 140,  70)
C_HP_BAR_BG  = (60,  20,  20)
C_HP_BAR_FG  = (220,  50,  50)
C_XP_BAR_FG  = (50,  180, 255)

C_EXPLOSION  = [(255,200,50),(255,140,30),(255,80,10),(200,200,200)]
C_WHITE      = (255, 255, 255)
C_BLACK      = (0,   0,   0)

BASE_X       = 60   # x-centre of the player / gun
BASE_HP_MAX  = 10

# ─── PYGAME INIT ──────────────────────────────────────────────────────────────
pygame.init()
screen  = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🧟 Zombie Lane Defense")
clock   = pygame.time.Clock()

font_big   = pygame.font.SysFont("consolas", 44, bold=True)
font_med   = pygame.font.SysFont("consolas", 26, bold=True)
font_sm    = pygame.font.SysFont("consolas", 18)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def lane_cy(lane_idx):
    return lane_idx * LANE_HEIGHT + LANE_HEIGHT // 2


def lerp_colour(c1, c2, t):
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))


def draw_text_shadow(surf, text, font, colour, x, y, anchor="topleft"):
    shadow = font.render(text, True, (0, 0, 0))
    label  = font.render(text, True, colour)
    r = label.get_rect(**{anchor: (x, y)})
    surf.blit(shadow, r.move(2, 2))
    surf.blit(label,  r)


# ─── PARTICLE / EXPLOSION ─────────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, colour):
        self.x, self.y = x, y
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-5, 2)
        self.life = random.randint(15, 35)
        self.max_life = self.life
        self.r = random.randint(3, 8)
        self.colour = colour

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.25
        self.life -= 1

    def draw(self, surf):
        alpha = self.life / self.max_life
        c = lerp_colour((20,20,20), self.colour, alpha)
        r = max(1, int(self.r * alpha))
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), r)


# ─── MUZZLE FLASH ─────────────────────────────────────────────────────────────

class MuzzleFlash:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.life = 6

    def update(self): self.life -= 1

    def draw(self, surf):
        if self.life <= 0: return
        r = self.life * 4
        pygame.draw.circle(surf, C_MUZZLE, (self.x, self.y), r)
        pygame.draw.circle(surf, C_WHITE,  (self.x, self.y), r//2)


# ─── BULLET ───────────────────────────────────────────────────────────────────

class Bullet:
    def __init__(self, lane_idx, speed=14, damage=1, pierce=False):
        self.lane    = lane_idx
        self.x       = BASE_X + 30
        self.speed   = speed
        self.damage  = damage
        self.pierce  = pierce
        self.alive   = True
        self.trail   = []

    def update(self):
        self.trail.append((self.x, lane_cy(self.lane)))
        if len(self.trail) > 8:
            self.trail.pop(0)
        self.x += self.speed
        if self.x > WIDTH + 20:
            self.alive = False

    def draw(self, surf):
        cy = lane_cy(self.lane)
        # trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha = i / len(self.trail)
            c = lerp_colour(BG_DARK, C_BULLET_GL, alpha)
            pygame.draw.circle(surf, c, (int(tx), ty), max(1, int(4*alpha)))
        # bullet
        pygame.draw.circle(surf, C_BULLET, (int(self.x), cy), 6)
        pygame.draw.circle(surf, C_WHITE,  (int(self.x), cy), 3)


# ─── ZOMBIE ───────────────────────────────────────────────────────────────────

ZOMBIE_TYPES = {
    "normal": dict(hp=2,  speed=1.2, size=32, colour=C_ZOMBIE_N, score=10, reward=1),
    "fast"  : dict(hp=1,  speed=2.8, size=26, colour=C_ZOMBIE_F, score=15, reward=1),
    "tank"  : dict(hp=6,  speed=0.6, size=42, colour=C_ZOMBIE_T, score=30, reward=3),
}

class Zombie:
    def __init__(self, lane_idx, ztype="normal"):
        self.lane  = lane_idx
        self.ztype = ztype
        cfg        = ZOMBIE_TYPES[ztype]
        self.hp    = cfg["hp"]
        self.max_hp= cfg["hp"]
        self.speed = cfg["speed"]
        self.size  = cfg["size"]
        self.colour= cfg["colour"]
        self.score_val = cfg["score"]
        self.reward    = cfg["reward"]
        self.x     = WIDTH + self.size
        self.alive = True
        self.hit_flash = 0
        self.wobble = random.uniform(0, math.pi*2)

    def update(self):
        self.x -= self.speed
        self.wobble += 0.18
        if self.hit_flash > 0:
            self.hit_flash -= 1
        if self.x < BASE_X - self.size:
            self.alive = False
            return "breach"   # reached the base

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
        s   = self.size
        c   = C_ZOMBIE_HL if self.hit_flash > 0 else self.colour

        # body
        pygame.draw.rect(surf, c, (sx - s//2, cy - s//2 + bob, s, s), border_radius=4)
        # head
        pygame.draw.circle(surf, lerp_colour(c, C_WHITE, 0.25),
                           (sx, cy - s//2 - s//3 + bob), s//3)
        # eyes
        eye_y = cy - s//2 - s//3 + bob - 3
        pygame.draw.circle(surf, C_ZOMBIE_EYE, (sx-5, eye_y), 4)
        pygame.draw.circle(surf, C_ZOMBIE_EYE, (sx+5, eye_y), 4)
        pygame.draw.circle(surf, C_WHITE, (sx-5, eye_y), 2)
        pygame.draw.circle(surf, C_WHITE, (sx+5, eye_y), 2)
        # arms outstretched
        arm_y = cy + bob
        pygame.draw.line(surf, c, (sx-s//2, arm_y), (sx-s//2-14, arm_y-8), 4)
        pygame.draw.line(surf, c, (sx+s//2, arm_y), (sx+s//2+14, arm_y-8), 4)

        # HP bar (only if damaged)
        if self.hp < self.max_hp:
            bw = s + 8
            bh = 5
            bx = sx - bw//2
            by = cy - s//2 - s//2 - 12 + bob
            pygame.draw.rect(surf, C_HP_BAR_BG, (bx, by, bw, bh))
            fw = int(bw * self.hp / self.max_hp)
            pygame.draw.rect(surf, C_HP_BAR_FG, (bx, by, fw, bh))

        # label for tank
        if self.ztype == "tank":
            lbl = font_sm.render("TANK", True, C_WHITE)
            surf.blit(lbl, lbl.get_rect(centerx=sx, bottom=cy-s//2-s//2-14+bob))


# ─── PLAYER ───────────────────────────────────────────────────────────────────

class Player:
    def __init__(self):
        self.lane      = 0
        self.target_y  = lane_cy(0)
        self.y         = float(lane_cy(0))
        self.shoot_cd  = 0
        self.base_hp   = BASE_HP_MAX
        self.ammo      = -1         # -1 = infinite normal
        self.weapon    = "normal"   # normal | rapid | pierce
        self.weapon_timer = 0
        self.muzzle_flash = None

    def set_lane(self, idx):
        self.lane = idx
        self.target_y = lane_cy(idx)

    def update(self):
        # smooth slide between lanes
        self.y += (self.target_y - self.y) * 0.22
        if self.shoot_cd > 0:
            self.shoot_cd -= 1
        if self.weapon_timer > 0:
            self.weapon_timer -= 1
            if self.weapon_timer == 0:
                self.weapon = "normal"
        if self.muzzle_flash:
            self.muzzle_flash.update()
            if self.muzzle_flash.life <= 0:
                self.muzzle_flash = None

    def shoot(self):
        cd_map = {"normal": 18, "rapid": 7, "pierce": 22}
        if self.shoot_cd > 0:
            return None
        self.shoot_cd = cd_map.get(self.weapon, 18)
        cx = BASE_X + 28
        cy = int(self.y)
        self.muzzle_flash = MuzzleFlash(cx, cy)
        if self.weapon == "rapid":
            return Bullet(self.lane, speed=18, damage=1)
        elif self.weapon == "pierce":
            return Bullet(self.lane, speed=13, damage=99, pierce=True)
        else:
            return Bullet(self.lane, speed=14, damage=1)

    def draw(self, surf):
        cy = int(self.y)
        x  = BASE_X

        # base / bunker
        pygame.draw.rect(surf, C_BASE,    (x-28, cy-26, 56, 52), border_radius=6)
        pygame.draw.rect(surf, C_BASE_HL, (x-28, cy-26, 56,  8), border_radius=6)

        # cannon barrel
        barrel_col = C_MUZZLE if self.shoot_cd > 10 else C_BARREL
        pygame.draw.rect(surf, barrel_col, (x, cy-6, 32, 12), border_radius=3)

        # aperture ring
        pygame.draw.circle(surf, C_PLAYER_HL, (x, cy), 16)
        pygame.draw.circle(surf, C_PLAYER,    (x, cy), 12)
        pygame.draw.circle(surf, C_WHITE,     (x, cy),  5)

        # weapon icon
        if self.weapon == "rapid":
            icon = font_sm.render("⚡", True, (255,230,0))
            surf.blit(icon, icon.get_rect(center=(x, cy-36)))
        elif self.weapon == "pierce":
            icon = font_sm.render("★", True, (120,180,255))
            surf.blit(icon, icon.get_rect(center=(x, cy-36)))

        # muzzle flash
        if self.muzzle_flash:
            self.muzzle_flash.draw(surf)

        # lane highlight strip
        lh = LANE_HEIGHT
        hl_rect = pygame.Surface((8, lh), pygame.SRCALPHA)
        hl_rect.fill((0,200,255,30))
        surf.blit(hl_rect, (0, self.lane * lh))


# ─── POWERUP ──────────────────────────────────────────────────────────────────

POWERUP_TYPES = ["rapid", "pierce", "heal"]

class PowerUp:
    def __init__(self):
        self.kind  = random.choice(POWERUP_TYPES)
        self.lane  = random.randint(0, LANES-1)
        self.x     = WIDTH + 20
        self.alive = True
        self.pulse = 0
        colours = {"rapid":(255,220,0),"pierce":(100,160,255),"heal":(80,220,80)}
        self.colour = colours[self.kind]

    def update(self):
        self.x -= 1.5
        self.pulse += 0.1
        if self.x < BASE_X - 20:
            self.alive = False

    def draw(self, surf):
        cy = lane_cy(self.lane)
        r  = 16 + int(math.sin(self.pulse)*3)
        pygame.draw.circle(surf, self.colour,  (int(self.x), cy), r)
        pygame.draw.circle(surf, C_WHITE,      (int(self.x), cy), r-6, 2)
        labels = {"rapid":"⚡","pierce":"★","heal":"♥"}
        lbl = font_sm.render(labels[self.kind], True, C_BLACK)
        surf.blit(lbl, lbl.get_rect(center=(int(self.x), cy)))


# ─── WAVE MANAGER ─────────────────────────────────────────────────────────────

class WaveManager:
    def __init__(self):
        self.wave        = 1
        self.spawn_timer = 0
        self.in_break    = False
        self.break_timer = 0
        self.zombies_spawned = 0
        self.zombies_this_wave = self._wave_count()

    def _wave_count(self):
        return 5 + self.wave * 3

    def _spawn_interval(self):
        return max(25, 90 - self.wave * 5)

    def _zombie_type(self):
        roll = random.random()
        if self.wave >= 4 and roll < 0.20:
            return "tank"
        if self.wave >= 2 and roll < 0.35:
            return "fast"
        return "normal"

    def update(self, zombies):
        """Returns a new zombie if one should spawn, else None."""
        if self.in_break:
            self.break_timer -= 1
            if self.break_timer <= 0:
                self.in_break   = False
                self.wave       += 1
                self.zombies_spawned = 0
                self.zombies_this_wave = self._wave_count()
            return None

        self.spawn_timer += 1
        if (self.spawn_timer >= self._spawn_interval()
                and self.zombies_spawned < self.zombies_this_wave):
            self.spawn_timer = 0
            self.zombies_spawned += 1
            return Zombie(random.randint(0, LANES-1), self._zombie_type())

        # Wave clear?
        if (self.zombies_spawned >= self.zombies_this_wave
                and not zombies):
            self.in_break    = True
            self.break_timer = FPS * 4   # 4-second break
        return None

    def wave_progress(self):
        if self.zombies_this_wave == 0: return 1.0
        return self.zombies_spawned / self.zombies_this_wave


# ─── DRAW BACKGROUND ──────────────────────────────────────────────────────────

def draw_background(surf, wave):
    surf.fill(BG_DARK)
    for i in range(LANES):
        c = GRASS_DARK if i % 2 == 0 else GRASS_LIGHT
        pygame.draw.rect(surf, c, (0, i*LANE_HEIGHT, WIDTH, LANE_HEIGHT))

    # lane dividers
    for i in range(1, LANES):
        pygame.draw.line(surf, LANE_LINE, (0, i*LANE_HEIGHT), (WIDTH, i*LANE_HEIGHT), 2)

    # base wall
    pygame.draw.rect(surf, (60, 40, 20), (0, 0, BASE_X-28, HEIGHT))
    pygame.draw.rect(surf, (80, 55, 25), (BASE_X-30, 0, 4, HEIGHT))


# ─── HUD ──────────────────────────────────────────────────────────────────────

def draw_hud(surf, score, player, wave_mgr, particles):
    # top bar background
    pygame.draw.rect(surf, (10, 10, 30), (0, 0, WIDTH, 40))

    # score
    draw_text_shadow(surf, f"SCORE  {score:06d}", font_med, C_WHITE, 10, 6)

    # wave
    wave_txt = f"WAVE {wave_mgr.wave}"
    if wave_mgr.in_break:
        secs = math.ceil(wave_mgr.break_timer / FPS)
        wave_txt += f"  —  Next in {secs}s"
    draw_text_shadow(surf, wave_txt, font_med, (255,200,80), WIDTH//2, 6, "midtop")

    # base HP bar
    bw = 160
    bx = WIDTH - bw - 10
    by = 8
    pygame.draw.rect(surf, C_HP_BAR_BG, (bx, by, bw, 22), border_radius=4)
    frac = max(0, player.base_hp / BASE_HP_MAX)
    hpcol = lerp_colour((220,50,50),(50,220,80), frac)
    pygame.draw.rect(surf, hpcol, (bx, by, int(bw*frac), 22), border_radius=4)
    pygame.draw.rect(surf, C_WHITE, (bx, by, bw, 22), 2, border_radius=4)
    draw_text_shadow(surf, f"BASE HP  {player.base_hp}/{BASE_HP_MAX}",
                     font_sm, C_WHITE, bx + bw//2, by+2, "midtop")

    # weapon indicator
    if player.weapon != "normal":
        secs = math.ceil(player.weapon_timer / FPS)
        wcol = (255,220,0) if player.weapon=="rapid" else (100,160,255)
        draw_text_shadow(surf, f"{player.weapon.upper()}  {secs}s", font_sm, wcol, 10, HEIGHT-24)

    # lane keys hint (bottom)
    for i in range(LANES):
        cy = lane_cy(i)
        lbl = font_sm.render(f"[{i+1}]", True, (80,100,120) if i!=player.lane else (120,200,255))
        surf.blit(lbl, lbl.get_rect(midright=(BASE_X-32, cy)))


# ─── SCREENS ──────────────────────────────────────────────────────────────────

def screen_menu():
    while True:
        screen.fill(BG_DARK)
        for i in range(LANES):
            c = GRASS_DARK if i%2==0 else GRASS_LIGHT
            pygame.draw.rect(screen, c, (0, i*LANE_HEIGHT, WIDTH, LANE_HEIGHT))
        for i in range(1, LANES):
            pygame.draw.line(screen, LANE_LINE, (0,i*LANE_HEIGHT),(WIDTH,i*LANE_HEIGHT),2)

        draw_text_shadow(screen, "🧟 ZOMBIE LANE DEFENSE", font_big, (80,220,80),
                         WIDTH//2, 120, "midtop")
        draw_text_shadow(screen, "Defend your base from the undead horde!", font_sm, C_WHITE,
                         WIDTH//2, 185, "midtop")

        lines = [
            "[1–4]  Switch lane",
            "[SPACE] or hold  Fire",
            "Collect power-ups for special ammo",
            "Tanks need multiple hits!",
            "",
            "Press  ENTER  to start",
        ]
        for j, l in enumerate(lines):
            draw_text_shadow(screen, l, font_sm, (180,200,180), WIDTH//2, 230+j*28, "midtop")

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return


def screen_game_over(score, wave):
    while True:
        screen.fill(BG_DARK)
        draw_text_shadow(screen, "GAME OVER", font_big, (220,50,50), WIDTH//2, 160, "midtop")
        draw_text_shadow(screen, f"Score:  {score:06d}", font_med, C_WHITE, WIDTH//2, 240, "midtop")
        draw_text_shadow(screen, f"Waves survived:  {wave}", font_med, (255,200,80), WIDTH//2, 280, "midtop")
        draw_text_shadow(screen, "Press  ENTER  to play again   ESC  to quit",
                         font_sm, (160,180,160), WIDTH//2, 360, "midtop")
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN: return True
                if event.key == pygame.K_ESCAPE: return False


# ─── MAIN GAME LOOP ───────────────────────────────────────────────────────────

def run_game():
    player    = Player()
    bullets   : list[Bullet]   = []
    zombies   : list[Zombie]   = []
    particles : list[Particle] = []
    powerups  : list[PowerUp]  = []
    wave_mgr  = WaveManager()
    score     = 0
    powerup_timer = 0
    holding_fire  = False

    while True:
        clock.tick(FPS)

        # ── EVENTS ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: player.set_lane(0)
                if event.key == pygame.K_2: player.set_lane(1)
                if event.key == pygame.K_3: player.set_lane(2)
                if event.key == pygame.K_4: player.set_lane(3)
                if event.key == pygame.K_SPACE:
                    holding_fire = True
                if event.key == pygame.K_ESCAPE:
                    return score, wave_mgr.wave
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    holding_fire = False

        # held fire
        if holding_fire:
            b = player.shoot()
            if b: bullets.append(b)

        # ── UPDATE ────────────────────────────────────────────────────────────
        player.update()

        for b in bullets:  b.update()
        for p in particles: p.update()
        for pu in powerups: pu.update()

        new_z = wave_mgr.update([z for z in zombies if z.alive])
        if new_z:
            zombies.append(new_z)

        game_over = False
        for z in zombies:
            result = z.update()
            if result == "breach":
                player.base_hp -= 1
                # breach particles
                for _ in range(12):
                    particles.append(Particle(BASE_X, lane_cy(z.lane), (220,60,60)))
                if player.base_hp <= 0:
                    game_over = True

        # ── COLLISIONS ────────────────────────────────────────────────────────
        for b in bullets:
            if not b.alive: continue
            for z in zombies:
                if not z.alive: continue
                if b.lane == z.lane and abs(b.x - z.x) < z.size//2 + 8:
                    killed = z.take_damage(b.damage)
                    if not b.pierce:
                        b.alive = False
                    if killed:
                        score += z.score_val
                        for _ in range(20):
                            particles.append(Particle(z.x, lane_cy(z.lane),
                                                      random.choice(C_EXPLOSION)))
                    break

        # ── POWERUP COLLISION ─────────────────────────────────────────────────
        for pu in powerups:
            if not pu.alive: continue
            if pu.lane == player.lane and abs(pu.x - BASE_X) < 40:
                pu.alive = False
                if pu.kind == "heal":
                    player.base_hp = min(BASE_HP_MAX, player.base_hp + 2)
                else:
                    player.weapon = pu.kind
                    player.weapon_timer = FPS * 15
                score += 50

        # ── POWERUP SPAWN ─────────────────────────────────────────────────────
        powerup_timer += 1
        if powerup_timer > FPS * random.randint(12, 20):
            powerup_timer = 0
            powerups.append(PowerUp())

        # ── CLEANUP ───────────────────────────────────────────────────────────
        bullets   = [b for b in bullets   if b.alive]
        zombies   = [z for z in zombies   if z.alive]
        particles = [p for p in particles if p.life > 0]
        powerups  = [pu for pu in powerups if pu.alive]

        # ── DRAW ──────────────────────────────────────────────────────────────
        draw_background(screen, wave_mgr.wave)

        for pu in powerups:  pu.draw(screen)
        for p  in particles: p.draw(screen)
        for b  in bullets:   b.draw(screen)
        for z  in zombies:   z.draw(screen)
        player.draw(screen)
        draw_hud(screen, score, player, wave_mgr, particles)

        # "Next wave" banner
        if wave_mgr.in_break:
            secs = math.ceil(wave_mgr.break_timer / FPS)
            banner = font_big.render(f"Wave {wave_mgr.wave} cleared!  Next in {secs}s…", True, (255,220,80))
            screen.blit(banner, banner.get_rect(center=(WIDTH//2, HEIGHT//2)))

        pygame.display.flip()

        if game_over:
            return score, wave_mgr.wave


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def main():
    screen_menu()
    while True:
        score, wave = run_game()
        again = screen_game_over(score, wave)
        if not again:
            break
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()