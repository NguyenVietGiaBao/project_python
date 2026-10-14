"""Giao diện: màu/font, nút, màn hình menu và bảng điều khiển khi chơi."""
import tkinter as tk

from kinhte import TECH_WIN, TOWERS_WIN
from dark import GRACE_TICKS, TICK_MS, LOSE_RATIO

PANEL_W = 300
PANEL = "#cdc8b8"
BOX = "#ebe7dc"
INK = "#2b2b2b"
FONT = ("Courier New", 11, "bold")
SMALL = ("Courier New", 9, "bold")


GUIDE = f"""MỤC TIÊU
- Thắng khi có {TOWERS_WIN} Tower of Light HOẶC đạt {TECH_WIN} Tech.
- Thua khi bóng tối nuốt hơn {int(LOSE_RATIO * 100)}% bản đồ.

BÓNG TỐI
- Tràn vào từ rìa bản đồ, đi theo vòng từ ngoài vào trong.
- {GRACE_TICKS} nhịp đầu chưa có bóng tối. Mỗi nhịp dài {TICK_MS / 1000:g} giây.
- Càng về sau bóng tối càng nhanh (tối đa 3 ô/nhịp).
- Khung tím trên bản đồ là ô sắp bị nuốt. Công trình trên ô bị nuốt sẽ bị phá huỷ.

CÁCH CHƠI
- Bấm 1 lần vào ô để chọn, rồi bấm nút công trình bên phải.
- Nhấp đúp vào ô để xây nhanh công trình phù hợp.
- Space: tạm dừng / tiếp tục.
- Góc dưới panel: nút II tạm dừng, nút \u25b6 đổi tốc độ x1 / x2 / x3 (hoặc
  bấm phím 1, 2, 3). Tốc độ cao làm cả tài nguyên và bóng tối chạy nhanh hơn.

CÔNG TRÌNH
- Lumber Camp (con thỏ): xây trên rừng, +2 gỗ/nhịp.
- Quarry: xây trên đá, +2 đá/nhịp.
- Workshop: xây trên cỏ, kề Lumber Camp hoặc Quarry, +1 tech/nhịp.
- Port: xây trên cỏ, kề nước, +2 tech/nhịp.
- Market: xây trên làng, +1 tech/nhịp.
- Tower of Light: xây trên cỏ, kề Workshop. Soi sáng bán kính 2 ô,
  bóng tối không nuốt được vùng này và các ô tối trong đó bị xua tan.
- Mỗi làng chưa bị tối cho +1 gỗ/nhịp.

MẸO
- Xây Lumber Camp trên rừng đầu tiên, rồi Quarry và Workshop.
- Đặt Tower gần vòng ngoài để chắn bóng tối và bảo vệ công trình.
"""


def show_guide(root):
    win = tk.Toplevel(root)
    win.title("Hướng dẫn trò chơi")
    win.configure(bg=PANEL)
    win.resizable(False, True)
    txt = tk.Text(win, width=62, height=30, bg=BOX, fg=INK, font=SMALL,
                  wrap="word", relief="solid", bd=2, padx=8, pady=8)
    txt.insert("1.0", GUIDE)
    txt.config(state="disabled")
    txt.pack(fill="both", expand=True, padx=8, pady=(8, 4))
    mkbtn(win, "Đóng", win.destroy, font=SMALL).pack(fill="x", padx=8, pady=(0, 8))
    win.transient(root)


def mkbtn(parent, text, cmd, **kw):
    kw.setdefault("font", FONT)
    kw.setdefault("takefocus", 0)
    return tk.Button(parent, text=text, command=cmd, bg=BOX, fg=INK,
                     activebackground="#f6f3ea", disabledforeground="#9a9a9a",
                     relief="solid", bd=2, cursor="hand2", **kw)


