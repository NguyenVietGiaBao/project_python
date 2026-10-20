"""Kinh tế: tài nguyên, hệ thống cấp của ô, chi phí tăng dần, sản xuất."""
from dark import TICK_MS
from map import neighbors, rect, TERRAIN_VI

RES_VI = {"wood": "Gỗ", "stone": "Đá", "mana": "Mana", "tech": "Tech"}
CIRCLE_COST = {"mana": 100, "stone": 100}   # chi phí kích hoạt vòng đá = điều kiện thắng duy nhất
PER_TICK = TICK_MS / 60000   # sản lượng ghi theo PHÚT -> đổi ra lượng nhận mỗi nhịp


def L(name, prod=None, base=None, step=None, need=None, sprite=None, desc="", boost=None):
    """Một cấp của ô.
    prod : sản lượng mỗi phút, vd {"wood": 5}
    base : chi phí khi nâng lên cấp này LẦN ĐẦU
    step : mỗi lần nâng sau đó, chi phí cộng thêm bấy nhiêu (vd {"wood": 2})
    need : điều kiện kề bên: (các loại ô, cấp tối thiểu, chữ hiển thị) hoặc None
    sprite: tên hình trong BUILD_SPRITES vẽ đè lên ô (None = không vẽ)
    boost: tăng sản lượng cho các ô KỀ BÊN, vd {"wood": 0.25, "stone": 0.25} = +25% gỗ, +25% đá"""
    return {"name": name, "prod": prod or {}, "base": base or {}, "step": step or {},
            "need": need, "sprite": sprite, "desc": desc, "boost": boost or {}}


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
        L("Workshop", {"tech": 2}, {"wood": 5}, {},
          need=(("forest", "rock"), 2, "Forest/Rocks cấp 2 trở lên"), sprite="Workshop",
          boost={"wood": 0.25, "stone": 0.25}),
        L("Workshop", {"tech": 2}, {"wood": 10, "stone": 4}, {}, sprite="Workshop 2",
          boost={"wood": 0.5, "stone": 0.5}),
    ],
    # --- ô cỏ nằm KỀ rừng nấm: tự động dùng chuỗi này thay cho "grass" (xem chain_at) ---
    "grass_magic": [
        L("Field"),
        L("Magic Workshop", {"mana": 2}, {"wood": 6, "mana": 1}, {},
          need=(("mushroom",), 2, "Market (nâng rừng nấm lên cấp 2)"), sprite="Magic Workshop",
          boost={"wood": 0.25, "mana": 0.25}),
        L("Magic Workshop", {"mana": 2}, {"wood": 15, "stone": 3, "mana": 5}, {},
          sprite="Magic Workshop 2", boost={"wood": 0.5, "mana": 0.5}),
    ],
    "mushroom": [
        L("Mushroom Forest"),
        L("Market", {"tech": 2, "mana": 2}, {"wood": 10}, {}, sprite="Market"),
        L("Market", {"tech": 2, "mana": 4}, {"wood": 15, "stone": 3, "mana": 5}, {},
          sprite="Market 2"),
    ],
    # --- vòng đá giữa bản đồ: nâng lên cấp 2 là THẮNG ---
    "circle": [
        L("Stone Circle", desc="Nâng cấp để kích hoạt và thắng game"),
        L("Stone Circle", None, CIRCLE_COST, {}, sprite="Stone Circle 2",
          desc="Vòng đá đã được kích hoạt"),
    ],
    # --- chưa nâng cấp được ---
    "water": [L("Water")],
}

# --- Tower of Light: công trình RIÊNG, không thuộc chuỗi Workshop ---
# Ô cỏ chưa xây mà KỀ một "Magic Workshop 2" (cấp 3/3) sẽ tự dùng chuỗi này thay cho Workshop,
# miễn là chưa có Tower nào (xem chain_at). Chỉ xây được 1 Tower; xây xong ô đó đổi loại
# thành "tower" để các hàm tra cấp/vẽ sprite biết đây là Tower.
TOWER_CHAIN = [
    L("Field"),
    L("Tower of Light", {"mana": 5}, {"wood": 10, "stone": 5, "mana": 25}, {},
      sprite="Tower of Light", desc="Soi sáng bán kính 2 ô, bóng tối tiến chậm hơn (không thắng game)"),
]
CHAINS["grass_tower"] = TOWER_CHAIN
CHAINS["tower"] = TOWER_CHAIN
TERRAIN_VI.setdefault("tower", TERRAIN_VI["grass"])   # Main.py tra tên ô trong bảng này


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


