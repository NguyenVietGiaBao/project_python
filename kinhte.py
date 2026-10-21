"""Hệ thống kinh tế và cây nâng cấp cho Stop the Darkness.

Bản tích hợp: cấu trúc ID/đồ thị nâng cấp của phiên bản 2, sprite phân biệt,
chọn nhánh bằng Tkinter và bonus kinh tế của phiên bản 1.
Mọi số liệu chưa có bằng chứng từ game gốc được giữ là thông số mô phỏng.

Thiết kế tương thích với Main.py hiện có:
- tiles vẫn nhận giá trị số (để phần vẽ hiện tại dùng được), nhưng mỗi giá trị
  là TileLevel nên cũng lưu mã công trình thật để hỗ trợ các nhánh nâng cấp.
- CHAINS vẫn tồn tại cho menu/các bên gọi cũ; luật nâng cấp dùng STRUCTURES + UPGRADES.
- Công trình được mở khóa dựa trên những ô kề, cấp thật của ô và tài nguyên.
"""
from collections import deque
from dark import TICK_MS
from map import neighbors, rect

RES_VI = {"wood": "Gỗ", "stone": "Đá", "mana": "Mana", "tech": "Công nghệ"}
# Giữ tên hằng để các module cũ còn import được. TECH_WIN là mức công nghệ cần
# chuẩn bị cho nhánh Light Research Facility, không tự nó kích hoạt chiến thắng.
TECH_WIN = 600
TOWERS_WIN = 2  # hằng tương thích ngược; Tower of Light là phòng thủ, không tự thắng.
PER_TICK = TICK_MS / 60000  # production được quy ước theo phút.
GAME_MODE = "standard"  # Main.py hiện chỉ triển khai Standard; Extended là opt-in.


def set_game_mode(mode):
    """Chọn standard / extended bằng code; Main.py chưa có menu đổi mode."""
    global GAME_MODE
    if mode not in {"standard", "extended"}:
        raise ValueError("Mode phải là 'standard' hoặc 'extended'.")
    GAME_MODE = mode


# Hiệu ứng cộng hưởng, tách khỏi sản lượng gốc trong STRUCTURES để dễ kiểm thử.
# Mẹo chơi của cộng đồng xác nhận Forest kề bên tăng 25% sản lượng gỗ của ô.
WOOD_ADJACENCY_BONUS = 0.25
# Cộng đồng cũng ghi nhận Dock tăng hiệu quả phép thuật gần nước, nhưng nguồn
# công khai không nêu chính xác hệ số. Hệ số này để riêng để dễ hiệu chỉnh khi
# có thể so sánh trực tiếp với giao diện bản gốc.
DOCK_MAGIC_BONUS = 0.25
# Hệ số dưới đây là cân bằng mô phỏng, CHƯA được xác nhận chính xác từ bản gốc.
ROCK_ADJACENCY_BONUS = 0.20
MUSHROOM_ADJACENCY_BONUS = 0.20
CITY_TECH_BONUS = 0.15
# Bonus "Workshop" từ bản cũ: công trình trong nhánh làng/thành phố (và Magical Water
# City) tăng sản lượng của các ô XUNG QUANH. Nhiều công trình thì cộng dồn.
# Phạm vi bonus: 8 = cả 4 ô cạnh và 4 ô góc; đổi thành 4 để chỉ tính 4 ô cạnh.
# (Chỉ bonus kiểu Workshop dùng phạm vi này; các bonus Forest/Rocks/nấm/Dock/thành
# phố và điều kiện xây vẫn tính theo 4 ô cạnh.)
BOOST_NEIGHBORS = 8
#   Workshop       : +Gỗ, +Đá   (nhánh làng gỗ và làng mỏ)
#   Magic Workshop : +Gỗ, +Mana (nhánh làng phép thuật)
# Cấp 1 của làng nhận hệ số x1 (+25%); cấp 2 trở lên và thành phố nhận x2 (+50%).
# Ngoại lệ: Magical City được +100% Gỗ và Mana (xem BOOST_BY_ID).
WORKSHOP_BOOST = {"wood": 0.25, "stone": 0.25}
MAGIC_WORKSHOP_BOOST = {"wood": 0.25, "mana": 0.25}

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


def _recolor(sprite, mapping):
    """Đổi màu một sprite theo bảng {màu cũ: màu mới}; màu không có trong bảng giữ nguyên."""
    return [(x, y, w, h, mapping.get(col, col)) for x, y, w, h, col in sprite]


# Bảng màu xanh dương cho Tower of Water (cùng hình dáng với Tower of Light).
_WATER_PALETTE = {
    T_WALL: "#3f6f96", T_WALL_L: "#5b97c2", T_WALL_D: "#24425f", T_LINE: "#31587a",
    T_ROOF: "#2e6fb0", T_ROOF_L: "#4f95d6", T_ROOF_D: "#1c4670",
    T_GLOW: "#4ac7ee", T_GLOW_IN: "#bdf1ff", T_DOOR: "#10243a",
    "#8a86b8": "#9fd3f5",
}


def _tower_water():
    """Tower of Water: giống Tower of Light nhưng toàn bộ màu chuyển sang xanh dương."""
    return _recolor(_tower(), _WATER_PALETTE)


BUILD_SPRITES = {"Forest 2": _treehouse2(), "Forest 3": _treehouse3(),
                 "Forest 4": _treehouse4(),
                 "Rocks 2": _stonehouse2(), "Rocks 3": _stonehouse3(),
                 "Rocks 4": _stonehouse4(),
                 "Workshop": _workshop(), "Workshop 2": _workshop2(),
                 "Magic Workshop": _magic_workshop(), "Magic Workshop 2": _magic_workshop2(),
                 "Port": _port(), "Market": _market(), "Market 2": _market(2),
                 "Tower of Light": _tower(),
                 "Stone Circle 2": _circle_active()}


# ---------- dữ liệu công trình và luật kinh tế ---------------------------------
# Giá trị chi phí/sản lượng giữ lại cho Forest/Rocks đang có trong dự án.
# Với nhánh nâng cấp mới, những thông số chưa được xác nhận đầy đủ từ game gốc
# được chọn để giữ cân bằng và nhất quán nội bộ, không được coi là số liệu gốc.

class TileLevel(int):
    """Giá trị tương thích int của Main.py, đồng thời mang mã công trình.

    Ví dụ: TileLevel(4, "potion_factory_1") vẫn so sánh/hiển thị như cấp 4,
    nhưng kinh tế biết ô đó là Potion Factory chứ không phải Forest cấp 4.
    """
    def __new__(cls, stage, building_id=None):
        obj = int.__new__(cls, int(stage))
        obj.building_id = building_id
        return obj


def _spec(building_id, name, kind, *, tier=1, stage=2, family=None, tags=(),
          prod=None, base=None, step=None, rule="always", sprite=None, desc="",
          priority=50):
    return {
        "id": building_id,
        "name": name,
        "kind": kind,
        "tier": tier,
        "stage": stage,
        "family": family or building_id,
        "tags": frozenset(tags),
        "prod": dict(prod or {}),
        "base": dict(base or {}),
        "step": dict(step or {}),
        "rule": rule,
        "sprite": sprite,
        "desc": desc,
        "priority": priority,
        "boost": {},
    }


STRUCTURES = {}


def _add(building_id, name, kind, **kwargs):
    info = _spec(building_id, name, kind, **kwargs)
    STRUCTURES[building_id] = info
    return info


# Địa hình/cấp gốc. Ô chưa xuất hiện trong tiles tương đương tier 1.
_add("field", "Field", "grass", tier=0, stage=1, family="field",
     tags=("field",), desc="Ô đất trống; công trình phụ thuộc địa hình liền kề.")
_add("forest_1", "Forest", "forest", tier=1, stage=1, family="forest",
     tags=("forest",), desc="Rừng tự nhiên.")
_add("forest_2", "Forest", "forest", tier=2, stage=2, family="forest",
     prod={"wood": 5}, base={"wood": 3}, step={"wood": 2},
     tags=("forest",), sprite="Forest 2", desc="Tạo gỗ.")
_add("forest_3", "Forest", "forest", tier=3, stage=3, family="forest",
     prod={"wood": 7}, base={"wood": 5}, step={"wood": 2},
     tags=("forest",), sprite="Forest 3", desc="Tạo gỗ nhiều hơn.")
_add("forest_4", "Forest", "forest", tier=4, stage=4, family="forest",
     prod={"wood": 9}, base={"wood": 7, "stone": 5}, step={"wood": 2, "stone": 2},
     tags=("forest",), sprite="Forest 4", desc="Rừng cấp cao; có thể mở nhánh Potion Factory.")
# Nhánh bí mật được cộng đồng ghi nhận: một Forest cấp 1 nằm giữa bốn Forest cấp 1
# có thể trở thành Treetop Village. Giá/sản lượng riêng của nhánh này là ước lượng cân bằng.
_add("treetop_village", "Treetop Village", "forest", tier=1, stage=2,
     family="treetop_village", tags=("wood_source", "city_seed", "wood_city"),
     rule="treetop_village", prod={"wood": 12, "tech": 1},
     base={"wood": 15, "stone": 5}, sprite="Forest 2",
     desc="Làng trên ngọn cây; cần bốn Forest cấp 1 ở các ô kề bên.", priority=1)
_add("rock_1", "Rocks", "rock", tier=1, stage=1, family="rock",
     tags=("rock",), desc="Địa hình đá tự nhiên.")
_add("rock_2", "Rocks", "rock", tier=2, stage=2, family="rock",
     prod={"stone": 3}, base={"wood": 8}, step={"wood": 2},
     tags=("rock",), sprite="Rocks 2", desc="Khai thác đá.")
_add("rock_3", "Rocks", "rock", tier=3, stage=3, family="rock",
     prod={"stone": 5}, base={"wood": 10, "stone": 3}, step={"wood": 2, "stone": 2},
     tags=("rock",), sprite="Rocks 3", desc="Khai thác đá hiệu quả hơn.")
_add("rock_4", "Rocks", "rock", tier=4, stage=4, family="rock",
     prod={"stone": 7}, base={"wood": 12, "stone": 5, "tech": 2},
     step={"wood": 2, "stone": 2, "tech": 1},
     tags=("rock",), sprite="Rocks 4", desc="Mỏ đá cấp cao.")
_add("mushroom_1", "Mushroom Forest", "mushroom", tier=1, stage=1,
     family="mushroom_forest", tags=("magic_source",), desc="Rừng nấm tự nhiên.")
_add("mushroom_2", "Mushroom Forest", "mushroom", tier=2, stage=2,
     family="mushroom_forest", tags=("magic_source",), prod={"mana": 3},
     base={"wood": 8}, step={"wood": 2}, sprite="Market",
     desc="Tạo Mana; mở rộng nguồn phép thuật.")
