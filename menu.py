"""Giao diện: màu/font, nút, màn hình menu và bảng điều khiển khi chơi."""
import tkinter as tk

from kinhte import CIRCLE_COST, CHAINS, cost_text, effect_text
from dark import TICK_MS, DARK_EVERY, LOSE_RATIO, TOWER_SLOW
from map import TERRAIN_VI
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


def _levels_text():
    """Liệt kê các cấp nâng được, lấy thẳng từ bảng CHAINS trong kinhte.py."""
    out = []
    labels = {"grass_magic": "ô cỏ kề rừng nấm",
              "grass_tower": "ô cỏ kề Magic Workshop cấp 2, chỉ xây được 1"}
    for kind in ("forest", "rock", "grass", "grass_magic", "mushroom", "grass_tower", "circle"):
        where = labels.get(kind) or f"ô {TERRAIN_VI[kind]}"
        for i, lv in enumerate(CHAINS[kind], 1):
            if i >= 2:
                out.append(f"- {lv['name']} (cấp {i}, trên {where}): {effect_text(lv)}")
    return "\n".join(out)


GUIDE = f"""MỤC TIÊU
- Thắng khi nâng cấp VÒNG ĐÁ giữa bản đồ (chi phí {cost_text(CIRCLE_COST)}).
- Thua khi bóng tối nuốt hơn {int(LOSE_RATIO * 100)}% bản đồ.

CÁCH CHƠI
- Rê chuột vào ô để xem thông tin, BẤM vào ô để nâng cấp.
- Khung bên phải cho biết ô hiện tại, chi phí nâng lên cấp kế tiếp và
  sản lượng ở cấp đó.
- Mọi thứ đứng yên cho đến khi bạn nâng cấp ô đầu tiên.
- Giá tăng dần: mỗi lần nâng một ô lên cùng một cấp, lần sau đắt hơn lần trước.
- Space: tạm dừng / tiếp tục.
- Phím T hoặc nút Giao diện: đổi sáng / tối (được nhớ cho lần sau).
- Nút II tạm dừng, nút \u25b6 đổi tốc độ x1 / x2 / x3 (hoặc phím 1, 2, 3).

BÓNG TỐI
- Tràn vào từ rìa bản đồ, đi theo vòng từ ngoài vào trong.
- Cứ {DARK_EVERY} nhịp tiến 1 lần (mỗi nhịp {TICK_MS / 1000:g} giây).
- Khung tím trên bản đồ là ô sắp bị nuốt. Ô đã nâng cấp bị nuốt sẽ mất.
- Tower of Light soi sáng bán kính 2 ô (bóng tối không vào được) và làm bóng tối
  tiến chậm gấp {TOWER_SLOW} lần. Tower KHÔNG giúp thắng game.

CÁC CẤP (sản lượng tính theo phút)
{_levels_text()}

ĐIỂM (chỉ ván thắng mới được ghi vào bảng xếp hạng)
- Cơ bản {scores.WIN_BONUS} điểm khi thắng.
- Thưởng thời gian: tối đa {scores.TIME_MAX}, mỗi nhịp trừ {scores.TIME_PER_TICK}.
- Mỗi ô chưa bị tối +{scores.DARK_PT}, mỗi ô đã nâng cấp còn sống +{scores.BUILD_PT}.
- Bảng lưu {scores.MAX_ENTRIES} điểm cao nhất (file scores.json).
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
        tk.Label(box, text=f"Ngắn gọn, không quá khó. Thắng bằng cách nâng cấp "
                           f"vòng đá giữa bản đồ ({cost_text(CIRCLE_COST)}).", font=SMALL, bg=theme.c("box"), fg=theme.c("ink"),
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


class GamePanel:
    def __init__(self, parent, on_pause, on_quit, on_speed, on_theme):
        g = self.frame = tk.Frame(parent, bg=theme.c("panel"))
        # HUD tài nguyên 2x2: icon, số lượng, mức thu mỗi phút
        hud = tk.Frame(g, bg=theme.c("panel"))
        hud.pack(fill="x")
        self.cells = {}
        for i, key in enumerate(RES_ORDER):
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

        # thanh dưới cùng: tốc độ + 1 hàng nút (pack trước để luôn nằm đáy)
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
        mkbtn(row, "Về menu", on_quit, font=SMALL).pack(
            side="left", fill="x", expand=True, padx=(4, 0))
        self.theme_btn = mkbtn(row, theme.label(), on_theme, font=SMALL, width=15)
        self.theme_btn.pack(side="left", padx=(4, 0))
        self.set_speed(1)

        # MỘT khung duy nhất: thông tin ô (trên), thông báo gần nhất (dưới)
        self.info = tk.Frame(g, bg=theme.c("box"), bd=2, relief="solid")
        self.info.pack(fill="both", expand=True, pady=(8, 0))
        self.msgs = []
        self.msg_label = tk.Label(self.info, font=("Courier New", 8, "bold"), bg=theme.c("box"),
                                  fg=theme.c("muted"), justify="left", anchor="nw",
                                  wraplength=270, height=3)
        self.msg_label.pack(side="bottom", fill="x", padx=6, pady=(0, 4))
        tk.Frame(self.info, bg=theme.c("ink"), height=2).pack(side="bottom", fill="x",
                                                               padx=4, pady=(0, 4))
        self.tile = tk.Frame(self.info, bg=theme.c("box"))
        self.tile.pack(side="top", fill="both", expand=True)

    def set_resources(self, res, inc):
        for key, (val, lbl) in self.cells.items():
            val.config(text=str(res[key]))
            lbl.config(text=f"+{inc.get(key, 0):g}/ph")

    def show_tile(self, head, now=(), next_title="", nxt=(), warn=""):
        """Vẽ lại khung thông tin ô (chỉ để đọc, không có nút).
        head: tên ô. now: các dòng về cấp hiện tại.
        next_title + nxt: cấp kế tiếp (chi phí, sản lượng), sau một gạch ngang.
        warn: lý do chưa nâng được (chữ đỏ)."""
        for w in self.tile.winfo_children():
            w.destroy()
        box, ink = theme.c("box"), theme.c("ink")

        def line(text, font, fg, pady=(0, 0)):
            tk.Label(self.tile, text=text, font=font, bg=box, fg=fg, justify="left",
                     anchor="w", wraplength=270).pack(fill="x", padx=6, pady=pady)

        line(head, FONT, ink, pady=(4, 4))
        for text in now:
            line(text, SMALL, ink, pady=(0, 2))
        if next_title:
            tk.Frame(self.tile, bg=ink, height=2).pack(fill="x", padx=4, pady=(8, 6))
            line(next_title, SMALL, ink, pady=(0, 2))
            for text in nxt:
                line(text, SMALL, theme.c("text2"), pady=(0, 2))
        if warn:
            line(f"! {warn}", SMALL, theme.c("warn"), pady=(6, 0))

    def say(self, text):
        """Hiện 3 thông báo gần nhất ở cuối khung."""
        self.msgs = (self.msgs + [text])[-3:]
        self.msg_label.config(text="\n".join(self.msgs))

    def clear_log(self):
        self.msgs = []
        self.msg_label.config(text="")

    def set_speed(self, speed):
        self.speed_label.config(text=f"Game Speed: {speed}")
        self.speed_btn.config(text=f"\u25b6{speed}")

    def set_paused(self, paused):
        self.pause_btn.config(text="\u25b6" if paused else "II")