"""Kinh tế: tài nguyên, hệ thống cấp của ô, chi phí tăng dần, sản xuất."""
from dark import TICK_MS
from map import neighbors, rect, TERRAIN_VI

RES_VI = {"wood": "Gỗ", "stone": "Đá", "mana": "Mana", "tech": "Tech"}
TECH_WIN = 60
TOWERS_WIN = 2
PER_TICK = TICK_MS / 60000   # sản lượng ghi theo PHÚT -> đổi ra lượng nhận mỗi nhịp


def L(name, prod=None, base=None, step=None, need=None, sprite=None, desc=""):
    """Một cấp của ô.
    prod : sản lượng mỗi phút, vd {"wood": 5}
    base : chi phí khi nâng lên cấp này LẦN ĐẦU
    step : mỗi lần nâng sau đó, chi phí cộng thêm bấy nhiêu (vd {"wood": 2})
    need : điều kiện kề bên: (các loại ô, cấp tối thiểu, chữ hiển thị) hoặc None
    sprite: tên hình trong BUILD_SPRITES vẽ đè lên ô (None = không vẽ)"""
    return {"name": name, "prod": prod or {}, "base": base or {}, "step": step or {},
            "need": need, "sprite": sprite, "desc": desc}


# ===== BẢNG SỐ LIỆU: sửa ở đây. Phần tử đầu tiên của mỗi danh sách là cấp 1 (miễn phí).
# Forest và Rocks lấy đúng theo bảng của bạn. Grass / Mushroom là SỐ TẠM, chưa có thiết kế.
CHAINS = {
    "forest": [
        L("Forest"),
        L("Forest", {"wood": 5}, {"wood": 3}, {"wood": 2}, sprite="Forest 2"),
        L("Forest", {"wood": 7}, {"wood": 5}, {"wood": 2}, sprite="Forest 3"),
        L("Forest", {"wood": 9}, {"wood": 7, "stone": 5}, {"wood": 2, "stone": 2},
          sprite="Forest 4"),
    ],
    "rock": [
        L("Rocks"),
        L("Rocks", {"stone": 3}, {"wood": 8}, {"wood": 2}, sprite="Rocks 2"),
        L("Rocks", {"stone": 5}, {"wood": 10, "stone": 3}, {"wood": 2, "stone": 2},
          sprite="Rocks 3"),
        L("Rocks", {"stone": 7}, {"wood": 12, "stone": 5, "tech": 2},
          {"wood": 2, "stone": 2, "tech": 1}, sprite="Rocks 4"),
    ],
    # --- số tạm ---
    "grass": [
        L("Field"),
        L("Workshop", {"tech": 2}, {"wood": 15, "stone": 5}, {"wood": 3, "stone": 1},
          need=(("forest", "rock"), 2, "Forest/Rocks cấp 2 trở lên"), sprite="Workshop"),
        L("Tower of Light", {}, {"wood": 30, "stone": 20, "tech": 10},
          {"wood": 10, "stone": 5, "tech": 2}, sprite="Tower of Light",
          desc="Soi sáng bán kính 2 ô, xua tan bóng tối"),
    ],
    "mushroom": [
        L("Mushroom Forest"),
        L("Market", {"tech": 2, "mana": 2}, {"wood": 20, "stone": 10},
          {"wood": 5, "stone": 2}, sprite="Market"),
    ],
    # --- chưa nâng cấp được ---
    "circle": [L("Stone Circle")],
    "water": [L("Water")],
}


