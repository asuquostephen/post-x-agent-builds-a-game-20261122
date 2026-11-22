#!/usr/bin/env python3
"""Render all frames of the NEON DASH entry video (1080x1920 @30fps).
Scenes: S1 prompt typing, S2 agent writing the real game code, S3 browser
title screen, S4 gameplay (simulated by sim.py, seed 57 — the game's own
logic), S5 payoff card. The make.fun end card is composited later by ffmpeg.
"""
import math, os, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import run as sim_run, LANES, SHIP_Y, BLOCK_W, BLOCK_H, ORB_R

W, H, FPS = 1080, 1920, 30
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
os.makedirs(OUT, exist_ok=True)

FD = "/usr/share/fonts/truetype/dejavu"
def F(name, size):
    return ImageFont.truetype(os.path.join(FD, name), size)
BOLD = "DejaVuSans-Bold.ttf"
SANS = "DejaVuSans.ttf"
MONO = "DejaVuSansMono.ttf"
MONOB = "DejaVuSansMono-Bold.ttf"

BG = (11, 14, 26)
PANEL = (18, 23, 43)
BORDER = (38, 48, 79)
TXT = (219, 228, 255)
DIM = (124, 136, 173)
CYAN = (0, 229, 255)
MAGENTA = (255, 43, 214)
GREEN = (61, 255, 142)
RED = (255, 43, 78)
ORANGE = (255, 184, 107)
YELLOW = (255, 233, 74)
WHITE = (240, 247, 255)
INK = (25, 20, 25)

PROMPT = ("Build me a neon arcade game: one tap switches lanes, "
          "dodge the falling blocks, grab the orbs. Make it FAST.")

# ---------- helpers ----------
def rr(d, box, r, **kw):
    d.rounded_rectangle(box, radius=r, **kw)

def centred(d, cx, y, text, font, fill):
    w = d.textlength(text, font=font)
    d.text((cx - w / 2, y), text, font=font, fill=fill)
    return w

