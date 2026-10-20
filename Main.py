"""Điểm vào của game. Chạy:  python main.py"""
import random
import tkinter as tk
from tkinter import messagebox, simpledialog

import kinhte
import scores
import theme
from kinhte import BUILD_SPRITES
from dark import Darkness, GRACE_TICKS, TICK_MS, dark_interval, is_lit
from map import COLS, ROWS, SIZE, GRASS, TERRAIN_VI, generate_map
from menu import PANEL_W, MenuFrame, GamePanel, show_guide, show_scores


# Sprite của bản đồ được thiết kế trên lưới 54 px; giữ nguyên kích thước pixel-art
# thay vì thu nhỏ còn 44 px để hiển thị sắc nét và gần tỉ lệ game gốc hơn.
VIEW_CELL = SIZE


def pick_tutorial_tile(terrain):
    """Chọn 1 ô rừng để mũi tên chỉ vào: ưu tiên ô xa rìa (bóng tối đến sau cùng)."""
    forests = [p for p, t in terrain.items() if t == "forest"]
    inner = [(r, c) for r, c in forests
             if min(r, c, ROWS - 1 - r, COLS - 1 - c) >= 2]
    return random.choice(inner or forests) if forests else None


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Stop the Darkness    ")
        root.configure(bg="#000")
        root.resizable(False, False)
        self.playing = False
        self.paused = False
        self.speed = 1
        self.after_id = None
        self._closed = False

        # Dọn bộ hẹn giờ trước khi đóng để tránh callback gọi vào cửa sổ đã hủy.
        root.protocol("WM_DELETE_WINDOW", self.close)

        frame = tk.Frame(root, bg="#000")
        frame.grid(row=0, column=0)
        self.canvas = tk.Canvas(frame, width=COLS * VIEW_CELL, height=ROWS * VIEW_CELL,
                                bg=GRASS, highlightthickness=0)
        self.canvas.pack(padx=3, pady=3)
        self.canvas.bind("<Button-1>", self.on_click)    # bấm vào ô = nâng cấp ô đó
        self.canvas.bind("<Motion>", self.on_motion)     # rê chuột = xem thông tin ô

        self.panel = tk.Frame(root, bg=theme.c("panel"), width=PANEL_W, height=ROWS * VIEW_CELL + 6)
        self.panel.grid(row=0, column=1, sticky="ns")
        self.panel.pack_propagate(False)
        self.menu = MenuFrame(self.panel, self.play, self.regenerate,
                              lambda: show_guide(self.root),
                              lambda: show_scores(self.root),
                              self.toggle_theme)
        self.hud = GamePanel(self.panel, self.toggle_pause, self.back_to_menu,
                             lambda: self.set_speed(self.speed % 3 + 1),
                             self.toggle_theme)

        root.bind("<space>", lambda e: self.toggle_pause())
        root.bind("<t>", lambda e: self.toggle_theme())
        root.bind("<F1>", lambda e: show_guide(self.root))
        for n in (1, 2, 3):
            root.bind(str(n), lambda e, n=n: self.set_speed(n))
        self.dark = Darkness()
        self.terrain, self.sprites = generate_map(exact_center=True)
        self.reset_state()
        self.show_menu()
        self.draw()

    # ---------- chuyển màn hình
    def show_menu(self):
        self.hud.frame.pack_forget()
        self.menu.frame.pack(fill="both", expand=True, padx=8, pady=8)

    def show_game(self):
        self.menu.frame.pack_forget()
        self.hud.frame.pack(fill="both", expand=True, padx=8, pady=8)

    # ---------- trạng thái ván chơi
    def reset_state(self):
        """Đặt lại toàn bộ trạng thái mô phỏng, không tạo thêm bộ hẹn giờ."""
        self._cancel_timer()
        kinhte.reset_terrain(self.terrain)   # ô Tower của ván trước trở về cỏ
        self.tiles = {}       # {(r, c): cấp} chỉ lưu ô đã nâng (cấp >= 2)
        self.counts = {}      # {(loại ô, cấp): số lần đã nâng lên cấp đó} -> giá tăng dần
        self.carry = kinhte.new_carry()  # phần lẻ tài nguyên chưa đủ 1 đơn vị
        self.dark.reset()
        self.paused = False
        self.hud.set_paused(False)
        self.speed = 1
        self.hud.set_speed(1)
        self.res = kinhte.new_resources()
        self.turn, self.selected, self.over = 1, None, False
        self.active_ticks = 0  # số nhịp mô phỏng kể từ khi xây công trình đầu tiên
        self.dark_timer = 0    # số nhịp từ lần bóng tối tiến gần nhất
        self.dark_moves = 0    # số lần bóng tối đã tiến (quyết định tốc độ nuốt)
        self.build_turn = None   # None = chưa bắt đầu; thời gian và bóng tối vẫn đứng yên
        self.hud.clear_log()

    def new_map(self):
        self.terrain, self.sprites = generate_map()

    def regenerate(self):
        self.new_map()
        self.reset_state()
        self.draw()

    def play(self):
        self._cancel_timer()
        self.playing = True
        self.reset_state()
        self.show_game()
        # như game gốc: chọn sẵn 1 ô rừng (khung + mũi tên xanh chỉ vào ô đó)
        self.selected = pick_tutorial_tile(self.terrain)
        self.refresh()
        self.schedule()

    def back_to_menu(self):
        self._cancel_timer()
        self.playing = False
        self.new_map()
        self.reset_state()
        self.show_menu()
        self.draw()

    # ---------- luật chơi
    def upgrade(self, pos):
        """Bấm vào ô: nâng lên cấp kế tiếp nếu đủ điều kiện, không thì báo lý do."""
        if not self.playing or self.over or pos not in self.terrain:
            return
        ok, reason = kinhte.can_upgrade(pos, self.terrain, self.tiles, self.counts,
                                        self.dark.cells, self.res, self.over)
        if not ok:
            self.hud.say(reason)
            self.draw_overlay()
            self.refresh_info()
            return
        name, lvl = kinhte.upgrade(pos, self.terrain, self.tiles, self.counts, self.res,
                                   self.dark.cells)
        started_simulation = self.build_turn is None
        if started_simulation:
            self.build_turn = self.turn
            self.hud.say("Bóng tối bắt đầu lan ra...")
        self.hud.say(f"{name} lên cấp {lvl}.")
        if name == "Tower of Light":
            self.hud.say("Tower of Light làm bóng tối tiến chậm lại.")
        # Tower mới có hiệu lực ngay: xua bóng tối trong vùng sáng và kiểm tra thắng
        cleared = self.dark.clear_lit(kinhte.towers(self.terrain, self.tiles))
        if cleared:
            self.hud.say(f"Ánh sáng xua tan {cleared} ô bóng tối.")
        self.check_end()
        if self.playing and not self.over:
            self.refresh()
            if started_simulation and not self.paused:
                self.schedule()

    def end_turn(self):
        """Chạy một nhịp mô phỏng: sản xuất, chiếu sáng, lan bóng tối, kiểm tra kết thúc."""
        if self.over or not self.playing or self.paused or self.build_turn is None:
            # Không xây gì thì game đứng yên; khi tạm dừng cũng không xử lý nhịp.
            return

        self.active_ticks += 1
        kinhte.produce(self.terrain, self.tiles, self.dark.cells, self.res, self.carry)
        tw = kinhte.towers(self.terrain, self.tiles)
        cleared = self.dark.clear_lit(tw)
        if cleared:
            self.hud.say(f"Ánh sáng xua tan {cleared} ô bóng tối.")

        # Bóng tối tiến sau mỗi DARK_EVERY nhịp kể từ khi người chơi bắt đầu xây.
        # Trước đây elapsed == 0 cũng thỏa phép chia dư, khiến bóng tối xuất hiện ngay
        # ở nhịp đầu tiên, trái với mô tả luật chơi.
        # Có Tower of Light thì khoảng cách giữa hai lần tiến dài hơn (dark_interval).
        self.dark_timer += 1
        if self.dark_timer >= dark_interval(tw):
            self.dark_timer = 0
            self.dark_moves += 1
            darkness_step = GRACE_TICKS + self.dark_moves - 1
            for msg in self.dark.advance(darkness_step, tw, self.tiles):
                self.hud.say(msg)

        self.turn += 1
        self.check_end()
        if self.playing and not self.over:
            self.refresh()

    def _cancel_timer(self):
        """Hủy callback đang chờ một cách an toàn; có thể gọi nhiều lần."""
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                # Cửa sổ có thể đã đóng hoặc callback vừa được Tk lấy khỏi hàng đợi.
                pass
            finally:
                self.after_id = None

    def schedule(self):
        """Chỉ duy trì một bộ hẹn giờ khi game đang thực sự chạy."""
        self._cancel_timer()
        if self._closed or not self.playing or self.over or self.paused or self.build_turn is None:
            return
        delay = max(1, int(TICK_MS / self.speed))
        self.after_id = self.root.after(delay, self.on_timer)

    def on_timer(self):
        # Callback đã được lấy khỏi hàng đợi nên không còn ID đang chờ.
        self.after_id = None
        if self._closed:
            return
        if self.playing and not self.over and not self.paused:
            self.end_turn()
        if self.playing and not self.over and not self.paused:
            self.schedule()

    def set_speed(self, speed):
        """Đổi tốc độ x1/x2/x3; chỉ thay nhịp thời gian, không tạo timer trùng."""
        if not self.playing or self.over:
            return
        try:
            speed = int(speed)
        except (TypeError, ValueError):
            return
        if speed not in (1, 2, 3):
            return
        self.speed = speed
        self.hud.set_speed(speed)
        if not self.paused:
            self.schedule()

    def toggle_theme(self):
        """Đổi giao diện sáng/tối: tô lại panel, các cửa sổ phụ và vẽ lại bản đồ."""
        old = theme.mode
        new = theme.toggle()
        theme.recolor(self.root, old, new)
        self.menu.theme_btn.config(text=theme.label())
        self.hud.theme_btn.config(text=theme.label())
        self.draw()
        if self.playing:
            self.refresh_info()

    def toggle_pause(self):
        if not self.playing or self.over:
            return
        self.paused = not self.paused
        self.hud.set_paused(self.paused)
        if self.paused:
            # Dừng hẳn timer để tránh callback lặp vô ích trong lúc tạm dừng.
            self._cancel_timer()
        else:
            self.schedule()

    def check_end(self):
        if self.over:
            return
        win = kinhte.check_win(self.terrain, self.tiles, self.res)
        if win:
            self.finish(win, won=True)
        elif self.dark.lost():
            self.finish("THUA CUỘC! Bóng tối đã nuốt chửng vùng đất.", won=False)

    def finish(self, msg, won=False):
        if self.over:
            return
        self.over = True
        self._cancel_timer()
        self.hud.say(msg)
        self.refresh()
        if won:
            score = scores.calc_score(self.turn, len(self.dark.cells), len(self.tiles))
            messagebox.showinfo("Stop the Darkness", f"{msg}\n\nĐiểm của bạn: {score}", parent=self.root)
            if scores.qualifies(score):
                name = simpledialog.askstring(
                    "Bảng xếp hạng", "Bạn vào top! Nhập tên (tối đa 12 ký tự):",
                    parent=self.root)
                # Hủy hộp thoại thì bỏ qua việc ghi tên; nhập chuỗi rỗng vẫn có thể là Ẩn danh.
                if name is not None:
                    rank = scores.add_score(name, score, self.turn)
                    if rank:
                        messagebox.showinfo("Bảng xếp hạng", f"Bạn đứng hạng #{rank}!", parent=self.root)
        else:
            messagebox.showinfo("Stop the Darkness", msg, parent=self.root)
        if not self._closed:
            self.back_to_menu()

    def close(self):
        """Đóng cửa sổ sau khi hủy callback, tránh tác vụ nền chạy sót."""
        if self._closed:
            return
        self._closed = True
        self.playing = False
        self._cancel_timer()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ---------- giao diện
    def cell_at(self, event):
        c, r = event.x // VIEW_CELL, event.y // VIEW_CELL
        return (r, c) if 0 <= r < ROWS and 0 <= c < COLS else None

    def on_motion(self, event):
        """Rê chuột qua ô nào thì khung bên phải hiện thông tin ô đó."""
        if not self.playing or self.over:
            return
        pos = self.cell_at(event)
        if pos and pos != self.selected:
            self.selected = pos
            self.draw_overlay()
            self.refresh_info()

    def on_click(self, event):
        if not self.playing or self.over:
            return
        pos = self.cell_at(event)
        if pos:
            self.selected = pos
            self.upgrade(pos)

    def refresh(self):
        self.draw()
        if not self.playing:
            return
        self.refresh_hud()
        self.refresh_info()

    def refresh_hud(self):
        if self.build_turn is None:
            inc = {k: 0 for k in kinhte.RES_VI}  # chưa bắt đầu: chưa thu gì
        else:
            inc = kinhte.income(self.terrain, self.tiles, self.dark.cells)
        self.hud.set_resources(self.res, inc)

    def refresh_info(self):
        """Khung thông tin: ô hiện tại + chi phí và sản lượng của cấp kế tiếp."""
        if not self.selected:
            self.hud.show_tile("Rê chuột vào một ô để xem, bấm để nâng cấp.")
            return
        pos = self.selected
        head = f"Ô ({pos[0]},{pos[1]}): {TERRAIN_VI[self.terrain[pos]]}"
        if pos in self.dark.cells:
            self.hud.show_tile(head, ["BỊ BÓNG TỐI NUỐT"])
            return
        now, next_title, nxt, warn = kinhte.describe(
            pos, self.terrain, self.tiles, self.counts, self.res, self.dark.cells)
        self.hud.show_tile(head, now, next_title, nxt, warn)

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        cv.config(bg=theme.tint(GRASS))
        tw = kinhte.towers(self.terrain, self.tiles)
        k = VIEW_CELL / SIZE  # giữ sprite 1:1 để pixel-art sắc nét, không hở đường nối

        def paint(ox, oy, rects, tint=True):
            for x, y, w, h, col in rects:
                if tint:
                    col = theme.tint(col)
                cv.create_rectangle(ox + round(x * k), oy + round(y * k),
                                    ox + round((x + w) * k), oy + round((y + h) * k),
                                    fill=col, outline=col)

        for (r, c), rects in self.sprites.items():
            ox, oy = c * VIEW_CELL, r * VIEW_CELL
            if (r, c) in self.dark.cells:  # bị nuốt: đen kịt, xoá sạch hình bên dưới
                cv.create_rectangle(ox, oy, ox + VIEW_CELL, oy + VIEW_CELL,
                                    fill="#000000", outline="#000000")
                continue
            paint(ox, oy, rects)
            lvl = self.tiles.get((r, c), 1)
            if lvl >= 2:
                sp = kinhte.level_at((r, c), self.terrain, lvl)["sprite"]
                if sp:
                    # Tower luôn sáng rực, không bị làm tối theo giao diện
                    paint(ox, oy, BUILD_SPRITES[sp], tint=sp != "Tower of Light")
                for i in range(lvl - 1):  # mỗi chấm vàng = 1 cấp đã nâng
                    x = ox + 3 + i * 7
                    cv.create_rectangle(x, oy + VIEW_CELL - 9, x + 5, oy + VIEW_CELL - 4,
                                        fill="#ffd54a", outline="#7a5a00")
            if self.playing and is_lit((r, c), tw):
                cv.create_rectangle(ox + 2, oy + 2, ox + VIEW_CELL - 2, oy + VIEW_CELL - 2,
                                    outline="#ffe66d", width=2, dash=(4, 3))
        self.draw_overlay()

    def draw_overlay(self):
        """Lớp vẽ nhẹ nằm trên bản đồ (khung tím, khung chọn, mũi tên); vẽ lại khi rê chuột."""
        cv = self.canvas
        cv.delete("ov")
        # khung tím báo hiệu chỉ hiện khi bóng tối đã bắt đầu lan
        if self.playing and not self.over and self.build_turn is not None:
            nxt = self.dark.current_cell()
            if nxt:
                r, c = nxt
                cv.create_rectangle(c * VIEW_CELL + 4, r * VIEW_CELL + 4, (c + 1) * VIEW_CELL - 4,
                                    (r + 1) * VIEW_CELL - 4, outline="#b36bff", width=2,
                                    tags="ov")
        if self.playing and self.selected:
            r, c = self.selected
            cv.create_rectangle(c * VIEW_CELL + 2, r * VIEW_CELL + 2, (c + 1) * VIEW_CELL - 2,
                                (r + 1) * VIEW_CELL - 2, outline="#1e90ff", width=3, tags="ov")
            if self.build_turn is None:  # mũi tên hướng dẫn chỉ hiện trước nước đi đầu tiên
                cx, top = c * VIEW_CELL + VIEW_CELL // 2, max(r * VIEW_CELL - 2, 14)
                cv.create_polygon(cx - 7, top - 12, cx + 7, top - 12, cx, top,
                                  fill="#1e90ff", outline="#0b5cad", tags="ov")


def main():
    """Khởi chạy ứng dụng desktop."""
    root = tk.Tk()
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()