class MenuFrame:
    def __init__(self, parent, on_play, on_regen, on_help):
        m = self.frame = tk.Frame(parent, bg=PANEL)
        tk.Label(m, text="Stop the\nDarkness", font=("Courier New", 24, "bold"),
                 bg=PANEL, fg=INK, justify="left", anchor="w").pack(fill="x")
        tk.Label(m, text=" Stop the Darkness "
                         "của Florian van Strien.", font=SMALL, bg=PANEL, fg="#555",
                 justify="left", anchor="w", wraplength=270).pack(fill="x", pady=(2, 0))
        tk.Label(m, text="Chọn chế độ chơi:", font=FONT, bg=PANEL, fg=INK,
                 anchor="w").pack(fill="x", pady=(12, 3))
        box = tk.Frame(m, bg=BOX, bd=2, relief="solid")
        box.pack(fill="x")
        tk.Label(box, text="Standard", font=("Courier New", 15, "bold"), bg=BOX,
                 fg=INK, anchor="w").pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(box, text=f"Ngắn gọn, không quá khó. Thắng bằng {TOWERS_WIN} Tower of "
                           f"Light hoặc {TECH_WIN} Tech.", font=SMALL, bg=BOX, fg=INK,
                 anchor="w", justify="left", wraplength=250).pack(fill="x", padx=6,
                                                                 pady=(0, 6))
        tk.Label(m, text="Chế độ Extended: chưa có trong bản này.", font=SMALL,
                 bg=PANEL, fg="#777", anchor="w").pack(fill="x", pady=(6, 0))
        tk.Frame(m, bg=PANEL).pack(expand=True, fill="both")
        mkbtn(m, "Play!", on_play, height=2).pack(fill="x", pady=(0, 6))
        row = tk.Frame(m, bg=PANEL)
        row.pack(fill="x")
        mkbtn(row, "Regenerate Map", on_regen, font=SMALL).pack(
            side="left", fill="x", expand=True)
        mkbtn(row, "Hướng dẫn", on_help, font=SMALL, width=12).pack(
            side="left", padx=(4, 0))


class GamePanel:
    def __init__(self, parent, on_pause, on_quit, on_speed):
        g = self.frame = tk.Frame(parent, bg=PANEL)
        self.res_label = tk.Label(g, font=FONT, bg=PANEL, fg=INK, justify="left",
                                  anchor="w")
        self.res_label.pack(fill="x")
        self.info_label = tk.Label(g, font=SMALL, bg=PANEL, fg=INK, justify="left",
                                   anchor="w", wraplength=275)
        self.info_label.pack(fill="x", pady=(6, 4))
        self.btn_frame = tk.Frame(g, bg=PANEL)
        self.btn_frame.pack(fill="x")
        tk.Frame(g, bg=PANEL, height=8).pack()
        mkbtn(g, "Bỏ ván / về menu", on_quit, font=SMALL).pack(fill="x")
        bar = tk.Frame(g, bg=PANEL)
        bar.pack(side="bottom", fill="x", pady=(6, 0))
        self.speed_label = tk.Label(bar, font=SMALL, bg=PANEL, fg=INK, anchor="w")
        self.speed_label.pack(fill="x")
        row = tk.Frame(bar, bg=PANEL)
        row.pack(fill="x")
        self.pause_btn = mkbtn(row, "II", on_pause, font=FONT, width=3)
        self.pause_btn.pack(side="left")
        self.speed_btn = mkbtn(row, "", on_speed, font=FONT, width=4)
        self.speed_btn.pack(side="left", padx=(4, 0))
        self.set_speed(1)
        self.log = tk.Text(g, height=6, bg=BOX, fg=INK, font=SMALL, state="disabled",
                           wrap="word", relief="solid", bd=2)
        self.log.pack(fill="both", expand=True, pady=(8, 0))

    def say(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def set_speed(self, speed):
        self.speed_label.config(text=f"Game Speed: {speed}")
        self.speed_btn.config(text=f"\u25b6{speed}")

    def set_paused(self, paused):
        self.pause_btn.config(text="\u25b6" if paused else "II")

    def clear_buttons(self):
        for w in self.btn_frame.winfo_children():
            w.destroy()

    def add_build_row(self, label, cmd, enabled, desc, reason):
        row = tk.Frame(self.btn_frame, bg=PANEL)
        row.pack(fill="x", pady=2)
        mkbtn(row, label, cmd, state="normal" if enabled else "disabled",
              font=SMALL, wraplength=265).pack(fill="x")
        tk.Label(row, text=desc if enabled else f"{desc}\n! {reason}",
                 font=("Courier New", 8, "bold"), bg=PANEL,
                 fg="#444" if enabled else "#a33", justify="left", anchor="w",
                 wraplength=275).pack(fill="x")