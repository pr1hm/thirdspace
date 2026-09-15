from __future__ import annotations
import sys
from pathlib import Path
from PIL import Image
from typofil import typ_filter

FILTERS_DIR = Path(__file__).resolve().parent.parent
if str(FILTERS_DIR) not in sys.path:
    sys.path.insert(0, str(FILTERS_DIR))

NAME = "Typography"
DESCRIPTION = "Renders the image as repeating typography."

def process(image: Image.Image, intensity: float = 100) -> Image.Image:
    intensity_ratio = max(0.0, min(100.0, float(intensity))) / 100.0
    filtered = typ_filter(image,canvaswidth=image.width,canvasheight=image.height,background_removal=True,debug=False,)
    if intensity_ratio >= 1.0:
        return filtered
    return Image.blend(image.convert("RGBA"), filtered.convert("RGBA"), intensity_ratio)
