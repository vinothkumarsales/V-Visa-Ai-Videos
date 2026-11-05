import math, sys, subprocess, functools
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from common import *

S = 2  # supersample for objects
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FBO = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

@functools.lru_cache(None)
def font(sz, path=FBO):
    return ImageFont.truetype(path, int(sz))

YEL = (255, 210, 63); TEAL = (0, 209, 178); COR = (255, 90, 95); WHT = (255, 255, 255)
NAVY = (20, 16, 46); PUR = (108, 71, 255); GRN = (46, 204, 113); INK = (28, 24, 60)
SKY = (86, 180, 255); PINK = (255, 120, 190)

def clamp(x, a=0, b=1): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x):
    x = clamp(x); c1 = 1.9; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def seg(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)

# ---------- supersampled object canvas ----------
class D:
    def __init__(s, w, h):
        s.im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); s.d = ImageDraw.Draw(s.im); s.w, s.h = w, h
    def _b(s, b): return [v * S for v in b]
    def rect(s, b, r=0, fill=None, outline=None, width=0):
        s.d.rounded_rectangle(s._b(b), radius=r * S, fill=fill, outline=outline, width=width * S)
    def ell(s, b, fill=None, outline=None, width=0):
        s.d.ellipse(s._b(b), fill=fill, outline=outline, width=width * S)
    def line(s, pts, fill, width=4, joint="curve"):
        s.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S), joint=joint)
    def poly(s, pts, fill=None, outline=None):
        s.d.polygon([(x * S, y * S) for x, y in pts], fill=fill, outline=outline)
    def text(s, xy, t, size, fill=WHT, anchor="mm", stroke=0, sfill=INK, path=FBO):
        s.d.text((xy[0] * S, xy[1] * S), t, font=font(size * S, path), fill=fill, anchor=anchor,
                 stroke_width=int(stroke * S), stroke_fill=sfill)
    def get(s): return s.im

def put(img, obj, cx, cy, sc=1.0, rot=0.0, alpha=1.0):
    if sc <= 0.01 or alpha <= 0: return
    o = obj
    nw, nh = max(1, int(o.width / S * sc)), max(1, int(o.height / S * sc))
    o = o.resize((nw, nh), Image.LANCZOS)
    if rot: o = o.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = o.getchannel("A").point(lambda v: int(v * alpha)); o.putalpha(a)
    img.alpha_composite(o, (int(cx - o.width / 2), int(cy - o.height / 2)))

def shadow_card(w, h, r=40, fill=WHT, border=None, sh=True):
    d = D(w + 40, h + 50)
    if sh: d.rect((20, 34, w + 20, h + 34), r, fill=(0, 0, 0, 90))
    d.rect((20, 20, w + 20, h + 20), r, fill=fill, outline=border, width=6 if border else 0)
    return d

# ---------- avatar (cartoon student) ----------
@functools.lru_cache(None)
def avatar(mood="smile", shirt=PUR, hair=(40, 30, 30), skin=(236, 178, 130)):
    d = D(300, 400)
    d.ell((40, 250, 260, 520), fill=shirt)                         # body
    d.rect((125, 215, 175, 270), 10, fill=skin)                    # neck
    d.ell((70, 60, 230, 230), fill=skin)                           # head
    d.ell((60, 40, 240, 150), fill=hair)                           # hair top
    d.rect((60, 90, 90, 170), 14, fill=hair); d.rect((210, 90, 240, 170), 14, fill=hair)
    d.ell((70, 100, 230, 150), fill=skin)
    d.ell((52, 135, 76, 185), fill=skin); d.ell((224, 135, 248, 185), fill=skin)
    # eyes
    if mood == "shock":
        for x in (118, 182): d.ell((x - 14, 136, x + 14, 170), fill=WHT, outline=INK, width=3); d.ell((x - 5, 148, x + 5, 160), fill=INK)
    elif mood == "think":
        for x in (118, 182): d.ell((x - 7, 148, x + 7, 168), fill=INK)
        d.line([(100, 126), (136, 120)], hair, 6); d.line([(164, 116), (200, 128)], hair, 6)
    else:
        for x in (118, 182): d.ell((x - 8, 146, x + 8, 168), fill=INK); d.ell((x - 3, 149, x + 1, 154), fill=WHT)
    # mouth
    if mood in ("smile", "cheer"):
        d.d.pieslice([(120) * S, (170) * S, (180) * S, (215) * S], 0, 180, fill=(150, 40, 60))
    elif mood == "shock":
        d.ell((140, 188, 162, 216), fill=(150, 40, 60))
    else:
        d.line([(130, 196), (170, 196)], INK, 5)
    d.ell((82, 178, 104, 194), fill=(255, 150, 140)); d.ell((196, 178, 218, 194), fill=(255, 150, 140))
    # arms
    if mood == "cheer":
        d.line([(60, 300), (20, 190)], skin, 28); d.line([(240, 300), (282, 190)], skin, 28)
    else:
        d.line([(60, 320), (50, 400)], shirt, 34)
        d.line([(240, 320), (250, 400)], shirt, 34)
    # collar V
    d.poly([(130, 262), (150, 300), (170, 262)], fill=WHT)
    return d.get()

