"""Điểm vào của game. Chạy:  python main.py"""
import tkinter as tk
from tkinter import messagebox

import kinhte
from kinhte import BUILDINGS, BUILD_SPRITES, TECH_WIN, TOWERS_WIN, cost_text
from dark import Darkness, RINGS, GRACE_TICKS, TICK_MS, is_lit
from map import COLS, ROWS, SIZE, GRASS, TERRAIN_VI, generate_map
from menu import PANEL, PANEL_W, MenuFrame, GamePanel, show_guide


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Stop the Darkness (Python)")
        root.configure(bg="#000")
        root.resizable(False, False)
        self.playing = False
        self.paused = False
        self.speed = 1
        self.after_id = None

        frame = tk.Frame(root, bg="#000")
        frame.grid(row=0, column=0)
        self.canvas = tk.Canvas(frame, width=COLS * SIZE, height=ROWS * SIZE,
                                bg=GRASS, highlightthickness=0)
        self.canvas.pack(padx=3, pady=3)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)

        self.panel = tk.Frame(root, bg=PANEL, width=PANEL_W, height=ROWS * SIZE + 6)
        self.panel.grid(row=0, column=1, sticky="ns")
        self.panel.pack_propagate(False)
        self.menu = MenuFrame(self.panel, self.play, self.regenerate,
                              lambda: show_guide(self.root))
        self.hud = GamePanel(self.panel, self.toggle_pause, self.back_to_menu,
                             lambda: self.set_speed(self.speed % 3 + 1))

        root.bind("<space>", lambda e: self.toggle_pause())
        for n in (1, 2, 3):
            root.bind(str(n), lambda e, n=n: self.set_speed(n))
        self.dark = Darkness()
        self.terrain, self.sprites = generate_map()
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
        self.reset_state()
        self.playing = True
        self.show_game()
        self.hud.say("Bóng tối sẽ tràn vào từ rìa bản đồ. Xây Lumber Camp trên rừng trước!")
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

    def toggle_pause(self):
        if not self.playing or self.over:
            return
        self.paused = not self.paused
        self.hud.set_paused(self.paused)

    def check_end(self):
        win = kinhte.check_win(self.buildings, self.res)
        if win:
            self.finish(win)
        elif self.dark.lost():
            self.finish("THUA CUỘC! Bóng tối đã nuốt chửng vùng đất.")

    def finish(self, msg):
        self.over = True
        self.hud.say(msg)
        self.refresh()
        messagebox.showinfo("Stop the Darkness", msg)
        self.back_to_menu()

    # ---------- giao diện
    def on_click(self, event):
        if not self.playing or self.over:
            return
        c, r = event.x // SIZE, event.y // SIZE
        if 0 <= r < ROWS and 0 <= c < COLS:
            self.selected = (r, c)
            self.refresh()

    def on_double_click(self, event):
        """Nhấp đúp vào ô: tự xây công trình đầu tiên xây được trên loại ô đó."""
        if not self.playing or self.over:
            return
        c, r = event.x // SIZE, event.y // SIZE
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
        self.hud.res_label.config(
            text=f"Nhịp {self.turn}" + ("  [TẠM DỪNG]" if self.paused else "") +
                 f"\nGỗ {self.res['wood']}  Đá {self.res['stone']}  "
                 f"Tech {self.res['tech']}/{TECH_WIN}\n"
                 f"Tower {len(kinhte.towers(self.buildings))}/{TOWERS_WIN}  "
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
        tw = kinhte.towers(self.buildings)
        for (r, c), rects in self.sprites.items():
            ox, oy = c * SIZE, r * SIZE
            if (r, c) in self.dark.cells:  # bị nuốt: đen kịt, xoá sạch hình bên dưới
                cv.create_rectangle(ox, oy, ox + SIZE, oy + SIZE,
                                    fill="#000000", outline="#000000")
                continue
            for x, y, w, h, col in rects:
                cv.create_rectangle(ox + x, oy + y, ox + x + w, oy + y + h,
                                    fill=col, outline=col)
            name = self.buildings.get((r, c))
            if name:
                for x, y, w, h, col in BUILD_SPRITES[name]:
                    cv.create_rectangle(ox + x, oy + y, ox + x + w, oy + y + h,
                                        fill=col, outline=col)
            if self.playing and is_lit((r, c), tw):
                cv.create_rectangle(ox + 2, oy + 2, ox + SIZE - 2, oy + SIZE - 2,
                                    outline="#ffe66d", width=2, dash=(4, 3))
        if self.playing and not self.over:
            nxt = self.dark.current_cell()
            if nxt:
                r, c = nxt
                cv.create_rectangle(c * SIZE + 5, r * SIZE + 5, (c + 1) * SIZE - 5,
                                    (r + 1) * SIZE - 5, outline="#b36bff", width=2)
        if self.playing and self.selected:
            r, c = self.selected
            cv.create_rectangle(c * SIZE + 2, r * SIZE + 2, (c + 1) * SIZE - 2,
                                (r + 1) * SIZE - 2, outline="#ffffff", width=3)


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()