_add("mushroom_3", "Mushroom Forest", "mushroom", tier=3, stage=3,
     family="mushroom_forest", tags=("magic_source",), prod={"mana": 7},
     base={"wood": 15, "stone": 5}, step={"wood": 3, "stone": 1}, sprite="Market",
     desc="Nguồn Mana mạnh; có thể mở khóa thành phố nấm.")
_add("water_1", "Water", "water", tier=1, stage=1, family="water",
     tags=("water",), desc="Vùng nước; có thể xây Dock.")
_add("dock", "Dock", "water", tier=1, stage=2, family="dock", tags=("dock",),
     prod={"tech": 1}, base={"wood": 8}, sprite="Port",
     desc="Bến tàu; tính vào điều kiện Mainport.")
_add("stone_circle_1", "Stone Circle", "circle", tier=1, stage=1,
     family="stone_circle", tags=("stone_circle",), desc="Vòng đá cổ.")
_add("stone_circle_2", "Stone Circle Level 2", "circle", tier=2, stage=2,
     family="stone_circle", tags=("stone_circle", "ending"),
     base={"stone": 100, "mana": 100},
     desc="Nâng cấp vòng đá bằng 100 Đá và 100 Mana để chặn bóng tối và hoàn thành nhánh chiến thắng.")

# Rừng rễ cây là một nhánh đặc biệt trên ô đất trống, không phải loại địa hình
# được sinh sẵn trên bản đồ. Đây là điều kiện được cộng đồng game ghi nhận.
_add("tree_roots_1", "Tree Roots", "grass", tier=1, stage=2, family="tree_roots",
     tags=("forest_like", "wood_source"), rule="tree_roots_seed",
     prod={"wood": 2, "mana": 1}, base={"wood": 18, "stone": 5},
     sprite="Forest 2", desc="Rễ cây cổ thụ; cần 3 Forest và 1 Village/City kề bên.", priority=2)
_add("tree_roots_2", "Tree Roots", "grass", tier=2, stage=3, family="tree_roots",
     tags=("forest_like", "wood_source"), prod={"wood": 5, "mana": 2},
     base={"wood": 25, "stone": 10}, step={"wood": 4, "stone": 2},
     sprite="Forest 3", desc="Rễ cây phát triển mạnh hơn.")
_add("tree_roots_3", "Tree Roots", "grass", tier=3, stage=4, family="tree_roots",
     tags=("forest_like", "wood_source"), prod={"wood": 8, "mana": 4},
     base={"wood": 35, "stone": 18}, step={"wood": 5, "stone": 3},
     sprite="Forest 4", desc="Có thể mở khóa Tree Roots City/Port City.")
_add("tree_roots_4", "Tree Roots", "grass", tier=4, stage=4, family="tree_roots",
     tags=("forest_like", "wood_source"), prod={"wood": 12, "mana": 6},
     base={"wood": 50, "stone": 25, "mana": 15}, step={"wood": 6, "stone": 3},
     sprite="Forest 4", desc="Cấp cao nhất; có thể hỗ trợ Potion Factory.")

# Nhánh dân cư trên ô Field. Tên/tuyến nâng cấp được giữ thành ID riêng vì mỗi
# nhánh có thể có hiệu ứng, yêu cầu và đường tiến triển khác nhau.
_add("wooden_village", "Wooden Village", "grass", tier=1, stage=2,
     family="wood_village", tags=("city_seed", "wood_city"), rule="adj_forest",
     prod={"wood": 2}, base={"wood": 10}, sprite="Workshop",
     desc="Làng gỗ; cần Forest kề bên.", priority=30)
_add("wooden_village_2", "Wooden Village Level 2", "grass", tier=2, stage=3,
     family="wood_village", tags=("city_seed", "wood_city"), prod={"wood": 5},
     base={"wood": 22, "stone": 4}, step={"wood": 3}, sprite="Workshop",
     desc="Làng gỗ cấp 2.")
_add("wooden_city", "Wooden City", "grass", tier=1, stage=4,
     family="wood_city", tags=("city", "wood_city"), rule="wooden_city_route",
     prod={"wood": 10, "tech": 1}, base={"wood": 40, "stone": 15}, sprite="Market",
     desc="Thành phố gỗ; có thể mở trực tiếp khi kề ba Forest và một ngôi làng.", priority=12)
_add("wooden_city_2", "Wooden City Level 2", "grass", tier=2, stage=4,
     family="wood_city", tags=("city", "city_level2", "wood_city"),
     prod={"wood": 15, "tech": 3}, base={"wood": 70, "stone": 30, "tech": 5},
     sprite="Market", desc="Thành phố gỗ cấp 2; có thể phát triển thành Great City.")
_add("wooden_port_city", "Wooden Port City", "grass", tier=1, stage=4,
     family="wood_city", tags=("city", "city_level2", "wood_city", "port_city"),
     rule="wooden_port_city", prod={"wood": 18, "tech": 8},
     base={"wood": 90, "stone": 35, "tech": 10}, sprite="Port",
     desc="Port cấp 2 kề ít nhất ba Forest cấp 4.", priority=15)

_add("mining_village", "Mining Village", "grass", tier=1, stage=2,
     family="mining_village", tags=("city_seed", "mining"), rule="adj_rock",
     prod={"stone": 2}, base={"wood": 14}, sprite="Rocks 2",
     desc="Làng khai mỏ; cần Rocks kề bên.", priority=35)
_add("mining_village_2", "Mining Village Level 2", "grass", tier=2, stage=3,
     family="mining_village", tags=("city_seed", "mining"), prod={"stone": 4, "tech": 1},
     base={"wood": 25, "stone": 5}, sprite="Rocks 2", desc="Làng khai mỏ cấp 2.")
_add("mining_city", "Mining City", "grass", tier=1, stage=4,
     family="mining_city", tags=("city", "mining"), prod={"stone": 8, "tech": 3},
     base={"wood": 40, "stone": 18}, sprite="Rocks 3", desc="Thành phố khai mỏ.")
_add("mining_research_facility", "Stone Tech Center", "grass", tier=1, stage=4,
     family="mining_research", tags=("research", "mining"),
     prod={"stone": 10, "tech": 8}, base={"wood": 55, "stone": 30, "tech": 10},
     sprite="Rocks 3", desc="Trung tâm công nghệ đá; mở khóa Mining Research City Level 2.")
_add("mining_research_city_2", "Mining Research City Level 2", "grass", tier=2, stage=4,
     family="mining_research", tags=("city", "city_level2", "research", "mining"),
     prod={"stone": 15, "tech": 16}, base={"wood": 85, "stone": 45, "tech": 25},
     sprite="Rocks 4", desc="Mở khóa các Great City dựa trên địa hình kề.")

# Nhánh phép thuật.
_add("magical_village", "Magical Village", "grass", tier=1, stage=2,
     family="magic_village", tags=("magic", "city_seed"), rule="adj_mushroom",
     prod={"mana": 3}, base={"wood": 14, "stone": 4}, sprite="Market",
     desc="Làng phép thuật; cần Mushroom Forest kề bên.", priority=40)
_add("magical_village_2", "Magical Village Level 2", "grass", tier=2, stage=3,
     family="magic_village", tags=("magic", "city_seed"), prod={"mana": 8, "tech": 2},
     base={"wood": 25, "stone": 10, "mana": 5}, sprite="Market",
     desc="Làng phép thuật cấp 2; giúp mở khóa Tower of Light.")
_add("magical_city", "Magical City", "grass", tier=1, stage=4,
     family="magic_city", tags=("magic", "city", "city_level2"), rule="magical_city",
     prod={"mana": 18, "tech": 8}, base={"wood": 50, "stone": 25, "mana": 30},
     sprite="Market", desc="Thành phố phép thuật; cần Tower of Light kề bên.", priority=15)
_add("magical_port_city", "Magical Port City", "grass", tier=1, stage=4,
     family="magic_city", tags=("magic", "city", "city_level2", "port_city"),
     rule="magical_port_city", prod={"mana": 20, "tech": 12},
     base={"wood": 75, "stone": 30, "mana": 25}, sprite="Port",
     desc="Thành phố cảng phép thuật; cần Water và Tower of Light kề bên.", priority=7)
_add("mushroom_city", "Mushroom City", "grass", tier=1, stage=4,
     family="magic_city", tags=("magic", "city", "city_level2"), rule="mushroom_city",
     prod={"mana": 14, "wood": 4}, base={"wood": 45, "stone": 15, "mana": 25},
     sprite="Market", desc="Thành phố nấm; cần Mushroom Forest cấp 3 kề bên.", priority=14)
_add("mushroom_port_city", "Mushroom Port City", "grass", tier=1, stage=4,
     family="magic_city", tags=("magic", "city", "city_level2", "port_city"),
     rule="mushroom_port_city", prod={"mana": 20, "tech": 7},
     base={"wood": 65, "stone": 25, "mana": 35}, sprite="Port",
     desc="Thành phố cảng nấm; cần nước và Mushroom Forest cấp 3 kề bên.", priority=10)
_add("tree_roots_city", "Tree Roots City", "grass", tier=1, stage=4,
     family="wood_city", tags=("city", "city_level2", "wood_city", "magic"),
     rule="tree_roots_city", prod={"wood": 15, "mana": 8},
     base={"wood": 60, "stone": 25, "mana": 15}, sprite="Forest 4",
     desc="Thành phố rễ cây; cần Tree Roots cấp 3 trở lên kề bên.", priority=12)
_add("tree_roots_port_city", "Tree Roots Port City", "grass", tier=1, stage=4,
     family="wood_city", tags=("city", "city_level2", "wood_city", "magic", "port_city"),
     rule="tree_roots_port_city", prod={"wood": 18, "mana": 12, "tech": 5},
     base={"wood": 80, "stone": 30, "mana": 20}, sprite="Port",
     desc="Thành phố cảng rễ cây; cần Tree Roots cấp 3+ và nước kề bên.", priority=8)
_add("magical_water_city", "Magical Water City", "grass", tier=1, stage=4,
     family="magic_city", tags=("magic", "city", "city_level2", "water_city"),
     rule="magical_water_city", prod={"mana": 20, "tech": 10},
     base={"wood": 80, "stone": 35, "mana": 45}, sprite="Port",
     desc="Thành phố phép thuật ven nước; hưởng cộng hưởng với Great City of Tech and Magic.", priority=9)

# Cảng và công trình liên quan đến nước.
_add("port", "Port", "grass", tier=1, stage=2, family="port", tags=("port",),
     rule="adj_water", prod={"tech": 3, "wood": 1}, base={"wood": 25, "stone": 8},
     sprite="Port", desc="Cảng; cần có Water kề bên.", priority=25)
