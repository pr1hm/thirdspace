from PIL import Image, ImageDraw

BANDS = [
    (200, [45]),
    (150, [45, -45]),
    (100, [45, -45, 0]),
    (50,  [45, -45, 0, 90])
]

INK = (0, 0, 0, 255)

def draw_lines(draw, gray, w, h, angle, threshold, spacing):
    if angle == 90:
        for x in range(0, w, spacing):
            for y in range(h):
                if gray.getpixel((x, y)) < threshold:
                    draw.point((x, y), fill=INK)

    elif angle == 0:
        for y in range(0, h, spacing):
            for x in range(w):
                if gray.getpixel((x, y)) < threshold:
                    draw.point((x, y), fill=INK)

    else:
        slope = 1 if angle > 0 else -1
        for offset in range(-h, w, spacing):
            for x in range(w):
                y = slope * x - offset
                if 0 <= y < h and gray.getpixel((x, y)) < threshold:
                    draw.point((x,y), fill=INK)

def crosshatch(path, spacing=6):
    OUT = f"{path}_ch.png"
    outrm = "ch.png"

    gray = Image.open(path).convert("L")
    w, h = gray.size
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    for threshold, angles in BANDS:
        for angle in angles:
            draw_lines(draw, gray, w, h, angle, threshold, spacing)

    bg = Image.new('RGB', (w, h), color='white')
    bg.paste(canvas, (0, 0), mask=canvas)
    img = bg.convert("RGB")
    img.save(OUT)
    return OUT

if __name__ == "__main__":
    crosshatch("test.jpg")
