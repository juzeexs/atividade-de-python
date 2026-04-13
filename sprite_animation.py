"""
sprite_animation.py
-------------------
Animação de sprite da 'Criatura das Sombras' usando Pygame.

Uso:
    python sprite_animation.py
"""

import sys
import math
import random
import os

# Tenta importar urllib para download automático da imagem
try:
    import urllib.request
except ImportError:
    pass  # Falharemos graciosamente se não tiver, pedindo download manual

import pygame

# ── Configuração ──────────────────────────────────────────────────────────────

WINDOW_W, WINDOW_H = 900, 420
FPS_CAP = 60

# Dimensões reais de cada frame no spritesheet
# Spritesheet: 1027x781 -> grade de 10 colunas x 10 linhas
SPRITE_W = 102
SPRITE_H = 78

# Mapeamento real das linhas e frames por animacao
ANIMATIONS = {
    "walk":   {"row": 0, "frames": 6,  "label": "WALK",    "move_speed": 2},
    "walk2":  {"row": 1, "frames": 6,  "label": "WALK 2",  "move_speed": 2},
    "run":    {"row": 2, "frames": 6,  "label": "RUN",     "move_speed": 4},
    "fly":    {"row": 3, "frames": 8,  "label": "FLY",     "move_speed": 3},
    "fly2":   {"row": 4, "frames": 10, "label": "FLY 2",   "move_speed": 3},
    "attack": {"row": 5, "frames": 5,  "label": "ATTACK",  "move_speed": 0},
    "rock":   {"row": 6, "frames": 6,  "label": "ROCK",    "move_speed": 0},
    "idle":   {"row": 7, "frames": 6,  "label": "IDLE",    "move_speed": 0},
    "run2":   {"row": 8, "frames": 10, "label": "RUN 2",   "move_speed": 4},
    "die":    {"row": 9, "frames": 8,  "label": "DIE",     "move_speed": 0},
}

ANIM_ORDER = ["walk", "walk2", "run", "fly", "fly2", "attack", "rock", "idle", "run2", "die"]

COLORS = {
    "bg":          (13,  13,  15),
    "ground":      (20,  20,  25),
    "ground_line": (35,  35,  45),
    "accent":      (200, 255,  0),
    "ui_text":     (70,  70,  85),
    "ui_hi":       (200, 255,  0),
    "help":        (40,  40,  52),
    "trees":       (28,  28,  36),
}

# URL da imagem fornecida no prompt
IMAGE_URL = "https://z-cdn-media.chatglm.cn/files/4e7f6c62-fb2d-4baa-958f-c3ec1eb0bd52.png?auth_key=1876109584-50568edfaa3b4a59936ba721638370d9-0-47baca6097ab2b4fb504bbb6a8cf7b86"
DEFAULT_FILENAME = "spritesheet.png"

# ── Utilitarios ──────────────────────────────────────────────────────────────

def slice_frames(sheet, row, n_frames, fw, fh):
    """Recorta n_frames frames horizontais de uma linha do spritesheet."""
    frames = []
    for col in range(n_frames):
        x = col * fw
        y = row * fh
        # Verificação de segurança para não sair da imagem
        if y + fh > sheet.get_height() or x + fw > sheet.get_width():
            break
        frames.append(sheet.subsurface(pygame.Rect(x, y, fw, fh)).copy())
    return frames

def scale_surf(surf, factor):
    w = max(1, int(surf.get_width() * factor))
    h = max(1, int(surf.get_height() * factor))
    return pygame.transform.scale(surf, (w, h))

def download_image(url, filename):
    print(f"Baixando imagem de {url}...")
    try:
        urllib.request.urlretrieve(url, filename)
        print("Download concluído!")
        return True
    except Exception as e:
        print(f"Erro no download: {e}")
        return False