_add("port_2", "Port Level 2", "grass", tier=2, stage=3, family="port", tags=("port",),
     rule="adj_water", prod={"tech": 6, "wood": 2},
     base={"wood": 40, "stone": 15, "tech": 4}, sprite="Port",
     desc="Cảng cấp 2; có thể phát triển thành Mainport hoặc thành phố cảng.")
_add("mainport_1", "Mainport Level 1", "grass", tier=1, stage=4,
     family="mainport", tags=("port",), rule="mainport_1",
     prod={"tech": 18, "wood": 4}, base={"wood": 65, "stone": 25, "tech": 20},
     sprite="Port", desc="Cần ít nhất ba Port trên cùng vùng nước liên thông.", priority=10)
_add("mainport_2", "Mainport Level 2", "grass", tier=2, stage=4,
     family="mainport", tags=("port",), rule="mainport_2",
     prod={"tech": 35, "wood": 8}, base={"wood": 95, "stone": 45, "tech": 40},
     sprite="Port", desc="Cần ít nhất bốn Port/Mainport trên cùng vùng nước liên thông (mốc cân bằng).")
_add("lighthouse", "Lighthouse", "grass", tier=1, stage=4,
     family="lighthouse", tags=("light", "tech_building"), rule="lighthouse",
     prod={"tech": 18}, base={"wood": 70, "stone": 35, "tech": 15},
     sprite="Tower of Light", desc="Hải đăng cần Water và một Port kề bên.", priority=3)
_add("tower_light_1", "Tower of Light", "grass", tier=1, stage=2,
     family="tower_light", tags=("tower_light", "light", "magic_building"), rule="tower_light",
     base={"wood": 30, "stone": 20, "tech": 10}, sprite="Tower of Light",
     desc="Thắp sáng vùng xung quanh và ngăn bóng tối xâm nhập.", priority=5)
_add("tower_light_2", "Tower of Light", "grass", tier=2, stage=3,
     family="tower_light", tags=("tower_light", "light", "magic_building"),
     prod={"tech": 4}, base={"wood": 45, "stone": 30, "mana": 20},
     sprite="Tower of Light", desc="Tower of Light nâng cấp, tăng hiệu quả phòng thủ.")
_add("tower_water_1", "Tower of Water", "grass", tier=1, stage=2,
     family="tower_water", tags=("tower_water", "magic_building"), rule="tower_water",
     prod={"mana": 4, "tech": 3}, base={"wood": 35, "stone": 18, "mana": 10},
     sprite="Tower of Light", desc="Cần Water và Magical Village kề bên.", priority=7)

# Khu nghiên cứu và thành phố đặc biệt: các điều kiện được viết thành rule có tên.
_add("great_city_cities", "Great City of Cities", "grass", tier=1, stage=4,
     family="great_city", tags=("city", "city_level2", "great_city"), rule="great_city_cities",
     prod={"wood": 15, "stone": 15, "tech": 25},
     base={"wood": 100, "stone": 60, "tech": 35}, sprite="Market",
     desc="Cần bốn ô thành phố cấp 2+ liền kề.", priority=3)
_add("great_city_tech_magic", "Great City of Tech and Magic", "grass", tier=1, stage=4,
     family="great_city", tags=("city", "city_level2", "great_city", "tech_magic"),
     rule="great_city_tech_magic", prod={"mana": 20, "tech": 35},
     base={"wood": 100, "stone": 60, "mana": 40, "tech": 45}, sprite="Market",
     desc="Cần ít nhất hai thành phố cấp 2+ và một công trình phép thuật kề bên.", priority=4)
_add("magical_city_of_cities", "Magical City of Cities", "grass", tier=1, stage=4,
     family="great_city", tags=("magic", "city", "city_level2", "great_city"),
     rule="magical_city_of_cities", prod={"mana": 30, "tech": 25},
     base={"wood": 110, "stone": 60, "mana": 45, "tech": 35}, sprite="Market",
     desc="Bốn ô kề phải thuộc thành phố hoặc công trình phép thuật/ánh sáng.", priority=5)
_add("great_city_mining", "Great City of Mining", "grass", tier=1, stage=4,
     family="great_city", tags=("city", "city_level2", "great_city", "mining"),
     rule="great_city_mining", prod={"stone": 30, "tech": 25},
     base={"wood": 105, "stone": 70, "tech": 30}, sprite="Rocks 4",
     desc="Cần ba ô Rocks cấp 4 kề bên.", priority=3)
_add("great_city_stone_wood", "Great City of Stone and Wood", "grass", tier=1, stage=4,
     family="great_city", tags=("city", "city_level2", "great_city", "mining", "wood_city"),
     rule="great_city_stone_wood", prod={"stone": 20, "wood": 20, "tech": 20},
     base={"wood": 105, "stone": 70, "tech": 30}, sprite="Market",
     desc="Cần hai Rocks và hai Forest cấp 4+ kề bên.", priority=4)
_add("great_city_magical_mining", "Great City of Magical Mining", "grass", tier=1, stage=4,
     family="great_city", tags=("city", "city_level2", "great_city", "mining", "magic"),
     rule="great_city_magical_mining", prod={"stone": 20, "mana": 20, "tech": 25},
     base={"wood": 110, "stone": 65, "mana": 35, "tech": 35}, sprite="Market",
     desc="Cần hai Rocks cấp 4+ và Mushroom Forest/Tree Roots cấp 3+ kề bên.", priority=5)
_add("light_research_facility", "Light Research Facility", "grass", tier=1, stage=4,
     family="light_research", tags=("research", "light", "ending"), rule="light_research",
     prod={"tech": 25}, base={"tech": TECH_WIN},
     sprite="Tower of Light", desc="Tiêu tốn 600 Công nghệ để hoàn thành nhánh chiến thắng nghiên cứu ánh sáng.", priority=1)

# Nhà máy thuốc: hai lần nâng cấp chi phí Công nghệ được cộng đồng ghi nhận;
# cấp 3 là một trong các hướng chiến thắng ở bản Extended.
_add("potion_factory_1", "Potion Factory", "forest", tier=1, stage=4,
     family="potion_factory", tags=("potion_factory", "magic_building"), rule="potion_factory",
     prod={"mana": 20, "tech": 5}, base={"wood": 45, "stone": 25, "mana": 20},
     sprite="Workshop", desc="Cần Forest cấp 4 kề Tree Roots cấp 4; nhân đôi sản lượng Gỗ và Đá toàn bản đồ.", priority=1)
_add("potion_factory_2", "Potion Factory Level 2", "forest", tier=2, stage=4,
     family="potion_factory", tags=("potion_factory", "magic_building"),
     prod={"mana": 35, "tech": 15}, base={"tech": 300},
     sprite="Market", desc="Tốn 300 Công nghệ; nâng hệ số sản lượng Gỗ và Đá toàn bản đồ lên x3.")
_add("potion_factory_3", "Potion Factory Level 3", "forest", tier=3, stage=4,
     family="potion_factory", tags=("potion_factory", "magic_building", "ending"),
     prod={"mana": 60, "tech": 30}, base={"tech": 600},
     sprite="Market", desc="Nhánh chiến thắng Potion Factory trong bản Extended.")

# ---- Sprite pixel-art mở rộng (chỉ dùng hàm rect, không cần ảnh/phụ thuộc khác).
def _build_house(body='#b58a56', roof='#854c35', size=1, tint='#ffe588',
                 flag=False, chimney=False):
    s = []
    w = 20 + 8 * size
    x = (54 - w) // 2
    bottom = 50
    wall_y = bottom - 12 - size * 6
    rect(s, x - 2, bottom, w + 4, 3, '#765a40')
    _planks(s, x, wall_y, w, bottom-wall_y, body, '#79583d')
    _roof(s, x - 3, wall_y - 9, w + 6, roof, '#573223', 3, 3)
    for xx in range(x + 6, x + w - 6, 10):
        rect(s, xx, wall_y + 4, 4, 5, tint)
    rect(s, 26, bottom - 11, 5, 11, '#4a2d23')
    if chimney:
        rect(s, x + w - 9, wall_y - 13, 5, 9, '#858585')
    if flag:
        rect(s, 26, wall_y - 17, 2, 11, '#765133')
        rect(s, 28, wall_y - 17, 10, 5, '#e4c05c')
    return s


def _magic_house():
    s = _build_house(body='#76528c', roof='#633b86', size=1, tint='#e1b9ff')
    for x, y in ((11, 6), (42, 10), (8, 23)):
        rect(s, x, y, 4, 4, '#f0baff')
        rect(s, x+1, y-2, 2, 8, '#f0baff')
    return s


def _dock():
    s = []
    for x in range(6, 52, 8):
        rect(s, x, 20, 6, 31, '#67452d')
    rect(s, 4, 26, 46, 7, '#b1814d')
    rect(s, 4, 31, 46, 2, '#64462d')
    for x in range(6, 50, 8):
        rect(s, x, 27, 1, 5, '#dcb17a')
    return s


def _research():
    s = _build_house(body='#bbcbd4', roof='#687e8e', size=2, tint='#c3f9a1')
    rect(s, 24, 5, 6, 15, '#d3e6ed')
    rect(s, 18, 8, 18, 4, '#9ed7ed')
    rect(s, 21, 1, 12, 6, '#eaffaa')
    return s


def _potion():
    s = _build_house(body='#e7d4ad', roof='#824ea3', size=2, tint='#d3a2ec')
    for x in (11, 37):
        rect(s, x, 12, 6, 10, '#694381')
        rect(s, x + 1, 16, 4, 6, '#7bffa2')
    return s


def _stone_circle():
    s = []
    for x, y in ((7, 22), (19, 8), (33, 8), (45, 22),
                 (33, 38), (19, 38)):
        rect(s, x, y, 7, 10, '#ded7c5')
        rect(s, x+2, y-2, 3, 3, '#f0e3ad')
    rect(s, 23, 21, 10, 10, '#edce75')
    rect(s, 26, 14, 4, 23, '#fff1ad')
    return s


BUILD_SPRITES.update({
    'Village': _build_house(size=1),
    'Town': _build_house(size=2, chimney=True),
    'City': _build_house(body='#c0b5a0', roof='#6b5b68', size=3, chimney=True),
    'Mining Village': _build_house(body='#aaa9a4', roof='#55585c', size=1),
    'Mining City': _build_house(body='#b7c0c5', roof='#676a70', size=2, chimney=True),
    'Research City': _research(),
    'Light Research Facility': _research(),
    'Magic Village': _magic_house(),
    'Magical City': _build_house(body='#8a6b9f', roof='#6f4c95', size=3,
                                 tint='#dfb9fe', flag=True),
    'Port City': _build_house(body='#b89866', roof='#a1653b', size=2, flag=True),
    'Mainport': _port() + _build_house(size=2, flag=True),
    'Tower of Water': _tower_water(),
    'Dock': _dock(),
    'Tree Roots': _treehouse3(),
    'Treetop Village': _treehouse4(),
    'Forest 2': _treehouse2(),
    'Wooden City': _treehouse4(),
    'Mushroom Forest II': _magic_house(),
    'Mushroom Forest III': _build_house(body='#b681a8', roof='#a54369', size=2),
    'Potion Factory': _potion(),
    'Great City': _build_house(body='#d6c8b4', roof='#ae8648', size=3, flag=True),
    'Stone Circle': _stone_circle(),
})