def draw_avatar(img, cx, cy, size, mood, t, flip=False):
    a = avatar(mood)
    if flip: a = a.transpose(Image.FLIP_LEFT_RIGHT)
    bob = math.sin(t * 5) * 8
    sc = size / 300 * (1 + 0.02 * math.sin(t * 9))
    put(img, a, cx, cy + bob, sc)

@functools.lru_cache(None)
def sticker(name, h=520):
    im = Image.open(f"stickers/{name}.png").convert("RGBA")
    im = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    # white die-cut outline
    a = im.getchannel("A").filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(1.5))
    out = Image.new("RGBA", im.size, (255, 255, 255, 0)); out.putalpha(a)
    w = Image.new("RGBA", im.size, (255, 255, 255, 255)); w.putalpha(a)
    w.alpha_composite(im)
    big = Image.new("RGBA", (im.width * S, im.height * S)); big.paste(w.resize(big.size, Image.LANCZOS))
    return big

def draw_sticker(img, name, cx, cy, h, t, t0=0.0, flip=False):
    k = back(seg(t, t0, t0 + .5))
    st = sticker(name, h)
    if flip: st = st.transpose(Image.FLIP_LEFT_RIGHT)
    sh = math.sin(t * 38) * 4 * (1 if name == "angry" else 0) * (seg(t, t0 + .5, t0 + .6) > 0)
    put(img, st, cx + sh, cy + (1 - k) * 500 + math.sin(t * 4) * 6, k, rot=math.sin(t * 3) * 3)

# ---------- icon objects ----------
@functools.lru_cache(None)
def logo_badge():
    d = D(360, 110)
    d.rect((6, 8, 354, 102), 30, fill=(0, 0, 0, 120))
    d.rect((0, 0, 348, 94), 30, fill=YEL)
    d.ell((12, 12, 82, 82), fill=INK)
    d.text((47, 48), "V", 54, YEL)
    d.text((215, 48), "V-VISA", 52, INK)
    return d.get()

@functools.lru_cache(None)
def aus_map(w=860):
    h = int(w * 0.8); d = D(w, h)
    pts = [(0.02,0.38),(0.08,0.30),(0.16,0.28),(0.24,0.22),(0.30,0.20),(0.36,0.12),(0.42,0.17),(0.48,0.12),(0.52,0.05),
           (0.58,0.08),(0.60,0.20),(0.66,0.30),(0.72,0.30),(0.80,0.40),(0.92,0.52),(0.96,0.66),(0.94,0.78),(0.86,0.90),
           (0.78,0.88),(0.72,0.78),(0.64,0.72),(0.56,0.80),(0.48,0.74),(0.40,0.78),(0.30,0.80),(0.20,0.82),(0.10,0.76),
           (0.04,0.62),(0.02,0.50)]
    P = [(x * w, y * h * 0.95 + 12) for x, y in pts]
    d.poly([(x + 8, y + 12) for x, y in P], fill=(0, 0, 0, 90))
    d.poly(P, fill=(255, 176, 70))
    d.line(P + [P[0]], YEL, 8)
    d.poly([(0.78*w,0.93*h),(0.86*w,0.92*h),(0.83*w,1.0*h),(0.79*w,0.98*h)], fill=(255, 176, 70))
    return d.get()

def pin(img, x, y, t, label=None):
    k = 1 + 0.12 * math.sin(t * 8)
    d = D(120, 160)
    d.ell((10, 10, 110, 110), fill=COR); d.poly([(22, 80), (60, 150), (98, 80)], fill=COR)
    d.ell((40, 40, 80, 80), fill=WHT)
    put(img, d.get(), x, y - 70 * k, k)

def plane(img, cx, cy, rot, sc=1.0):
    d = D(200, 200)
    d.poly([(100, 10), (126, 100), (190, 140), (190, 156), (120, 132), (112, 180), (140, 192), (140, 200),
            (100, 192), (60, 200), (60, 192), (88, 180), (80, 132), (10, 156), (10, 140), (74, 100)], fill=WHT)
    put(img, d.get(), cx, cy, sc, rot)

