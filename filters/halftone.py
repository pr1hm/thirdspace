import os
import sys
from PIL import Image, ImageDraw, ImageOps, ImageStat

class Halftone(object):
    def __init__(self, path):
        self.path = path
    def make(
        self,
        sample=10,
        scale=1,
        percentage=0,
        filename_addition="_halftoned",
        angles=[0, 15, 30, 45],
        style="color",
        antialias=False,
        output_format="default",
        output_quality=75,
        save_channels=False,
        save_channels_format="default",
        save_channels_style="color",
    ):
        self.check_arguments(
            angles=angles,
            antialias=antialias,
            output_format=output_format,
            output_quality=output_quality,
            percentage=percentage,
            sample=sample,
            save_channels=save_channels,
            save_channels_format=save_channels_format,
            save_channels_style=save_channels_style,
            scale=scale,
            style=style,
        )
        f, extension = os.path.splitext(self.path)
        if output_format == "jpeg":
            extension = ".jpg"
        elif output_format.startswith("png"):
            extension = ".png"
        output_filename = "%s%s%s" % (f, str(filename_addition), extension)
        try:
            im = Image.open(self.path)
        except IOError as e:
            raise Exception("Couldn't open source file '%s'" % (self.path)) from e
        if style == "grayscale":
            angles = angles[:1]
            gray_im = im.convert("L")
            channel_images = self.halftone(
                im, gray_im, sample, scale, angles, antialias
            )
            new = channel_images[0]
        else:
            cmyk = self.gcr(im, percentage)
            channel_images = self.halftone(im, cmyk, sample, scale, angles, antialias)
            if save_channels:
                self.save_channel_images(
                    channel_images,
                    channels_style=save_channels_style,
                    channels_format=save_channels_format,
                    output_filename=output_filename,
                    output_quality=output_quality,
                )
            new = Image.merge("CMYK", channel_images)
        if extension == ".jpg":
            new.save(output_filename, "JPEG", subsampling=0, quality=output_quality)
        elif extension == ".png":
            new.convert("RGB").save(output_filename, "PNG")

    def check_arguments(
        self,
        angles,
        antialias,
        output_format,
        output_quality,
        percentage,
        sample,
        save_channels,
        save_channels_format,
        save_channels_style,
        scale,
        style,
    ):
        if not isinstance(angles, list):
            raise TypeError( "Invalid")
        if style == "grayscale":
            if len(angles) < 1:
                raise ValueError("Invalid")
        else:
            if len(angles) != 4:
                raise ValueError("Invalid")
        for a in angles:
            if not isinstance(a, int):
                raise ValueError("Invalid")
        if not isinstance(antialias, bool):
            raise TypeError("Invalid")
        if output_format not in ["default", "jpeg", "png"]:
            raise ValueError("Invalid")
        if not isinstance(output_quality, int):
            raise TypeError("Invalid")
        if output_quality < 0 or output_quality > 100:
            raise ValueError("Invalid")
        if not isinstance(percentage, (float, int)):
            raise TypeError("Invalid")
        if not isinstance(sample, int):
            raise TypeError("Invalid")
        if not isinstance(save_channels, bool):
            raise TypeError("Invalid")
        if save_channels_format not in ["default", "jpeg", "png"]:
            raise ValueError("Invalid")
        if save_channels_style not in ["color", "grayscale"]:
            raise ValueError("Invalid")
        if not isinstance(scale, int):
            raise TypeError("The scale argument must be an integer, not '%s'." % scale)
        if style not in ["color", "grayscale"]:
            raise ValueError("Invalid")
        return True

    def gcr(self, im, percentage):
        cmyk_im = im.convert("CMYK")
        if not percentage:
            return cmyk_im
        cmyk_im = cmyk_im.split()
        cmyk = []
        for i in range(4):
            cmyk.append(cmyk_im[i].load())
        for x in range(im.size[0]):
            for y in range(im.size[1]):
                gray = int(
                    min(cmyk[0][x, y], cmyk[1][x, y], cmyk[2][x, y]) * percentage / 100
                )
                for i in range(3):
                    cmyk[i][x, y] = cmyk[i][x, y] - gray
                cmyk[3][x, y] = gray
        return Image.merge("CMYK", cmyk_im)

    def halftone(self, im, cmyk, sample, scale, angles, antialias):
        antialias_scale = 4
        if antialias is True:
            scale = scale * antialias_scale
        cmyk = cmyk.split()
        dots = []
        for channel, angle in zip(cmyk, angles):
            channel = channel.rotate(angle, expand=1)
            size = channel.size[0] * scale, channel.size[1] * scale
            half_tone = Image.new("L", size)
            draw = ImageDraw.Draw(half_tone)
            for x in range(0, channel.size[0], sample):
                for y in range(0, channel.size[1], sample):
                    box = channel.crop((x, y, x + sample, y + sample))
                    mean = ImageStat.Stat(box).mean[0]
                    diameter = (mean / 255) ** 0.5
                    box_size = sample * scale
                    draw_diameter = diameter * box_size
                    box_x, box_y = (x * scale), (y * scale)
                    x1 = box_x + ((box_size - draw_diameter) / 2)
                    y1 = box_y + ((box_size - draw_diameter) / 2)
                    x2 = x1 + draw_diameter
                    y2 = y1 + draw_diameter
                    draw.ellipse([(x1, y1), (x2, y2)], fill=255)
            half_tone = half_tone.rotate(-angle, expand=1)
            width_half, height_half = half_tone.size
            xx1 = (width_half - im.size[0] * scale) / 2
            yy1 = (height_half - im.size[1] * scale) / 2
            xx2 = xx1 + im.size[0] * scale
            yy2 = yy1 + im.size[1] * scale
            half_tone = half_tone.crop((xx1, yy1, xx2, yy2))
            if antialias is True:
                w = int((xx2 - xx1) / antialias_scale)
                h = int((yy2 - yy1) / antialias_scale)
                half_tone = half_tone.resize((w, h), resample=Image.LANCZOS)
            dots.append(half_tone)
        return dots

    def save_channel_images(
        self,
        channel_images,
        channels_style,
        channels_format,
        output_filename,
        output_quality,
    ):
        channel_names = (
            ("c", "cyan"),
            ("m", "magenta"),
            ("y", "yellow"),
            ("k", "black"),
        )
        f, extension = os.path.splitext(output_filename)
        if channels_format == "jpeg":
            extension = ".jpg"
        elif channels_format.startswith("png"):
            extension = ".png"
        for count, channel_img in enumerate(channel_images):
            channel_filename = "%s_%s%s" % (
                f,
                channel_names[count][0],
                extension,
            )
            i = ImageOps.invert(channel_img)
            if channels_style == "color" and count < 3:
                i = ImageOps.colorize(i, black=channel_names[count][1], white="white")
            if extension == ".jpg":
                i.convert("CMYK").save(
                    channel_filename, "JPEG", subsampling=0, quality=output_quality
                )
            elif extension == ".png":
                i.save(channel_filename, "PNG")

NAME = "Halftone"
DESCRIPTION = "Converts the image into a color halftone pattern."

def process(image: Image.Image, intensity: float = 100) -> Image.Image:
    intensity_ratio = max(0.0, min(100.0, float(intensity))) / 100.0
    if intensity_ratio == 0:
        return image.copy()
    source = image.convert("RGBA")
    halftone = Halftone("")
    cmyk = halftone.gcr(source, 0)
    channel_images = halftone.halftone(
        source,
        cmyk,
        sample=10,
        scale=1,
        angles=[0, 15, 30, 45],
        antialias=True,
    )
    filtered = Image.merge("CMYK", channel_images).convert("RGB").convert("RGBA")
    return Image.blend(source, filtered, intensity_ratio)


if __name__ == "__main__":
    path = sys.argv[1]
    h = Halftone(path)
    h.make()