# ── Particulas ────────────────────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y):
        self.x = x + random.randint(-8, 8)
        self.y = float(y)
        self.vy = -0.5 - random.random() * 0.8
        self.life = 1.0

    def update(self):
        self.y += self.vy
        self.life -= 0.04

    def draw(self, surf):
        if self.life <= 0:
            return
        alpha = int(self.life * 180)
        s = pygame.Surface((4, 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*COLORS["accent"], alpha), (2, 2), 2)
        surf.blit(s, (int(self.x - 2), int(self.y - 2)))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    sheet_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILENAME

    # Verifica se o arquivo existe, tenta baixar se não existir
    if not os.path.exists(sheet_path):
        if 'urllib.request' in sys.modules:
            if not download_image(IMAGE_URL, sheet_path):
                print(f"\n[ERRO] Não foi possível baixar a imagem automaticamente.")
                print(f"Por favor, baixe manualmente e salve como '{sheet_path}'")
                return
        else:
            print(f"\n[ERRO] Arquivo '{sheet_path}' não encontrado.")
            print("Por favor, coloque a imagem na mesma pasta do script.")
            return

    pygame.init()
    pygame.display.set_caption("Criatura das Sombras — Sprite Animation")
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock = pygame.time.Clock()

    font_sm = pygame.font.SysFont("monospace", 12, bold=True)
    font_lg = pygame.font.SysFont("monospace", 18, bold=True)

    # Carrega spritesheet
    try:
        raw_sheet = pygame.image.load(sheet_path).convert_alpha()
        print(f"[OK] Spritesheet: {raw_sheet.get_size()}")
    except pygame.error as e:
        print(f"\n[ERRO] Não foi possivel carregar '{sheet_path}': {e}")
        return

    # Pre-processa frames
    all_frames = {}
    for name, cfg in ANIMATIONS.items():
        frames = slice_frames(raw_sheet, cfg["row"], cfg["frames"], SPRITE_W, SPRITE_H)
        all_frames[name] = frames
        print(f"  {name:8s}: {len(frames)} frames (row {cfg['row']})")

    # Estado
    current_anim = "walk"
    frame_idx    = 0
    anim_fps     = 8
    scale        = 3.0
    auto_move    = True
    pos_x        = float(WINDOW_W // 2 - int(SPRITE_W * scale) // 2)
    direction    = 1
    particles    = []
    frame_timer  = 0.0
    frame_period = 1.0 / anim_fps

    GROUND_Y = WINDOW_H - 80

    random.seed(42)
    trees = [
        (random.randint(0, WINDOW_W), random.randint(20, 80), random.randint(2, 5))
        for _ in range(30)
    ]

    running = True

    while running:
        dt = clock.tick(FPS_CAP) / 1000.0
        fps_real = clock.get_fps()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Teclas 1-9 e 0 para trocar animacao
                for i, name in enumerate(ANIM_ORDER):
                    key = pygame.K_0 if i == 9 else getattr(pygame, f"K_{i+1}", None)
                    if key and event.key == key:
                        current_anim = name
                        frame_idx = 0

                if event.key == pygame.K_a:
                    auto_move = not auto_move

                if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    anim_fps = min(24, anim_fps + 1)
                    frame_period = 1.0 / anim_fps
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    anim_fps = max(1, anim_fps - 1)
                    frame_period = 1.0 / anim_fps
                if event.key == pygame.K_s:
                    scale = min(5.0, scale + 0.5)
                if event.key == pygame.K_d:
                    scale = max(1.0, scale - 0.5)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_RIGHT]:
            pos_x += 3; direction = 1
        if keys[pygame.K_LEFT]:
            pos_x -= 3; direction = -1

        # Avanca frame
        frame_timer += dt
        if frame_timer >= frame_period:
            frame_timer -= frame_period
            anim_cfg = ANIMATIONS[current_anim]
            frame_idx = (frame_idx + 1) % anim_cfg["frames"]

            if current_anim in ("walk", "walk2", "run", "run2") and frame_idx % 2 == 0:
                spr_w = int(SPRITE_W * scale)
                particles.append(Particle(pos_x + spr_w // 2, GROUND_Y + 5))

        # Auto-movimento
        anim_cfg = ANIMATIONS[current_anim]
        if auto_move and anim_cfg["move_speed"] > 0:
            pos_x += direction * anim_cfg["move_speed"]
            spr_w = int(SPRITE_W * scale)
            if pos_x + spr_w > WINDOW_W:
                direction = -1; pos_x = float(WINDOW_W - spr_w)
            if pos_x < 0:
                direction = 1; pos_x = 0.0

        pos_x = max(0.0, min(float(WINDOW_W), pos_x))

        # Flutuacao vertical no voo
        t = pygame.time.get_ticks() / 1000.0
        fly_offset = int(math.sin(t * 2.5) * 18) if current_anim in ("fly", "fly2") else 0

        spr_w = int(SPRITE_W * scale)
        spr_h = int(SPRITE_H * scale)
        draw_y = GROUND_Y - spr_h - fly_offset

        for p in particles:
            p.update()
        particles = [p for p in particles if p.life > 0]

        # ── Render ──────────────────────────────────────────────

        screen.fill(COLORS["bg"])

        # Arvores (paralaxe)
        parallax = pos_x * 0.08
        for tx, th, tw in trees:
            x = int((tx - parallax) % WINDOW_W)
            pygame.draw.rect(screen, COLORS["trees"], (x, GROUND_Y - th, tw, th))

        # Chao
        pygame.draw.rect(screen, COLORS["ground"], (0, GROUND_Y, WINDOW_W, 80))
        pygame.draw.line(screen, (42, 42, 52), (0, GROUND_Y), (WINDOW_W, GROUND_Y), 2)
        for i in range(0, WINDOW_W, 80):
            pygame.draw.line(screen, COLORS["ground_line"], (i, GROUND_Y), (i, WINDOW_H))

        # Sombra do sprite
        shadow_alpha = max(20, 90 - fly_offset * 2)
        sh = pygame.Surface((spr_w, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (*COLORS["accent"], shadow_alpha), (0, 0, spr_w, 14))
        screen.blit(sh, (int(pos_x), GROUND_Y + 3))

        for p in particles:
            p.draw(screen)

        # Sprite
        frames = all_frames[current_anim]
        if frames and frame_idx < len(frames):
            scaled = scale_surf(frames[frame_idx], scale)
            if direction == -1:
                scaled = pygame.transform.flip(scaled, True, False)
            screen.blit(scaled, (int(pos_x), draw_y))

        # Scanlines
        sl = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        for sy in range(0, WINDOW_H, 4):
            pygame.draw.line(sl, (0, 0, 0, 28), (0, sy), (WINDOW_W, sy))
        screen.blit(sl, (0, 0))

        # HUD
        hud = [
            ("ANIMACAO", ANIMATIONS[current_anim]["label"]),
            ("FRAME",    f"{frame_idx+1}/{ANIMATIONS[current_anim]['frames']}"),
            ("SPR FPS",  str(anim_fps)),
            ("FPS",      f"{fps_real:.0f}"),
            ("ESCALA",   f"{scale:.1f}x"),
            ("AUTO-MOV", "ON" if auto_move else "OFF"),
            ("POS X",    str(int(pos_x))),
        ]
        hx, hy = 12, 12
        for lbl, val in hud:
            s1 = font_sm.render(lbl + ":", True, COLORS["ui_text"])
            s2 = font_sm.render(val, True, COLORS["ui_hi"])
            screen.blit(s1, (hx, hy))
            screen.blit(s2, (hx + s1.get_width() + 4, hy))
            hy += 20

        help_lines = [
            "1-9/0 : animacao",
            "+/-   : vel. frames",
            "S/D   : escala",
            "<- -> : mover",
            "A     : auto-mover",
            "ESC   : sair",
        ]
        hx2, hy2 = WINDOW_W - 170, 12
        for line in help_lines:
            screen.blit(font_sm.render(line, True, COLORS["help"]), (hx2, hy2))
            hy2 += 18

        title = font_lg.render("CRIATURA DAS SOMBRAS", True, COLORS["accent"])
        screen.blit(title, (WINDOW_W // 2 - title.get_width() // 2, 10))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()