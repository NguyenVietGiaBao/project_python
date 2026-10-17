"""Điểm vào của game. Chạy:  python main.py"""
import random
import tkinter as tk
from tkinter import messagebox, simpledialog

import kinhte
import scores
import theme
from kinhte import BUILDINGS, BUILD_SPRITES, TECH_WIN, TOWERS_WIN, cost_text
from dark import Darkness, RINGS, GRACE_TICKS, TICK_MS, is_lit
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
        root.title("Stop the Darkness Fake")
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
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)

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
        self.buildings = {}
        self.dark.reset()
        self.paused = False
        self.hud.set_paused(False)
        self.speed = 1
        self.hud.set_speed(1)
        self.res = kinhte.new_resources()
        self.turn, self.selected, self.over = 1, None, False
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
    def can_build(self, pos, name):
        return kinhte.can_build(pos, name, self.terrain, self.buildings,
                                self.dark.cells, self.res, self.over)

    def build(self, name):
        if not self.selected or not self.can_build(self.selected, name)[0]:
            return
        kinhte.build(self.selected, name, self.buildings, self.res)
        self.hud.say(f"Đã xây {name}.")
        # Tower mới có hiệu lực ngay: xua bóng tối trong vùng sáng và kiểm tra thắng
        cleared = self.dark.clear_lit(kinhte.towers(self.buildings))
        if cleared:
            self.hud.say(f"Ánh sáng xua tan {cleared} ô bóng tối.")
        self.check_end()
        self.refresh()

    def end_turn(self):
        if self.over or not self.playing:
            return
        kinhte.produce(self.terrain, self.buildings, self.dark.cells, self.res)
        tw = kinhte.towers(self.buildings)
        cleared = self.dark.clear_lit(tw)
        if cleared:
            self.hud.say(f"Ánh sáng xua tan {cleared} ô bóng tối.")
        if self.turn > GRACE_TICKS:
            for msg in self.dark.advance(self.turn, tw, self.buildings):
                self.hud.say(msg)
        self.turn += 1
        self.check_end()
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

    def toggle_pause(self):
        if not self.playing or self.over:
            return
        self.paused = not self.paused
        self.hud.set_paused(self.paused)

    def check_end(self):
        win = kinhte.check_win(self.buildings, self.res)
        if win:
            self.finish(win, won=True)
        elif self.dark.lost():
            self.finish("THUA CUỘC! Bóng tối đã nuốt chửng vùng đất.", won=False)

    def finish(self, msg, won=False):
        self.over = True
        self.hud.say(msg)
        self.refresh()
        if won:
            score = scores.calc_score(self.turn, len(self.dark.cells),
                                      len(self.buildings))
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
    def on_click(self, event):
        if not self.playing or self.over:
            return
        c, r = event.x // CELL, event.y // CELL
        if 0 <= r < ROWS and 0 <= c < COLS:
            self.selected = (r, c)
            self.refresh()

    def on_double_click(self, event):
        """Nhấp đúp vào ô: tự xây công trình đầu tiên xây được trên loại ô đó."""
        if not self.playing or self.over:
            return
        c, r = event.x // CELL, event.y // CELL
        if not (0 <= r < ROWS and 0 <= c < COLS):
            return
        pos = (r, c)
        self.selected = pos
        first_reason = None
        for name, b in BUILDINGS.items():
            if b["terrain"] != self.terrain[pos]:
                continue
            ok, reason = self.can_build(pos, name)
            if ok:
                self.build(name)
                return
            first_reason = first_reason or reason
        if first_reason:
            self.hud.say(first_reason)
        self.refresh()

    def refresh(self):
        self.draw()
        if not self.playing:
            return
        d = self.dark
        self.hud.set_resources(self.res, kinhte.income(
            self.terrain, self.buildings, d.cells))
        self.hud.res_label.config(
            text=f"Nhịp {self.turn}" + ("  [TẠM DỪNG]" if self.paused else "") +
                 f"\nTower {len(kinhte.towers(self.buildings))}/{TOWERS_WIN}"
                 f"  Tech mục tiêu {TECH_WIN}\n"
                 f"Tối {len(d.cells)}/{ROWS * COLS}"
                 f"  Vòng {min(d.ring + 1, len(RINGS))}/{len(RINGS)}")
        self.hud.clear_buttons()
        if not self.selected:
            self.hud.info_label.config(text="Bấm vào một ô để chọn.")
            return
        pos = self.selected
        built = self.buildings.get(pos)
        status = "BỊ BÓNG TỐI" if pos in d.cells else (built or "trống")
        self.hud.info_label.config(
            text=f"Ô ({pos[0]},{pos[1]}): {TERRAIN_VI[self.terrain[pos]]} - {status}")
        for name, b in BUILDINGS.items():
            if b["terrain"] != self.terrain[pos]:
                continue
            ok, reason = self.can_build(pos, name)
            self.hud.add_build_row(f"{name} ({cost_text(b['cost'])})",
                                   lambda n=name: self.build(n), ok, b["desc"], reason)

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        cv.config(bg=theme.tint(GRASS))
        tw = kinhte.towers(self.buildings)
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
            name = self.buildings.get((r, c))
            if name:
                # Tower luôn sáng rực, không bị làm tối theo giao diện
                paint(ox, oy, BUILD_SPRITES[name], tint=name != "Tower of Light")
            if self.playing and is_lit((r, c), tw):
                cv.create_rectangle(ox + 2, oy + 2, ox + CELL - 2, oy + CELL - 2,
                                    outline="#ffe66d", width=2, dash=(4, 3))
        if self.playing and not self.over:
            nxt = self.dark.current_cell()
            if nxt:
                r, c = nxt
                cv.create_rectangle(c * CELL + 4, r * CELL + 4, (c + 1) * CELL - 4,
                                    (r + 1) * CELL - 4, outline="#b36bff", width=2)
        if self.playing and self.selected:
            r, c = self.selected
            cv.create_rectangle(c * CELL + 2, r * CELL + 2, (c + 1) * CELL - 2,
                                (r + 1) * CELL - 2, outline="#1e90ff", width=3)
            cx, top = c * CELL + CELL // 2, max(r * CELL - 2, 14)
            cv.create_polygon(cx - 7, top - 12, cx + 7, top - 12, cx, top,
                              fill="#1e90ff", outline="#0b5cad")


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()