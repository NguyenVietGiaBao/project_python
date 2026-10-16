"""Bảng xếp hạng: tính điểm, lưu/đọc top điểm cao vào scores.json."""
import json
import os
from datetime import datetime

from map import ROWS, COLS

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")
MAX_ENTRIES = 10

WIN_BONUS = 1000     # điểm cơ bản khi thắng
TIME_MAX = 1000      # thưởng thời gian tối đa, giảm dần theo số nhịp
TIME_PER_TICK = 8    # mỗi nhịp trôi qua trừ bấy nhiêu điểm thưởng thời gian
DARK_PT = 3          # thưởng cho mỗi ô chưa bị bóng tối nuốt
BUILD_PT = 10        # thưởng cho mỗi công trình còn sống


def calc_score(turn, dark_count, building_count):
    """Điểm của một ván thắng: thắng càng nhanh, giữ đất càng nhiều càng cao."""
    time_bonus = max(0, TIME_MAX - turn * TIME_PER_TICK)
    land_bonus = (ROWS * COLS - dark_count) * DARK_PT
    return WIN_BONUS + time_bonus + land_bonus + building_count * BUILD_PT


def load():
    """Đọc danh sách điểm; file thiếu hoặc hỏng thì trả về danh sách rỗng."""
    try:
        with open(FILE, encoding="utf-8") as f:
            data = json.load(f)
        return [e for e in data
                if isinstance(e, dict) and "name" in e and "score" in e]
    except (OSError, ValueError):
        return []


def add_score(name, score, turn):
    """Thêm điểm vào bảng. Trả về hạng (1..MAX_ENTRIES) hoặc None nếu không vào top."""
    name = (name or "").strip()[:12] or "Ẩn danh"
    entry = {"name": name, "score": score, "turn": turn,
             "date": datetime.now().strftime("%d/%m/%Y")}
    entries = load()
    entries.append(entry)
    entries.sort(key=lambda e: e["score"], reverse=True)  # sort ổn định: hoà điểm thì ai có trước đứng trên
    entries = entries[:MAX_ENTRIES]
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except OSError:
        return None
    for i, e in enumerate(entries):
        if e is entry:
            return i + 1
    return None


def qualifies(score):
    """Điểm này có vào được top không (để quyết định có hỏi tên hay không)."""
    entries = load()
    return len(entries) < MAX_ENTRIES or score > entries[-1]["score"]


def table_text():
    entries = load()
    if not entries:
        return "Chưa có ai trên bảng xếp hạng.\nHãy thắng một ván để ghi tên!"
    lines = [f"{'#':>2}  {'Tên':<12} {'Điểm':>5}  {'Nhịp':>4}  Ngày"]
    for i, e in enumerate(entries, 1):
        lines.append(f"{i:>2}. {e['name']:<12} {e['score']:>5}  "
                     f"{e.get('turn', '?'):>4}  {e.get('date', '')}")
    return "\n".join(lines)
