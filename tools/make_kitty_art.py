"""
Draws Lil Kitty as clean, sketchy line art (white floof, soft dark lines) and saves PNG sprites:
  assets/kitty/body_<face>.png  (one per mood, 400x400, transparent)
  assets/kitty/tail.png         (separate so it can swish)
Original art, drawn with code. Run: python tools/make_kitty_art.py
"""
import math
import os
import random

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "kitty")
S, K = 400, 4                    # final size, supersample factor
INK = (58, 52, 66, 255)
SOFT = (58, 52, 66, 90)
FILL = (255, 255, 255, 255)
BLUSH = (255, 150, 180, 255)
LW = 2.6                          # line width at 1x
FACES = ["idle", "blink", "happy", "shy", "sleepy", "boop", "eat", "grumpy", "hungry", "love"]


def P(x, y):
    return (x * K, y * K)


def spline(pts, n=10, closed=False):
    """Catmull-Rom through the points -> smooth polyline."""
    if closed:
        pts = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        pts = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    if not closed:
        out.append(pts[-2])
    return out


class Pen:
    def __init__(self, img, seed=1):
        self.d = ImageDraw.Draw(img)
        self.rng = random.Random(seed)

    def line(self, pts, w=LW, color=INK, sketch=True, closed=False, smooth=True):
        line = spline(pts, closed=closed) if smooth else list(pts) + ([pts[0]] if closed else [])
        if closed and smooth:
            line = line + [line[0]]
        sc = [P(*p) for p in line]
        self.d.line(sc, fill=color, width=int(w * K), joint="curve")
        r = w * K / 2
        for x, y in (sc[0], sc[-1]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=color)
        if sketch:      # a lighter second pass, a hair off, so it feels hand-drawn
            j = [(x + self.rng.uniform(-0.7, 0.7) * K, y + self.rng.uniform(-0.7, 0.7) * K) for x, y in sc]
            self.d.line(j, fill=SOFT, width=max(1, int(w * K * 0.55)), joint="curve")

    def fill(self, pts, color=FILL, smooth=True, closed=True):
        line = spline(pts, closed=True) if smooth else pts
        self.d.polygon([P(*p) for p in line], fill=color)

    def shape(self, pts, w=LW, color=FILL):
        self.fill(pts, color)
        self.line(pts, w, closed=True)

    def dot(self, x, y, r, color=INK):
        self.d.ellipse([(x - r) * K, (y - r) * K, (x + r) * K, (y + r) * K], fill=color)


# ------------------------------------------------------------------ the kitty ---
HEAD = [(200, 64), (232, 68), (258, 82), (271, 104), (272, 126), (283, 138), (268, 146), (278, 158), (258, 162),
        (240, 176), (200, 182), (160, 176), (142, 162), (122, 158), (132, 146), (117, 138), (128, 126), (129, 104),
        (142, 82), (168, 68)]
EAR_L = [(152, 88), (130, 64), (104, 50), (78, 48), (64, 56), (66, 72), (82, 92), (106, 108), (132, 116)]
EAR_R = [(248, 88), (270, 64), (296, 50), (322, 48), (336, 56), (334, 72), (318, 92), (294, 108), (268, 116)]
TUFT = [(188, 74), (182, 60), (174, 50), (166, 46), (180, 46), (194, 56), (196, 44), (204, 34), (216, 30), (210, 40), (208, 54), (214, 66), (216, 76)]
TORSO = [(180, 196), (220, 196), (225, 236), (221, 262), (179, 262), (175, 236)]
LEG_L = [(181, 252), (198, 252), (199, 300), (200, 326), (195, 334), (181, 334), (177, 326), (179, 300)]
LEG_R = [(202, 252), (219, 252), (221, 300), (223, 326), (219, 334), (205, 334), (200, 326), (201, 300)]
ARM_L = [(170, 194), (184, 196), (191, 234), (199, 254), (196, 264), (187, 263), (181, 240), (166, 206)]
ARM_R = [(230, 194), (216, 196), (209, 234), (201, 254), (204, 264), (213, 263), (219, 240), (234, 206)]
CHEST = [(166, 168), (234, 168), (248, 180), (240, 188), (248, 200), (232, 204), (236, 216), (218, 214), (208, 234), (200, 222), (192, 234), (182, 214), (164, 216), (168, 204), (152, 200), (160, 188), (152, 180)]
TAIL = [(222, 258), (250, 280), (280, 292), (306, 290), (326, 276), (340, 256), (348, 234), (344, 212), (336, 226), (330, 210), (324, 230), (316, 246), (302, 260), (282, 268), (258, 266), (236, 254), (226, 246)]
TAIL_PIVOT = (224, 248)


