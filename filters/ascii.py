from PIL import Image, ImageDraw, ImageFont
import os

WIDTH_OUT = 80
ASCII_CHARS = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~i!lI;:,\"^`."

def get_char(val):
    index = int(val / 256 * len(ASCII_CHARS))
    return ASCII_CHARS[index]

def save_ascii_as_png(ascii_lines, output_path="ascii_output.png", font_size=20, target_size=None):
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()
    bbox = font.getbbox("A")
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]
    img_w = char_w * max(len(line) for line in ascii_lines)
    img_h = char_h * len(ascii_lines)
    img = Image.new("RGBA", (img_w, img_h), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    for y, line in enumerate(ascii_lines):
        draw.text(
            (0, y * char_h),
            line,
            fill=(0, 0, 0, 150),
            font=font
        )
    if target_size:
        img = img.resize(target_size, Image.Resampling.LANCZOS)
    img.save(output_path)


NAME = "ASCII"
DESCRIPTION = "Renders the image as a character-based grayscale overlay."

def process(image: Image.Image, intensity: float = 100) -> Image.Image:
    intensity_ratio = max(0.0, min(100.0, float(intensity))) / 100.0
    if intensity_ratio == 0:
        return image.copy()
    source = image.convert("RGBA")
    width, height = source.size
    output_width = min(80, max(1, width))
    output_height = max(1, int(output_width * height / width * 0.55))
    grayscale = source.convert("L").resize((output_width, output_height))
    ascii_lines = [
        "".join(get_char(grayscale.getpixel((x, y))) for x in range(output_width))
        for y in range(output_height)
    ]
    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", max(1, int(width / output_width)))
    except OSError:
        font = ImageFont.load_default()
    bbox = font.getbbox("A")
    char_width = max(1, bbox[2] - bbox[0])
    char_height = max(1, bbox[3] - bbox[1])
    text_layer = Image.new(
        "RGBA",
        (char_width * output_width, char_height * output_height),
        (255, 255, 255, 0),
    )
    text_draw = ImageDraw.Draw(text_layer)
    for y, line in enumerate(ascii_lines):
        text_draw.text((0, y * char_height), line, fill=(0, 0, 0, 220), font=font)
    overlay.alpha_composite(text_layer.resize((width, height), Image.Resampling.LANCZOS))
    filtered = Image.alpha_composite(source, overlay)
    return Image.blend(source, filtered, intensity_ratio)

def overlay(file_path):
    bg = Image.open(f"{file_path}.jpg")
    ol = Image.open(f"{file_path}_ascii.png")
    position = (0, 0)
    bg.paste(ol, position, mask=ol)
    final_image = bg.convert("RGB")
    final_image.save("result.jpg")

def main():
    file_path, ext = input("Filepath: ").rsplit(".", 1)
    imgg = Image.open(f"{file_path}.{ext}").convert("RGBA")
    w_in, h_in = imgg.size
    pixels = []
    for y in range(h_in):
        row = []
        for x in range(w_in):
            r, g, b, a = imgg.getpixel((x, y))
            if a == 0:
                row.append(None)
            else:
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                row.append(gray)
        pixels.append(row)
    h_out = int(WIDTH_OUT * (h_in / w_in) * 0.55)
    for y in range(h_out):
        line = ""
        for x in range(WIDTH_OUT):
            src_x = int(x * (w_in / WIDTH_OUT))
            src_y = int(y * (h_in / h_out))
            pixel_brightness = pixels[src_y][src_x]
            line += get_char(pixel_brightness)
        print(line)
        ascii_lines = []
    for y in range(h_out):
        line = ""
        for x in range(WIDTH_OUT):
            src_x = int(x * (w_in / WIDTH_OUT))
            src_y = int(y * (h_in / h_out))
            pixel_brightness = pixels[src_y][src_x]
            line += get_char(pixel_brightness)
        ascii_lines.append(line)
        save_ascii_as_png(ascii_lines, f"{file_path}_ascii.png", target_size=(w_in, h_in))
    overlay(file_path)
    os.remove(f"{file_path}_ascii.png")
        
if __name__ == "__main__":
    main()