# Gán hình phân biệt theo tên nhánh, giữ pixel rectangles tương thích Main.py.
_EXTRA_SPRITES = {
    "Mushroom City": _build_house(body="#9c779e", roof="#b65080", size=3, tint="#f4d3fa", flag=True),
    "Mushroom Port City": _port() + _build_house(body="#a07f9e", roof="#c858a1", size=1, tint="#f5d7f1"),
    "Tree Roots City": _treehouse4() + [(26, 6, 5, 6, "#c4e4b6")],
    "Tree Roots Port City": _port() + _treehouse3(),
    "Magical Port City": _port() + _magic_house(),
    "Magical Water City": _port() + _build_house(body="#6f89bd", roof="#627fa7", size=2, tint="#a6ffff"),
    "Wooden Port City": _port() + _treehouse2(),
    "Wooden Village II": _build_house(size=2, body="#ba9461"),
    "Magical Village II": _build_house(size=2, body="#86629d", roof="#7245a0", tint="#e9c6ff"),
    "Mining Village II": _build_house(size=2, body="#aaaaad", roof="#5d5961"),
    "Mainport II": _port() + _build_house(body="#a88d63", size=3, flag=True),
    "Port II": _port() + [(20, 12, 16, 6, "#d8bc86")],
    "Tower of Light II": _tower() + [(24, 1, 7, 7, "#fff6b5"), (16, 9, 22, 4, "#f2e28b")],
    "Tower of Water": _tower_water(),
    "Potion Factory II": _potion() + [(12, 16, 5, 6, "#66f2c7"), (39, 10, 5, 6, "#66f2c7")],
    "Potion Factory III": _potion() + [(23, 2, 9, 9, "#f2cfff"), (13, 6, 4, 4, "#93ffff")],
    "Stone Tech Center": _research() + [(10, 14, 8, 10, '#94999a')],
    "Mining Research City": _research() + [(41, 16, 6, 23, '#91918c')],
    "Lighthouse": _tower() + [(26, 0, 5, 6, "#fff7a0"), (11, 8, 33, 4, "#fff7b0")],
    "Great City of Tech and Magic": _build_house(body="#a48dab", roof="#76528e", size=3, flag=True, tint="#dcd8ff"),
    "Great City of Mining": _build_house(body="#b2b6bc", roof="#666b6c", size=3, flag=True),
    "Great City of Stone and Wood": _build_house(body="#bfa88d", roof="#765a48", size=3, flag=True),
    "Great City of Magical Mining": _build_house(body="#9ca8b8", roof="#835a95", size=3, flag=True),
    "Magical City of Cities": _build_house(body="#b68cb8", roof="#98629f", size=3, flag=True),
}
BUILD_SPRITES.update(_EXTRA_SPRITES)
SPRITE_BY_ID = {
    "mushroom_2": "Mushroom Forest II", "mushroom_3": "Mushroom Forest III",
    "dock": "Dock", "stone_circle_2": "Stone Circle",
    "tree_roots_1": "Tree Roots", "tree_roots_2": "Tree Roots", "tree_roots_3": "Tree Roots", "tree_roots_4": "Treetop Village",
    "treetop_village": "Treetop Village",
    "wooden_village": "Village", "wooden_village_2": "Wooden Village II", "wooden_city": "Wooden City",
    "wooden_city_2": "City", "wooden_port_city": "Wooden Port City",
    "mining_village": "Mining Village", "mining_village_2": "Mining Village II", "mining_city": "Mining City",
    "mining_research_facility": "Stone Tech Center", "mining_research_city_2": "Mining Research City",
    "magical_village": "Magic Village", "magical_village_2": "Magical Village II",
    "magical_city": "Magical City", "magical_port_city": "Magical Port City",
    "mushroom_city": "Mushroom City", "mushroom_port_city": "Mushroom Port City",
    "tree_roots_city": "Tree Roots City", "tree_roots_port_city": "Tree Roots Port City",
    "magical_water_city": "Magical Water City", "port": "Port", "port_2": "Port II",
    "mainport_1": "Mainport", "mainport_2": "Mainport II", "lighthouse": "Lighthouse",
    "tower_light_1": "Tower of Light", "tower_light_2": "Tower of Light II",
    "tower_water_1": "Tower of Water", "great_city_cities": "Great City",
    "great_city_tech_magic": "Great City of Tech and Magic", "magical_city_of_cities": "Magical City of Cities",
    "great_city_mining": "Great City of Mining", "great_city_stone_wood": "Great City of Stone and Wood",
    "great_city_magical_mining": "Great City of Magical Mining",
    "light_research_facility": "Light Research Facility",
    "potion_factory_1": "Potion Factory", "potion_factory_2": "Potion Factory II", "potion_factory_3": "Potion Factory III",
}
for _building_id, _sprite_name in SPRITE_BY_ID.items():
    STRUCTURES[_building_id]["sprite"] = _sprite_name


def _scaled(boost, factor):
    return {resource: value * factor for resource, value in boost.items()}


# id -> bonus cho ô kề bên. Sửa ở đây để cân bằng lại.
BOOST_BY_ID = {
    # Workshop (Gỗ + Đá)
    "wooden_village": _scaled(WORKSHOP_BOOST, 1),
    "wooden_village_2": _scaled(WORKSHOP_BOOST, 2),
    "wooden_city": _scaled(WORKSHOP_BOOST, 2),
    "wooden_city_2": _scaled(WORKSHOP_BOOST, 2),
    "mining_village": _scaled(WORKSHOP_BOOST, 1),
    "mining_village_2": _scaled(WORKSHOP_BOOST, 2),
    "mining_city": _scaled(WORKSHOP_BOOST, 2),
    # Magic Workshop (Gỗ + Mana)
    "magical_village": _scaled(MAGIC_WORKSHOP_BOOST, 1),
    "magical_village_2": _scaled(MAGIC_WORKSHOP_BOOST, 2),
    "magical_city": {"wood": 1.0, "mana": 1.0},   # +100% Gỗ và Mana cho ô xung quanh
    "magical_water_city": {"wood": 0.25, "mana": 0.25},
}
for _building_id, _boost in BOOST_BY_ID.items():
    STRUCTURES[_building_id]["boost"] = _boost

# Những ô Field có nhiều nhánh được xử lý bằng UPGRADES, không ép vào một
# đường tuyến tính duy nhất.
CHAINS = {
    "forest": [STRUCTURES[f"forest_{i}"] for i in range(1, 5)],
    "rock": [STRUCTURES[f"rock_{i}"] for i in range(1, 5)],
    "grass": [STRUCTURES["field"], STRUCTURES["wooden_village"],
              STRUCTURES["wooden_village_2"], STRUCTURES["wooden_city"],
              STRUCTURES["wooden_city_2"]],
    "mushroom": [STRUCTURES[f"mushroom_{i}"] for i in range(1, 4)],
    "circle": [STRUCTURES["stone_circle_1"], STRUCTURES["stone_circle_2"]],
    "water": [STRUCTURES["water_1"], STRUCTURES["dock"]],
}

# Hai nhánh của ô Field mà menu.py liệt kê riêng (xem _levels_text).
CHAINS["grass_magic"] = [STRUCTURES["field"], STRUCTURES["magical_village"],
                         STRUCTURES["magical_village_2"]]
CHAINS["grass_tower"] = [STRUCTURES["field"], STRUCTURES["tower_light_1"],
                         STRUCTURES["tower_light_2"]]

# Các công trình có thể xuất hiện tiếp theo tùy loại ô hiện tại.
UPGRADES = {
    "forest_1": ("forest_2", "treetop_village"), "forest_2": ("forest_3",),
    "forest_3": ("forest_4",), "forest_4": ("potion_factory_1",),
    "potion_factory_1": ("potion_factory_2",),
    "potion_factory_2": ("potion_factory_3",),
    "rock_1": ("rock_2",), "rock_2": ("rock_3",),
    "rock_3": ("rock_4",), "rock_4": (),
    "mushroom_1": ("mushroom_2",), "mushroom_2": ("mushroom_3",),
    "mushroom_3": (),
    "water_1": ("dock",), "dock": (),
    "stone_circle_1": ("stone_circle_2",), "stone_circle_2": (),
    "field": ("tree_roots_1", "tower_light_1", "tower_water_1", "lighthouse",
              "magical_water_city", "port", "wooden_village", "wooden_city",
              "mining_village", "magical_village", "mushroom_city",
              "tree_roots_city"),
    "tree_roots_1": ("tree_roots_2",), "tree_roots_2": ("tree_roots_3",),
    "tree_roots_3": ("tree_roots_4",), "tree_roots_4": (),
    "wooden_village": ("wooden_village_2",),
    "wooden_village_2": ("wooden_city",),
    "wooden_city": ("wooden_city_2",),
    "wooden_city_2": ("great_city_cities", "great_city_tech_magic",
                      "magical_city_of_cities"),
    "wooden_port_city": ("great_city_cities", "great_city_tech_magic"),
    "mining_village": ("mining_village_2",),
    "mining_village_2": ("mining_city",),
    "mining_city": ("mining_research_facility",),
    "mining_research_facility": ("mining_research_city_2",),
    "mining_research_city_2": ("great_city_cities", "great_city_tech_magic",
                                "great_city_mining", "great_city_stone_wood",
                                "great_city_magical_mining", "light_research_facility"),
    "magical_village": ("magical_village_2",),
    "magical_village_2": ("magical_city", "magical_water_city"),
    "magical_city": ("great_city_cities", "great_city_tech_magic", "magical_city_of_cities", "magical_water_city"),
    "mushroom_city": ("great_city_cities", "great_city_tech_magic", "magical_city_of_cities"),
    "mushroom_port_city": ("great_city_cities", "great_city_tech_magic"),
    "tree_roots_city": ("great_city_cities", "great_city_tech_magic", "magical_city_of_cities"),
    "tree_roots_port_city": ("great_city_cities", "great_city_tech_magic"),
    "magical_water_city": ("great_city_cities", "great_city_tech_magic", "magical_city_of_cities"),
    "port": ("port_2",),
    "port_2": ("mainport_1", "wooden_port_city", "magical_port_city",
               "mushroom_port_city", "tree_roots_port_city"),
    "mainport_1": ("mainport_2", "great_city_cities", "great_city_tech_magic"),
    "lighthouse": (), "tower_light_1": ("tower_light_2",),
    "tower_light_2": (), "tower_water_1": (), "great_city_cities": (),
    "great_city_tech_magic": (), "magical_city_of_cities": (),
    "great_city_mining": (), "great_city_stone_wood": (),
    "great_city_magical_mining": (), "light_research_facility": (),
}

