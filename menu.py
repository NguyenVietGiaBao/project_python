"""Giao diện: màu/font, nút, màn hình menu và bảng điều khiển khi chơi."""
import tkinter as tk

from kinhte import TECH_WIN, TOWERS_WIN
from dark import GRACE_TICKS, TICK_MS, LOSE_RATIO
import scores
import theme

PANEL_W = 310
FONT = ("Courier New", 11, "bold")
SMALL = ("Courier New", 9, "bold")

RES_ORDER = ("wood", "stone", "mana", "tech")
# ---------- icon tài nguyên: pixel-art 16x16 (mỗi điểm nhân đôi khi vẽ)
# '.' = trong suốt; các chữ còn lại tra trong bảng màu của từng icon.
ICON_ART = {
    "wood": ([                      # khúc gỗ nằm ngang, mặt cắt có vân tròn
        "................",
        "................",
        "................",
        "...KKKKKKKKKKK..",
        "..KLLLKBBBBBBBK.",
        "..KLDDLKBbBBBBK.",
        ".KLDLLDLKBBbBBBK",
        ".KLDLLDLKBBBBbBK",
        ".KLDLLDLKBbBBBBK",
        "..KLDDLKBBBBBbK.",
        "..KLLLKBBBBBBBK.",
        "...KKKKKKKKKKK..",
        "................",
        "................",
        "................",
        "................",
    ], {"K": "#3b2412", "B": "#8a5a2e", "b": "#6b4a2b",
        "L": "#e3c38a", "D": "#b58a4e"}),
    "stone": ([                     # viên đá tròn có điểm sáng
        "................",
        "................",
        "................",
        ".....KKKKKKK....",
        "...KKGGGGGGGKK..",
        "..KGGWWGGGGGGGK.",
        ".KGGWWGGGGGGGGGK",
        ".KGGGGGGGGGDGGGK",
        ".KGGGGGGGGDDGGGK",
        ".KGGGGGGDDDDGGDK",
        "..KGGGDDDDDDDDK.",
        "...KKDDDDDDDKK..",
        ".....KKKKKKK....",
        "................",
        "................",
        "................",
    ], {"K": "#3a3a3a", "G": "#8c8c8c", "W": "#cfcfcf", "D": "#666666"}),
    "mana": ([                      # ba tia sáng 4 cánh màu tím
        "................",
        "................",
        "......P.....P...",
        "......P.....P...",
        ".....PLP..PPLPP.",
        ".....PLP....P...",
        "....PPLPP...P...",
        "...PPPLPPP......",
        "PPPLLLLLLLPPP...",
        "...PPPLPPP......",
        "....PPLPP...P...",
        ".....PLP....P...",
        ".....PLP..PPLPP.",
        "......P.....P...",
        "......P.....P...",
        "................",
    ], {"P": "#8e44ad", "L": "#e6c2ff"}),
    "tech": ([                      # bình thí nghiệm chứa dung dịch xanh lục
        "................",
        "....KKKKKKKK....",
        ".....KWWWWK.....",
        ".....KWWWWK.....",
        ".....KWWWWK.....",
        "....KWWWWWWK....",
        "...KWWWWWWWWK...",
        "..KWWWWWWWWWWK..",
        ".KWWLLLLLLLLWWK.",
        ".KLLLLLLLLLLLLK.",
        ".KLLBLLLLLLLBLK.",
        ".KLLLLLLLLBLLLK.",
        ".KLLLLLLLLLLLLK.",
        "..KKKKKKKKKKKK..",
        "................",
        "................",
    ], {"K": "#4a5d1a", "W": "#e8f5c0", "L": "#a6d93a", "B": "#e9ff9a"}),
}


def _art_to_rects(art, palette):
    """Đổi bản vẽ chữ thành danh sách (x, y, w, h, màu), gộp các điểm liền nhau."""
    rects = []
    for y, row in enumerate(art):
        assert len(row) == 16, (y, row)
        x = 0
        while x < 16:
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            end = x
            while end + 1 < 16 and row[end + 1] == ch:
                end += 1
            rects.append((x, y, end - x + 1, 1, palette[ch]))
            x = end + 1
    return rects


ICONS = {k: _art_to_rects(*v) for k, v in ICON_ART.items()}


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
- Phím T hoặc nút Giao diện: đổi sáng / tối (được nhớ cho lần sau).
- Góc dưới panel: nút II tạm dừng, nút \u25b6 đổi tốc độ x1 / x2 / x3 (hoặc
  bấm phím 1, 2, 3). Tốc độ cao làm cả tài nguyên và bóng tối chạy nhanh hơn.