def check(d, cx, cy, s, col=GRN, w=14):
    d.line([(cx - s * .5, cy), (cx - s * .12, cy + s * .4), (cx + s * .55, cy - s * .4)], col, w)

def cross(d, cx, cy, s, col=COR, w=16):
    d.line([(cx - s, cy - s), (cx + s, cy + s)], col, w); d.line([(cx + s, cy - s), (cx - s, cy + s)], col, w)

def stamp_obj(text, col, w=700, h=160, size=84):
    d = D(w, h)
    d.rect((6, 6, w - 6, h - 6), 24, outline=col, width=12)
    d.text((w / 2, h / 2 + 2), text, size, col)
    return d.get()

def window(w, h, url, title_col=PUR):
    d = D(w + 40, h + 50)
    d.rect((20, 34, w + 20, h + 34), 36, fill=(0, 0, 0, 90))
    d.rect((20, 20, w + 20, h + 20), 36, fill=WHT)
    d.rect((20, 20, w + 20, 100), 36, fill=title_col); d.rect((20, 70, w + 20, 100), 0, fill=title_col)
    for i, c in enumerate((COR, YEL, GRN)): d.ell((46 + i * 40, 48, 70 + i * 40, 72), fill=c)
    d.rect((190, 40, w - 10, 82), 20, fill=(255, 255, 255, 235))
    d.text((200, 62), url, 28, INK, "lm")
    return d

# ---------- background ----------
GRAD = None
def bg(t):
    global GRAD
    if GRAD is None:
        y = np.linspace(0, 1, H)[:, None, None]
        a = np.array([16, 12, 40])[None, None, :]; b = np.array([62, 30, 120])[None, None, :]
        GRAD = (a + (b - a) * y ** 1.3).repeat(W, 1).astype("uint8")
    img = Image.fromarray(GRAD).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    off = (t * 40) % 90
    for gx in range(-1, 14):
        for gy in range(-1, 24):
            x = gx * 90 + off; y = gy * 90 + off
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255, 28))
    for i, (c, r) in enumerate(((PUR, 380), (TEAL, 300), (PINK, 260))):
        cx = W / 2 + math.sin(t * .5 + i * 2) * 380; cy = 600 + i * 450 + math.cos(t * .4 + i) * 120
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c + (38,))
    ov = ov.filter(ImageFilter.GaussianBlur(40)) if False else ov
    img.alpha_composite(ov)
    return img

# ---------- captions ----------
def make_chunks():
    ch = []; cur = []
    NUMS = ("one", "two", "three", "four")
    for i, w in enumerate(WORDS):
        gap = w["t"] - (cur[-1]["t"] + cur[-1]["d"]) if cur else 0
        if cur and (len(cur) >= 3 or gap > 0.35 or w["w"] == "Step"):
            ch.append(cur); cur = []
        cur.append(w)
        if w["w"] in NUMS and len(cur) == 2 and cur[0]["w"] == "Step":
            ch.append(cur); cur = []
        elif w["w"] in ("189", "sponsor", "limits", "rank", "apply", "changing", "website", "plan", "SkillSelect", "back", "skills", "list", "visa"):
            ch.append(cur); cur = []
    if cur: ch.append(cur)
    return ch
CHUNKS = make_chunks()

def caption(img, t):
    ci = None
    for i, c in enumerate(CHUNKS):
        start = c[0]["t"]; end = CHUNKS[i + 1][0]["t"] if i + 1 < len(CHUNKS) else c[-1]["t"] + c[-1]["d"] + .6
        if start - 0.03 <= t < end: ci = i; st = start; break
    if ci is None: return
    c = CHUNKS[ci]
    words = [w["w"].upper().replace("CUT-OFFS", "CUT-OFFS") for w in c]
    size = 128
    while size > 60:
        tw = sum(font(size).getlength(w) for w in words) + 26 * (len(words) - 1)
        if tw <= 960: break
        size -= 4
    if size <= 80 and len(words) > 1: pass
    k = back((t - st) / 0.22) if t - st < .22 else 1
    d = D(1040, 220)
    x = 1040 / 2 - tw / 2
    for j, (w, wd) in enumerate(zip(words, c)):
        wl = font(size).getlength(w)
        active = wd["t"] <= t < wd["t"] + wd["d"] + 0.18
        col = YEL if (active or t >= wd["t"] and j == len(words) - 1 and False) else WHT
        if t >= wd["t"] and not active and False: col = WHT
        wk = back((t - wd["t"]) / .2) if t >= wd["t"] else 0.0
        if t >= wd["t"] and wk < 1.0 or active:
            pass
        wy = 110 - (8 * math.sin(clamp((t - wd["t"]) / .25) * math.pi) if t >= wd["t"] else 0)
        d.text((x + wl / 2, wy), w, size, col, stroke=11, sfill=(18, 12, 44))
        if active:
            d.rect((x, 178, x + wl, 190), 6, fill=col)
        x += wl + 26
    put(img, d.get(), W / 2, 395, k, rot=(1 - k) * -3)

