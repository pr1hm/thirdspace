from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
import pilgram2

# SLIDERS

# Use:
# Contrast: val = float where one is midpoint < 1 is less contrast > 1 is greater contrast
# Color: val = 0-1 0 is full bw 1 is full color
# Brightness: val = float where one is midpoint < 1 is less brightness > 1 is greater brightness
# Sharpness: val = 0-2 with one as the midpoint

def enhance(filter, file, val):
    path = Path(file)
    img = Image.open(path)
    getattr(ImageEnhance, filter)(img).enhance(val).save(f"{path.stem}_{filter}{path.suffix}")


# Use:
# BoxBlur: higher the val, higher the blur
# GaussianBlur: higher the val higher the blur 

def filterr(filter, file, val):
    path = Path(file)
    img = Image.open(path)
    img.filter(getattr(ImageFilter, filter)(val)).save(f"{path.stem}_{filter}{path.suffix}")


# FILTERS

# Filter list:
# _1997, aden, ashby, amaro, brannan, brooklyn, charmes, clarendon, crema, dogpatch, earlybird, gingham, ginza, hefe, helena, hudson,
# inkwell, juno, kelvin, lark, lofi, ludwig, maven, mayfair, moon, nashville, perpetua, poprocket, reyes, rise, sierra, skyline,
# slumber, stinson, sutro, toaster, valencia, walden, willow, xpro2

def pilgram2Filter(filter, file):
    path = Path(file)
    cmd = getattr(pilgram2, filter)
    cmd(Image.open(path)).save(f"{path.stem}_{filter}{path.suffix}")