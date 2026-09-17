from __future__ import annotations
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

NAME = "Computer Vision HUD"
DESCRIPTION = "Adds a CV filter."

HUD_COLOR = (0, 255, 65)
MIN_TARGET_EDGE_DENSITY = 18.0

def _clamp_intensity(value: float) -> float:
    try:
        intensity = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid") from exc
    if not 0 <= intensity <= 100:
        raise ValueError("Invalid")
    return intensity / 100.0


def _draw_dashed_circle(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    radius: int,
    fill: tuple[int, int, int, int],
    width: int,
    dash_degrees: int = 12,
    gap_degrees: int = 8,
) -> None:
    if radius <= 0:
        return
    left = center[0] - radius
    top = center[1] - radius
    right = center[0] + radius
    bottom = center[1] + radius
    angle = -90
    while angle < 270:
        end = min(angle + dash_degrees, 270)
        draw.arc((left, top, right, bottom), angle, end, fill=fill, width=width)
        angle += dash_degrees + gap_degrees


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: tuple[int, int, int, int],
    width: int,
    dash_length: int,
    gap_length: int,
) -> None:
    start_x, start_y = start
    end_x, end_y = end
    delta_x = end_x - start_x
    delta_y = end_y - start_y
    distance = math.hypot(delta_x, delta_y)
    if distance == 0:
        return

    unit_x = delta_x / distance
    unit_y = delta_y / distance
    position = 0.0
    while position < distance:
        dash_end = min(position + dash_length, distance)
        draw.line(
            (
                start_x + unit_x * position,
                start_y + unit_y * position,
                start_x + unit_x * dash_end,
                start_y + unit_y * dash_end,
            ),
            fill=fill,
            width=width,
        )
        position += dash_length + gap_length


def _edge_density_cells(edges: Image.Image, columns: int = 8, rows: int = 8) -> list[list[float]]:
    width, height = edges.size
    densities: list[list[float]] = []
    for row in range(rows):
        row_values: list[float] = []
        top = row * height // rows
        bottom = max(top + 1, (row + 1) * height // rows)
        for column in range(columns):
            left = column * width // columns
            right = max(left + 1, (column + 1) * width // columns)
            cell = edges.crop((left, top, right, bottom))
            row_values.append(sum(cell.getdata()) / max(1, cell.width * cell.height))
        densities.append(row_values)
    return densities


def _find_hud_points(
    edges: Image.Image,
    max_targets: int,
) -> tuple[tuple[int, int], list[tuple[int, int]]]:
    width, height = edges.size
    columns = min(8, max(2, width))
    rows = min(8, max(2, height))
    densities = _edge_density_cells(edges, columns, rows)
    cells = sorted(
        (
            densities[row][column],
            column,
            row,
        )
        for row in range(rows)
        for column in range(columns)
    )
    _, center_column, center_row = cells[-1]
    center_density = densities[center_row][center_column]
    center = (
        (center_column * 2 + 1) * width // (columns * 2),
        (center_row * 2 + 1) * height // (rows * 2),
    )

    targets: list[tuple[int, int]] = []
    max_target_distance = min(width, height) * 0.42
    target_density_threshold = max(
        MIN_TARGET_EDGE_DENSITY,
        center_density * 0.45,
    )
    for density, column, row in reversed(cells[:-1]):
        point = (
            (column * 2 + 1) * width // (columns * 2),
            (row * 2 + 1) * height // (rows * 2),
        )
        if (
            density >= target_density_threshold
            and min(width, height) * 0.12 < math.dist(center, point) <= max_target_distance
        ):
            targets.append(point)
        if len(targets) == max_targets:
            break
    return center, targets


def process(
    image: Image.Image,
    intensity: float = 100,
    max_targets: int = 6,
    **kwargs: object,
) -> Image.Image:
    del kwargs
    intensity_ratio = _clamp_intensity(intensity)
    try:
        target_limit = int(max_targets)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid") from exc
    if target_limit < 0:
        raise ValueError("Invalid")
    if intensity_ratio == 0:
        return image.copy()

    grayscale = ImageOps.autocontrast(image.convert("L"))
    edges = grayscale.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.0))
    center, target_points = _find_hud_points(edges, target_limit)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    alpha = round(215 * intensity_ratio)
    main_fill = (*HUD_COLOR, alpha)
    faint_fill = (*HUD_COLOR, round(80 * intensity_ratio))
    radius = max(1, round(min(image.size) * 0.30))
    line_width = max(1, round(min(image.size) / 350))
    _draw_dashed_circle(draw, center, radius, main_fill, line_width)
    _draw_dashed_line(draw, (center[0] - radius, center[1]), (center[0] + radius, center[1]), faint_fill, line_width, 18, 12)
    _draw_dashed_line(draw, (center[0], center[1] - radius), (center[0], center[1] + radius), faint_fill, line_width, 18, 12)
    draw.ellipse((center[0] - 3, center[1] - 3, center[0] + 3, center[1] + 3), outline=main_fill, width=line_width)

    font = ImageFont.load_default()
    box_size = max(1, min(100, max(40, round(min(image.size) * 0.12))))
    box_size = min(box_size, max(1, min(image.size) // 2))
    for index, point in enumerate(target_points):
        left = max(0, min(image.width - box_size, point[0] - box_size // 2))
        top = max(0, min(image.height - box_size, point[1] - box_size // 2))
        right = left + box_size
        bottom = top + box_size
        draw.rectangle((left, top, right, bottom), outline=main_fill, width=line_width)
        corner = max(3, box_size // 5)
        draw.line((left, top, left + corner, top), fill=main_fill, width=line_width + 1)
        draw.line((left, top, left, top + corner), fill=main_fill, width=line_width + 1)
        text_x = min(image.width - 1, right + max(4, box_size // 10))
        text_y = max(0, top - font.getbbox("CONF: 0.86")[1])
        confidence = 0.86 / (1.0 + index * 0.08)
        lines = (
            f"CONF: {confidence:.3f}",
            f"ID: 0x{0x9A4F + index * 0x31:04X}",
            "TYPE: PATTERN" if index == 0 else "TYPE: DETAIL",
            f"SCAN RAD: {radius}px",
        )
        for line_number, text in enumerate(lines):
            draw.text((text_x, text_y + line_number * 10), text, font=font, fill=main_fill)

    result = Image.alpha_composite(image.convert("RGBA"), overlay)
    if "A" not in image.getbands():
        return result.convert("RGB")
    return result
