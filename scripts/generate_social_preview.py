from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets" / "social-preview.png"
SIZE = (1280, 640)


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    fonts_dir = Path("C:/Windows/Fonts")
    candidates = [
        fonts_dir / name,
        fonts_dir / "arial.ttf",
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    width, height = size
    gradient = Image.new("RGB", size, top)
    draw = ImageDraw.Draw(gradient)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    return gradient


def draw_chip(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], label: str, font: ImageFont.ImageFont) -> None:
    draw.rounded_rectangle(xy, radius=24, fill=(11, 78, 94, 210), outline=(133, 233, 255, 180), width=2)
    left, top, right, bottom = xy
    text_box = draw.textbbox((0, 0), label, font=font)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    x = left + (right - left - text_width) / 2
    y = top + (bottom - top - text_height) / 2 - 2
    draw.text((x, y), label, font=font, fill=(236, 250, 252))


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    base = vertical_gradient(SIZE, (5, 24, 36), (9, 81, 99)).convert("RGBA")
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    title_font = load_font("segoeuib.ttf", 76)
    subtitle_font = load_font("segoeui.ttf", 26)
    chip_font = load_font("segoeui.ttf", 24)
    tiny_font = load_font("segoeui.ttf", 18)

    draw.ellipse((770, 40, 1210, 480), fill=(28, 143, 166, 70))
    draw.ellipse((910, 120, 1300, 560), fill=(248, 182, 72, 55))
    draw.rounded_rectangle((60, 64, 716, 576), radius=36, fill=(7, 32, 44, 150), outline=(123, 220, 242, 70), width=2)

    draw.text((96, 108), "MediaScribe", font=title_font, fill=(244, 251, 252))
    draw.text(
        (98, 212),
        "Transcribe and summarize audio, text, and video",
        font=subtitle_font,
        fill=(202, 235, 240),
    )
    draw.text(
        (98, 256),
        "Local or cloud ASR, reusable CLI workflows,",
        font=subtitle_font,
        fill=(177, 223, 231),
    )
    draw.text(
        (98, 294),
        "subtitle-first video summaries.",
        font=subtitle_font,
        fill=(177, 223, 231),
    )

    draw_chip(draw, (98, 358, 224, 412), "audio", chip_font)
    draw_chip(draw, (240, 358, 348, 412), "text", chip_font)
    draw_chip(draw, (364, 358, 486, 412), "video", chip_font)

    draw.text((98, 466), "Python 3.10+  |  Whisper  |  Ollama  |  yt-dlp", font=tiny_font, fill=(167, 216, 223))

    card_shadow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(card_shadow)
    shadow_draw.rounded_rectangle((824, 108, 1164, 540), radius=34, fill=(0, 0, 0, 110))
    card_shadow = card_shadow.filter(ImageFilter.GaussianBlur(24))
    base.alpha_composite(card_shadow)

    card = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card)
    card_draw.rounded_rectangle((842, 92, 1182, 524), radius=34, fill=(238, 247, 248, 235))
    card_draw.rounded_rectangle((872, 128, 1152, 266), radius=26, fill=(216, 244, 246))
    card_draw.rounded_rectangle((872, 286, 1152, 358), radius=22, fill=(10, 102, 124))
    card_draw.rounded_rectangle((872, 378, 1022, 450), radius=22, fill=(248, 182, 72))
    card_draw.rounded_rectangle((1038, 378, 1152, 450), radius=22, fill=(38, 139, 121))
    card_draw.line((902, 170, 1116, 170), fill=(75, 156, 175), width=8)
    card_draw.line((902, 202, 1082, 202), fill=(109, 179, 194), width=8)
    card_draw.line((902, 234, 1056, 234), fill=(144, 201, 211), width=8)

    waveform = [(870, 318), (900, 300), (930, 334), (960, 286), (990, 342), (1020, 294), (1050, 330), (1080, 304), (1110, 324)]
    for start, end in zip(waveform, waveform[1:]):
        card_draw.line((*start, *end), fill=(214, 248, 251), width=6)

    card_draw.text((902, 395), "ASR", font=chip_font, fill=(36, 46, 52))
    card_draw.text((1066, 395), "AI", font=chip_font, fill=(236, 248, 244))
    base.alpha_composite(card)

    final = Image.alpha_composite(base, overlay).convert("RGB")
    final.save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
