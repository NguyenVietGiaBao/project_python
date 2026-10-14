"""Bóng tối: các vòng, tốc độ tiến, ánh sáng của Tower, điều kiện thua."""
from map import ROWS, COLS

LIGHT_RADIUS = 2
TICK_MS = 1500     # mỗi nhịp (ms): sản xuất tài nguyên + bóng tối tiến lên
GRACE_TICKS = 4    # số nhịp đầu tiên chưa có bóng tối
STEP_EVERY = 50    # cứ sau bấy nhiêu nhịp, bóng tối nhanh thêm 1 ô/nhịp (tối đa 3)
LOSE_RATIO = 0.6


def ring_cells(k):
    """Các ô của vòng thứ k (0 = ngoài cùng), đi theo chiều kim đồng hồ."""
    top, left, bottom, right = k, k, ROWS - 1 - k, COLS - 1 - k
    if top > bottom or left > right:
        return []
    cells = [(top, c) for c in range(left, right + 1)]
    cells += [(r, right) for r in range(top + 1, bottom + 1)]
    if bottom > top:
        cells += [(bottom, c) for c in range(right - 1, left - 1, -1)]
    if right > left:
        cells += [(r, left) for r in range(bottom - 1, top, -1)]
    return cells


RINGS = [ring_cells(k) for k in range(min(ROWS, COLS) // 2)]


def is_lit(pos, tower_list):
    return any(abs(pos[0] - t[0]) + abs(pos[1] - t[1]) <= LIGHT_RADIUS
               for t in tower_list)


class Darkness:
    def __init__(self):
        self.reset()

    def reset(self):
        self.cells = set()
        self.ring, self.idx = 0, 0  # bóng tối bắt đầu từ vòng ngoài cùng

    def clear_lit(self, tower_list):
        """Xua tan các ô tối nằm trong vùng sáng. Trả về số ô được xoá."""
        cleared = {p for p in self.cells if is_lit(p, tower_list)}
        self.cells -= cleared
        return len(cleared)

    def current_cell(self):
        """Ô tiếp theo bóng tối sẽ nuốt (để vẽ khung báo hiệu) hoặc None."""
        if self.ring < len(RINGS) and self.idx < len(RINGS[self.ring]):
            return RINGS[self.ring][self.idx]
        return None

    def advance(self, turn, tower_list, buildings):
        """Bóng tối tiến theo chiều kim đồng hồ dọc từng vòng, từ ngoài vào trong.
        Có thể xoá công trình khỏi `buildings`. Trả về danh sách thông báo."""
        msgs = []
        steps = min(1 + (turn - GRACE_TICKS) // STEP_EVERY, 3)
        while steps > 0 and self.ring < len(RINGS):
            cells = RINGS[self.ring]
            if self.idx >= len(cells):
                self.ring += 1
                self.idx = 0
                if self.ring < len(RINGS):
                    msgs.append(f"Bóng tối tiến vào vòng {self.ring + 1}!")
                continue
            pos = cells[self.idx]
            self.idx += 1
            if is_lit(pos, tower_list):  # ô được Tower soi sáng thì bóng tối bỏ qua
                continue
            self.cells.add(pos)
            steps -= 1
            if pos in buildings:
                msgs.append(f"{buildings[pos]} bị bóng tối phá huỷ!")
                del buildings[pos]
        return msgs

    def lost(self):
        return len(self.cells) > ROWS * COLS * LOSE_RATIO