# ---------- scene helpers ----------
CY = 930  # centre of middle zone

def label(img, text, cx, cy, col=YEL, tc=INK, size=48, sc=1.0, w=None):
    tw = font(size * S).getlength(text) / S + 70
    d = D(int(tw), 100)
    d.rect((0, 0, tw, 90), 40, fill=col); d.text((tw / 2, 47), text, size, tc)
    put(img, d.get(), cx, cy, sc)

def s_hook(img, t):
    k = back(seg(t, 0, .5)); m = aus_map()
    put(img, m, 540, CY + 20, k * 1.0)
    pin(img, 540 + 90, CY + 20 + 40, t) if t > .5 else None
    # plane orbit
    a = t * 1.8
    plane(img, 540 + math.cos(a) * 420, CY - 120 + math.sin(a) * 200, math.degrees(-a) - 0, 0.6)
    q = D(300, 300)
    for i, (x, y, s_) in enumerate(((60, 90, 120), (200, 190, 150))):
        q.text((x + 40, y + 20), "?", s_, YEL, stroke=8)
    put(img, q.get(), 220, 640 + math.sin(t * 6) * 12, 1, -8)
    draw_avatar(img, 900, 1230, 300, "think", t, True)
    label(img, "STAY BACK IN AUSTRALIA?", 470, 1330, COR, WHT, 46, ease_out(seg(t, 1.2, 1.6)))

def s_title(img, t):
    k = back(seg(t, 0, .45))
    d = D(940, 560)
    d.rect((12, 28, 928, 540), 60, fill=(0, 0, 0, 100))
    d.rect((0, 0, 916, 512), 60, fill=WHT)
    d.rect((0, 0, 916, 150), 60, fill=PUR); d.rect((0, 100, 916, 150), 0, fill=PUR)
    d.text((458, 78), "AUSTRALIA  VISA", 52, WHT)
    d.text((458, 280), "SUBCLASS", 78, INK)
    d.text((458, 400), "189", 190, PUR, stroke=0)
    d.ell((770, 190, 890, 310), outline=COR, width=8)
    put(img, d.get(), 540, CY, k, rot=math.sin(t * 3) * 1.2)
    # sparkle
    for i in range(6):
        a = i * 1.05 + t * 2; r = 460 + 30 * math.sin(t * 4 + i)
        x = 540 + math.cos(a) * r * 1.0; y = CY + math.sin(a) * r * .65
        s_ = 10 + 8 * math.sin(t * 7 + i)
        ImageDraw.Draw(img).polygon([(x, y - s_ * 2), (x + s_, y), (x, y + s_ * 2), (x - s_, y)], fill=YEL)
    draw_avatar(img, 190, 1290, 320, "cheer", t)

def s_sponsor(img, t):
    # t: voice time 6.5-15
    items = [(7.0, "SKILLED INDEPENDENT", PUR, None), (9.35, "NO EMPLOYER SPONSOR", COR, "emp"),
             (11.4, "NO STATE SPONSOR", COR, "state"), (13.2, "JUST YOUR SKILLS", GRN, "skill")]
    ys = [660, 880, 1100, 1320]
    for (t0, txt, col, ic), y in zip(items, ys):
        k = back(seg(t, t0 - .15, t0 + .3))
        if k <= 0: continue
        d = D(960, 190)
        d.rect((10, 22, 950, 180), 40, fill=(0, 0, 0, 100))
        d.rect((0, 0, 936, 160), 40, fill=WHT, outline=col, width=10)
        d.ell((26, 22, 136, 132), fill=col)
        if ic == "emp":
            d.rect((50, 55, 112, 112), 4, fill=WHT)
            for i in range(3):
                for j in range(2): d.rect((58 + i * 18, 62 + j * 24, 66 + i * 18, 76 + j * 24), 1, fill=col)
        elif ic == "state":
            d.line([(60, 40), (60, 118)], WHT, 8); d.poly([(64, 42), (112, 54), (64, 78)], fill=WHT)
        elif ic == "skill":
            d.poly([(81 + 36 * math.sin(i * 2 * math.pi / 5), 77 - 36 * math.cos(i * 2 * math.pi / 5)) for i in (0, 2, 4, 1, 3)], fill=WHT)
        else:
            d.text((81, 78), "189", 36, WHT)
        d.text((520, 82), txt, 46 if len(txt) > 17 else 52, INK)
        if ic in ("emp", "state"):
            sk = seg(t, t0 + .3, t0 + .5)
            if sk > 0:
                cross(d, 870, 82, 34 * ease_out(sk), COR, 16)
        if ic == "skill":
            sk = seg(t, t0 + .3, t0 + .5)
            if sk > 0: check(d, 870, 82, 80 * ease_out(sk), GRN, 16)
        put(img, d.get(), 540, y, k)

