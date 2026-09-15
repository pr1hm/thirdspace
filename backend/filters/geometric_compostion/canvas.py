from PIL import Image
from typing import Tuple

def create_canvas(width: int = 1080, height: int = 1080, background_color: Tuple[int, int, int] = (15, 15, 15)):
    canvas = Image.new('RGB', (width, height), background_color)
    return canvas

if __name__ == __main___:
    