# Các ID dùng trong cơ chế chiếu sáng/điều kiện lân cận.
TOWER_IDS = {"tower_light_1", "tower_light_2"}
CITY_IDS = {
    "wooden_city", "wooden_city_2", "wooden_port_city", "mining_city",
    "mining_research_city_2", "magical_city", "mushroom_city",
    "mushroom_port_city", "tree_roots_city", "tree_roots_port_city",
    "magical_water_city", "great_city_cities", "great_city_tech_magic",
    "magical_city_of_cities", "great_city_mining", "great_city_stone_wood",
    "great_city_magical_mining", "magical_port_city",
}
MAGIC_IDS = {
    "magical_village", "magical_village_2", "magical_city", "mushroom_city",
    "mushroom_port_city", "tree_roots_city", "tree_roots_port_city", "magical_port_city",
    "magical_water_city", "great_city_tech_magic", "magical_city_of_cities",
    "great_city_magical_mining", "tower_light_1", "tower_light_2",
    "tower_water_1", "potion_factory_1", "potion_factory_2",
    "potion_factory_3",
}


def _base_id(kind):
    return {
        "grass": "field", "forest": "forest_1", "rock": "rock_1",
        "mushroom": "mushroom_1", "water": "water_1", "circle": "stone_circle_1",
    }.get(kind, "field")


def level_info(kind, lvl):
    """Trả thông tin công trình thật; chấp nhận cả TileLevel và int cũ."""
    building_id = getattr(lvl, "building_id", None)
    if building_id in STRUCTURES:
        return STRUCTURES[building_id]
    chain = CHAINS.get(kind, ())
    try:
        level = int(lvl)
    except (TypeError, ValueError):
        level = 1
    if chain:
        return chain[max(0, min(level - 1, len(chain) - 1))]
    return STRUCTURES[_base_id(kind)]


def _state_info(pos, terrain, tiles):
    return level_info(terrain[pos], tiles.get(pos, 1))


def _adjacent(pos, terrain, tiles, excluded=()):
    """Trả các ô liền kề hợp lệ; có thể bỏ qua ô đã bị bóng tối nuốt."""
    excluded = excluded if isinstance(excluded, (set, frozenset)) else set(excluded)
    return [(q, terrain[q], _state_info(q, terrain, tiles))
            for q in neighbors(pos) if q in terrain and q not in excluded]


def _adj_count(pos, terrain, tiles, predicate, excluded=()):
    return sum(1 for q, kind, info in _adjacent(pos, terrain, tiles, excluded)
               if predicate(q, kind, info))


def _adj_has(pos, terrain, tiles, predicate, excluded=()):
    return _adj_count(pos, terrain, tiles, predicate, excluded) > 0


def _is_city(info):
    return "city" in info["tags"] or info["id"] in CITY_IDS


def _is_magic(info):
    return "magic" in info["tags"] or "magic_building" in info["tags"] or info["id"] in MAGIC_IDS


def _water_body_ports(pos, terrain, tiles):
    """Đếm Port/Mainport thuộc cùng một vùng nước liên thông.

    Một Port đứng trên ô đất kề nước; đếm Dock trên ô nước sẽ bỏ sót các
    Port thực sự. Duyệt tập ô nước liên thông rồi gom các công trình ven bờ.
    """
    starts = [q for q in neighbors(pos) if terrain.get(q) == "water"]
    seen = set(starts)
    queue = deque(starts)
    ports = set()
    while queue:
        water = queue.popleft()
        for near in neighbors(water):
            kind = terrain.get(near)
            if kind == "water" and near not in seen:
                seen.add(near)
                queue.append(near)
            elif kind == "grass" and _state_info(near, terrain, tiles)["id"] in {
                "port", "port_2", "mainport_1", "mainport_2"
            }:
                ports.add(near)
    return len(ports)


def _water_body_docks(pos, terrain, tiles):
    """API phụ để đọc số Dock vùng nước, không dùng cho yêu cầu Mainport."""
    starts = [q for q in neighbors(pos) if terrain.get(q) == "water"]
    seen, queue = set(starts), deque(starts)
    count = 0
    while queue:
        water = queue.popleft()
        if _state_info(water, terrain, tiles)["id"] == "dock":
            count += 1
        for near in neighbors(water):
            if terrain.get(near) == "water" and near not in seen:
                seen.add(near)
                queue.append(near)
    return count


def _requirement(target_id, pos, terrain, tiles, res=None):
    """Kiểm tra điều kiện địa hình của một nâng cấp; trả (đạt, lý do)."""
    rule = STRUCTURES[target_id]["rule"]
    adj = _adjacent(pos, terrain, tiles)
    has_forest = lambda q, k, i: k == "forest" and i["family"] == "forest"
    has_rock = lambda q, k, i: k == "rock" and i["family"] == "rock"
    has_water = lambda q, k, i: k == "water"
    has_mushroom = lambda q, k, i: i["family"] == "mushroom_forest"
    has_magic = lambda q, k, i: _is_magic(i)
    has_city = lambda q, k, i: _is_city(i)
    has_city2 = lambda q, k, i: "city_level2" in i["tags"] or i["id"] in CITY_IDS and i["tier"] >= 2
    has_tree_roots3 = lambda q, k, i: i["family"] == "tree_roots" and i["tier"] >= 3
    has_mushroom3 = lambda q, k, i: i["family"] == "mushroom_forest" and i["tier"] >= 3
    has_forest4 = lambda q, k, i: k == "forest" and i["family"] == "forest" and i["tier"] >= 4
    has_rock4 = lambda q, k, i: k == "rock" and i["family"] == "rock" and i["tier"] >= 4
    has_port_or_wood_city = lambda q, k, i: i["id"] in {
        "wooden_city", "wooden_city_2", "wooden_port_city", "port", "port_2",
        "mainport_1", "mainport_2", "magical_port_city", "mushroom_port_city",
        "tree_roots_port_city"
    }
    has_tower_light = lambda q, k, i: i["id"] in TOWER_IDS

    if rule == "always":
        return True, ""
    if rule == "adj_forest":
        return (_adj_has(pos, terrain, tiles, has_forest), "Cần có Forest kề bên.")
    if rule == "treetop_village":
        count = _adj_count(pos, terrain, tiles, lambda q, k, i:
                        k == "forest" and i["family"] == "forest" and i["tier"] == 1)
        return count >= 4, "Cần đủ bốn Forest cấp 1 ở các ô kề bên."
    if rule == "wooden_city_route":
        # Nhánh tiến hóa thường từ Wooden Village Level 2 không cần điều kiện này.
        if _state_info(pos, terrain, tiles)["id"] != "field":
            return True, ""
        forests = _adj_count(pos, terrain, tiles, has_forest)
        village = _adj_has(pos, terrain, tiles, lambda q, k, i:
                           "city_seed" in i["tags"] or i["family"] in {
                               "wood_village", "mining_village", "magic_village", "treetop_village"
                           })
        return forests >= 3 and village, "Cần ít nhất 3 Forest và một ngôi làng kề bên."
    if rule == "adj_rock":
        return (_adj_has(pos, terrain, tiles, has_rock), "Cần có Rocks kề bên.")
    if rule == "adj_mushroom":
        return (_adj_has(pos, terrain, tiles, has_mushroom), "Cần có Mushroom Forest kề bên.")
    if rule == "adj_water":
        return (_adj_has(pos, terrain, tiles, has_water), "Cần có Water kề bên.")
    if rule == "tree_roots_seed":
        forests = _adj_count(pos, terrain, tiles, has_forest)
        helper_building = _adj_has(
            pos, terrain, tiles,
            lambda q, k, i: "city_seed" in i["tags"] or has_port_or_wood_city(q, k, i)
        )
        return forests >= 3 and helper_building, "Cần 3 Forest và một Village/City kề bên."
    if rule == "tower_light":
        ok = _adj_has(pos, terrain, tiles, lambda q, k, i: i["id"] == "magical_village_2")
        return ok, "Cần có Magical Village cấp 2 kề bên."
    if rule == "tower_water":
        # Yêu cầu Tower of Water được người chơi công bố: Water + Magic Village.
        ok = _adj_has(pos, terrain, tiles, has_water) and _adj_has(
            pos, terrain, tiles,
            lambda q, k, i: i["id"] in {"magical_village", "magical_village_2"}
        )
        return ok, "Cần có Water và Magical Village ở các ô kề bên."
    if rule == "lighthouse":
        ok = _adj_has(pos, terrain, tiles, has_water) and _adj_has(
            pos, terrain, tiles, lambda q, k, i: i["id"] in {"port", "port_2", "mainport_1", "mainport_2"})
        return ok, "Cần có Water và Port kề bên."
    if rule == "wooden_port_city":
        ok = _adj_count(pos, terrain, tiles, has_forest4) >= 3 and _adj_has(pos, terrain, tiles, has_water)
        return ok, "Cần Water và ít nhất 3 Forest cấp 4 kề bên."
    if rule == "mushroom_city":
        return (_adj_has(pos, terrain, tiles, has_mushroom3), "Cần Mushroom Forest cấp 3 kề bên.")
    if rule == "mushroom_port_city":
        ok = _adj_has(pos, terrain, tiles, has_mushroom3) and _adj_has(pos, terrain, tiles, has_water)
        return ok, "Cần Mushroom Forest cấp 3 và Water kề bên."
    if rule == "tree_roots_city":
        return (_adj_has(pos, terrain, tiles, has_tree_roots3), "Cần Tree Roots cấp 3 trở lên kề bên.")
    if rule == "tree_roots_port_city":
        ok = _adj_has(pos, terrain, tiles, has_tree_roots3) and _adj_has(pos, terrain, tiles, has_water)
        return ok, "Cần Tree Roots cấp 3+ và Water kề bên."
    if rule == "magical_city":
        return (_adj_has(pos, terrain, tiles, has_tower_light), "Cần có Tower of Light kề bên.")
    if rule == "magical_port_city":
        ok = _adj_has(pos, terrain, tiles, has_water) and _adj_has(pos, terrain, tiles, has_tower_light)
        return ok, "Cần Water và Tower of Light kề bên."
    if rule == "magical_water_city":
        ok = _adj_has(pos, terrain, tiles, has_water) and _adj_has(pos, terrain, tiles, has_magic)
        return ok, "Cần Water và một công trình phép thuật đã xây kề bên."
    if rule == "mainport_1":
        # Ghi nhận người chơi: 3 Port cùng một vùng nước để có Mainport.
        ports_ok = _water_body_ports(pos, terrain, tiles) >= 3
        city_nearby = _adj_has(pos, terrain, tiles, lambda q, k, i: _is_city(i))
        return ports_ok and not city_nearby, (
            "Cần ít nhất 3 Port cùng vùng nước và không có City kề bên."
        )
    if rule == "mainport_2":
        # Mốc 4 Port là quy ước cân bằng của bản Python, chưa xác minh số gốc.
        return (_water_body_ports(pos, terrain, tiles) >= 4,
                "Cần ít nhất 4 Port/Mainport trong vùng nước liên thông.")
    if rule == "great_city_cities":
        ok = _adj_count(pos, terrain, tiles, has_city2) >= 4
        return ok, "Cần 4 thành phố cấp 2 trở lên ở các ô liền kề."
    if rule == "great_city_tech_magic":
        cities = _adj_count(pos, terrain, tiles, has_city2)
        magic = _adj_count(pos, terrain, tiles, has_magic)
        allowed = _adj_count(pos, terrain, tiles, lambda q, k, i:
                             (_is_city(i) and i["tier"] >= 2) or has_magic(q, k, i) or i["id"] in TOWER_IDS)
        ok = cities >= 2 and magic >= 1 and allowed == len(adj)
        return ok, "Cần ít nhất 2 thành phố cấp 2+, 1 công trình phép thuật; các ô kề còn lại phải là thành phố/phép thuật/Tower of Light."
    if rule == "magical_city_of_cities":
        ok = len(adj) == 4 and all(_is_city(i) or has_magic(q, k, i) or i["id"] in TOWER_IDS
                                   for q, k, i in adj)
        return ok, "Cả 4 ô kề phải là thành phố hoặc công trình phép thuật/ánh sáng."
    if rule == "great_city_mining":
        return (_adj_count(pos, terrain, tiles, has_rock4) >= 3, "Cần 3 Rocks cấp 4 kề bên.")
    if rule == "great_city_stone_wood":
        rocks = _adj_count(pos, terrain, tiles, has_rock4)
        forests = _adj_count(pos, terrain, tiles, has_forest4)
        return (rocks >= 2 and forests >= 2, "Cần 2 Rocks và 2 Forest cấp 4+ kề bên.")
    if rule == "great_city_magical_mining":
        rocks = _adj_count(pos, terrain, tiles, has_rock4)
        magic_land = _adj_has(pos, terrain, tiles, lambda q, k, i: has_mushroom3(q, k, i) or has_tree_roots3(q, k, i))
        return (rocks >= 2 and magic_land, "Cần 2 Rocks cấp 4+ và Mushroom Forest/Tree Roots cấp 3+ kề bên.")
    if rule == "light_research":
        has_tech = (res or {}).get("tech", 0) >= TECH_WIN
        return has_tech, f"Cần đủ {TECH_WIN} Công nghệ để xây Light Research Facility."
    if rule == "potion_factory":
        ok = _adj_has(pos, terrain, tiles, lambda q, k, i: i["family"] == "tree_roots" and i["tier"] >= 4)
        return ok, "Cần Tree Roots cấp 4 kề bên Forest cấp 4."
    return False, "Điều kiện nâng cấp chưa được định nghĩa."