def s_step1(img, t):
    k = back(seg(t, 0, .4))
    d = shadow_card(860, 640)
    d.text((450, 80), "SKILLED OCCUPATION LIST", 46, PUR)
    rows = 5
    for i in range(rows):
        y = 150 + i * 100
        hit = i == 2
        hl = ease_out(seg(t, 1.8, 2.4))
        if hit and hl > 0:
            d.rect((50, y - 8, 870, y + 78), 20, fill=(255, 235, 150))
        d.ell((70, y + 6, 120, y + 56), fill=(220, 220, 235))
        d.rect((150, y + 14, 150 + (400 if not hit else 480), y + 48), 12, fill=(215, 215, 232) if not hit else PUR)
        if hit:
            d.text((700, y + 33), "YOUR JOB", 26, WHT if False else INK)
    put(img, d.get(), 540, CY - 40, k)
    # magnifier moving down list
    mx = 760; my = 760 + 100 * (ease_out(seg(t, .6, 2.0)) * 2)
    m = D(220, 220); m.ell((20, 20, 140, 140), outline=INK, width=16, fill=(255, 255, 255, 60)); m.line([(120, 120), (200, 200)], INK, 24)
    put(img, m.get(), mx + 60, my + 30, 1.0)
    tk = ease_out(seg(t, 2.6, 3.0))
    if tk > 0:
        c = D(200, 200); c.ell((10, 10, 190, 190), fill=GRN); check(c, 100, 100, 100, WHT, 20)
        put(img, c.get(), 900, 600, back(seg(t, 2.6, 3.0)))
    draw_avatar(img, 190, 1330, 300, "think" if t < 3 else "smile", t)

def s_step2(img, t):
    k = back(seg(t, 0, .4))
    d = shadow_card(800, 700)
    d.text((420, 80), "SKILLS ASSESSMENT", 54, PUR)
    d.rect((60, 130, 780, 142), 4, fill=(230, 230, 245))
    for i in range(6):
        d.rect((80, 190 + i * 52, 80 + (620 if i % 3 else 480), 214 + i * 52), 10, fill=(220, 220, 238))
    d.ell((560, 470, 720, 630), fill=(255, 230, 150), outline=YEL, width=6)
    d.text((640, 550), "★", 80, YEL, path=FB)
    put(img, d.get(), 540, CY - 20, k)
    sk = seg(t, 1.3, 1.65)
    if sk > 0:
        put(img, stamp_obj("POSITIVE", GRN, 620, 160, 90), 540, CY + 60, 2.2 - 1.2 * ease_out(sk), -10, ease_out(sk * 2))
    draw_avatar(img, 890, 1330, 300, "cheer" if t > 1.6 else "smile", t, True)

def s_step3(img, t):
    # English card + age card
    k1 = back(seg(t, 0, .4)); k2 = back(seg(t, 1.4, 1.8))
    d = shadow_card(860, 360)
    d.text((430, 70), "ENGLISH SCORE", 48, PUR)
    d.rect((60, 140, 800, 190), 25, fill=(225, 225, 240))
    fill = ease_out(seg(t, .3, 1.2))
    d.rect((60, 140, 60 + 740 * .8 * fill, 190), 25, fill=TEAL)
    d.rect((60 + 740 * .8 - 4, 120, 60 + 740 * .8 + 4, 210), 2, fill=INK)
    d.text((60 + 740 * .8, 245), "REQUIRED LEVEL", 30, INK)
    if fill > .95: check(d, 760, 290, 60, GRN, 14)
    put(img, d.get(), 540, 790, k1)
    d = shadow_card(860, 360)
    d.text((430, 70), "AGE LIMIT", 48, PUR)
    d.rect((60, 140, 800, 190), 25, fill=(225, 225, 240))
    d.rect((60, 140, 560, 190), 25, fill=COR if False else YEL)
    pos = 60 + 500 * ease_out(seg(t, 1.8, 2.8))
    d.ell((pos - 28, 130, pos + 28, 200), fill=PUR, outline=WHT, width=5)
    d.text((300, 245), "WITHIN LIMITS", 34, INK)
    if t > 2.8: check(d, 760, 290, 60, GRN, 14)
    put(img, d.get(), 540, 1190, k2)

