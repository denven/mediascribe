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


def draw_pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    label: str,
    font: ImageFont.ImageFont,
    *,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    text_fill: tuple[int, int, int],
) -> None:
    draw.rounded_rectangle(xy, radius=22, fill=fill, outline=outline, width=2)
    left, top, right, bottom = xy
    text_box = draw.textbbox((0, 0), label, font=font)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    x = left + (right - left - text_width) / 2
    y = top + (bottom - top - text_height) / 2 - 2
    draw.text((x, y), label, font=font, fill=text_fill)


def add_soft_blobs(base: Image.Image) -> None:
    blobs = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(blobs)
    draw.ellipse((760, 10, 1210, 460), fill=(32, 174, 163, 58))
    draw.ellipse((920, 120, 1320, 560), fill=(250, 188, 92, 48))
    draw.ellipse((-120, 410, 300, 820), fill=(33, 106, 199, 38))
    base.alpha_composite(blobs.filter(ImageFilter.GaussianBlur(26)))


def add_grid(base: Image.Image) -> None:
    grid = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(grid)
    for x in range(54, SIZE[0], 48):
        draw.line((x, 44, x, SIZE[1] - 44), fill=(130, 181, 197, 18), width=1)
    for y in range(44, SIZE[1], 48):
        draw.line((44, y, SIZE[0] - 44, y), fill=(130, 181, 197, 14), width=1)
    base.alpha_composite(grid)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    base = vertical_gradient(SIZE, (8, 23, 34), (15, 70, 88)).convert("RGBA")
    add_soft_blobs(base)
    add_grid(base)

    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    eyebrow_font = load_font("segoeui.ttf", 22)
    title_font = load_font("segoeuib.ttf", 84)
    subtitle_font = load_font("segoeui.ttf", 27)
    pill_font = load_font("segoeui.ttf", 22)
    section_font = load_font("segoeuib.ttf", 23)
    body_font = load_font("segoeui.ttf", 20)
    tiny_font = load_font("segoeui.ttf", 18)

    # Left copy block.
    draw.text((84, 86), "AI media workflows", font=eyebrow_font, fill=(129, 232, 223))
    draw.text((84, 122), "MediaScribe", font=title_font, fill=(244, 249, 250))
    draw.text(
        (88, 246),
        "Transcribe audio, video, and text",
        font=subtitle_font,
        fill=(212, 234, 239),
    )
    draw.text(
        (88, 286),
        "with ASR + AI summaries.",
        font=subtitle_font,
        fill=(212, 234, 239),
    )
    draw.text(
        (88, 340),
        "Subtitle-first workflows, Whisper-ready ASR,",
        font=body_font,
        fill=(171, 211, 219),
    )
    draw.text(
        (88, 372),
        "and local Ollama or cloud backends.",
        font=body_font,
        fill=(171, 211, 219),
    )

    draw_pill(
        draw,
        (88, 442, 226, 492),
        "audio",
        pill_font,
        fill=(16, 73, 90, 215),
        outline=(99, 210, 224, 180),
        text_fill=(234, 248, 251),
    )
    draw_pill(
        draw,
        (242, 442, 364, 492),
        "video",
        pill_font,
        fill=(16, 73, 90, 215),
        outline=(99, 210, 224, 180),
        text_fill=(234, 248, 251),
    )
    draw_pill(
        draw,
        (380, 442, 490, 492),
        "text",
        pill_font,
        fill=(16, 73, 90, 215),
        outline=(99, 210, 224, 180),
        text_fill=(234, 248, 251),
    )

    draw.text(
        (88, 534),
        "Python 3.10+   Whisper   Ollama   subtitles   yt-dlp",
        font=tiny_font,
        fill=(155, 203, 211),
    )

    # Right social-card panel.
    card_shadow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(card_shadow)
    shadow_draw.rounded_rectangle((744, 70, 1192, 570), radius=34, fill=(0, 0, 0, 122))
    base.alpha_composite(card_shadow.filter(ImageFilter.GaussianBlur(28)))

    panel = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rounded_rectangle((760, 56, 1208, 556), radius=34, fill=(239, 246, 247, 236))
    panel_draw.rounded_rectangle((784, 84, 1184, 178), radius=24, fill=(224, 245, 241))
    panel_draw.rounded_rectangle((784, 194, 1184, 344), radius=24, fill=(13, 92, 108))
    panel_draw.rounded_rectangle((784, 360, 1184, 528), radius=24, fill=(245, 250, 249))

    panel_draw.text((812, 112), "Inputs", font=section_font, fill=(22, 53, 61))
    draw_pill(
        panel_draw,
        (812, 128, 928, 166),
        "audio",
        tiny_font,
        fill=(255, 255, 255, 210),
        outline=(134, 208, 194, 120),
        text_fill=(33, 74, 85),
    )
    draw_pill(
        panel_draw,
        (942, 128, 1056, 166),
        "video",
        tiny_font,
        fill=(255, 255, 255, 210),
        outline=(134, 208, 194, 120),
        text_fill=(33, 74, 85),
    )
    draw_pill(
        panel_draw,
        (1070, 128, 1156, 166),
        "text",
        tiny_font,
        fill=(255, 255, 255, 210),
        outline=(134, 208, 194, 120),
        text_fill=(33, 74, 85),
    )

    panel_draw.text((812, 218), "Transcript + subtitles", font=section_font, fill=(235, 248, 249))
    panel_draw.text((812, 258), "[00:00:12] Speaker 1", font=tiny_font, fill=(167, 230, 237))
    panel_draw.rounded_rectangle((812, 282, 960, 320), radius=16, fill=(33, 133, 148))
    panel_draw.text((838, 290), "subtitle-first", font=tiny_font, fill=(233, 248, 250))
    panel_draw.rounded_rectangle((1026, 282, 1156, 320), radius=16, fill=(247, 187, 92))
    panel_draw.text((1060, 290), "ASR", font=tiny_font, fill=(34, 46, 53))
    panel_draw.line((812, 334, 1148, 334), fill=(149, 216, 223), width=7)
    panel_draw.line((812, 356, 1094, 356), fill=(102, 191, 203), width=7)

    panel_draw.text((812, 388), "Summary", font=section_font, fill=(22, 53, 61))
    panel_draw.text((812, 424), "- Provider-based ASR + summaries", font=body_font, fill=(53, 83, 90))
    panel_draw.text((812, 454), "- Local Ollama or cloud LLMs", font=body_font, fill=(53, 83, 90))
    panel_draw.text((812, 484), "- Reusable CLI media workflows", font=body_font, fill=(53, 83, 90))
    draw_pill(
        panel_draw,
        (1010, 382, 1114, 420),
        "Whisper",
        tiny_font,
        fill=(18, 105, 119, 220),
        outline=(18, 105, 119, 0),
        text_fill=(237, 248, 250),
    )
    draw_pill(
        panel_draw,
        (1124, 382, 1170, 420),
        "O",
        tiny_font,
        fill=(245, 190, 96, 240),
        outline=(245, 190, 96, 0),
        text_fill=(38, 50, 55),
    )

    base.alpha_composite(panel)

    final = Image.alpha_composite(base, overlay).convert("RGB")
    final.save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
