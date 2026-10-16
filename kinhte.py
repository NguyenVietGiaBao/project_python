"""Kinh tế: tài nguyên, công trình, chi phí, sản xuất, điều kiện xây."""
from map import neighbors, rect, TERRAIN_VI

RES_VI = {"wood": "Gỗ", "stone": "Đá", "mana": "Mana", "tech": "Tech"}
TECH_WIN = 60
TOWERS_WIN = 2

BUILDINGS = {
    "Lumber Camp": {"terrain": "forest", "cost": {"wood": 5}, "gives": {"wood": 2},
                    "desc": "+2 gỗ/lượt"},
    "Quarry": {"terrain": "rock", "cost": {"wood": 10}, "gives": {"stone": 2},
               "desc": "+2 đá/lượt"},
    "Workshop": {"terrain": "grass", "cost": {"wood": 15, "stone": 5},
                 "gives": {"tech": 1}, "near_building": ["Lumber Camp", "Quarry"],
                 "desc": "+1 tech/lượt. Cần Lumber Camp hoặc Quarry kề bên"},
    "Port": {"terrain": "grass", "cost": {"wood": 20}, "gives": {"tech": 2},
             "near_terrain": "water", "desc": "+2 tech/lượt. Cần nước kề bên"},
    "Market": {"terrain": "mushroom", "cost": {"wood": 20, "stone": 10},
               "gives": {"tech": 1, "mana": 1},
               "desc": "+1 tech, +1 mana/lượt (rừng nấm cũng cho +1 gỗ/lượt)"},
    "Tower of Light": {"terrain": "grass",
                       "cost": {"wood": 30, "stone": 20, "tech": 10}, "gives": {},
                       "near_building": ["Workshop"],
                       "desc": "Đốt tan bóng tối trong bán kính 2 ô. Cần Workshop kề bên"},
}


# ---------- sprite công trình
def _lumber():
    """Con thỏ trắng thay cho Lumber Camp."""
    s = []
    rect(s, 16, 2, 6, 20, "#ffffff")    # tai trái
    rect(s, 18, 6, 2, 14, "#f4a6b8")
    rect(s, 30, 2, 6, 20, "#ffffff")    # tai phải
    rect(s, 32, 6, 2, 14, "#f4a6b8")
    rect(s, 14, 20, 24, 16, "#ffffff")  # đầu
    rect(s, 19, 25, 3, 3, "#222222")    # mắt
    rect(s, 30, 25, 3, 3, "#222222")
    rect(s, 25, 30, 3, 3, "#f4a6b8")    # mũi
    rect(s, 12, 34, 30, 16, "#ffffff")  # thân
    rect(s, 12, 46, 30, 4, "#d8d8d8")
    rect(s, 12, 48, 10, 4, "#e8e8e8")   # chân
    rect(s, 32, 48, 10, 4, "#e8e8e8")
    rect(s, 40, 38, 8, 8, "#f2f2f2")    # đuôi
    return s


def _quarry():
    s = []
    rect(s, 8, 28, 16, 14, "#d0d0d0")
    rect(s, 28, 24, 18, 18, "#bdbdbd")
    rect(s, 18, 12, 16, 14, "#e6e6e6")
    rect(s, 8, 39, 16, 3, "#8a8a8a")
    rect(s, 28, 39, 18, 3, "#8a8a8a")
    rect(s, 38, 4, 3, 20, "#6b4a2b")
    rect(s, 31, 4, 17, 4, "#444444")
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


BUILD_SPRITES = {"Lumber Camp": _lumber(), "Quarry": _quarry(), "Workshop": _workshop(),
                 "Port": _port(), "Market": _market(), "Tower of Light": _tower()}


# ---------- luật kinh tế
def new_resources():
    return {"wood": 10, "stone": 0, "mana": 0, "tech": 0}


def cost_text(cost):
    return ", ".join(f"{v} {RES_VI[k]}" for k, v in cost.items())


def towers(buildings):
    return [p for p, b in buildings.items() if b == "Tower of Light"]


def can_build(pos, name, terrain, buildings, dark_cells, res, over=False):
    b = BUILDINGS[name]
    if over:
        return False, "Game đã kết thúc"
    if pos in dark_cells:
        return False, "Ô này đã bị bóng tối nuốt"
    if pos in buildings:
        return False, "Đã có công trình"
    if terrain[pos] != b["terrain"]:
        return False, f"Cần ô {TERRAIN_VI[b['terrain']]}"
    if "near_building" in b and not any(
            buildings.get(n) in b["near_building"] for n in neighbors(pos)):
        return False, "Cần " + " / ".join(b["near_building"]) + " kề bên"
    if "near_terrain" in b and not any(
            terrain[n] == b["near_terrain"] for n in neighbors(pos)):
        return False, f"Cần {TERRAIN_VI[b['near_terrain']]} kề bên"
    for k, v in b["cost"].items():
        if res[k] < v:
            return False, f"Thiếu {RES_VI[k]} ({res[k]}/{v})"
    return True, ""


def build(pos, name, buildings, res):
    """Trừ tài nguyên và đặt công trình (đã kiểm tra can_build trước)."""
    for k, v in BUILDINGS[name]["cost"].items():
        res[k] -= v
    buildings[pos] = name


def income(terrain, buildings, dark_cells):
    """Tài nguyên thu được mỗi nhịp (hiện cạnh số trên HUD)."""
    inc = {"wood": 0, "stone": 0, "mana": 0, "tech": 0}
    for name in buildings.values():
        for k, v in BUILDINGS[name]["gives"].items():
            inc[k] += v
    for p, t in terrain.items():
        if t == "mushroom" and p not in dark_cells:
            inc["wood"] += 1
    return inc


def produce(terrain, buildings, dark_cells, res):
    """Mỗi nhịp: công trình sinh tài nguyên; rừng nấm chưa bị tối cho +1 gỗ."""
    for k, v in income(terrain, buildings, dark_cells).items():
        res[k] += v


def check_win(buildings, res):
    """Trả về thông báo thắng hoặc None."""
    if len(towers(buildings)) >= TOWERS_WIN:
        return "CHIẾN THẮNG! Các Tower of Light đã soi sáng vùng đất."
    if res["tech"] >= TECH_WIN:
        return "CHIẾN THẮNG! Công nghệ đã đánh bại bóng tối."
    return None