def s_step4(img, t):
    k = back(seg(t, 0, .4))
    w = window(880, 560, "skillselect.homeaffairs.gov.au")
    d = w
    d.text((460, 150), "EXPRESSION OF INTEREST", 38, PUR)
    fields = ["NAME", "OCCUPATION", "ENGLISH"]
    for i, f in enumerate(fields):
        y = 210 + i * 100
        d.text((70, y), f, 24, (120, 120, 150), "lm")
        d.rect((70, y + 20, 830, y + 70), 14, fill=(236, 236, 246))
        fl = ease_out(seg(t, .8 + i * .7, 1.5 + i * .7))
        d.rect((80, y + 32, 80 + 480 * fl, y + 58), 8, fill=PUR)
    sub = seg(t, 3.0, 3.4)
    d.rect((510, 500, 830, 580), 28, fill=GRN if sub > 0 else TEAL)
    d.text((670, 541), "SUBMIT", 40, WHT)
    put(img, d.get(), 540, 740, k)
    # points -> rank ladder
    k2 = back(seg(t, 3.9, 4.4))
    if k2 > 0:
        c = shadow_card(900, 470)
        c.text((450, 62), "POINTS TEST  =  YOUR RANK", 42, PUR)
        pts = ease_out(seg(t, 4.4, 6.4))
        names = [("#1", .95), ("#2", .8), ("YOU", .55 + .35 * pts), ("#4", .5)]
        order = sorted(names, key=lambda n: -n[1])
        for i, (n, v) in enumerate(order):
            y = 130 + i * 82
            me = n == "YOU"
            c.rect((50, y, 850, y + 66), 18, fill=(255, 235, 150) if me else (236, 236, 246))
            c.text((100, y + 34), n, 34, INK, "lm")
            c.rect((200, y + 16, 200 + 560 * v, y + 50), 12, fill=PUR if me else (190, 190, 215))
        put(img, c.get(), 540, 1330, k2)

def s_invite(img, t):
    k = back(seg(t, 0, .4))
    e = D(700, 520)
    e.rect((20, 40, 680, 500), 28, fill=(0, 0, 0, 90))
    op = ease_out(seg(t, .5, 1.1))
    # letter rising
    ly = 230 - 215 * op
    e.rect((100, ly, 600, ly + 360), 20, fill=WHT)
    e.text((350, ly + 60), "INVITATION", 56, PUR); e.text((350, ly + 135), "TO APPLY", 50, INK)
    e.rect((20, 230, 680, 500), 28, fill=YEL)
    e.poly([(20, 230), (350, 400 - 200 * op), (680, 230)], fill=(255, 190, 40))
    e.poly([(20, 500), (350, 340), (680, 500)], fill=(255, 200, 60))
    put(img, e.get(), 540, CY - 40, k)
    b = seg(t, 1.5, 1.9)
    if b > 0: label(img, "THEN APPLY!", 540, 1290, GRN, WHT, 58, back(b))
    for i in range(10):
        a = i * .63 + t * 3; r = 420 * ease_out(seg(t, .5, 1.5)); x = 540 + math.cos(a) * r; y = CY - 40 + math.sin(a) * r * .7
        ImageDraw.Draw(img).ellipse((x - 9, y - 9, x + 9, y + 9), fill=[YEL, PINK, TEAL][i % 3])

def s_warn(img, t):
    k = back(seg(t, 0, .4))
    d = shadow_card(880, 520)
    d.text((440, 70), "POINTS CUT-OFFS", 48, PUR)
    # moving chart
    pts = []
    for i in range(14):
        x = 70 + i * 55; y = 300 + math.sin(i * .9 + t * 2) * 80 + math.sin(i * .37) * 40
        pts.append((x, y))
    d.line(pts, COR, 10)
    for p in pts[::3]: d.ell((p[0] - 10, p[1] - 10, p[0] + 10, p[1] + 10), fill=PUR)
    d.text((440, 450), "KEEPS CHANGING", 44, INK)
    put(img, d.get(), 540, 780, k)
    sk = seg(t, 2.35, 2.7)
    if sk > 0: put(img, stamp_obj("NOT GUARANTEED", COR, 860, 160, 70), 540, 1130, 2.0 - 1.0 * ease_out(sk), -6, ease_out(sk * 2))
    draw_sticker(img, "angry", 200, 1290, 380, t, 0.2)

