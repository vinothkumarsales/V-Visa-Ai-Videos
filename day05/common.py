import json
OFF = 3.0            # opener length; voice starts here
DUR = 56.4           # total video length
FPS = 30
W, H = 1080, 1920
WORDS = json.load(open("words.json"))
# scenes in voice-time seconds: (start, end, name)
SCENES = [
    (0.0, 3.55, "hook"), (3.55, 6.5, "title"), (6.5, 9.2, "skilled"),
    (9.2, 11.3, "nosponsor1"), (11.3, 13.2, "nosponsor2"), (13.2, 15.0, "skills"),
    (15.0, 20.0, "step1"), (20.0, 23.3, "step2"), (23.3, 27.3, "step3"),
    (27.3, 34.6, "step4"), (34.6, 37.0, "invite"), (37.0, 42.3, "warn"),
    (42.3, 45.5, "official"), (45.5, 99.0, "cta"),
]
# sfx: (video time, kind)
SFX = [(0.0, "whoosh"), (0.15, "hit")]
for s, e, n in SCENES:
    SFX.append((OFF + s, "whoosh"))
for t in (9.5, 11.5): SFX.append((OFF + t, "stamp"))
SFX += [(OFF + 13.5, "ding"), (OFF + 19.3, "ding"), (OFF + 22.5, "ding"), (OFF + 26.4, "ding"),
        (OFF + 31.0, "ding"), (OFF + 35.0, "ding2"), (OFF + 39.4, "stamp"), (OFF + 47.9, "pop")]
