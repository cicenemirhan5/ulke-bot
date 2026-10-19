"""Senaryoyu seslendirir (edge-tts) ve 1080x1920 dikey videoya çevirir."""
import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H = 1080, 1920
PALETTES = [
    ((20, 30, 60), (90, 40, 120)),
    ((10, 60, 50), (20, 110, 90)),
    ((70, 20, 20), (150, 60, 40)),
    ((15, 25, 45), (30, 90, 150)),
    ((50, 35, 10), (140, 100, 30)),
]


def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_frame(text, idx, total, day, path):
    top, bottom = PALETTES[(day + idx) % len(PALETTES)]
    img = Image.new("RGB", (W, H), top)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    d.text((60, 110), f"{tr_upper(cfg['country_name'])} • GÜN {day}", font=font(54), fill=(255, 215, 100))
    big = font(96)
    lines = wrap(d, tr_upper(text), big, W - 160)
    lh = 120
    y = (H - lh * len(lines)) // 2
    for ln in lines:
        w = d.textlength(ln, font=big)
        d.text(((W - w) / 2, y), ln, font=big, fill="white", stroke_width=4, stroke_fill=(0, 0, 0))
        y += lh
    for i in range(total):
        x = W // 2 - (total * 40) // 2 + i * 40
        d.ellipse([x, H - 200, x + 20, H - 180], fill="white" if i == idx else (120, 120, 120))
    img.save(path)


async def main():
    data = json.loads((ROOT / "output" / "today.json").read_text(encoding="utf-8"))
    day = data["day"]
    work = ROOT / "output" / "work"
    work.mkdir(parents=True, exist_ok=True)
    segs = []
    for i, s in enumerate(data["scenes"]):
        png, mp3, mp4 = work / f"s{i}.png", work / f"s{i}.mp3", work / f"s{i}.mp4"
        make_frame(s["visual_text"], i, len(data["scenes"]), day, png)
        await edge_tts.Communicate(s["narration"], cfg["voice"], rate=cfg.get("rate", "+8%")).save(str(mp3))
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(png), "-i", str(mp3),
            "-af", "apad=pad_dur=0.35",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
            "-shortest", str(mp4),
        ], check=True, capture_output=True)
        segs.append(mp4)

    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segs), encoding="utf-8")
    vids = ROOT / "videos"
    vids.mkdir(exist_ok=True)
    out = vids / f"day-{day:03d}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)],
                   check=True, capture_output=True)

    for old in sorted(vids.glob("day-*.mp4"))[:-3]:
        old.unlink()

    data["video_path"] = f"videos/{out.name}"
    (ROOT / "output" / "today.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Video hazır:", out)


if __name__ == "__main__":
    asyncio.run(main())
