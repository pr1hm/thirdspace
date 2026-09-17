from pathlib import Path
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONT_PATH = str(Path(__file__).resolve().parent.parent / "fonts" / "WorkSans-Regular.ttf")


def apply_typography_filter(
    image: Image.Image,
    text: str = "batman",
    font_path: str = FONT_PATH,
    canvas_width: int = 1200,
    canvasheight: int = 800,
    base_font_size: int = 10,
    line_height_mult: float = 0.9,
    white_threshold: int = 255,
    background_brightness_cutoff: int = 210,
    random_seed: int | None = None,
    edge_percentile: float = 75.0,
    background_removal: bool = False,
    background_tolerance: int = 20,
    edge_blur_radius: float = 2.0,
    noise_floor_percentile: float = 10.0,
    debug: bool = False,
    text_color: tuple = (0, 0, 0),
    bg_color: tuple | None = (255, 255, 255),
    contrast: float = 1.0,
    brightness: float = 1.0,
) -> Image.Image:
    
    if bg_color is None:
        letterbox_color = (0, 0, 0)
    else:
        letterbox_color = tuple(bg_color[:3])
    contained_canvas = Image.new("RGB", (canvas_width, canvasheight), letterbox_color)
    contained_image = image.convert("RGB").copy()
    contained_image.thumbnail((canvas_width, canvasheight), Image.Resampling.LANCZOS)
    paste_position = (
        (canvas_width - contained_image.width) // 2,
        (canvasheight - contained_image.height) // 2,
    )
    contained_canvas.paste(contained_image, paste_position)

    grayscale = contained_canvas.convert("L")
    grayscale = ImageEnhance.Contrast(grayscale).enhance(contrast)
    grayscale = ImageEnhance.Brightness(grayscale).enhance(brightness)
    brightness_array = np.asarray(grayscale)
    edge_image = grayscale.filter(ImageFilter.FIND_EDGES).filter(
        ImageFilter.GaussianBlur(radius=edge_blur_radius)
    )
    edge_array = np.asarray(edge_image)
    noise_floor = np.percentile(edge_array, noise_floor_percentile)
    edge_denoised = np.clip(
        edge_array.astype(np.float32) - noise_floor,
        0,
        None,
    )
    denoised_max = edge_denoised.max()
    edge_array_normalized = (
        edge_denoised / denoised_max
        if denoised_max > 0
        else np.zeros_like(edge_denoised)
    )
    edge_threshold_value = np.percentile(edge_array_normalized, edge_percentile)

    if debug:
        print(
            "Edge stats: "
            f"min={edge_array_normalized.min():.4f}, "
            f"max={edge_array_normalized.max():.4f}, "
            f"mean={edge_array_normalized.mean():.4f}, "
            f"p75={np.percentile(edge_array_normalized, 75):.4f}, "
            f"p90={np.percentile(edge_array_normalized, 90):.4f}, "
            f"noise_floor={noise_floor:.4f}, "
            f"edge_denoised_max={denoised_max:.4f}"
        )

    if background_removal:
        corner_brightness = np.array(
            [
                brightness_array[0, 0],
                brightness_array[0, -1],
                brightness_array[-1, 0],
                brightness_array[-1, -1],
            ],
            dtype=np.float32,
        )
        background_brightness = corner_brightness.mean()

    if random_seed is not None:
        random.seed(random_seed)

    if bg_color is None:
        background = (0, 0, 0, 0)
    elif len(bg_color) == 3:
        background = (*bg_color, 255)
    else:
        background = bg_color

    canvas = Image.new("RGBA", (canvas_width, canvasheight), background)
    draw = ImageDraw.Draw(canvas)

    font_cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
    font_fallback_warned = False
    char_idx = 0
    text_length = len(text)
    background_grid_count = 0
    content_grid_count = 0

    def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        nonlocal font_fallback_warned
        if size not in font_cache:
            try:
                font_cache[size] = ImageFont.truetype(font_path, size)
            except (OSError, IOError):
                if not font_fallback_warned:
                    print(
                        f"Could not load font '{font_path}'; "
                    )
                    font_fallback_warned = True
                font_cache[size] = ImageFont.load_default()
        return font_cache[size]

    def next_character() -> str:
        nonlocal char_idx
        character = text[char_idx % text_length]
        char_idx += 1
        return character

    y = 0
    row_step = int(base_font_size * line_height_mult)
    while y < canvasheight:
        x = 0
        while x < canvas_width:
            y_index = min(max(int(y), 0), brightness_array.shape[0] - 1)
            x_index = min(max(int(x), 0), brightness_array.shape[1] - 1)
            pixel_brightness = brightness_array[y_index, x_index]
            is_likely_background = pixel_brightness >= background_brightness_cutoff
            if is_likely_background:
                background_grid_count += 1
            else:
                content_grid_count += 1

            matches_removed_background = (
                background_removal
                and abs(pixel_brightness - background_brightness) <= background_tolerance
            )
            is_background = (
                pixel_brightness >= white_threshold
                or is_likely_background
                or matches_removed_background
            )
            integer_font_size = 2 if is_background else base_font_size
            font = get_font(integer_font_size)
            character = next_character()

            if len(text_color) == 3:
                color = text_color
            else:
                color = text_color[:3]
            alpha = int(255 * (1 - pixel_brightness / 255))
            fill = (*color, alpha)
            character_width = draw.textlength(character, font=font)
            draw.text((x, y), character, font=font, fill=fill)
            x += character_width

        y += row_step

    if debug:
        total_grid_count = background_grid_count + content_grid_count
        if total_grid_count:
            background_percentage = background_grid_count / total_grid_count * 100
            content_percentage = content_grid_count / total_grid_count * 100
        else:
            background_percentage = 0.0
            content_percentage = 0.0
        print(
            "Grid background classification: "
            f"background={background_percentage:.2f}%, "
            f"content={content_percentage:.2f}%"
        )

    return canvas


if __name__ == "__main__":
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "test.jpg"
    if not input_path.is_file():
        raise FileNotFoundError(
            f"Image not found: {input_path}\n"
        )
    output_directory = Path(__file__).parent
    test_image = Image.open(input_path)

    auto_result = apply_typography_filter(
        test_image,
        background_removal=True,
        debug=True,
    )
    auto_result.save(output_directory / "output1.png")