# ---------- sprite công trình
# --- vẽ nhà: các hàm dùng chung -------------------------------------------------
def _roof(s, x, y, w, col, col_d, step=4, row=3):
    """Mái nhà bậc thang (hình tháp), rộng w, bắt đầu từ y. Trả về chiều cao mái."""
    n = max((w - 4) // (2 * step), 1)
    for i in range(n):
        inset = (n - 1 - i) * step
        rect(s, x + inset, y + i * row, w - 2 * inset, row, col)
    rect(s, x, y + (n - 1) * row + row - 1, w, 1, col_d)   # mép dưới mái
    return n * row


def _planks(s, x, y, w, h, wall, line):
    """Tường gỗ: nền + các đường ván dọc."""
    rect(s, x, y, w, h, wall)
    for px in range(x + 4, x + w - 1, 5):
        rect(s, px, y, 1, h, line)


def _bricks(s, x, y, w, h, wall, line):
    """Tường đá: nền + các hàng gạch so le."""
    rect(s, x, y, w, h, wall)
    for r, py in enumerate(range(y + 3, y + h, 4)):
        rect(s, x, py, w, 1, line)
        for px in range(x + 3 + (r % 2) * 3, x + w - 1, 6):
            rect(s, px, py - 3, 1, 3, line)


WOOD, WOOD_L, WOOD_D = "#a9743f", "#c18b52", "#6b4a2b"
ROOF_W, ROOF_WD = "#7a3f1d", "#4f2810"
STONE, STONE_L, STONE_D = "#cfcfcf", "#e6e6e6", "#9a9a9a"
ROOF_S, ROOF_SD = "#5f6368", "#3c3f43"
LEAF, LEAF_D = "#3f9a45", "#2f7d3a"
GLOW = "#ffe66d"


def _treehouse2():
    """Forest cấp 2: nhà cây nhỏ, một căn gỗ trên thân cây."""
    s = []
    rect(s, 22, 28, 10, 24, WOOD_D)                 # thân cây
    rect(s, 29, 28, 3, 24, "#4f361d")
    rect(s, 18, 48, 18, 4, WOOD_D)                  # rễ
    rect(s, 4, 24, 12, 9, LEAF)                      # tán lá hai bên
    rect(s, 38, 24, 12, 9, LEAF)
    rect(s, 4, 30, 12, 3, LEAF_D)
    rect(s, 38, 30, 12, 3, LEAF_D)
    rect(s, 12, 27, 30, 3, WOOD_D)                  # sàn
    _planks(s, 16, 17, 22, 10, WOOD, WOOD_D)        # căn nhà
    rect(s, 24, 19, 6, 8, "#3b2412")                # cửa
    rect(s, 18, 20, 4, 4, GLOW)                     # cửa sổ
    _roof(s, 13, 8, 28, ROOF_W, ROOF_WD)
    return s


def _treehouse3():
    """Forest cấp 3: nhà cây lớn hơn, hai tầng, có ống khói và thang."""
    s = []
    rect(s, 20, 38, 14, 14, WOOD_D)                 # thân cây
    rect(s, 31, 38, 3, 14, "#4f361d")
    rect(s, 16, 48, 22, 4, WOOD_D)
    rect(s, 2, 34, 12, 10, LEAF)
    rect(s, 40, 34, 12, 10, LEAF)
    rect(s, 2, 41, 12, 3, LEAF_D)
    rect(s, 40, 41, 12, 3, LEAF_D)
    rect(s, 40, 44, 2, 8, WOOD_D)                   # thang
    for ly in range(45, 52, 3):
        rect(s, 38, ly, 6, 1, WOOD_D)
    _planks(s, 8, 27, 38, 13, WOOD, WOOD_D)         # tầng dưới
    rect(s, 5, 24, 44, 4, ROOF_W)                   # mái hiên tầng dưới
    rect(s, 5, 27, 44, 1, ROOF_WD)
    rect(s, 24, 30, 7, 10, "#3b2412")               # cửa
    rect(s, 11, 31, 5, 5, GLOW)
    rect(s, 38, 31, 5, 5, GLOW)
    _planks(s, 15, 13, 24, 11, WOOD_L, WOOD_D)      # tầng trên
    rect(s, 24, 16, 6, 5, GLOW)
    rect(s, 33, 2, 4, 9, "#5a3a1a")                 # ống khói
    _roof(s, 12, 4, 30, ROOF_W, ROOF_WD)
    return s


def _treehouse4():
    """Forest cấp 4: toà nhà gỗ khổng lồ nhiều tầng, tháp giữa, cửa lớn sáng đèn."""
    s = []
    rect(s, 0, 20, 10, 12, LEAF)                    # tán lá hai bên
    rect(s, 44, 20, 10, 12, LEAF)
    rect(s, 0, 29, 10, 3, LEAF_D)
    rect(s, 44, 29, 10, 3, LEAF_D)
    rect(s, 0, 48, 54, 6, WOOD_D)                   # nền / rễ
    rect(s, 0, 48, 54, 1, "#4f361d")
    _planks(s, 3, 31, 48, 17, WOOD, WOOD_D)         # sảnh chính
    rect(s, 22, 35, 10, 13, "#3b2412")              # cổng lớn
    rect(s, 24, 33, 6, 3, "#3b2412")
    rect(s, 26, 38, 2, 10, GLOW)
    for wx in (7, 15, 36, 44):                      # cửa sổ sáng đèn
        rect(s, wx, 35, 4, 5, GLOW)
        rect(s, wx + 1, 35, 1, 5, WOOD_D)
    _roof(s, 0, 18, 54, ROOF_W, ROOF_WD, step=4, row=3)
    _planks(s, 19, 8, 16, 11, WOOD_L, WOOD_D)       # tháp giữa
    rect(s, 24, 10, 6, 6, GLOW)
    _roof(s, 16, 0, 22, ROOF_W, ROOF_WD, step=3, row=3)
    rect(s, 26, 16, 2, 3, WOOD_D)
    rect(s, 4, 14, 3, 6, "#5a3a1a")                 # ống khói hai bên
    rect(s, 47, 14, 3, 6, "#5a3a1a")
    return s


def _stonehouse2():
    """Rocks cấp 2: nhà đá nhỏ màu xám, mái đá phiến."""
    s = []
    rect(s, 12, 40, 30, 3, "#8c8c8c")               # móng
    _bricks(s, 14, 24, 26, 16, STONE, STONE_D)
    rect(s, 24, 30, 6, 10, "#3a3a3a")               # cửa
    rect(s, 17, 28, 4, 4, "#9fd3ff")                # cửa sổ
    rect(s, 33, 28, 4, 4, "#9fd3ff")
    rect(s, 34, 8, 5, 10, "#8a8a8a")                # ống khói
    _roof(s, 10, 13, 34, ROOF_S, ROOF_SD)
    return s


def _stonehouse3():
    """Rocks cấp 3: nhà đá lớn có tháp bên cạnh."""
    s = []
    rect(s, 2, 44, 50, 3, "#8c8c8c")
    _bricks(s, 4, 26, 30, 18, STONE, STONE_D)       # nhà chính
    rect(s, 16, 33, 7, 11, "#3a3a3a")
    rect(s, 7, 30, 5, 5, "#9fd3ff")
    rect(s, 26, 30, 5, 5, "#9fd3ff")
    _roof(s, 1, 14, 36, ROOF_S, ROOF_SD)
    _bricks(s, 36, 12, 14, 32, STONE_L, STONE_D)    # tháp
    rect(s, 40, 18, 6, 6, "#9fd3ff")
    rect(s, 40, 30, 6, 6, "#9fd3ff")
    _roof(s, 34, 4, 18, ROOF_S, ROOF_SD, step=3, row=3)
    return s


def _stonehouse4():
    """Rocks cấp 4: lâu đài đá khổng lồ, tường thành có răng cưa, bốn tháp và cờ."""
    s = []
    rect(s, 0, 48, 54, 4, "#8c8c8c")
    _bricks(s, 8, 28, 38, 20, STONE, STONE_D)       # tường thành
    for cx in range(8, 44, 8):                      # răng cưa tường thành
        rect(s, cx, 24, 5, 4, STONE)
        rect(s, cx, 27, 5, 1, STONE_D)
    _bricks(s, 17, 8, 20, 22, STONE_L, STONE_D)     # tháp chính
    for cx in (17, 24, 31):
        rect(s, cx, 4, 6, 4, STONE_L)
        rect(s, cx, 7, 6, 1, STONE_D)
    rect(s, 24, 12, 6, 8, "#9fd3ff")                # cửa sổ tháp chính
    rect(s, 25, 12, 1, 8, STONE_D)
    for tx in (0, 42):                              # hai tháp góc
        _bricks(s, tx, 16, 12, 32, STONE_L, STONE_D)
        rect(s, tx, 12, 4, 4, STONE_L)
        rect(s, tx + 8, 12, 4, 4, STONE_L)
        rect(s, tx + 4, 14, 4, 2, STONE_L)
        rect(s, tx + 4, 22, 4, 6, "#9fd3ff")
    rect(s, 22, 34, 10, 14, "#2f2f2f")              # cổng
    rect(s, 24, 32, 6, 3, "#2f2f2f")
    for gx in range(23, 31, 2):
        rect(s, gx, 36, 1, 12, "#6b6b6b")
    rect(s, 26, 0, 2, 5, "#5a3a1a")                 # cờ
    rect(s, 28, 0, 8, 4, "#c0392b")
    return s


def _workshop():
    s = []
    rect(s, 10, 24, 34, 24, "#d9a066")
    rect(s, 6, 14, 42, 12, "#c0392b")
    rect(s, 36, 6, 6, 10, "#7a7a7a")
    rect(s, 24, 34, 8, 14, "#4a2f18")
    rect(s, 14, 30, 6, 6, "#9fd3ff")
    return s


def _port():
    s = []
    rect(s, 14, 26, 26, 8, "#7a4a2a")
    rect(s, 25, 6, 12, 20, "#f5f5f5")
    rect(s, 24, 6, 2, 22, "#6b4a2b")
    rect(s, 6, 38, 42, 7, "#9a6b3a")
    rect(s, 8, 36, 4, 16, "#5a3a1a")
    rect(s, 42, 36, 4, 16, "#5a3a1a")
    return s


def _market():
    s = []
    for i in range(4):
        rect(s, 8 + i * 10, 14, 10, 10, "#e67e22" if i % 2 == 0 else "#f4d03f")
    rect(s, 10, 24, 34, 18, "#8a5a2e")
    rect(s, 14, 28, 8, 8, "#c9a063")
    rect(s, 28, 28, 10, 6, "#e74c3c")
    return s


def _tower():
    s = []
    rect(s, 10, 2, 34, 28, "#fff7c2")
    rect(s, 16, 10, 22, 12, "#ffe66d")
    rect(s, 14, 4, 26, 6, "#c0392b")
    rect(s, 18, 22, 18, 28, "#d8d2c4")
    rect(s, 18, 22, 4, 28, "#b9b2a2")
    rect(s, 24, 38, 6, 12, "#4a2f18")
    return s


BUILD_SPRITES = {"Forest 2": _treehouse2(), "Forest 3": _treehouse3(),
                 "Forest 4": _treehouse4(),
                 "Rocks 2": _stonehouse2(), "Rocks 3": _stonehouse3(),
                 "Rocks 4": _stonehouse4(),
                 "Workshop": _workshop(), "Port": _port(), "Market": _market(),
                 "Tower of Light": _tower()}


# ---------- luật kinh tế
# Trạng thái ván chơi:
#   tiles  = {(r, c): cấp}  chỉ lưu ô đã nâng (cấp >= 2); ô không có trong dict là cấp 1
#   counts = {(loại ô, cấp): số lần đã nâng lên cấp đó} -> làm giá tăng dần
#   carry  = phần lẻ tài nguyên chưa đủ 1 đơn vị (sản lượng/nhịp là số lẻ)
def new_resources():
    return {"wood": 10, "stone": 0, "mana": 0, "tech": 0}


def new_carry():
    return {k: 0.0 for k in RES_VI}


def cost_text(cost):
    return ", ".join(f"{v} {RES_VI[k]}" for k, v in cost.items())


def effect_text(lv):
    """Mô tả tác dụng của một cấp: sản lượng/phút hoặc mô tả riêng."""
    if lv["prod"]:
        return ", ".join(f"{v:g} {RES_VI[k]}/phút" for k, v in lv["prod"].items())
    return lv["desc"] or "chưa sản xuất"


def level_info(kind, lvl):
    return CHAINS[kind][lvl - 1]


def towers(terrain, tiles):
    return [p for p, lvl in tiles.items()
            if level_info(terrain[p], lvl)["name"] == "Tower of Light"]


def next_level(pos, terrain, tiles, counts):
    """(thông tin cấp kế tiếp, chi phí lần này) hoặc None nếu đã tối đa."""
    kind = terrain[pos]
    chain = CHAINS[kind]
    lvl = tiles.get(pos, 1)
    if lvl >= len(chain):
        return None
    nxt = chain[lvl]
    n = counts.get((kind, lvl + 1), 0)  # đã nâng bao nhiêu ô lên cấp này rồi
    cost = {}
    for k in RES_VI:
        v = nxt["base"].get(k, 0) + n * nxt["step"].get(k, 0)
        if v > 0:
            cost[k] = v
    return nxt, cost


def can_upgrade(pos, terrain, tiles, counts, dark_cells, res, over=False):
    if over:
        return False, "Game đã kết thúc"
    if pos in dark_cells:
        return False, "Ô này đã bị bóng tối nuốt"
    info = next_level(pos, terrain, tiles, counts)
    if info is None:
        if len(CHAINS[terrain[pos]]) > 1:
            return False, "Ô này đã ở cấp tối đa"
        return False, "Ô này không nâng cấp được"
    nxt, cost = info
    if nxt["need"]:
        kinds, min_lvl, text = nxt["need"]
        if not any(terrain[n] in kinds and tiles.get(n, 1) >= min_lvl
                   for n in neighbors(pos)):
            return False, f"Cần {text} kề bên"
    for k, v in cost.items():
        if res[k] < v:
            return False, f"Thiếu {RES_VI[k]} ({res[k]}/{v})"
    return True, ""


def upgrade(pos, terrain, tiles, counts, res):
    """Trừ tài nguyên và nâng ô lên 1 cấp (đã kiểm tra can_upgrade trước).
    Trả về (tên mới, cấp mới)."""
    nxt, cost = next_level(pos, terrain, tiles, counts)
    for k, v in cost.items():
        res[k] -= v
    kind = terrain[pos]
    lvl = tiles.get(pos, 1) + 1
    counts[(kind, lvl)] = counts.get((kind, lvl), 0) + 1
    tiles[pos] = lvl
    return nxt["name"], lvl


def describe(pos, terrain, tiles, counts, res):
    """Nội dung khung thông tin: (dòng hiện tại, tiêu đề cấp kế, dòng cấp kế, cảnh báo)."""
    kind = terrain[pos]
    chain = CHAINS[kind]
    lvl = tiles.get(pos, 1)
    cur = chain[lvl - 1]
    if len(chain) == 1:
        return [cur["name"], "Không nâng cấp được"], "", [], ""
    now = [f"{cur['name']} - cấp {lvl}/{len(chain)}", "Sản lượng: " + effect_text(cur)]
    info = next_level(pos, terrain, tiles, counts)
    if info is None:
        now.append("Đã đạt cấp tối đa")
        return now, "", [], ""
    nxt, cost = info
    ok, reason = can_upgrade(pos, terrain, tiles, counts, (), res)
    return (now, f"Nâng lên cấp {lvl + 1}: {nxt['name']}",
            [f"Chi phí: {cost_text(cost)}", "Sản lượng: " + effect_text(nxt)],
            "" if ok else reason)


def income(terrain, tiles, dark_cells):
    """Tài nguyên thu được mỗi PHÚT (hiện cạnh số trên HUD)."""
    inc = {k: 0 for k in RES_VI}
    for pos, lvl in tiles.items():
        if pos in dark_cells:
            continue
        for k, v in level_info(terrain[pos], lvl)["prod"].items():
            inc[k] += v
    return inc


def produce(terrain, tiles, dark_cells, res, carry):
    """Mỗi nhịp: cộng phần sản lượng của nhịp đó vào carry, đủ 1 đơn vị thì chuyển sang res."""
    for k, v in income(terrain, tiles, dark_cells).items():
        carry[k] += v * PER_TICK
        whole = int(carry[k] + 1e-9)
        if whole:
            res[k] += whole
            carry[k] -= whole


def check_win(terrain, tiles, res):
    """Trả về thông báo thắng hoặc None."""
    if len(towers(terrain, tiles)) >= TOWERS_WIN:
        return "CHIẾN THẮNG! Các Tower of Light đã soi sáng vùng đất."
    if res["tech"] >= TECH_WIN:
        return "CHIẾN THẮNG! Công nghệ đã đánh bại bóng tối."
    return None