def wrap(text, font, maxw, draw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

# ---------- S1: the prompt ----------
def s1_frame(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    centred(d, W / 2, 250, "ONE PROMPT.", F(BOLD, 92), WHITE)
    # chat card
    card = (70, 640, 1010, 1230)
    rr(d, card, 36, fill=PANEL, outline=BORDER, width=3)
    d.ellipse((110, 690, 146, 726), fill=MAGENTA)
    d.text((166, 688), "Muse — coding agent", font=F(MONOB, 36), fill=DIM)
    d.text((110, 770), "you", font=F(MONOB, 32), fill=DIM)
    # typed prompt
    font = F(MONO, 40)
    lines = wrap(PROMPT, font, 830, d)
    typed = max(0.0, t - 0.6) * 42
    total = sum(len(l) for l in lines)
    shown, acc, caret = [], 0, None
    for l in lines:
        if typed >= acc + len(l):
            shown.append(l); acc += len(l)
        elif typed > acc:
            shown.append(l[: int(typed - acc)]); acc = typed
        else:
            break
    y = 830
    for i, l in enumerate(shown):
        d.text((110, y), l, font=font, fill=TXT)
        y += 56
    # caret
    if t < dur - 0.55 and int(t * 2.2) % 2 == 0:
        last = shown[-1] if shown else ""
        cx = 110 + d.textlength(last, font=font) + 6
        cy = 830 + (len(shown) - 1) * 56 if shown else 830
        d.rectangle((cx, cy + 4, cx + 20, cy + 48), fill=CYAN)
    # build button lights up at the end
    if t >= dur - 0.55:
        rr(d, (640, 1090, 950, 1180), 45, fill=(10, 40, 48), outline=CYAN, width=4)
        centred(d, 795, 1112, "Build it  ⏎", F(BOLD, 40), CYAN)
    if t >= 3.35:
        centred(d, W / 2, 1560, "…and it built the whole game.", F(BOLD, 52), CYAN)
    return img

# ---------- S2: the agent writes the code ----------
CODE_LINES = []
def load_code():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game", "neon-dash.html")
    with open(path) as f:
        for line in f.read().splitlines():
            line = line.rstrip()
            if len(line) > 62:
                line = line[:61] + "…"
            CODE_LINES.append(line)
load_code()

KW = re.compile(r"\b(const|let|var|function|return|if|else|for|of|new|typeof)\b")
def draw_code_line(d, x, y, line, font):
    # comment
    if "//" in line:
        head, tail = line.split("//", 1)
        draw_code_line(d, x, y, head, font)
        w = d.textlength(head, font=font)
        d.text((x + w, y), "//" + tail, font=font, fill=(96, 128, 96))
        return
    pos = 0
    for m in re.finditer(r"(\"[^\"]*\"|'[^']*'|\b\d+(?:\.\d+)?\b|\b(?:const|let|var|function|return|if|else|for|of|new)\b)", line):
        if m.start() > pos:
            seg = line[pos:m.start()]
            d.text((x, y), seg, font=font, fill=TXT)
            x += d.textlength(seg, font=font)
        seg = m.group(0)
        col = GREEN if seg[0] in "\"'" else (ORANGE if seg[0].isdigit() else MAGENTA)
        d.text((x, y), seg, font=font, fill=col)
        x += d.textlength(seg, font=font)
        pos = m.end()
    if pos < len(line):
        d.text((x, y), line[pos:], font=font, fill=TXT)

def s2_frame(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # editor chrome
    d.rectangle((0, 0, W, 120), fill=(8, 10, 20))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse((46 + i * 52, 42, 82 + i * 52, 78), fill=c)
    rr(d, (250, 30, 640, 100), 16, fill=PANEL, outline=BORDER, width=2)
    d.text((276, 48), "neon-dash.html", font=F(MONO, 34), fill=TXT)
    d.text((700, 48), "Muse is writing…", font=F(MONO, 30), fill=DIM)
    # code
    font = F(MONO, 29)
    lh, top, view = 43, 170, 34
    total = len(CODE_LINES)
    revealed = int(total * (t / dur) ** 1.3) + 1
    start = max(0, revealed - view)
    y = top
    for i in range(start, min(revealed, total)):
        d.text((46, y), str(i + 1), font=F(MONO, 24), fill=(70, 80, 110))
        draw_code_line(d, 130, y, CODE_LINES[i], font)
        y += lh
    # status bar
    d.rectangle((0, 1750, W, H), fill=(8, 10, 20))
    if t < 2.6:
        msg, col = "✍  writing neon-dash.html…", TXT
    elif t < 5.2:
        msg, col = "✍  adding collision, score + speed…", TXT
    elif t < 7.6:
        msg, col = "✍  tuning the difficulty curve…", TXT
    else:
        msg, col = "✓  done — one file, zero dependencies", GREEN
    d.text((46, 1790), msg, font=F(MONOB, 38), fill=col)
    d.text((46, 1852), "one prompt in → one game out", font=F(MONO, 30), fill=DIM)
    return img

# ---------- game drawing (shared by S3/S4/S5) ----------
GW, GH = 870, 1547
GX, GY = (W - GW) // 2, 262
SCALE = GW / 540.0

def draw_game(snap, title_mode=False):
    """Render one game frame at 2x game resolution, return GWxGH image."""
    S = 2  # supersample over 540x960
    img = Image.new("RGB", (540 * S, 960 * S), (7, 8, 24))
    d = ImageDraw.Draw(img)
    t = snap["time"]
    # vertical gradient
    for i in range(32):
        y0 = i * 960 * S // 32
        col = (7 + i // 6, 8 + i // 5, 24 + i * 2)
        d.rectangle((0, y0, 540 * S, y0 + 960 * S // 32 + 2), fill=col)
    # lanes
    for i in range(4):
        x = i * 180 * S
        d.line((x, 0, x, 960 * S), fill=(0, 90, 105), width=3 * S)
    off = (t * snap["speed"] * 0.6) % 120
    y = -120 + off
    while y < 960:
        d.line((0, y * S, 540 * S, y * S), fill=(60, 14, 52), width=2 * S)
        y += 120
    glow = Image.new("RGB", img.size, (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for e in snap["entities"]:
        x, yy = LANES[e["lane"]] * S, e["y"] * S
        if e["kind"] == "block":
            rr(gd, (x - BLOCK_W * S / 2, yy - BLOCK_H * S / 2, x + BLOCK_W * S / 2, yy + BLOCK_H * S / 2), 10 * S, fill=(255, 43, 78))
            rr(d, (x - BLOCK_W * S / 2, yy - BLOCK_H * S / 2, x + BLOCK_W * S / 2, yy + BLOCK_H * S / 2), 10 * S, fill=(255, 43, 78))
            rr(d, (x - BLOCK_W * S / 2 + 8 * S, yy - BLOCK_H * S / 2 + 7 * S, x + BLOCK_W * S / 2 - 8 * S, yy - BLOCK_H * S / 2 + 15 * S), 4 * S, fill=(255, 140, 160))
        else:
            gd.ellipse((x - ORB_R * S, yy - ORB_R * S, x + ORB_R * S, yy + ORB_R * S), fill=(0, 229, 255))
            d.ellipse((x - ORB_R * S, yy - ORB_R * S, x + ORB_R * S, yy + ORB_R * S), fill=(174, 247, 255))
            ring = ORB_R + 7 + math.sin(t * 6) * 2
            d.ellipse((x - ring * S, yy - ring * S, x + ring * S, yy + ring * S), outline=(0, 229, 255), width=3 * S)
    # ship
    sx, sy = snap["ship_x"] * S, SHIP_Y * S
    bob = math.sin(t * 3.2) * 4 * S if title_mode else 0
    ship = [(sx, sy - 34 * S + bob), (sx - 27 * S, sy + 24 * S + bob), (sx, sy + 10 * S + bob), (sx + 27 * S, sy + 24 * S + bob)]
    gd.polygon(ship, fill=(255, 233, 74))
    d.polygon(ship, fill=(255, 233, 74))
    img = Image.blend(img, Image.blend(img, glow, 0.55).filter(ImageFilter.GaussianBlur(6 * S)), 0.5)
    d = ImageDraw.Draw(img)
    for p in snap["pops"]:
        a = max(0.0, 1 - p["t"] / 0.7)
        col = tuple(int(c * a + b * (1 - a)) for c, b in zip(CYAN, (7, 8, 24)))
        d.text((p["x"] * S - 30 * S, p["y"] * S - 16 * S), p["text"], font=F(BOLD, 30 * S), fill=col)
    # HUD
    d.text((22 * S, 18 * S), str(snap["score"]), font=F(BOLD, 44 * S), fill=WHITE)
    mult = snap["speed"] / 380.0
    label = "SPEED x%.1f" % mult
    w = d.textlength(label, font=F(BOLD, 20 * S))
    d.text((540 * S - 22 * S - w, 26 * S), label, font=F(BOLD, 20 * S), fill=(150, 170, 200))
    if title_mode:
        ov = Image.new("RGBA", img.size, (4, 5, 18, 185))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(img)
        centred(d, 270 * S, 330 * S, "NEON", F(BOLD, 84 * S), CYAN)
        centred(d, 270 * S, 428 * S, "DASH", F(BOLD, 84 * S), MAGENTA)
        pulse = 0.65 + 0.35 * math.sin(t * 4.5)
        col = tuple(int(c * pulse + 10 * (1 - pulse)) for c in WHITE)
        centred(d, 270 * S, 580 * S, "TAP TO START", F(BOLD, 30 * S), col)
        centred(d, 270 * S, 632 * S, "dodge the red blocks · grab the orbs", F(SANS, 24 * S), (170, 185, 205))
    return img.resize((GW, GH), Image.LANCZOS)

def browser_frame(caption):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    if caption:
        centred(d, W / 2, 52, caption, F(BOLD, 50), WHITE)
    rr(d, (80, 150, 1000, 1845), 34, fill=(10, 12, 24), outline=BORDER, width=3)
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse((116 + i * 48, 182, 148 + i * 48, 214), fill=c)
    rr(d, (300, 172, 950, 226), 27, fill=PANEL)
    d.text((330, 184), "file:///neon-dash.html", font=F(MONO, 30), fill=DIM)
    return img

# ---------- S5 payoff ----------
def s5_frame(base_game_img, t, final_score):
    img = browser_frame("THE FINISHED GAME")
    img.paste(base_game_img, (GX, GY))
    dark = Image.new("RGB", (W, H), (3, 4, 12))
    a = min(0.82, t / 0.4 * 0.82) if t > 0 else 0
    img = Image.blend(img, dark, a * 0.85)
    d = ImageDraw.Draw(img)
    if t >= 0.25:
        centred(d, W / 2, 560, "FINAL SCORE", F(BOLD, 44), DIM)
        centred(d, W / 2, 630, str(final_score), F(BOLD, 190), WHITE)
    if t >= 1.05:
        centred(d, W / 2, 920, "Built from ONE prompt.", F(BOLD, 60), CYAN)
    if t >= 1.85:
        centred(d, W / 2, 1030, "Your agent can build one too.", F(SANS, 46), WHITE)
    return img

def main():
    sim, frames = sim_run(24.0, 57)
    assert not sim.crashed, "sim crashed — pick another seed"
    final_score = int(sim.score)
    events = sim.events
    print("final score:", final_score, "events:", [(round(t, 1), k) for t, k, _ in events])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "events.txt"), "w") as f:
        for t, k, data in events:
            f.write(f"{t:.3f} {k} {data}\n")
        f.write(f"final_score {final_score}\n")

    idx = 0
    def save(img):
        nonlocal idx
        img.save(os.path.join(OUT, f"{idx:04d}.png"))
        idx += 1

    # S1 — 4.2 s
    n = int(4.2 * FPS)
    for i in range(n):
        save(s1_frame(i / FPS, 4.2))
    print("S1 done", idx)
    # S2 — 8.8 s
    n = int(8.8 * FPS)
    for i in range(n):
        save(s2_frame(i / FPS, 8.8))
    print("S2 done", idx)
    # S3 — 2.5 s title screen in browser
    title_snap = {"time": 0.0, "speed": 380, "score": 0, "ship_x": LANES[1],
                  "entities": [], "pops": [], "crashed": False}
    n = int(2.5 * FPS)
    for i in range(n):
        t = i / FPS
        title_snap["time"] = t
        base = browser_frame("ONE PROMPT LATER…")
        g = draw_game(title_snap, title_mode=True)
        if t < 0.35:  # fade/slide in
            k = t / 0.35
            dark = Image.new("RGB", (W, H), BG)
            base = Image.blend(dark, base, k)
        base.paste(g, (GX, GY))
        save(base)
    print("S3 done", idx)
    # S4 — 24 s gameplay
    speedup_t = next((t for t, k, _ in events if k == "speedup"), None)
    close_ts = [t for t, k, _ in events if k == "close"]
    for i, snap in enumerate(frames):
        t = i / FPS
        base = browser_frame("THE FINISHED GAME")
        g = draw_game(snap)
        gd = ImageDraw.Draw(g)
        if speedup_t is not None and speedup_t <= t < speedup_t + 1.0:
            k = min(1.0, (t - speedup_t) / 0.15)
            centred(gd, GW / 2, 300, "SPEED UP!", F(BOLD, int(64 * k) + 8), YELLOW)
        for ct in close_ts:
            if ct <= t < ct + 0.7:
                centred(gd, GW / 2, 420, "CLOSE!", F(BOLD, 54), ORANGE)
        base.paste(g, (GX, GY))
        save(base)
    print("S4 done", idx)
    # S5 — 3.5 s payoff on the frozen last frame
    last_g = draw_game(frames[-1])
    n = int(3.5 * FPS)
    for i in range(n):
        save(s5_frame(last_g, i / FPS, final_score))
    print("S5 done", idx, "total frames")

if __name__ == "__main__":
    main()
