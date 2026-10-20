"""Điểm vào của game. Chạy:  python main.py"""
import random
import tkinter as tk
from tkinter import messagebox, simpledialog

import kinhte
import scores
import theme
from kinhte import BUILD_SPRITES
from dark import Darkness, GRACE_TICKS, TICK_MS, DARK_EVERY, is_lit
from map import COLS, ROWS, SIZE, CELL, GRASS, TERRAIN_VI, generate_map
from menu import PANEL_W, MenuFrame, GamePanel, show_guide, show_scores


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

        frame = tk.Frame(root, bg="#000")
        frame.grid(row=0, column=0)
        self.canvas = tk.Canvas(frame, width=COLS * CELL, height=ROWS * CELL,
                                bg=GRASS, highlightthickness=0)
        self.canvas.pack(padx=3, pady=3)
        self.canvas.bind("<Button-1>", self.on_click)    # bấm vào ô = nâng cấp ô đó
        self.canvas.bind("<Motion>", self.on_motion)     # rê chuột = xem thông tin ô

        self.panel = tk.Frame(root, bg=theme.c("panel"), width=PANEL_W, height=ROWS * CELL + 6)
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
        self.build_turn = None   # nhịp nâng cấp đầu tiên (None = chưa bắt đầu, mọi thứ đứng yên)
        self.hud.clear_log()

    def new_map(self):
        self.terrain, self.sprites = generate_map()

    def regenerate(self):
        self.new_map()
        self.reset_state()
        self.draw()

    def play(self):
        self.playing = True
        self.reset_state()
        self.show_game()
        # như game gốc: chọn sẵn 1 ô rừng (khung + mũi tên xanh chỉ vào ô đó)
        self.selected = pick_tutorial_tile(self.terrain)
        self.refresh()
        self.schedule()

    def back_to_menu(self):
        self.playing = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.new_map()
        self.reset_state()
        self.show_menu()
        self.draw()

    # ---------- luật chơi
    def upgrade(self, pos):
        """Bấm vào ô: nâng lên cấp kế tiếp nếu đủ điều kiện, không thì báo lý do."""
        if not self.playing or self.over:
            return
        ok, reason = kinhte.can_upgrade(pos, self.terrain, self.tiles, self.counts,
                                        self.dark.cells, self.res, self.over)
        if not ok:
            self.hud.say(reason)
            self.draw_overlay()
            self.refresh_info()
            return
        name, lvl = kinhte.upgrade(pos, self.terrain, self.tiles, self.counts, self.res)
        if self.build_turn is None:
            self.build_turn = self.turn
            self.hud.say("Bóng tối bắt đầu lan ra...")
        self.hud.say(f"{name} lên cấp {lvl}.")
        # Tower mới có hiệu lực ngay: xua bóng tối trong vùng sáng và kiểm tra thắng
        cleared = self.dark.clear_lit(kinhte.towers(self.terrain, self.tiles))
        if cleared:
            self.hud.say(f"Ánh sáng xua tan {cleared} ô bóng tối.")
        self.check_end()
        if not self.over:
            self.refresh()

    def end_turn(self):
        if self.over or not self.playing:
            return
        if self.build_turn is None:
            # chưa nâng cấp gì: mọi thứ đứng yên (không sản xuất, không bóng tối, không tính nhịp)
            return
        kinhte.produce(self.terrain, self.tiles, self.dark.cells, self.res, self.carry)
        tw = kinhte.towers(self.terrain, self.tiles)
        cleared = self.dark.clear_lit(tw)
        if cleared:
            self.hud.say(f"Ánh sáng xua tan {cleared} ô bóng tối.")
        # bóng tối chỉ tiến 1 lần sau mỗi DARK_EVERY nhịp, kể từ lúc nâng cấp đầu tiên
        elapsed = self.turn - self.build_turn
        if elapsed % DARK_EVERY == 0:
            for msg in self.dark.advance(GRACE_TICKS + elapsed // DARK_EVERY, tw, self.tiles):
                self.hud.say(msg)
        self.turn += 1
        self.check_end()
        if not self.over:
            self.refresh()

    def schedule(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.after_id = self.root.after(TICK_MS // self.speed, self.on_timer)

    def on_timer(self):
        self.after_id = None
        if self.playing and not self.over and not self.paused:
            self.end_turn()
        if self.playing and not self.over:
            self.schedule()

    def set_speed(self, speed):
        """Đổi tốc độ x1/x2/x3: nhịp ngắn lại, tài nguyên và bóng tối nhanh theo."""
        if not self.playing or self.over:
            return
        self.speed = speed
        self.hud.set_speed(speed)
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

    def check_end(self):
        win = kinhte.check_win(self.terrain, self.tiles, self.res)
        if win:
            self.finish(win, won=True)
        elif self.dark.lost():
            self.finish("THUA CUỘC! Bóng tối đã nuốt chửng vùng đất.", won=False)

    def finish(self, msg, won=False):
        self.over = True
        self.hud.say(msg)
        self.refresh()
        if won:
            score = scores.calc_score(self.turn, len(self.dark.cells), len(self.tiles))
            messagebox.showinfo("Stop the Darkness", f"{msg}\n\nĐiểm của bạn: {score}")
            if scores.qualifies(score):
                name = simpledialog.askstring(
                    "Bảng xếp hạng", "Bạn vào top! Nhập tên (tối đa 12 ký tự):",
                    parent=self.root)
                rank = scores.add_score(name, score, self.turn)
                if rank:
                    messagebox.showinfo("Bảng xếp hạng", f"Bạn đứng hạng #{rank}!")
        else:
            messagebox.showinfo("Stop the Darkness", msg)
        self.back_to_menu()

    # ---------- giao diện
    def cell_at(self, event):
        c, r = event.x // CELL, event.y // CELL
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
            pos, self.terrain, self.tiles, self.counts, self.res)
        self.hud.show_tile(head, now, next_title, nxt, warn)

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        cv.config(bg=theme.tint(GRASS))
        tw = kinhte.towers(self.terrain, self.tiles)
        k = CELL / SIZE  # tỉ lệ thu nhỏ sprite; làm tròn theo biên nên không hở đường nối

        def paint(ox, oy, rects, tint=True):
            for x, y, w, h, col in rects:
                if tint:
                    col = theme.tint(col)
                cv.create_rectangle(ox + round(x * k), oy + round(y * k),
                                    ox + round((x + w) * k), oy + round((y + h) * k),
                                    fill=col, outline=col)

        for (r, c), rects in self.sprites.items():
            ox, oy = c * CELL, r * CELL
            if (r, c) in self.dark.cells:  # bị nuốt: đen kịt, xoá sạch hình bên dưới
                cv.create_rectangle(ox, oy, ox + CELL, oy + CELL,
                                    fill="#000000", outline="#000000")
                continue
            paint(ox, oy, rects)
            lvl = self.tiles.get((r, c), 1)
            if lvl >= 2:
                sp = kinhte.level_info(self.terrain[(r, c)], lvl)["sprite"]
                if sp:
                    # Tower luôn sáng rực, không bị làm tối theo giao diện
                    paint(ox, oy, BUILD_SPRITES[sp], tint=sp != "Tower of Light")
                for i in range(lvl - 1):  # mỗi chấm vàng = 1 cấp đã nâng
                    x = ox + 3 + i * 7
                    cv.create_rectangle(x, oy + CELL - 9, x + 5, oy + CELL - 4,
                                        fill="#ffd54a", outline="#7a5a00")
            if self.playing and is_lit((r, c), tw):
                cv.create_rectangle(ox + 2, oy + 2, ox + CELL - 2, oy + CELL - 2,
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
                cv.create_rectangle(c * CELL + 4, r * CELL + 4, (c + 1) * CELL - 4,
                                    (r + 1) * CELL - 4, outline="#b36bff", width=2,
                                    tags="ov")
        if self.playing and self.selected:
            r, c = self.selected
            cv.create_rectangle(c * CELL + 2, r * CELL + 2, (c + 1) * CELL - 2,
                                (r + 1) * CELL - 2, outline="#1e90ff", width=3, tags="ov")
            if self.build_turn is None:  # mũi tên hướng dẫn chỉ hiện trước nước đi đầu tiên
                cx, top = c * CELL + CELL // 2, max(r * CELL - 2, 14)
                cv.create_polygon(cx - 7, top - 12, cx + 7, top - 12, cx, top,
                                  fill="#1e90ff", outline="#0b5cad", tags="ov")


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()