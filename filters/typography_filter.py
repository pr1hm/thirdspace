from __future__ import annotations
from PIL import Image
from typography_filter import apply_typography_filter

NAME = "Typography"
DESCRIPTION = "Renders the image as repeating typography."

def process(image: Image.Image, intensity: float = 100) -> Image.Image:
    intensity_ratio = max(0.0, min(100.0, float(intensity))) / 100.0
    filtered = apply_typography_filter(
        image,
        canvas_width=image.width,
        canvasheight=image.height,
        background_removal=True,
        debug=False,
    )
    if intensity_ratio >= 1.0:
        return filtered
    return Image.blend(image.convert("RGBA"), filtered.convert("RGBA"), intensity_ratio)