def _cost_for(target, counts):
    """Tính giá tăng dần theo số lần đã xây cùng công trình/cấp đích."""
    count = counts.get((target["id"], target["tier"]), 0)
    cost = {}
    for resource in RES_VI:
        value = target["base"].get(resource, 0) + count * target["step"].get(resource, 0)
        if value > 0:
            cost[resource] = int(value) if float(value).is_integer() else value
    return cost


def _available_targets(pos, terrain, tiles, counts, res=None):
    """Các đích nâng cấp hợp lệ, sắp xếp lựa chọn đủ tiền lên trước."""
    current = _state_info(pos, terrain, tiles)
    choices = []
    blocked_reasons = []
    for target_id in UPGRADES.get(current["id"], ()):
        target = STRUCTURES[target_id]
        ok, reason = _requirement(target_id, pos, terrain, tiles, res)
        if not ok:
            blocked_reasons.append((target.get("priority", 50), target, reason))
            continue
        cost = _cost_for(target, counts)
        affordable = res is not None and all(res.get(k, 0) >= v for k, v in cost.items())
        # Chỉ dùng priority để sắp xếp HUD mặc định; UI vẫn cho chọn nhánh khác.
        choices.append((0 if affordable else 1, target.get("priority", 50), target, cost))
    choices.sort(key=lambda item: (item[0], item[1], item[2]["name"]))
    return choices, blocked_reasons


def available_upgrades(pos, terrain, tiles, counts, res=None, *, affordable_only=False):
    """Trả danh sách nhánh nâng cấp hợp lệ cho UI; không sửa trạng thái game."""
    if pos not in terrain:
        return []
    choices, _ = _available_targets(pos, terrain, tiles, counts, res)
    result = []
    for _, _, target, cost in choices:
        affordable = res is not None and all(res.get(k, 0) >= value for k, value in cost.items())
        if affordable_only and not affordable:
            continue
        result.append({
            "id": target["id"],
            "name": target["name"],
            "tier": target["tier"],
            "cost": dict(cost),
            "affordable": affordable,
            "structure": target,
        })
    return result


def _first_blocked_reason(pos, terrain, tiles, counts, res=None):
    current = _state_info(pos, terrain, tiles)
    options = UPGRADES.get(current["id"], ())
    if not options:
        return "Ô này đã ở cấp tối đa."
    _, blocked = _available_targets(pos, terrain, tiles, counts, res)
    if blocked:
        blocked.sort(key=lambda item: (item[0], item[1]["name"]))
        return blocked[0][2]
    # Có nhánh hợp lệ nhưng thiếu tài nguyên: báo theo nhánh ưu tiên nhất.
    target = STRUCTURES[options[0]]
    cost = _cost_for(target, counts)
    deficits = [f"thiếu {RES_VI[k]} ({res.get(k, 0)}/{v})"
                for k, v in cost.items() if res is not None and res.get(k, 0) < v]
    if deficits:
        return "; ".join(deficits)
    return "Chưa đủ điều kiện nâng cấp."


def new_resources():
    return {"wood": 10, "stone": 0, "mana": 0, "tech": 0}


def new_carry():
    return {resource: 0.0 for resource in RES_VI}


def cost_text(cost):
    parts = [f"{cost[k]} {RES_VI[k]}" for k in RES_VI if cost.get(k, 0) > 0]
    return ", ".join(parts) if parts else "Miễn phí"


def effect_text(lv):
    """Hiển thị sản lượng/phút kèm các hiệu ứng kinh tế quan trọng."""
    prod = lv.get("prod", {})
    parts = [f"{prod[k]:g} {RES_VI.get(k, k)}/phút" for k in RES_VI if k in prod]
    building_id = lv.get("id")
    if building_id == "potion_factory_1":
        parts.append("nhân đôi sản lượng Gỗ và Đá toàn bản đồ")
    elif building_id in {"potion_factory_2", "potion_factory_3"}:
        parts.append("nhân ba sản lượng Gỗ và Đá toàn bản đồ")
    elif building_id == "magical_water_city":
        parts.append("có thể tăng sản lượng Potion Factory khi đủ công trình kề bên")
    boost = lv.get("boost")
    if boost:
        parts.append(f"{BOOST_NEIGHBORS} ô xung quanh: " + ", ".join(
            f"+{value * 100:g}% {RES_VI.get(k, k)}" for k, value in boost.items()))
    if parts:
        return ", ".join(parts)
    return lv.get("desc") or "Không tạo tài nguyên trực tiếp."


def next_level(pos, terrain, tiles, counts, res=None, dark_cells=()):
    """Trả (thông tin công trình kế tiếp, giá hiện tại) hoặc None.

    Với nhiều nhánh, Main.py dùng bộ chọn của can_upgrade trước khi gọi upgrade;
    lời gọi trực tiếp không có lựa chọn sẽ chọn nhánh đủ giá và ưu tiên cao.
    Tương thích cách gọi cũ next_level(pos, terrain, tiles, counts, dark_cells).
    """
    if res is not None and not isinstance(res, dict):
        dark_cells, res = res, None
    if pos not in terrain or pos in dark_cells:
        return None
    choices, _ = _available_targets(pos, terrain, tiles, counts, res)
    if not choices:
        return None
    _, _, target, cost = choices[0]
    return target, cost


# Khi Main.py gọi can_upgrade -> upgrade không truyền target_id, lưu lựa chọn
# của một lần bấm ở đây. Không sửa tiles/counts/res cho tới khi upgrade thành công.
_PENDING_TARGET = None


