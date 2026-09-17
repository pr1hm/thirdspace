from __future__ import annotations
from collections.abc import Sequence
from PIL import Image, ImageChops, ImageFilter, ImageOps

NAME = "Dither Overlay"
DESCRIPTION = "Adds dotted texture while preserving the source colors."

Color = str | Sequence[int]

def _parse_color(color: Color) -> tuple[int, int, int]:
    if isinstance(color, str):
        value = color.removeprefix("#")
        if len(value) == 3:
            value = "".join(channel * 2 for channel in value)
        if len(value) != 6:
            raise ValueError("Invalid #RGB value")
        try:
            channels = tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))
        except ValueError as exc:
            raise ValueError("Invalid hexadecimal values") from exc
        return channels  

    if len(color) < 3:
        raise ValueError("Invalid values")
    channels = tuple(color[:3])
    if any(not isinstance(channel, int) or not 0 <= channel <= 255 for channel in channels):
        raise ValueError("Invalid integers")
    return channels  


def _clamp_percentage(value: float, name: str) -> float:
    try:
        percentage = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("must be numeric") from exc
    if not 0 <= percentage <= 100:
        raise ValueError("Invalid")
    return percentage


def process(
    image: Image.Image,
    intensity: float = 100,
    dot_color: Color = "#FFFFFF",
    dither_intensity: float = 100,
    detail_threshold: int = 32,
    **kwargs: object,
) -> Image.Image:
    del kwargs
    filter_intensity = _clamp_percentage(intensity, "intensity") / 100.0
    overlay_intensity = _clamp_percentage(dither_intensity, "dither_intensity")
    mask_opacity = round(overlay_intensity * filter_intensity * 2.55)

    grayscale = image.convert("L")
    dithered = grayscale.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    mask = dithered.convert("L")
    if mask_opacity < 255:
        mask = mask.point(lambda value: value * mask_opacity // 255)

    try:
        detail_cutoff = int(detail_threshold)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid") from exc
    if not 0 <= detail_cutoff <= 255:
        raise ValueError("Invalid")

    edges = grayscale.filter(ImageFilter.FIND_EDGES)
    if image.width > 2 and image.height > 2:
        inner_edges = edges.crop((1, 1, image.width - 1, image.height - 1))
        edges = Image.new("L", image.size, 0)
        edges.paste(inner_edges, (1, 1))
    edges = ImageOps.autocontrast(edges).filter(ImageFilter.GaussianBlur(radius=1.0))
    detail_mask = edges.point(
        lambda value: 255 if value >= detail_cutoff else 0
    )
    mask = ImageChops.multiply(mask, detail_mask)

    original = image.convert("RGB")
    red, green, blue = _parse_color(dot_color)
    dots = Image.new("RGB", image.size, (red, green, blue))
    result = Image.composite(dots, original, mask)

    if "A" in image.getbands():
        result.putalpha(image.getchannel("A"))
        return result
    return result if image.mode == "RGB" else result.convert("RGB")
