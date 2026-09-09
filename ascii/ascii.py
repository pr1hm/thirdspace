import subprocess
from PIL import Image, ImageDraw, ImageFont

FILE_PATH, ext = input("Filepath: ").split(".")
WIDTH_OUT = 80

ASCII_CHARS = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~i!lI;:,\"^`."

def get_char(val):
    index = int(val / 256 * len(ASCII_CHARS))
    return ASCII_CHARS[index]

def save_ascii_as_png(ascii_lines, output_path="ascii_output.png", font_size=20, target_size=None):
    font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)
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

def overlay():
    bg = Image.open(f"{FILE_PATH}.jpg")
    ol = Image.open(f"{FILE_PATH}_ascii.png")
    position = (0, 0)
    bg.paste(ol, position, mask=ol)
    final_image = bg.convert("RGB")
    final_image.save("result.jpg")

def main():
    imgg = Image.open(f"{FILE_PATH}.{ext}").convert("RGBA")
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
        save_ascii_as_png(ascii_lines, f"{FILE_PATH}_ascii.png", target_size=(w_in, h_in))
    overlay()
    subprocess.run(["rm", f"{FILE_PATH}_ascii.png"])
        

if __name__ == "__main__":
    main()