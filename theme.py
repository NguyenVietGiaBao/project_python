"""Giao diện sáng/tối: bảng màu, đổi màu widget đang có, làm tối bản đồ, nhớ lựa chọn."""
import json
import os
from functools import lru_cache

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme.json")

PALETTES = {
    "light": {"panel": "#cdc8b8", "box": "#ebe7dc", "ink": "#2b2b2b",
              "active": "#f6f3ea", "disabled": "#9a9a9a", "muted": "#555555",
              "faint": "#777777", "text2": "#444444", "warn": "#aa3333",
              "box_off": "#d9d5c8", "off_ink": "#888888"},
    "dark": {"panel": "#2a2d36", "box": "#3a3e4a", "ink": "#e8e6df",
             "active": "#4a4f5e", "disabled": "#7a7e8b", "muted": "#b0aea6",
             "faint": "#8d909b", "text2": "#cfcdc5", "warn": "#ff7b72",
             "box_off": "#32353f", "off_ink": "#6b6f7c"},
}
NAMES = {"light": "Sáng", "dark": "Tối"}
MAP_DIM = 0.6   # bản đồ ở chế độ tối: nhân mỗi kênh màu với hệ số này

mode = "light"


def _load():
    global mode
    try:
        with open(FILE, encoding="utf-8") as f:
            m = json.load(f).get("mode")
        if m in PALETTES:
            mode = m
    except (OSError, ValueError, AttributeError):
        pass


_load()


def c(role):
    """Màu của vai trò `role` theo giao diện hiện tại."""
    return PALETTES[mode][role]


def label():
    return f"Giao diện: {NAMES[mode]}"


def toggle():
    """Đổi sáng <-> tối, lưu lại, trả về chế độ mới."""
    global mode
    mode = "dark" if mode == "light" else "light"
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump({"mode": mode}, f)
    except OSError:
        pass
    return mode


@lru_cache(maxsize=None)
def _dim(col):
    r, g, b = (int(col[i:i + 2], 16) for i in (1, 3, 5))
    return f"#{int(r * MAP_DIM):02x}{int(g * MAP_DIM):02x}{int(b * MAP_DIM):02x}"


def tint(col):
    """Màu dùng để vẽ bản đồ: giữ nguyên khi sáng, tối đi khi ở chế độ tối."""
    return _dim(col) if mode == "dark" else col


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def recolor(root, old, new):
    """Đổi màu mọi widget (kể cả cửa sổ phụ) từ bảng màu `old` sang `new`."""
    rev = {v.lower(): role for role, v in PALETTES[old].items()}
    opts = ("background", "foreground", "activebackground", "disabledforeground")
    for w in _walk(root):
        for opt in opts:
            try:
                role = rev.get(str(w.cget(opt)).lower())
            except Exception:       # widget không có tuỳ chọn này
                continue
            if role:
                w.configure(**{opt: PALETTES[new][role]})