def s_official(img, t):
    k = back(seg(t, 0, .4))
    w = window(900, 600, "homeaffairs.gov.au", (30, 90, 170))
    w.text((470, 190), "DEPARTMENT OF", 36, (30, 90, 170)); w.text((470, 240), "HOME AFFAIRS", 54, (30, 90, 170))
    for i in range(4): w.rect((90, 310 + i * 50, 90 + (700 if i % 2 else 560), 336 + i * 50), 10, fill=(220, 225, 240))
    put(img, w.get(), 540, 830, k)
    m = D(260, 260); m.ell((20, 20, 170, 170), outline=COR, width=20, fill=(255, 255, 255, 50)); m.line([(150, 150), (240, 240)], COR, 28)
    put(img, m.get(), 660 + math.sin(t * 3) * 40, 900 + math.cos(t * 3) * 30, back(seg(t, .5, .9)))
    label(img, "CHECK THE OFFICIAL SITE", 540, 1230, TEAL, INK, 48, ease_out(seg(t, 1.0, 1.4)))

def s_cta(img, t):
    k = back(seg(t, 0, .5))
    pul = 1 + .05 * math.sin(t * 7)
    d = D(900, 380)
    d.rect((14, 28, 886, 366), 70, fill=(0, 0, 0, 110))
    d.rect((0, 0, 872, 330), 70, fill=YEL)
    d.text((436, 110), "DM", 96, INK); d.text((436, 235), "START", 150, PUR)
    put(img, d.get(), 540, 760, k * pul, math.sin(t * 3) * 1.5)
    label(img, "vvisa.in", 540, 1010, WHT, PUR, 76, back(seg(t, .6, 1.0)))
    label(img, "YOUR AUSTRALIA PLAN", 540, 1150, PUR, WHT, 46, ease_out(seg(t, 1.0, 1.4)))
    draw_avatar(img, 540, 1400, 360, "cheer", t)
    for i in range(14):
        a = i * .9 + t * 1.5; x = 540 + math.cos(a) * 470; y = 800 + math.sin(a * 1.3) * 420
        ImageDraw.Draw(img).ellipse((x - 8, y - 8, x + 8, y + 8), fill=[YEL, PINK, TEAL, WHT][i % 4])

def scene_for(t):
    if t < 3.55: return s_hook, t
    if t < 6.5: return s_title, t - 3.55
    if t < 15.0: return s_sponsor, t
    if t < 20.0: return s_step1, t - 15.0
    if t < 23.3: return s_step2, t - 20.0
    if t < 27.3: return s_step3, t - 23.3
    if t < 34.6: return s_step4, t - 27.3
    if t < 37.0: return s_invite, t - 34.6
    if t < 42.3: return s_warn, t - 37.0
    if t < 45.5: return s_official, t - 42.3
    return s_cta, t - 45.5

STEP_T = [15.0, 20.0, 23.3, 27.3, 34.6]
STEP_L = ["OCCUPATION", "ASSESSMENT", "ENGLISH+AGE", "EOI+POINTS", "INVITE"]
def ladder(img, t):
    a = ease_out(seg(t, 14.4, 15.0)) * (1 - seg(t, 45.2, 45.6))
    if a <= 0: return
    d = D(1040, 200)
    xs = [100 + i * 210 for i in range(5)]
    d.line([(xs[0], 70), (xs[-1], 70)], (255, 255, 255, 60), 12)
    prog = 0
    for i, x in enumerate(xs):
        st = STEP_T[i]; nxt = STEP_T[i + 1] if i < 4 else 37.0
        done = t >= nxt; act = st <= t < nxt
        if i < 4 and t >= st: prog = max(prog, x + (xs[i + 1] - x) * clamp((t - st) / (nxt - st)))
        col = GRN if done else (YEL if act else (120, 110, 160))
        r = 40 + (6 * math.sin(t * 8) if act else 0)
        d.ell((x - r, 70 - r, x + r, 70 + r), fill=col, outline=WHT, width=5)
        if done: check(d, x, 70, 44, WHT, 9)
        else: d.text((x, 72), str(i + 1), 40, INK)
        d.text((x, 150), STEP_L[i], 24, WHT if (done or act) else (170, 160, 210))
    if prog: d.line([(xs[0], 70), (prog, 70)], GRN, 12)
    put(img, d.get(), W / 2, 1620, 1.0, alpha=a)

