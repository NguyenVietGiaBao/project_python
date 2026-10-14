"""Bản đồ: hằng số lưới, địa hình, sprite địa hình, sinh bản đồ ngẫu nhiên."""
import random

COLS = ROWS = 12
SIZE = 54

GRASS, SPECK = "#b6e6a1", "#a2d78c"
WATER, WAVE_D, WAVE_L = "#bfdcf0", "#a6c9e4", "#dcedf8"
SAND = "#ecd9b0"

TERRAIN_VI = {"grass": "cỏ", "forest": "rừng", "rock": "đá",
              "village": "làng", "water": "nước"}


def rect(s, x, y, w, h, col):
    s.append((x, y, w, h, col))


def boulder(s, x, y, w, h):
    rect(s, x, y, w, h, "#6f6f6f")
    rect(s, x + 2, y, w - 4, 4, "#9a9a9a")
    rect(s, x, y + h - 3, w, 3, "#4f4f4f")


def tree(s, x, y):
    rect(s, x + 4, y + 12, 2, 6, "#6b4a2b")
    rect(s, x + 1, y + 2, 8, 11, "#2f7d3a")
    rect(s, x, y + 5, 10, 5, "#2f7d3a")
    rect(s, x + 1, y + 2, 8, 2, "#4fa650")


def make_sprite(kind, rng):
    s = []
    if kind == "water":
        rect(s, 0, 0, SIZE, SIZE, WATER)
        for _ in range(4):
            rect(s, rng.randrange(2, SIZE - 14, 2), rng.randrange(4, SIZE - 4, 2),
                 10, 2, rng.choice([WAVE_D, WAVE_L]))
        return s
    rect(s, 0, 0, SIZE, SIZE, SAND if kind == "village" else GRASS)
    if kind != "village":
        for _ in range(8):
            rect(s, rng.randrange(0, SIZE - 2, 2), rng.randrange(0, SIZE - 2, 2),
                 2, 2, SPECK)
    if kind == "forest":
        # rừng dày: lưới cây nhỏ phủ kín ô, hàng lẻ lệch nửa cây
        for row in range(3):
            n, x0 = (5, 2) if row % 2 == 0 else (4, 7)
            for i in range(n):
                tree(s, x0 + i * 10 + rng.randint(-1, 1), row * 18 + rng.randint(-1, 0))
    elif kind == "rock":
        boulder(s, 14, 6, 18, 16)
        boulder(s, 26, 14, 20, 20)
        boulder(s, 6 + rng.randint(0, 2), 24, 22, 18)
    elif kind == "village":
        # 3 nhà nhỏ: mái đỏ, mái nâu, mái tím như trong game gốc
        for (x, y), roof in zip(((6, 8), (30, 10), (16, 30)),
                                ("#c0392b", "#8a5a2e", "#7a4aa0")):
            rect(s, x, y + 8, 14, 12, "#9b7a52")
            rect(s, x + 5, y + 13, 4, 7, "#3b2a1a")
            rect(s, x - 2, y, 18, 9, roof)
            rect(s, x - 2, y, 18, 2, "#e9d8b0")
    return s


def neighbors(pos):
    r, c = pos
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < ROWS and 0 <= nc < COLS:
            yield (nr, nc)


def _blob(terrain, kind, count, size):
    for _ in range(count):
        p = (random.randrange(ROWS), random.randrange(COLS))
        if terrain[p] != "grass":
            continue
        terrain[p] = kind
        cells, n, tries = [p], random.randint(*size) - 1, 0
        while n > 0 and tries < 200:
            tries += 1
            q = random.choice(list(neighbors(random.choice(cells))))
            if terrain[q] == "grass":
                terrain[q] = kind
                cells.append(q)
                n -= 1


def generate_map():
    """Trả về (terrain, sprites). terrain: {(r, c): loại ô}."""
    terrain = {}
    for _ in range(60):
        terrain = {(r, c): "grass" for r in range(ROWS) for c in range(COLS)}
        _blob(terrain, "water", 6, (8, 16))
        _blob(terrain, "forest", 9, (5, 12))
        _blob(terrain, "rock", 14, (1, 3))
        v = list(terrain.values())
        if (v.count("forest") >= 14 and v.count("rock") >= 10
                and v.count("water") >= 25 and v.count("grass") >= 50):
            break
    grass = [p for p, t in terrain.items() if t == "grass"]
    random.shuffle(grass)
    chosen = []
    for p in grass:
        if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) >= 5 for q in chosen):
            chosen.append(p)
        if len(chosen) == 4:
            break
    for p in chosen:
        terrain[p] = "village"
    rng = random.Random()
    sprites = {p: make_sprite(t, rng) for p, t in terrain.items()}
    return terrain, sprites