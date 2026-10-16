"""Bản đồ: hằng số lưới, địa hình, sprite địa hình, sinh bản đồ ngẫu nhiên."""
import random

COLS = ROWS = 12
SIZE = 54   # kích thước ô khi thiết kế sprite (toạ độ pixel-art dựa trên số này)
CELL = 44   # kích thước ô hiển thị trên màn hình: nhỏ hơn SIZE -> cửa sổ gọn hơn

GRASS, SPECK, TUFT = "#b6e6a1", "#a2d78c", "#8fcf79"
WATER, WAVE_D, WAVE_L = "#bfdcf0", "#a6c9e4", "#dcedf8"
SAND, SAND_D = "#ecd9b0", "#e0c996"

TERRAIN_VI = {"grass": "cỏ", "forest": "rừng", "rock": "đá",
              "mushroom": "rừng nấm", "circle": "vòng đá", "water": "nước"}

# Số ô mỗi loại địa hình (random trong khoảng). Cỏ = phần còn lại.
FOREST_RANGE = (30, 35)
ROCK_RANGE = (12, 15)
WATER_RANGE = (30, 35)
MUSHROOM_COUNT = 4

# Vòng đá nằm giữa bản đồ (lưới chẵn nên lấy ô giữa-dưới-phải)
CENTER = (ROWS // 2, COLS // 2)


# ---------- sprite
def rect(s, x, y, w, h, col):
    s.append((x, y, w, h, col))


def tree(s, x, y):
    """Cây thông nhỏ: tán nhiều tầng, thân nâu, bóng mờ dưới gốc."""
    rect(s, x + 2, y + 17, 6, 1, TUFT)            # bóng dưới gốc
    rect(s, x + 4, y + 12, 2, 6, "#6b4a2b")       # thân
    rect(s, x + 4, y, 2, 2, "#3f9a45")            # đỉnh
    rect(s, x + 3, y + 2, 4, 3, "#2f7d3a")
    rect(s, x + 1, y + 4, 8, 4, "#2f7d3a")
    rect(s, x, y + 7, 10, 5, "#276b31")
    rect(s, x + 3, y + 2, 2, 2, "#58b85a")        # điểm sáng
    rect(s, x + 2, y + 5, 2, 2, "#4fa650")


def boulder(s, x, y, w, h):
    """Tảng đá nhiều mặt: sáng ở góc trên-trái, tối ở đáy, có vết nứt."""
    rect(s, x + 2, y, w - 4, h, "#6f6f6f")
    rect(s, x, y + 3, w, h - 6, "#6f6f6f")
    rect(s, x + 3, y + 1, max(w - 8, 3), 3, "#a8a8a8")   # mặt sáng
    rect(s, x + 1, y + 4, 3, 4, "#8e8e8e")
    rect(s, x + 2, y + h - 4, w - 4, 4, "#4f4f4f")       # mặt tối
    rect(s, x, y + h - 6, 2, 3, "#4f4f4f")
    rect(s, x + w // 2, y + 5, 2, 4, "#555555")          # vết nứt


CREAM, CREAM_D, CREAM_EDGE = "#fff8e1", "#d9c48f", "#bfa56c"
# màu mũ nấm: (màu chính, vùng sáng, vùng tối)
CAP_RED = ("#c0392b", "#e8604c", "#8e2a20")
CAP_BROWN = ("#8a5a2e", "#b07a45", "#5e3d1e")
CAP_PURPLE = ("#7a4aa0", "#a06fc8", "#523070")


def mushroom(s, cx, base, cap_w, cap_h, stem_w, stem_h, colors):
    """Một cây nấm: thân kem có chân loe, mũ vòm có điểm sáng, mép tối và đốm trắng.
    cx = tâm ngang, base = y của gốc nấm."""
    cap, light, dark = colors
    rect(s, cx - stem_w // 2 - 3, base, stem_w + 6, 2, SAND_D)           # bóng dưới gốc
    rect(s, cx - stem_w // 2, base - stem_h, stem_w, stem_h, CREAM)      # thân
    rect(s, cx + stem_w // 2 - 2, base - stem_h, 2, stem_h, CREAM_D)     # mặt tối của thân
    rect(s, cx - stem_w // 2, base - stem_h, 1, stem_h, CREAM_EDGE)      # viền trái của thân
    rect(s, cx - stem_w // 2 - 1, base - 3, stem_w + 2, 3, CREAM)        # chân loe
    rect(s, cx - stem_w // 2 - 1, base - 3, 1, 3, CREAM_EDGE)
    rect(s, cx + stem_w // 2 - 2, base - 3, 3, 3, CREAM_D)
    y0 = base - stem_h - cap_h + 3                                        # mũ chồm lên thân 3px
    x0 = cx - cap_w // 2
    rect(s, x0 + 4, y0, cap_w - 8, 3, cap)                                # mũ vòm 3 tầng
    rect(s, x0 + 2, y0 + 3, cap_w - 4, 3, cap)
    rect(s, x0, y0 + 6, cap_w, cap_h - 6, cap)
    rect(s, x0, y0 + cap_h - 3, cap_w, 3, dark)                           # mép dưới tối
    rect(s, x0 + 5, y0 + 1, max(cap_w // 4, 3), 2, light)                 # điểm sáng
    rect(s, x0 + 2, y0 + 4, 2, 3, light)
    rect(s, cx - cap_w // 4 - 1, y0 + 5, 3, 3, "#f5f5f5")                # đốm trắng
    rect(s, cx + cap_w // 6, y0 + 7, 3, 3, "#f5f5f5")
    if cap_w >= 20:
        rect(s, cx - 1, y0 + 2, 3, 2, "#f5f5f5")
        rect(s, cx + cap_w // 3 - 1, y0 + 4, 2, 2, "#f5f5f5")


def pebble(s, x, y):
    rect(s, x, y + 3, 8, 6, "#4a4a4a")
    rect(s, x + 2, y, 5, 4, "#6f6f6f")
    rect(s, x + 1, y + 7, 7, 2, "#2f2f2f")


def wave(s, x, y, col):
    """Sóng nước hình bậc thang: ~"""
    rect(s, x, y + 2, 4, 2, col)
    rect(s, x + 4, y, 6, 2, col)
    rect(s, x + 10, y + 2, 4, 2, col)


def make_sprite(kind, rng):
    s = []
    if kind == "water":
        rect(s, 0, 0, SIZE, SIZE, WATER)
        for _ in range(5):
            wave(s, rng.randrange(2, SIZE - 16, 2), rng.randrange(4, SIZE - 8, 2),
                 rng.choice([WAVE_D, WAVE_L]))
        return s
    on_sand = kind in ("mushroom", "circle")
    rect(s, 0, 0, SIZE, SIZE, SAND if on_sand else GRASS)
    # hạt nền: cỏ có chấm xanh sẫm, cát có hạt cát sẫm
    for _ in range(8):
        rect(s, rng.randrange(0, SIZE - 2, 2), rng.randrange(0, SIZE - 2, 2),
             2, 2, SAND_D if on_sand else SPECK)
    if kind == "grass":
        for _ in range(3):  # cụm cỏ nhỏ
            x, y = rng.randrange(2, SIZE - 8, 2), rng.randrange(6, SIZE - 8, 2)
            rect(s, x, y + 2, 2, 4, TUFT)
            rect(s, x + 3, y, 2, 6, TUFT)
            rect(s, x + 6, y + 3, 2, 3, TUFT)
        if rng.random() < 0.25:  # thỉnh thoảng có hoa
            x, y = rng.randrange(4, SIZE - 8, 2), rng.randrange(4, SIZE - 8, 2)
            rect(s, x, y + 2, 6, 2, rng.choice(["#ffffff", "#ffe27a", "#f4a6b8"]))
            rect(s, x + 2, y, 2, 6, s[-1][4])
            rect(s, x + 2, y + 2, 2, 2, "#e8a33d")
    elif kind == "forest":
        # rừng dày: lưới cây nhỏ phủ kín ô, hàng lẻ lệch nửa cây
        for row in range(3):
            n, x0 = (5, 2) if row % 2 == 0 else (4, 7)
            for i in range(n):
                tree(s, x0 + i * 10 + rng.randint(-1, 1), row * 18 + rng.randint(-1, 0))
    elif kind == "rock":
        boulder(s, 14, 6, 18, 16)
        boulder(s, 26, 14, 20, 20)
        boulder(s, 6 + rng.randint(0, 2), 24, 22, 18)
    elif kind == "mushroom":
        # rừng nấm: 2 cây thấp hai bên, 1 cây cao ở giữa (vẽ cây cao sau cùng)
        mushroom(s, 11, 46, 16, 11, 6, 13, CAP_BROWN)
        mushroom(s, 43, 46, 16, 11, 6, 13, CAP_PURPLE)
        mushroom(s, 27, 48, 24, 16, 8, 24, CAP_RED)
    elif kind == "circle":
        # vòng đá: 8 viên đá xếp thành vòng tròn quanh một viên ở giữa
        for x, y in ((23, 5), (38, 10), (43, 23), (38, 37),
                     (23, 42), (8, 37), (3, 23), (8, 10)):
            pebble(s, x, y)
        pebble(s, 23, 23)
    return s


# ---------- sinh bản đồ
def neighbors(pos):
    r, c = pos
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < ROWS and 0 <= nc < COLS:
            yield (nr, nc)


def _fill(terrain, kind, target, blob, blocked=()):
    """Phủ đúng `target` ô loại `kind` lên các ô cỏ, theo từng mảng liền nhau
    có kích thước trong khoảng `blob`. Trả về số ô đã đặt."""
    placed = 0
    while placed < target:
        free = [p for p, t in terrain.items() if t == "grass" and p not in blocked]
        if not free:
            break
        p = random.choice(free)
        terrain[p] = kind
        cells, placed = [p], placed + 1
        size = min(random.randint(*blob), target - placed + 1) - 1
        while size > 0:
            frontier = [q for c in cells for q in neighbors(c)
                        if terrain[q] == "grass" and q not in blocked]
            if not frontier:
                break
            q = random.choice(frontier)
            terrain[q] = kind
            cells.append(q)
            placed += 1
            size -= 1
    return placed


def _spread(cells, k, min_dist):
    """Chọn k ô cách nhau ít nhất min_dist (giảm dần nếu không đủ chỗ)."""
    for d in range(min_dist, 0, -1):
        random.shuffle(cells)
        chosen = []
        for p in cells:
            if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) >= d for q in chosen):
                chosen.append(p)
            if len(chosen) == k:
                return chosen
    return cells[:k]


def _circle_pos(exact_center):
    """Ván đầu: đúng giữa bản đồ. Regenerate: ngẫu nhiên quanh trung tâm."""
    if exact_center:
        return CENTER
    return (random.randint(ROWS // 2 - 2, ROWS // 2 + 1),
            random.randint(COLS // 2 - 2, COLS // 2 + 1))


def generate_map(exact_center=False):
    """Trả về (terrain, sprites). terrain: {(r, c): loại ô}.
    Số ô: rừng 30-35, đá 12-15, nước 30-35, rừng nấm 4, vòng đá 1, còn lại là cỏ."""
    terrain = {(r, c): "grass" for r in range(ROWS) for c in range(COLS)}

    cp = _circle_pos(exact_center)
    terrain[cp] = "circle"
    near_circle = set(neighbors(cp))  # giữ cỏ quanh vòng đá để không bị nước chặn

    _fill(terrain, "water", random.randint(*WATER_RANGE), (6, 14), near_circle)
    _fill(terrain, "forest", random.randint(*FOREST_RANGE), (4, 10))
    _fill(terrain, "rock", random.randint(*ROCK_RANGE), (1, 3))

    # rừng nấm: lấy từ ô cỏ, cách nhau xa và không sát vòng đá
    grass = [p for p, t in terrain.items()
             if t == "grass" and abs(p[0] - cp[0]) + abs(p[1] - cp[1]) >= 2]
    for p in _spread(grass, MUSHROOM_COUNT, 5):
        terrain[p] = "mushroom"

    rng = random.Random()
    sprites = {p: make_sprite(t, rng) for p, t in terrain.items()}
    return terrain, sprites