def opener(img, t):
    # 0-3s: "DAY 05" title card, exits by slide-up
    ex = ease_out(seg(t, 2.6, 3.0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    k = back(seg(t, .1, .6))
    d = D(1000, 560)
    d.text((500, 170), "DAY 05", 250, YEL, stroke=14, sfill=INK)
    d.text((500, 360), "of knowing", 100, WHT, stroke=8, sfill=INK)
    d.text((500, 470), "study visa", 100, WHT, stroke=8, sfill=INK)
    put(ov, d.get(), W / 2, 760, k)
    draw_avatar(ov, 540, 1400, 420, "cheer", t)
    label(ov, "AUSTRALIA 189", 540, 1130, PINK, WHT, 56, back(seg(t, 1.0, 1.4)))
    img.alpha_composite(ov, (0, int(-ex * H * 1.1)) if False else (0, 0)) if ex <= 0 else img.alpha_composite(ov.crop((0, 0, W, H)), (0, int(-ex * H)))  # slide up

HITS = [OFF + 9.5, OFF + 11.5, OFF + 39.4, OFF + 19.3, OFF + 22.5, OFF + 26.4, OFF + 31.0, OFF + 35.0, OFF + 47.9]
BOUNDS = [OFF + sc[0] for sc in SCENES[1:]]

def camera(layer, T, lt):
    z = 1 + 0.09 * (1 - ease_out(seg(lt, 0, .45))) + 0.012 * min(lt, 6) / 6
    dx = dy = 0.0
    for h in HITS:
        dt = T - h
        if 0 <= dt < .35:
            dx += math.sin(dt * 90) * 14 * (1 - dt / .35); dy += math.cos(dt * 75) * 10 * (1 - dt / .35)
            z += 0.035 * (1 - dt / .35)
    if z == 1 and not dx: return layer
    nw, nh = int(W * z), int(H * z)
    r = layer.resize((nw, nh), Image.BILINEAR)
    cx, cy = 540 * z, 1000 * z
    ox = int(cx - 540 - dx); oy = int(cy - 1000 - dy)
    ox = max(0, min(nw - W, ox)); oy = max(0, min(nh - H, oy))
    return r.crop((ox, oy, ox + W, oy + H))

def fx(img, T):
    d = ImageDraw.Draw(img, "RGBA")
    for h in HITS:
        dt = T - h
        if 0 <= dt < .45:
            p = ease_out(dt / .45)
            for k in range(18):
                a = k * math.pi / 9 + .2
                r0 = 120 + 520 * p; r1 = r0 + 160 * (1 - p) + 20
                d.line([(540 + math.cos(a) * r0, 980 + math.sin(a) * r0), (540 + math.cos(a) * r1, 980 + math.sin(a) * r1)],
                       fill=(255, 255, 255, int(200 * (1 - p))), width=8)
    for bt in BOUNDS:
        dt = T - bt
        if -0.05 <= dt < .38:
            p = clamp((dt + .05) / .43); x = -W + (2 * W + 300) * ease_out(p) if False else -500 + (W + 1000) * p
            col = [YEL, TEAL, PINK][int(bt) % 3]
            d.polygon([(x, 0), (x + 260, 0), (x - 140, H), (x - 400, H)], fill=col + (150,))
            d.polygon([(x + 300, 0), (x + 380, 0), (x - 20, H), (x - 100, H)], fill=(255, 255, 255, 120))

def frame(i):
    T = i / FPS
    t = T - OFF
    img = bg(T)
    if t >= 0:
        fn, lt = scene_for(t)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fn(layer, lt)
        layer = camera(layer, T, lt)
        img.alpha_composite(layer)
        ladder(img, t)
        caption(img, t)
        fx(img, T)
    if T < OFF + .4:
        opener(img, T)
    put(img, logo_badge(), 60 + 190 + 4 * math.sin(T * 3), 120, 1.0 + 0.02 * math.sin(T * 5))
    d = ImageDraw.Draw(img)
    f = font(40)
    if t >= 0 and t < 45.4:
        d.text((W - 60, 105), "DAY 05  |  AUSTRALIA", font=f, fill=WHT, anchor="rm", stroke_width=6, stroke_fill=INK)
    if t >= 0:
        d.text((W / 2, 1850), "vvisa.in", font=font(44), fill=(255, 255, 255, 200), anchor="mm")
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "still":
        for tt in a[1:]:
            i = int(float(tt) * FPS)
            Image.frombytes("RGB", (W, H), frame(i)).save(f"still_{tt}.png")
        sys.exit()
    n = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                           "video_silent.mp4"], stdin=subprocess.PIPE)
    with Pool(4) as p:
        for k, b in enumerate(p.imap(frame, range(n), chunksize=4)):
            ff.stdin.write(b)
            if k % 100 == 0: print(k, n, flush=True)
    ff.stdin.close(); ff.wait()