def _choose_upgrade_gui(options):
    """Hộp thoại chọn nhánh (chỉ hiện khi đang chạy giao diện game Tkinter).

    Trả (handled, target_id): handled=False khi chạy headless/test.
    Nhấn Escape/Đóng = hủy giao dịch; không mua nhầm nhánh khác.
    """
    try:
        import tkinter as tk
        root = tk._default_root
        if root is None or not root.winfo_exists() or "Stop the Darkness" not in root.title():
            return False, None
        dialog = tk.Toplevel(root)
        dialog.title("Chọn công trình để xây")
        dialog.configure(bg="#e7e1d5")
        dialog.resizable(False, False)
        dialog.transient(root)
        selected = {"id": None}
        tk.Label(dialog, text="CHỌN NHÁNH NÂNG CẤP", bg="#e7e1d5",
                 fg="#302c26", font=("Arial", 12, "bold")).pack(padx=18, pady=(14, 6))
        tk.Label(dialog, text="Các công trình mở khóa tại ô này:", bg="#e7e1d5",
                 fg="#514a41").pack(padx=16, pady=(0, 7))
        region = tk.Frame(dialog, bg="#e7e1d5")
        region.pack(padx=12, fill="x")
        def confirm(target_id):
            selected["id"] = target_id
            dialog.destroy()
        for index, option in enumerate(options, 1):
            label = (f"{index}. {option['name']}  (cấp {option['tier']})\n"
                     f"     {cost_text(option['cost'])}"
                     f"{'  [ĐỦ]' if option['affordable'] else '  [THIẾU]'}")
            btn = tk.Button(region, text=label, anchor="w", justify="left",
                            width=47, relief="groove", pady=3,
                            command=lambda key=option["id"]: confirm(key),
                            state="normal" if option["affordable"] else "disabled")
            btn.pack(fill="x", pady=2)
            if option["affordable"]:
                dialog.bind(str(index), lambda e, key=option["id"]: confirm(key))
        tk.Button(dialog, text="Hủy (Esc)", command=dialog.destroy,
                  width=18, bg="#dad1c2").pack(pady=(10, 12))
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() - dialog.winfo_width()) // 2
        y = root.winfo_rooty() + (root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.grab_set()
        dialog.focus_force()
        root.wait_window(dialog)
        return True, selected["id"]
    except (ImportError, RuntimeError):
        return False, None


def can_upgrade(pos, terrain, tiles, counts, dark_cells, res, over=False, target_id=None):
    global _PENDING_TARGET
    _PENDING_TARGET = None
    if over:
        return False, "Game đã kết thúc."
    if pos not in terrain:
        return False, "Ô không hợp lệ."
    if pos in dark_cells:
        return False, "Ô này đã bị bóng tối nuốt."
    current = _state_info(pos, terrain, tiles)
    options = UPGRADES.get(current["id"], ())
    if not options:
        return False, "Ô này đã ở cấp tối đa."

    if target_id is not None:
        if target_id not in options or target_id not in STRUCTURES:
            return False, "Công trình được chọn không phải nhánh nâng cấp của ô này."
        ok, reason = _requirement(target_id, pos, terrain, tiles, res)
        if not ok:
            return False, reason
        cost = _cost_for(STRUCTURES[target_id], counts)
        deficits = [f"thiếu {RES_VI[k]} ({res.get(k, 0)}/{v})"
                    for k, v in cost.items() if res.get(k, 0) < v]
        return (False, "; ".join(deficits)) if deficits else (True, "")

    choices, _ = _available_targets(pos, terrain, tiles, counts, res)
    if not choices:
        return False, _first_blocked_reason(pos, terrain, tiles, counts, res)
    affordable = [choice for choice in choices if all(res.get(k, 0) >= v for k, v in choice[3].items())]
    if not affordable:
        _, _, target, cost = choices[0]
        deficits = [f"thiếu {RES_VI[k]} ({res.get(k, 0)}/{v})"
                    for k, v in cost.items() if res.get(k, 0) < v]
        return False, "; ".join(deficits) if deficits else "Không đủ tài nguyên."
    if len(choices) > 1 and target_id is None:
        options = available_upgrades(pos, terrain, tiles, counts, res)
        handled, selection = _choose_upgrade_gui(options)
        if handled:
            if selection is None:
                return False, "Đã hủy lựa chọn công trình."
            _PENDING_TARGET = (id(tiles), pos, selection)
    return True, ""


def upgrade(pos, terrain, tiles, counts, res, target_id=None, dark_cells=()):
    """Xây công trình hợp lệ, trừ tài nguyên theo kiểu atomic và trả tên/cấp.

    Main.py vẫn gọi can_upgrade trước để xử lý trạng thái game/tối. Hàm này tự
    kiểm tra lại nhánh, điều kiện kề và tài nguyên để tránh trừ âm nếu được gọi
    trực tiếp bởi module khác.
    """
    global _PENDING_TARGET
    if target_id is not None and not isinstance(target_id, str):
        dark_cells, target_id = target_id, None      # cách gọi cũ: upgrade(..., res, dark_cells)
    if pos not in terrain:
        raise ValueError("Ô không hợp lệ.")
    if target_id is None and _PENDING_TARGET and _PENDING_TARGET[:2] == (id(tiles), pos):
        target_id = _PENDING_TARGET[2]
    _PENDING_TARGET = None

    current = _state_info(pos, terrain, tiles)
    options = UPGRADES.get(current["id"], ())
    if not options:
        raise ValueError("Ô này đã ở cấp tối đa.")

    if target_id is None:
        info = next_level(pos, terrain, tiles, counts, res)
    elif target_id in options and target_id in STRUCTURES:
        ok, reason = _requirement(target_id, pos, terrain, tiles, res)
        info = (STRUCTURES[target_id], _cost_for(STRUCTURES[target_id], counts)) if ok else None
        if not ok:
            raise ValueError(reason)
    else:
        info = None

    if info is None:
        raise ValueError("Không có công trình kế tiếp đã mở khóa cho lựa chọn này.")

    target, cost = info
    deficits = [f"thiếu {RES_VI[resource]} ({res.get(resource, 0)}/{amount})"
                for resource, amount in cost.items()
                if res.get(resource, 0) < amount]
    if deficits:
        raise ValueError("; ".join(deficits))

    # Chỉ trừ sau khi đã kiểm tra đủ tất cả tài nguyên: tránh trạng thái nửa chừng.
    for resource, amount in cost.items():
        res[resource] = res.get(resource, 0) - amount
    tiles[pos] = TileLevel(target["stage"], target["id"])
    count_key = (target["id"], target["tier"])
    counts[count_key] = counts.get(count_key, 0) + 1
    return target["name"], target["tier"]

def describe(pos, terrain, tiles, counts, res, dark_cells=()):
    """Trả nội dung khung ô theo đúng giao diện mà Main.py đang gọi."""
    if pos not in terrain:
        return ["Ô không hợp lệ"], "", [], ""
    if pos in dark_cells:
        return ["Ô đã bị bóng tối nuốt"], "", [], ""
    cur = _state_info(pos, terrain, tiles)
    tier_label = f" cấp {cur['tier']}" if cur["tier"] > 0 else ""
    now = [f"{cur['name']}{tier_label}", "Sản lượng: " + effect_text(cur)]
    if not UPGRADES.get(cur["id"], ()):
        now.append("Đã đạt cấp tối đa")
        return now, "", [], ""
    choices, blocked = _available_targets(pos, terrain, tiles, counts, res)
    if not choices:
        _, why = (blocked[0][0], blocked[0][2]) if blocked else (50, "Chưa đủ điều kiện nâng cấp.")
        return now, "Chưa mở khóa công trình kế tiếp", [], why
    _, _, nxt, cost = choices[0]
    nxt_tier = f" cấp {nxt['tier']}" if nxt["tier"] > 0 else ""
    title = f"Nâng cấp tiếp theo: {nxt['name']}{nxt_tier}"
    details = [f"Chi phí: {cost_text(cost)}", "Sản lượng: " + effect_text(nxt)]
    # Bộ chọn hiển thị trong kinhte.can_upgrade() khi bấm ô có nhiều nhánh.
    alternates = [choice[2]["name"] for choice in choices if choice[2]["id"] != nxt["id"]]
    if alternates:
        details.append("Nhánh khác có thể chọn: " + ", ".join(alternates))
    deficits = [f"Thiếu {RES_VI[k]} ({res.get(k, 0)}/{v})"
                for k, v in cost.items() if res.get(k, 0) < v]
    return now, title, details, "; ".join(deficits)


def towers(terrain, tiles):
    """Trả các nguồn sáng; không thay đổi API của dark.is_lit().

    Tower cấp 2 được mở rộng từ bán kính Manhattan 2 -> 3 bằng cách thêm
    bốn điểm chiếu sáng phụ. Lighthouse cũng chiếu sáng bán kính 2.
    """
    emitters = set()
    for pos in terrain:
        building_id = _state_info(pos, terrain, tiles)["id"]
        if building_id in TOWER_IDS or building_id == "lighthouse":
            emitters.add(pos)
        if building_id == "tower_light_2":
            for p in neighbors(pos):
                if p in terrain:
                    emitters.add(p)
    return sorted(emitters)


def _all_info(terrain, tiles, dark_cells=()):
    for pos in terrain:
        if pos not in dark_cells:
            yield pos, _state_info(pos, terrain, tiles)


def _boost_adjacent(pos, terrain, tiles, excluded=()):
    """Các ô nằm trong phạm vi bonus kiểu Workshop (4 hoặc 8 ô xung quanh)."""
    excluded = excluded if isinstance(excluded, (set, frozenset)) else set(excluded)
    offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if BOOST_NEIGHBORS >= 8:
        offsets += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    result = []
    for dr, dc in offsets:
        q = (pos[0] + dr, pos[1] + dc)
        if q in terrain and q not in excluded:
            result.append((q, terrain[q], _state_info(q, terrain, tiles)))
    return result


def _local_multipliers(pos, terrain, tiles, excluded, info=None):
    """Hệ số nhân sản lượng của ô pos do các ô kề bên (rừng, đá, nấm, dock, thành phố).

    Dùng chung cho income() và boost_at() để hai nơi không bao giờ lệch số.
    """
    info = info or _state_info(pos, terrain, tiles)
    nearby = _adjacent(pos, terrain, tiles, excluded)
    wood_neighbors = sum(1 for q, kind, inf in nearby
                         if kind == "forest" and inf["family"] == "forest")
    rock_neighbors = sum(1 for q, kind, inf in nearby
                         if kind == "rock" and inf["family"] == "rock" and inf["tier"] >= 2)
    mush_neighbors = sum(1 for q, kind, inf in nearby
                         if inf["family"] == "mushroom_forest" and inf["tier"] >= 2)
    city_neighbors = sum(1 for q, kind, inf in nearby if _is_city(inf))
    dock_neighbors = sum(1 for q, kind, inf in nearby if inf["id"] == "dock")
    mana = 1.0 + MUSHROOM_ADJACENCY_BONUS * mush_neighbors
    if _is_magic(info):
        mana += DOCK_MAGIC_BONUS * dock_neighbors
    # Bonus kiểu Workshop của các công trình xung quanh (8 ô), cộng dồn theo từng tài nguyên.
    workshop = {}
    for _q, _kind, inf in _boost_adjacent(pos, terrain, tiles, excluded):
        for resource, value in inf.get("boost", {}).items():
            workshop[resource] = workshop.get(resource, 0.0) + value
    return {
        "wood": 1.0 + WOOD_ADJACENCY_BONUS * wood_neighbors + workshop.get("wood", 0.0),
        "stone": 1.0 + ROCK_ADJACENCY_BONUS * rock_neighbors + workshop.get("stone", 0.0),
        "mana": mana + workshop.get("mana", 0.0),
        "tech": 1.0 + CITY_TECH_BONUS * city_neighbors + workshop.get("tech", 0.0),
    }


def boost_at(pos, terrain, tiles, dark_cells=()):
    """Hệ số nhân sản lượng của ô pos do ô kề bên (API cũ của Main.py).
    Ô bị bóng tối nuốt không còn tạo bonus."""
    return _local_multipliers(pos, terrain, tiles, set(dark_cells or ()))


def income(terrain, tiles, dark_cells):
    """Tính sản lượng/phút sau khi áp dụng hiệu ứng lân cận/toàn bản đồ.

    * Mỗi Forest đang tồn tại kề một ô sẽ cộng 25% vào sản lượng Gỗ của ô đó.
    * Rock/Mushroom/City tăng sản lượng tương ứng theo hệ số cân bằng mô phỏng.
    * Dock kề công trình phép thuật tăng sản lượng Mana theo DOCK_MAGIC_BONUS.
    * Làng/thành phố có `boost` (Workshop / Magic Workshop, xem BOOST_BY_ID) tăng
      sản lượng của các ô xung quanh (BOOST_NEIGHBORS = 8); nhiều ô cộng dồn.
    * Potion Factory cấp 1/2+ nhân x2/x3 sản lượng Gỗ và Đá toàn bản đồ.
    * Potion Factory nhận hệ số 2.25x khi kề Magical Water City và thành phố này
      kề Great City of Tech and Magic; nếu Factory đồng thời kề Water, nhân 1.5x.

    Ô đã bị bóng tối nuốt không sản xuất và không còn tạo bonus lân cận.
    """
    excluded = set(dark_cells or ())
    active = list(_all_info(terrain, tiles, excluded))
    total = {resource: 0.0 for resource in RES_VI}

    potion_tier = max((info["tier"] for _, info in active
                       if info["family"] == "potion_factory"), default=0)
    wood_stone_multiplier = 3.0 if potion_tier >= 2 else 2.0 if potion_tier == 1 else 1.0

    def is_forest(_q, kind, info):
        # Chỉ ô còn là Forest thật mới tạo bonus; Potion Factory đã thay thế Forest.
        return kind == "forest" and info["family"] == "forest"

    def is_dock(_q, _kind, info):
        return info["id"] == "dock"

    def is_water(_q, kind, _info):
        return kind == "water"

    def is_great_tech_magic(_q, _kind, info):
        return info["id"] == "great_city_tech_magic"

    def is_magical_water_city(_q, _kind, info):
        return info["id"] == "magical_water_city"

    for pos, info in active:
        # Bonus của Potion Factory. Loại trừ ô tối để công trình đã bị nuốt không
        # tiếp tục tăng sản lượng của công trình khác.
        multiplier = 1.0
        if info["family"] == "potion_factory":
            touches_water = _adj_has(pos, terrain, tiles, is_water, excluded)
            for q, _kind, neighbor_info in _adjacent(pos, terrain, tiles, excluded):
                if neighbor_info["id"] == "magical_water_city" and _adj_has(
                    q, terrain, tiles, is_great_tech_magic, excluded
                ):
                    multiplier *= 2.25
                    if touches_water:
                        multiplier *= 1.5
                    break

        local = _local_multipliers(pos, terrain, tiles, excluded, info)
        for resource, amount in info["prod"].items():
            local_multiplier = local.get(resource, 1.0)
            global_multiplier = (
                wood_stone_multiplier if resource in ("wood", "stone") else 1.0
            )
            total[resource] += amount * local_multiplier * global_multiplier * multiplier

    return {resource: round(value, 4) for resource, value in total.items()}

# ---------- tương thích API của phiên bản cũ (chuỗi CHAINS / ô "tower") ----------
CIRCLE_COST = dict(STRUCTURES["stone_circle_2"]["base"])   # = chi phí kích hoạt vòng đá


def chain_at(pos, terrain, tiles=None, dark_cells=()):
    """Chuỗi cấp tuyến tính theo loại ô. Nhánh Field thật nằm ở UPGRADES."""
    return CHAINS.get(terrain[pos], CHAINS["grass"])


def level_at(pos, terrain, lvl):
    return level_info(terrain[pos], lvl)


def reset_terrain(terrain):
    """Bản cũ đổi ô Tower thành terrain "tower"; bản mới giữ terrain là cỏ nên chỉ
    cần trả các ô "tower" sót lại (nếu có) về cỏ khi bắt đầu ván mới."""
    for p, kind in terrain.items():
        if kind == "tower":
            terrain[p] = "grass"


def produce(terrain, tiles, dark_cells, res, carry):
    """Cộng sản lượng mỗi nhịp; giữ phần thập phân để không mất tài nguyên."""
    for resource, per_minute in income(terrain, tiles, dark_cells).items():
        carry[resource] = carry.get(resource, 0.0) + per_minute * PER_TICK
        whole = int(carry[resource] + 1e-9)
        if whole > 0:
            res[resource] = res.get(resource, 0) + whole
            carry[resource] = max(0.0, carry[resource] - whole)


def check_win(terrain, tiles, res):
    """Kiểm tra các hướng chiến thắng có trong bộ công trình.

    Stone Circle cấp 2 và Light Research Facility là hai cách thắng chuẩn.
    Potion Factory cấp 3 chỉ thắng ở mode Extended khi được chọn rõ ràng.
    Tower of Light và lượng Tech thô không tự động kết thúc ván.
    """
    built = {_state_info(pos, terrain, tiles)["id"] for pos in terrain}
    if "stone_circle_2" in built:
        return "CHIẾN THẮNG! Stone Circle Level 2 đã chặn bóng tối."
    if "light_research_facility" in built:
        return "CHIẾN THẮNG! Light Research Facility đã tìm ra cách ngăn bóng tối."
    if GAME_MODE == "extended" and "potion_factory_3" in built:
        return "CHIẾN THẮNG! Potion Factory Level 3 đã hoàn tất nhánh giả kim."
    return None



# Những loại luật này đều phải có nhánh xử lý tường minh trong _requirement.
# Validator dùng danh sách này để phát hiện công trình được khai báo nhưng quên code điều kiện.
RULE_HANDLERS = frozenset({
    "always", "adj_forest", "treetop_village", "wooden_city_route", "adj_rock",
    "adj_mushroom", "adj_water", "tree_roots_seed", "tower_light", "tower_water",
    "lighthouse", "wooden_port_city", "mushroom_city", "mushroom_port_city",
    "tree_roots_city", "tree_roots_port_city", "magical_city", "magical_port_city",
    "magical_water_city", "mainport_1", "mainport_2", "great_city_cities",
    "great_city_tech_magic", "magical_city_of_cities", "great_city_mining",
    "great_city_stone_wood", "great_city_magical_mining", "light_research",
    "potion_factory",
})
BASE_BUILDINGS = frozenset({
    "field", "forest_1", "rock_1", "mushroom_1", "water_1", "stone_circle_1",
})


def validate_catalog():
    """Rà tính nhất quán catalog; trả danh sách lỗi (rỗng nghĩa là pass)."""
    errors = []
    required_keys = {"id", "name", "kind", "tier", "stage", "family", "tags",
                     "prod", "base", "step", "rule", "sprite", "desc", "priority", "boost"}
    resource_keys = set(RES_VI)
    valid_kinds = {"grass", "forest", "rock", "mushroom", "water", "circle"}

    for building_id, info in STRUCTURES.items():
        missing = required_keys - set(info)
        if missing:
            errors.append(f"{building_id}: thiếu field {sorted(missing)}")
        if info.get("id") != building_id:
            errors.append(f"{building_id}: ID trong record không khớp key")
        if info.get("kind") not in valid_kinds:
            errors.append(f"{building_id}: loại địa hình không hợp lệ {info.get('kind')!r}")
        if info.get("rule") not in RULE_HANDLERS:
            errors.append(f"{building_id}: chưa có handler cho rule {info.get('rule')!r}")
        sprite = info.get("sprite")
        if sprite is not None and sprite not in BUILD_SPRITES:
            errors.append(f"{building_id}: sprite {sprite!r} không có trong BUILD_SPRITES")
        if sprite is not None and sprite in BUILD_SPRITES:
            for pixel in BUILD_SPRITES[sprite]:
                if len(pixel) != 5 or not all(isinstance(v, (int, float)) for v in pixel[:4]):
                    errors.append(f"{building_id}: sprite {sprite!r} có hình chữ nhật lỗi")
                    break
        if not isinstance(info.get("priority"), int):
            errors.append(f"{building_id}: priority phải là số nguyên")
        if not isinstance(info.get("name"), str) or not info["name"].strip():
            errors.append(f"{building_id}: thiếu tên hợp lệ")
        for section in ("prod", "base", "step"):
            for resource, value in info.get(section, {}).items():
                if resource not in resource_keys:
                    errors.append(f"{building_id}.{section}: tài nguyên lạ {resource}")
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                    errors.append(f"{building_id}.{section}.{resource}: giá trị phải là số không âm")
        for resource, value in info.get("boost", {}).items():
            if resource not in resource_keys:
                errors.append(f"{building_id}.boost: tài nguyên lạ {resource}")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                errors.append(f"{building_id}.boost.{resource}: giá trị phải là số không âm")
        if not isinstance(info.get("tier"), int) or info["tier"] < 0:
            errors.append(f"{building_id}: tier phải là số nguyên không âm")
        if not isinstance(info.get("stage"), int) or not 1 <= info["stage"] <= 4:
            errors.append(f"{building_id}: stage phải là số nguyên từ 1 đến 4")
        if not isinstance(info.get("tags"), (set, frozenset, tuple, list)):
            errors.append(f"{building_id}: tags phải là một tập hợp")

    incoming = {building_id: [] for building_id in STRUCTURES}
    for source, targets in UPGRADES.items():
        if source not in STRUCTURES:
            errors.append(f"UPGRADES: nguồn không tồn tại {source}")
            continue
        if len(targets) != len(set(targets)):
            errors.append(f"UPGRADES[{source}]: có nhánh nâng cấp bị lặp")
        for target in targets:
            if target not in STRUCTURES:
                errors.append(f"UPGRADES[{source}]: đích không tồn tại {target}")
            else:
                incoming[target].append(source)
                if STRUCTURES[target]["kind"] != STRUCTURES[source]["kind"]:
                    errors.append(f"UPGRADES[{source}] => {target}: khác loại địa hình")

    for building_id, sources in incoming.items():
        if building_id not in BASE_BUILDINGS and not sources:
            errors.append(f"{building_id}: công trình không có đường nâng cấp đi tới")

    # Tìm các ID có thể đi tới từ địa hình/công trình khởi đầu.
    reachable = set(BASE_BUILDINGS)
    pending = deque(BASE_BUILDINGS)
    while pending:
        source = pending.popleft()
        for target in UPGRADES.get(source, ()):
            if target in STRUCTURES and target not in reachable:
                reachable.add(target)
                pending.append(target)
    for building_id in sorted(set(STRUCTURES) - reachable):
        errors.append(f"{building_id}: không thể tiếp cận từ công trình khởi đầu")

    # Phát hiện vòng lặp trong đồ thị nâng cấp.
    visiting, visited = set(), set()
    def visit(node):
        if node in visiting:
            errors.append(f"UPGRADES: phát hiện vòng lặp qua {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for target in UPGRADES.get(node, ()):
            if target in STRUCTURES:
                visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in STRUCTURES:
        visit(node)

    return errors