CÔNG TRÌNH
- Lumber Camp (con thỏ): xây trên rừng, +2 gỗ/nhịp.
- Quarry: xây trên đá, +2 đá/nhịp.
- Workshop: xây trên cỏ, kề Lumber Camp hoặc Quarry, +1 tech/nhịp.
- Port: xây trên cỏ, kề nước, +2 tech/nhịp.
- Market: xây trên rừng nấm, +1 tech và +1 mana/nhịp.
- Tower of Light: xây trên cỏ, kề Workshop. Soi sáng bán kính 2 ô,
  bóng tối không nuốt được vùng này và các ô tối trong đó bị xua tan.
- Mỗi rừng nấm chưa bị tối cho +1 gỗ/nhịp.

ĐIỂM (chỉ ván thắng mới được ghi vào bảng xếp hạng)
- Cơ bản {scores.WIN_BONUS} điểm khi thắng.
- Thưởng thời gian: tối đa {scores.TIME_MAX}, mỗi nhịp trừ {scores.TIME_PER_TICK}.
- Mỗi ô chưa bị tối +{scores.DARK_PT}, mỗi công trình còn sống +{scores.BUILD_PT}.
- Bảng lưu {scores.MAX_ENTRIES} điểm cao nhất (file scores.json).

MẸO
- Xây Lumber Camp trên rừng đầu tiên, rồi Quarry và Workshop.
- Vòng đá nằm gần giữa bản đồ (chưa có công dụng, sẽ dùng cho bản sau).
- Đặt Tower gần vòng ngoài để chắn bóng tối và bảo vệ công trình.
"""


def show_guide(root):
    win = tk.Toplevel(root)
    win.title("Hướng dẫn trò chơi")
    win.configure(bg=theme.c("panel"))
    win.resizable(False, True)
    txt = tk.Text(win, width=62, height=30, bg=theme.c("box"), fg=theme.c("ink"), font=SMALL,
                  wrap="word", relief="solid", bd=2, padx=8, pady=8)
    txt.insert("1.0", GUIDE)
    txt.config(state="disabled")
    txt.pack(fill="both", expand=True, padx=8, pady=(8, 4))
    mkbtn(win, "Đóng", win.destroy, font=SMALL).pack(fill="x", padx=8, pady=(0, 8))
    win.transient(root)


def show_scores(root):
    win = tk.Toplevel(root)
    win.title("Bảng xếp hạng")
    win.configure(bg=theme.c("panel"))
    win.resizable(False, False)
    tk.Label(win, text="TOP ĐIỂM CAO", font=("Courier New", 16, "bold"),
             bg=theme.c("panel"), fg=theme.c("ink")).pack(pady=(10, 4))
    txt = tk.Text(win, width=46, height=13, bg=theme.c("box"), fg=theme.c("ink"), font=SMALL,
                  relief="solid", bd=2, padx=8, pady=8)
    txt.insert("1.0", scores.table_text())
    txt.config(state="disabled")
    txt.pack(padx=8, pady=4)
    mkbtn(win, "Đóng", win.destroy, font=SMALL).pack(fill="x", padx=8, pady=(4, 8))
    win.transient(root)


def mkbtn(parent, text, cmd, **kw):
    kw.setdefault("font", FONT)
    kw.setdefault("takefocus", 0)
    return tk.Button(parent, text=text, command=cmd, bg=theme.c("box"), fg=theme.c("ink"),
                     activebackground=theme.c("active"), disabledforeground=theme.c("disabled"),
                     relief="solid", bd=2, cursor="hand2", **kw)


class MenuFrame:
    def __init__(self, parent, on_play, on_regen, on_help, on_scores, on_theme):
        m = self.frame = tk.Frame(parent, bg=theme.c("panel"))
        tk.Label(m, text="Stop the\nDarkness", font=("Courier New", 24, "bold"),
                 bg=theme.c("panel"), fg=theme.c("ink"), justify="left", anchor="w").pack(fill="x")
        tk.Label(m, text=" Stop the Darkness "
                         "của Florian van Strien.", font=SMALL, bg=theme.c("panel"), fg=theme.c("muted"),
                 justify="left", anchor="w", wraplength=280).pack(fill="x", pady=(2, 0))
        tk.Label(m, text="Chọn chế độ chơi:", font=FONT, bg=theme.c("panel"), fg=theme.c("ink"),
                 anchor="w").pack(fill="x", pady=(12, 3))
        box = tk.Frame(m, bg=theme.c("box"), bd=2, relief="solid")
        box.pack(fill="x")
        tk.Label(box, text="Standard", font=("Courier New", 15, "bold"), bg=theme.c("box"),
                 fg=theme.c("ink"), anchor="w").pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(box, text=f"Ngắn gọn, không quá khó. Thắng bằng {TOWERS_WIN} Tower of "
                           f"Light hoặc {TECH_WIN} Tech.", font=SMALL, bg=theme.c("box"), fg=theme.c("ink"),
                 anchor="w", justify="left", wraplength=265).pack(fill="x", padx=6,
                                                                 pady=(0, 6))
        box2 = tk.Frame(m, bg=theme.c("box_off"), bd=2, relief="solid")
        box2.pack(fill="x", pady=(6, 0))
        tk.Label(box2, text="Extended", font=("Courier New", 15, "bold"), bg=theme.c("box_off"),
                 fg=theme.c("off_ink"), anchor="w").pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(box2, text="Nhiều nâng cấp hơn, thử thách hơn. (Chưa có trong bản này)",
                 font=SMALL, bg=theme.c("box_off"), fg=theme.c("off_ink"), anchor="w", justify="left",
                 wraplength=265).pack(fill="x", padx=6, pady=(0, 6))
        tk.Frame(m, bg=theme.c("panel")).pack(expand=True, fill="both")
        mkbtn(m, "Play!", on_play, height=2).pack(fill="x", pady=(0, 6))
        row = tk.Frame(m, bg=theme.c("panel"))
        row.pack(fill="x")
        mkbtn(row, "Regenerate Map", on_regen, font=SMALL).pack(
            side="left", fill="x", expand=True)
        mkbtn(row, "Hướng dẫn", on_help, font=SMALL, width=10).pack(
            side="left", padx=(4, 0))
        row2 = tk.Frame(m, bg=theme.c("panel"))
        row2.pack(fill="x", pady=(4, 0))
        mkbtn(row2, "Bảng xếp hạng", on_scores, font=SMALL).pack(
            side="left", fill="x", expand=True)
        self.theme_btn = mkbtn(row2, theme.label(), on_theme, font=SMALL, width=15)
        self.theme_btn.pack(side="left", padx=(4, 0))


# class GamePanel:
#     def __init__(self, parent, on_pause, on_quit, on_speed):
#         g = self.frame = tk.Frame(parent, bg=PANEL)
#         # HUD tài nguyên 2x2: icon, số lượng, mức thu mỗi nhịp
#         hud = tk.Frame(g, bg=PANEL)
#         hud.pack(fill="x")
#         hud.columnconfigure((0, 1), weight=1, uniform="res")
#         self.cells = {}
#         for i, key in enumerate(RES_ORDER):
#             cell = tk.Frame(hud, bg=BOX, bd=2, relief="solid")
#             cell.grid(row=i // 2, column=i % 2, sticky="ew", padx=1, pady=1)
#             icon = tk.Canvas(cell, width=32, height=32, bg=BOX, highlightthickness=0)
#             icon.pack(side="left", padx=(3, 0))
#             for x, y, w, h, col in ICONS[key]:
#                 icon.create_rectangle(x * 2, y * 2, (x + w) * 2, (y + h) * 2,
#                                       fill=col, outline=col)
#             val = tk.Label(cell, font=("Courier New", 16, "bold"), bg=BOX, fg=INK,
#                            anchor="w")
#             val.pack(side="left", padx=2)
#             inc = tk.Label(cell, font=SMALL, bg=BOX, fg="#777", anchor="e")
#             inc.pack(side="right", padx=3, anchor="s")
#             self.cells[key] = (val, inc)
#         self.res_label = tk.Label(g, font=SMALL, bg=PANEL, fg=INK, justify="left",
#                                   anchor="w")
#         self.res_label.pack(fill="x", pady=(6, 0))
#         self.info_label = tk.Label(g, font=SMALL, bg=PANEL, fg=INK, justify="left",
#                                    anchor="w", wraplength=285)
#         self.info_label.pack(fill="x", pady=(6, 4))
#         self.btn_frame = tk.Frame(g, bg=PANEL)
#         self.btn_frame.pack(fill="x")
#         tk.Frame(g, bg=PANEL, height=8).pack()
#         mkbtn(g, "Bỏ ván / về menu", on_quit, font=SMALL).pack(fill="x")
#         bar = tk.Frame(g, bg=PANEL)
#         bar.pack(side="bottom", fill="x", pady=(6, 0))
#         self.speed_label = tk.Label(bar, font=SMALL, bg=PANEL, fg=INK, anchor="w")
#         self.speed_label.pack(fill="x")
#         row = tk.Frame(bar, bg=PANEL)
#         row.pack(fill="x")
#         self.pause_btn = mkbtn(row, "II", on_pause, font=FONT, width=3)
#         self.pause_btn.pack(side="left")
#         self.speed_btn = mkbtn(row, "", on_speed, font=FONT, width=4)
#         self.speed_btn.pack(side="left", padx=(4, 0))
#         self.set_speed(1)
#         # nhật ký sự kiện nằm trong panel (cửa sổ giữ nguyên kích thước như menu)
#         self.log = tk.Text(g, height=6, bg=BOX, fg=INK, font=SMALL, state="disabled",
#                            wrap="word", relief="solid", bd=2)
#         self.log.pack(fill="both", expand=True, pady=(8, 0))

class GamePanel:
    def __init__(self, parent, on_pause, on_quit, on_speed, on_theme):
        g = self.frame = tk.Frame(parent, bg=theme.c("panel"))
        # HUD tài nguyên 2x2: icon, số lượng, mức thu mỗi nhịp
        hud = tk.Frame(g, bg=theme.c("panel"))
        hud.pack(fill="x")
        self.cells = {}
        for i, key in enumerate(RES_ORDER):
            # Cố định kích thước khung chứa tài nguyên với width và height, đồng thời bật pack_propagate(False)
            cell = tk.Frame(hud, bg=theme.c("box"), bd=2, relief="solid", width=145, height=45)
            cell.grid(row=i // 2, column=i % 2, padx=1, pady=1)
            cell.pack_propagate(False)

            icon = tk.Canvas(cell, width=32, height=32, bg=theme.c("box"), highlightthickness=0)
            icon.pack(side="left", padx=(3, 0))
            for x, y, w, h, col in ICONS[key]:
                icon.create_rectangle(x * 2, y * 2, (x + w) * 2, (y + h) * 2,
                                      fill=col, outline=col)
            val = tk.Label(cell, font=("Courier New", 16, "bold"), bg=theme.c("box"), fg=theme.c("ink"),
                           anchor="w")
            val.pack(side="left", padx=2)
            inc = tk.Label(cell, font=SMALL, bg=theme.c("box"), fg=theme.c("faint"), anchor="e")
            inc.pack(side="right", padx=3, anchor="s")
            self.cells[key] = (val, inc)
        self.res_label = tk.Label(g, font=SMALL, bg=theme.c("panel"), fg=theme.c("ink"), justify="left",
                                  anchor="w")
        self.res_label.pack(fill="x", pady=(6, 0))
        self.info_label = tk.Label(g, font=SMALL, bg=theme.c("panel"), fg=theme.c("ink"), justify="left",
                                   anchor="w", wraplength=285)
        self.info_label.pack(fill="x", pady=(6, 4))
        self.btn_frame = tk.Frame(g, bg=theme.c("panel"))
        self.btn_frame.pack(fill="x")
        tk.Frame(g, bg=theme.c("panel"), height=8).pack()
        mkbtn(g, "Bỏ ván / về menu", on_quit, font=SMALL).pack(fill="x")
        bar = tk.Frame(g, bg=theme.c("panel"))
        bar.pack(side="bottom", fill="x", pady=(6, 0))
        self.speed_label = tk.Label(bar, font=SMALL, bg=theme.c("panel"), fg=theme.c("ink"), anchor="w")
        self.speed_label.pack(fill="x")
        row = tk.Frame(bar, bg=theme.c("panel"))
        row.pack(fill="x")
        self.pause_btn = mkbtn(row, "II", on_pause, font=FONT, width=3)
        self.pause_btn.pack(side="left")
        self.speed_btn = mkbtn(row, "", on_speed, font=FONT, width=4)
        self.speed_btn.pack(side="left", padx=(4, 0))
        self.theme_btn = mkbtn(row, theme.label(), on_theme, font=SMALL, width=15)
        self.theme_btn.pack(side="left", padx=(4, 0))
        self.set_speed(1)
        # nhật ký sự kiện nằm trong panel (cửa sổ giữ nguyên kích thước như menu)
        self.log = tk.Text(g, height=6, bg=theme.c("box"), fg=theme.c("ink"), font=SMALL, state="disabled",
                           wrap="word", relief="solid", bd=2)
        self.log.pack(fill="both", expand=True, pady=(8, 0))

    def set_resources(self, res, inc):
        for key, (val, lbl) in self.cells.items():
            val.config(text=str(res[key]))
            lbl.config(text=f"+{inc.get(key, 0)}")

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
        row = tk.Frame(self.btn_frame, bg=theme.c("panel"))
        row.pack(fill="x", pady=2)
        mkbtn(row, label, cmd, state="normal" if enabled else "disabled",
              font=SMALL, wraplength=275).pack(fill="x")
        tk.Label(row, text=desc if enabled else f"{desc}\n! {reason}",
                 font=("Courier New", 8, "bold"), bg=theme.c("panel"),
                 fg=theme.c("text2") if enabled else theme.c("warn"), justify="left", anchor="w",
                 wraplength=285).pack(fill="x")