def body(face):
    img = Image.new("RGBA", (S * K, S * K), (0, 0, 0, 0))
    pen = Pen(img, seed=FACES.index(face) + 3)
    # legs + torso
    pen.shape(LEG_L)
    pen.shape(LEG_R)
    pen.line([(186, 326), (186, 330)], w=1.6, sketch=False)      # toe beans lines
    pen.line([(214, 326), (214, 330)], w=1.6, sketch=False)
    pen.shape(TORSO)
    # arms down in front, paws meeting
    pen.shape(ARM_L)
    pen.shape(ARM_R)
    for x in (192, 208):                                          # paw toe lines
        pen.line([(x, 258), (x + (2 if x < 200 else -2), 263)], w=1.4, sketch=False)
    # big chest ruff over the shoulders
    pen.fill(CHEST, smooth=False)
    pen.line(CHEST, w=2.4, closed=True, smooth=False)
    pen.line([(186, 196), (192, 206)], w=1.4)                    # lil fluff strokes
    pen.line([(214, 196), (208, 206)], w=1.4)
    # ears behind the head
    for ear, inner in ((EAR_L, [(140, 100), (112, 76), (86, 62)]),
                       (EAR_R, [(260, 100), (288, 76), (314, 62)])):
        pen.shape(ear)
        pen.line(inner, w=1.6)
    # head + tuft
    pen.shape(HEAD)
    pen.fill(TUFT + [(200, 82)])                                  # swoopy hair curl on top
    pen.line(TUFT, w=2.4)
    # face
    ex = (176, 224)
    ey = 128
    blush = face in ("shy", "happy", "love", "eat", "idle", "hungry")
    if blush:
        for x0 in (156, 232):
            for k in range(3):
                pen.line([(x0 + k * 5, 152), (x0 + k * 5 + 4, 146)], w=1.5, color=BLUSH, sketch=False)
    if face in ("idle", "shy", "hungry", "grumpy"):
        for i, x in enumerate(ex):
            look = -3 if face == "shy" else 0
            pen.d.ellipse([P(x - 9 + look, ey - 12), P(x + 9 + look, ey + 12)], fill=INK)
            pen.dot(x - 3 + look, ey - 5, 3.6, (255, 255, 255, 255))
            pen.dot(x + 3 + look, ey + 5, 1.6, (255, 255, 255, 255))
            if face == "shy":        # worried lil brows
                pen.line([(x - 9, ey - 20 + (4 if i == 0 else 0)), (x + 9, ey - 20 + (0 if i == 0 else 4))], w=1.8)
            if face == "grumpy":     # flat annoyed lids
                pen.d.rectangle([P(x - 11, ey - 14), P(x + 11, ey - 3)], fill=FILL)
                pen.line([(x - 11, ey - 3), (x + 11, ey - 3)], w=2.4)
    elif face == "love":
        for x in ex:
            pts = [(x, ey + 9), (x - 10, ey - 1), (x - 8, ey - 9), (x - 2, ey - 9), (x, ey - 4), (x + 2, ey - 9),
                   (x + 8, ey - 9), (x + 10, ey - 1)]
            pen.fill(pts, (255, 110, 160, 255))
    elif face in ("happy", "eat"):
        for x in ex:
            pen.line([(x - 9, ey + 3), (x, ey - 6), (x + 9, ey + 3)], w=3)          # ^ ^
    elif face in ("blink", "sleepy"):
        for x in ex:
            pen.line([(x - 9, ey + 2), (x, ey + 5), (x + 9, ey + 2)], w=2.6)         # closed
    elif face == "boop":
        for x in ex:
            pen.line([(x - 8, ey - 7), (x + 5, ey), (x - 8, ey + 7)] if x < 200 else [(x + 8, ey - 7), (x - 5, ey), (x + 8, ey + 7)],
                     w=2.8, smooth=False)                                           # > <
    # nose + mouth
    pen.fill([(196, 146), (204, 146), (200, 151)], INK, smooth=False)
    if face in ("eat", "hungry", "boop"):
        h = 9 if face == "eat" else 6
        pen.d.ellipse([P(195, 153), P(205, 153 + h)], fill=INK)
    else:
        pen.line([(191, 152), (195, 156), (200, 152), (205, 156), (209, 152)], w=2)   # :3
    return img.resize((S, S), Image.LANCZOS)


def tail():
    img = Image.new("RGBA", (S * K, S * K), (0, 0, 0, 0))
    pen = Pen(img, seed=99)
    pen.shape(TAIL)
    pen.line([(300, 262), (318, 248)], w=1.4)
    return img.resize((S, S), Image.LANCZOS)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in FACES:
        body(f).save(os.path.join(OUT, f"body_{f}.png"))
    tail().save(os.path.join(OUT, "tail.png"))
    print("saved", len(FACES) + 1, "kitty sprites to", os.path.abspath(OUT))