WINDOW = "#9fd3ff"                           # mọi cửa sổ cùng một màu
DOOR = "#3b2412"
PLASTER, PLASTER_D = "#e3bd6a", "#c99a4a"    # tường vàng tầng trên
ROOF_R, ROOF_RD = "#a8322a", "#7d221c"       # mái đỏ phẳng khung gỗ


def _house(s, x, g, w, stone_h, upper_h, roof_h):
    """Nhà chính: tầng dưới xây đá, tầng trên tường vàng + cột gỗ, mái đỏ phẳng khung gỗ.
    x = mép trái, g = mặt đất, w = bề rộng. Trả về y đỉnh mái."""
    y_stone = g - stone_h
    y_upper = y_stone - upper_h
    y_roof = y_upper - roof_h
    _bricks(s, x + 1, y_stone, w - 2, stone_h, STONE, STONE_D)           # tầng đá
    rect(s, x, y_stone - 1, w, 2, WOOD_D)                                # sàn / xà gỗ giữa hai tầng
    rect(s, x, y_stone - 1, w, 1, WOOD)
    rect(s, x + 1, y_upper, w - 2, upper_h - 1, PLASTER)                 # tầng trên
    for py in range(y_upper + 2, y_stone - 1, 3):
        rect(s, x + 1, py, w - 2, 1, PLASTER_D)
    for px in (x + 1, x + w // 2 - 1, x + w - 3):                        # cột gỗ
        rect(s, px, y_upper, 2, upper_h - 1, WOOD_D)
    for cx in (x + w // 4, x + 3 * w // 4):                              # 2 cửa sổ
        rect(s, cx - 2, y_upper + 1, 4, 6, WOOD_D)
        rect(s, cx - 1, y_upper + 2, 2, 4, WINDOW)
    dx = x + w // 4 - 2                                                  # cửa ra vào
    rect(s, dx - 1, g - 9, 6, 9, WOOD_D)
    rect(s, dx, g - 8, 4, 8, DOOR)
    rect(s, x - 1, y_roof, w + 2, roof_h, WOOD)                          # khung mái
    rect(s, x + 1, y_roof + 2, w - 2, roof_h - 4, ROOF_R)                # mặt mái đỏ
    rect(s, x + 1, y_roof + roof_h // 2, w - 2, 1, ROOF_RD)
    rect(s, x + w // 2 - 1, y_roof, 2, roof_h, WOOD_D)                   # xà nóc
    rect(s, x - 1, y_roof + roof_h - 1, w + 2, 1, WOOD_D)                # mép mái
    _bricks(s, x + 3, y_roof - 5, 5, 6, STONE, STONE_D)                  # ống khói duy nhất
    rect(s, x + 2, y_roof - 5, 7, 1, STONE_D)
    return y_roof


def _stone_tower(s, x, g, w, top):
    """Tháp đá có răng cưa trên đỉnh."""
    _bricks(s, x, top + 4, w, g - top - 4, STONE_L, STONE_D)
    rect(s, x - 1, top + 3, w + 2, 2, STONE)                             # sàn đỉnh tháp
    for mx in (x - 1, x + w // 2 - 1, x + w - 2):
        rect(s, mx, top, 3, 3, STONE)
    rect(s, x + w // 2 - 1, top + 9, 3, 4, WINDOW)                       # cửa sổ tháp


def _lean_to(s, x, g, w, h):
    """Mái chái bằng gỗ, mái dốc bậc thang xuống phía phải."""
    _planks(s, x, g - h, w, h, WOOD, WOOD_D)
    rect(s, x, g - h, 2, h, WOOD_D)                                      # cột gỗ hai đầu
    rect(s, x + w - 2, g - h, 2, h, WOOD_D)
    rect(s, x + w // 2 - 1, g - 5, 3, 5, DOOR)                           # cửa
    third = w // 3
    rect(s, x, g - h - 3, third + 1, 2, WOOD_D)                          # mái bậc thang
    rect(s, x + third, g - h - 1, third + 1, 2, WOOD_D)
    rect(s, x + 2 * third, g - h + 1, w - 2 * third, 2, WOOD_D)


def _workshop():
    """Workshop cấp 1: nhà đá + gỗ mái đỏ và một mái chái nhỏ."""
    s = []
    _house(s, 6, 52, 27, stone_h=9, upper_h=7, roof_h=8)
    _lean_to(s, 32, 52, 15, 9)
    return s


def _workshop2():
    """Workshop cấp 2: nhà to hơn, thêm tháp đá giữa nhà và mái chái."""
    s = []
    _house(s, 1, 52, 32, stone_h=12, upper_h=8, roof_h=9)
    _stone_tower(s, 30, 52, 9, top=9)
    _lean_to(s, 39, 52, 14, 11)
    return s


# ---------- Magic Workshop: nhà phép thuật tông tím, cửa sổ vàng phát sáng
M_WALL, M_WALL_D, M_WALL_L = "#6a4a82", "#46305c", "#7d5c96"
M_ROOF, M_ROOF_D = "#3f2656", "#2a1740"
M_TRIM, M_GLOW, M_DOOR, M_TREE = "#d9a441", "#ffc93c", "#a83232", "#2e1a42"


def _glow_window(s, x, y, w=3, h=5):
    """Cửa sổ vàng sáng có viền tím sẫm (mọi cửa sổ cùng một màu)."""
    rect(s, x - 1, y - 1, w + 2, h + 2, M_WALL_D)
    rect(s, x, y, w, h, M_GLOW)


def _dead_tree(s, x, g):
    """Cây khô: x = mép trái thân cây, g = mặt đất."""
    rect(s, x, g - 18, 3, 18, M_TREE)                    # thân
    rect(s, x - 1, g - 3, 5, 3, M_TREE)                  # gốc
    rect(s, x - 4, g - 22, 4, 2, M_TREE)                 # nhánh trái
    rect(s, x - 4, g - 24, 2, 3, M_TREE)
    rect(s, x + 3, g - 24, 4, 2, M_TREE)                 # nhánh phải
    rect(s, x + 5, g - 27, 2, 4, M_TREE)
    rect(s, x + 1, g - 26, 2, 8, M_TREE)                 # ngọn
    rect(s, x - 1, g - 28, 2, 3, M_TREE)


def _magic_workshop():
    """Magic Workshop cấp 1: nhà nhỏ một tháp, mái nhọn, cửa sổ vàng."""
    s = []
    rect(s, 14, 40, 26, 12, M_WALL)                      # tầng trệt
    rect(s, 13, 50, 28, 2, M_WALL_D)
    rect(s, 23, 41, 8, 11, M_WALL_D)                     # cửa
    rect(s, 24, 42, 6, 10, M_DOOR)
    _glow_window(s, 17, 43)
    _glow_window(s, 34, 43)
    rect(s, 19, 24, 16, 14, M_WALL_L)                    # tháp giữa
    _glow_window(s, 22, 28)
    _glow_window(s, 30, 28)
    rect(s, 11, 37, 32, 3, M_ROOF)                       # mái hiên
    rect(s, 11, 39, 32, 1, M_TRIM)
    _roof(s, 16, 15, 22, M_ROOF, M_ROOF_D, step=3, row=3)   # mái tháp nhọn
    rect(s, 26, 18, 3, 3, M_GLOW)                        # cửa sổ áp mái
    rect(s, 26, 10, 2, 5, M_TRIM)                        # cột cờ
    rect(s, 25, 9, 4, 1, M_TRIM)
    return s


def _magic_workshop2():
    """Magic Workshop cấp 2: nhà lớn có hai cánh, tháp cao, cây khô bên cạnh."""
    s = []
    _dead_tree(s, 47, 52)
    rect(s, 6, 40, 38, 12, M_WALL)                       # tầng trệt
    rect(s, 5, 50, 40, 2, M_WALL_D)
    for cx in (6, 19, 29, 42):                           # cột hiên vàng
        rect(s, cx, 41, 2, 10, M_TRIM)
    rect(s, 21, 41, 8, 11, M_WALL_D)                     # cửa
    rect(s, 22, 42, 6, 10, M_DOOR)
    for wx in (9, 15, 32, 38):
        _glow_window(s, wx, 43)
    rect(s, 9, 27, 32, 11, M_WALL)                       # tầng giữa
    for wx in (11, 15, 33, 37):
        _glow_window(s, wx, 29)
    rect(s, 3, 37, 44, 3, M_ROOF)                        # mái hiên tầng trệt
    rect(s, 3, 39, 44, 1, M_TRIM)
    rect(s, 7, 24, 36, 3, M_ROOF)                        # mái hai cánh (bậc thang)
    rect(s, 10, 21, 30, 3, M_ROOF)
    rect(s, 13, 18, 24, 3, M_ROOF)
    rect(s, 7, 26, 36, 1, M_ROOF_D)
    rect(s, 13, 22, 3, 3, M_GLOW)                        # cửa sổ áp mái
    rect(s, 34, 22, 3, 3, M_GLOW)
    rect(s, 19, 13, 12, 25, M_WALL_L)                    # tháp giữa (vẽ đè lên mái hai cánh)
    rect(s, 19, 24, 12, 1, M_TRIM)
    _glow_window(s, 21, 16)
    _glow_window(s, 26, 16)
    _glow_window(s, 21, 29)
    _glow_window(s, 26, 29)
    rect(s, 17, 10, 16, 3, M_ROOF)                       # mái tháp nhọn
    rect(s, 17, 12, 16, 1, M_ROOF_D)
    rect(s, 19, 7, 12, 3, M_ROOF)
    rect(s, 21, 4, 8, 3, M_ROOF)
    rect(s, 23, 2, 4, 2, M_ROOF)
    rect(s, 24, 0, 2, 2, M_TRIM)                         # đỉnh tháp
    rect(s, 23, 8, 3, 3, M_GLOW)                         # cửa sổ áp mái tháp
    return s


# ---------- Vòng đá đã kích hoạt: các viên đá phát sáng xanh, tinh thể ở giữa
C_GL, C_GL_D, C_GL_L = "#7fe8ff", "#3aa7d9", "#e6fbff"


def _circle_active():
    s = []
    for x, y in ((23, 5), (38, 10), (43, 23), (38, 37),
                 (23, 42), (8, 37), (3, 23), (8, 10)):
        rect(s, x - 1, y + 2, 10, 8, C_GL_D)         # quầng sáng
        rect(s, x + 1, y, 6, 4, C_GL)
        rect(s, x + 2, y + 1, 3, 2, C_GL_L)
        rect(s, x + 1, y + 6, 7, 2, C_GL)
    rect(s, 22, 32, 10, 3, C_GL_D)                    # tinh thể ở tâm
    rect(s, 24, 19, 6, 13, C_GL)
    rect(s, 25, 19, 2, 11, C_GL_L)
    rect(s, 26, 15, 2, 4, C_GL_L)
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


# ---------- Market (nhà dưới gốc rừng nấm): mái ngói cam, tường vàng khung gỗ, cửa sổ tròn
TILE, TILE_L, TILE_D, TILE_DD = "#d98a5e", "#e8a077", "#b4623f", "#7a3f2a"
PLAS, PLAS_D, TIMB = "#e8c26a", "#c99a4a", "#5a3a22"
H_DOOR, H_WHITE, H_BASE, H_BASE_L, H_CHIM = "#7a4e2a", "#f6f3ea", "#34343a", "#4a4a52", "#2e2e33"


def _market(level=1):
    """Nhà nhỏ đứng trước gốc nấm: ba cây nấm vẫn thấy rõ phía sau.
    level 2: cửa sổ sáng đèn vàng và thêm ống khói thứ hai."""
    s = []
    glass = GLOW if level >= 2 else H_WHITE
    for cx in ((17,) if level == 1 else (17, 33)):          # ống khói
        rect(s, cx, 31, 3, 6, H_CHIM)
        rect(s, cx - 1, 30, 5, 1, H_BASE_L)
    rect(s, 15, 36, 24, 7, TILE)                            # mái ngói
    for y in (36, 39):
        rect(s, 15, y, 24, 1, TILE_L)
        rect(s, 15, y + 2, 24, 1, TILE_D)
    rect(s, 14, 42, 26, 1, TILE_DD)                         # mép mái
    for wx in (19, 25, 31):                                 # cửa sổ áp mái
        rect(s, wx - 1, 37, 5, 4, TIMB)
        rect(s, wx, 38, 3, 2, glass)
    rect(s, 16, 43, 22, 6, PLAS)                            # tường vàng
    rect(s, 16, 43, 22, 1, TIMB)
    rect(s, 16, 43, 1, 6, TIMB)
    rect(s, 37, 43, 1, 6, TIMB)
    rect(s, 25, 44, 4, 5, TIMB)                             # cửa
    rect(s, 26, 45, 2, 4, H_DOOR)
    for wx in (19, 32):                                     # cửa sổ tròn
        rect(s, wx, 45, 3, 3, TIMB)
        rect(s, wx + 1, 46, 1, 1, glass)
    rect(s, 15, 49, 24, 2, H_BASE)                          # móng đá tối
    rect(s, 24, 49, 6, 2, H_BASE_L)
    return s


# ---------- Tower of Light: tháp đá tối, mái nhọn, ban công, cửa sổ vàng (theo ảnh tham khảo)
T_WALL, T_WALL_L, T_WALL_D = "#4a4a63", "#62627f", "#2c2b42"
T_LINE = "#3a3a52"
T_ROOF, T_ROOF_L, T_ROOF_D = "#34305a", "#4d4980", "#211e3d"
T_GLOW, T_GLOW_IN, T_DOOR = "#ff9d2e", "#ffd96a", "#15131f"


def _tower_window(s, x, y, w=2, h=4):
    """Cửa sổ sáng đèn: viền tối, ánh cam, nửa trên vàng nhạt."""
    rect(s, x - 1, y - 1, w + 2, h + 2, T_WALL_D)
    rect(s, x, y, w, h, T_GLOW)
    rect(s, x, y, w, 2, T_GLOW_IN)


def _tower_rail(s, x, y, w):
    """Lan can ban công: thanh ngang + các cột nhỏ."""
    rect(s, x, y, w, 1, T_WALL_L)
    for px in range(x, x + w, 3):
        rect(s, px, y + 1, 1, 2, T_WALL_D)


def _tower():
    """Tower of Light: tháp đá cao, mái nón nhọn, ban công, cửa sổ sáng, đèn lồng cạnh chân tháp."""
    s = []
    rect(s, 8, 50, 38, 4, T_WALL_D)                       # đá vụn dưới chân
    rect(s, 12, 48, 8, 3, T_WALL)
    rect(s, 35, 48, 9, 3, T_WALL)
    _bricks(s, 18, 40, 18, 10, T_WALL, T_LINE)            # móng rộng
    rect(s, 18, 40, 2, 10, T_WALL_L)
    rect(s, 34, 40, 2, 10, T_WALL_D)
    rect(s, 24, 43, 6, 7, T_WALL_D)                       # cửa vòm
    rect(s, 25, 44, 4, 6, T_DOOR)
    rect(s, 26, 43, 2, 1, T_DOOR)
    _bricks(s, 20, 24, 14, 16, T_WALL, T_LINE)            # thân tháp
    rect(s, 20, 24, 2, 16, T_WALL_L)
    rect(s, 32, 24, 2, 16, T_WALL_D)
    _tower_window(s, 24, 27)
    _tower_window(s, 29, 32)
    _tower_window(s, 24, 36)
    _tower_rail(s, 34, 28, 5)                             # ban công nhỏ bên phải
    rect(s, 34, 31, 5, 2, T_WALL_L)
    rect(s, 34, 33, 5, 1, T_WALL_D)
    _tower_rail(s, 15, 34, 5)                             # ban công nhỏ bên trái
    rect(s, 15, 37, 5, 2, T_WALL_L)
    rect(s, 15, 39, 5, 1, T_WALL_D)
    rect(s, 17, 22, 20, 3, T_WALL_L)                      # sàn ban công trên đỉnh
    rect(s, 17, 24, 20, 1, T_WALL_D)
    rect(s, 19, 25, 2, 2, T_WALL_D)
    rect(s, 33, 25, 2, 2, T_WALL_D)
    _bricks(s, 20, 14, 14, 8, T_WALL, T_LINE)             # phòng đèn trên cùng
    rect(s, 20, 14, 2, 8, T_WALL_L)
    rect(s, 32, 14, 2, 8, T_WALL_D)
    _tower_window(s, 23, 16)
    _tower_window(s, 29, 16)
    _tower_rail(s, 17, 20, 3)
    _tower_rail(s, 34, 20, 3)
    rect(s, 26, 0, 2, 4, T_ROOF_D)                        # cột đỉnh mái
    rect(s, 26, 0, 2, 1, "#8a86b8")
    for rx, ry, rw, lw in ((25, 4, 4, 1), (23, 6, 8, 2), (21, 8, 12, 2), (19, 10, 16, 2)):
        rect(s, rx, ry, rw, 2, T_ROOF)                    # mái nón nhiều bậc
        rect(s, rx, ry, lw, 2, T_ROOF_L)
    rect(s, 17, 12, 20, 2, T_ROOF_D)                      # mép mái
    rect(s, 26, 8, 2, 3, T_GLOW)                          # cửa sổ áp mái
    rect(s, 44, 44, 1, 6, T_WALL_D)                       # đèn lồng bên chân tháp
    rect(s, 43, 42, 3, 3, T_GLOW)
    rect(s, 44, 43, 1, 1, T_GLOW_IN)
    return s


BUILD_SPRITES = {"Forest 2": _treehouse2(), "Forest 3": _treehouse3(),
                 "Forest 4": _treehouse4(),
                 "Rocks 2": _stonehouse2(), "Rocks 3": _stonehouse3(),
                 "Rocks 4": _stonehouse4(),
                 "Workshop": _workshop(), "Workshop 2": _workshop2(),
                 "Magic Workshop": _magic_workshop(), "Magic Workshop 2": _magic_workshop2(),
                 "Port": _port(), "Market": _market(), "Market 2": _market(2),
                 "Tower of Light": _tower(),
                 "Stone Circle 2": _circle_active()}


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
    parts = []
    if lv["prod"]:
        parts.append(", ".join(f"{v:g} {RES_VI[k]}/phút" for k, v in lv["prod"].items()))
    if lv["boost"]:
        parts.append("Ô kề bên: " + ", ".join(f"+{v * 100:g}% {RES_VI[k]}"
                                               for k, v in lv["boost"].items()))
    if lv["desc"]:
        parts.append(lv["desc"])
    return "; ".join(parts) if parts else "chưa sản xuất"


def level_info(kind, lvl):
    """Tra cấp theo LOẠI ô. Không biết vị trí nên không thấy chuỗi Magic Workshop;
    chỗ nào có pos thì dùng level_at."""
    return CHAINS[kind][lvl - 1]


def _next_to(pos, terrain, tiles, dark_cells, sprite):
    """Có ô kề bên (chưa bị bóng tối nuốt) đang là công trình có sprite này không?"""
    return any(n not in dark_cells and n in tiles
               and level_at(n, terrain, tiles[n])["sprite"] == sprite
               for n in neighbors(pos))


def chain_at(pos, terrain, tiles=None, dark_cells=()):
    """Chuỗi cấp của ô pos.
    - Ô cỏ chưa xây, kề Magic Workshop 2, và chưa có Tower nào -> chuỗi Tower of Light
      (chỉ xét khi truyền tiles; khi không truyền thì chỉ tra chuỗi cố định của ô).
    - Ô cỏ kề rừng nấm -> chuỗi Magic Workshop thay cho Workshop.
    - Còn lại -> chuỗi theo loại ô."""
    kind = terrain[pos]
    if kind == "grass":
        if (tiles is not None and pos not in tiles and not towers(terrain, tiles)
                and _next_to(pos, terrain, tiles, dark_cells, "Magic Workshop 2")):
            return CHAINS["grass_tower"]
        if any(terrain.get(n) == "mushroom" for n in neighbors(pos)):
            return CHAINS["grass_magic"]
    return CHAINS[kind]


def level_at(pos, terrain, lvl):
    return chain_at(pos, terrain)[lvl - 1]


def towers(terrain, tiles):
    return [p for p, lvl in tiles.items()
            if level_at(p, terrain, lvl)["name"] == "Tower of Light"]


def next_level(pos, terrain, tiles, counts, dark_cells=()):
    """(thông tin cấp kế tiếp, chi phí lần này) hoặc None nếu đã tối đa."""
    kind = terrain[pos]
    chain = chain_at(pos, terrain, tiles, dark_cells)
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
    info = next_level(pos, terrain, tiles, counts, dark_cells)
    if info is None:
        if len(chain_at(pos, terrain, tiles, dark_cells)) > 1:
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


def upgrade(pos, terrain, tiles, counts, res, dark_cells=()):
    """Trừ tài nguyên và nâng ô lên 1 cấp (đã kiểm tra can_upgrade trước).
    Trả về (tên mới, cấp mới)."""
    nxt, cost = next_level(pos, terrain, tiles, counts, dark_cells)
    chain = chain_at(pos, terrain, tiles, dark_cells)
    for k, v in cost.items():
        res[k] -= v
    kind = terrain[pos]
    lvl = tiles.get(pos, 1) + 1
    counts[(kind, lvl)] = counts.get((kind, lvl), 0) + 1
    tiles[pos] = lvl
    if chain is TOWER_CHAIN:
        terrain[pos] = "tower"   # nhớ ô này là Tower (towers/level_at/vẽ sprite dựa vào đây)
    return nxt["name"], lvl


def reset_terrain(terrain):
    """Trả các ô "tower" về cỏ khi bắt đầu ván mới trên cùng một bản đồ."""
    for p, kind in terrain.items():
        if kind == "tower":
            terrain[p] = "grass"


def describe(pos, terrain, tiles, counts, res, dark_cells=()):
    """Nội dung khung thông tin: (dòng hiện tại, tiêu đề cấp kế, dòng cấp kế, cảnh báo)."""
    chain = chain_at(pos, terrain, tiles, dark_cells)
    lvl = tiles.get(pos, 1)
    cur = chain[lvl - 1]
    if len(chain) == 1:
        return [cur["name"], "Không nâng cấp được"], "", [], ""
    now = [f"{cur['name']} - cấp {lvl}/{len(chain)}", "Sản lượng: " + effect_text(cur)]
    info = next_level(pos, terrain, tiles, counts, dark_cells)
    if info is None:
        now.append("Đã đạt cấp tối đa")
        return now, "", [], ""
    nxt, cost = info
    ok, reason = can_upgrade(pos, terrain, tiles, counts, dark_cells, res)
    return (now, f"Nâng lên cấp {lvl + 1}: {nxt['name']}",
            [f"Chi phí: {cost_text(cost)}", "Sản lượng: " + effect_text(nxt)],
            "" if ok else reason)


def boost_at(pos, terrain, tiles, dark_cells):
    """Hệ số nhân sản lượng của ô pos, do các ô kề bên có boost (vd Workshop).
    Nhiều ô boost cộng dồn: 2 Workshop cấp 1 kề nhau = +50%. Ô bị bóng tối nuốt thì mất boost."""
    mult = {}
    for n in neighbors(pos):
        if n in dark_cells or n not in tiles:
            continue
        for k, v in level_at(n, terrain, tiles[n])["boost"].items():
            mult[k] = mult.get(k, 1.0) + v
    return mult


def income(terrain, tiles, dark_cells):
    """Tài nguyên thu được mỗi PHÚT (hiện cạnh số trên HUD)."""
    inc = {k: 0 for k in RES_VI}
    for pos, lvl in tiles.items():
        if pos in dark_cells:
            continue
        mult = boost_at(pos, terrain, tiles, dark_cells)
        for k, v in level_at(pos, terrain, lvl)["prod"].items():
            inc[k] += v * mult.get(k, 1.0)
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
    for pos, lvl in tiles.items():
        if terrain[pos] == "circle" and lvl >= len(CHAINS["circle"]):
            return "CHIẾN THẮNG! Vòng đá đã được kích hoạt, bóng tối bị đẩy lùi."
    return None