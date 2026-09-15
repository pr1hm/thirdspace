from pathlib import Path
import random
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONT_PATH= str(Path(__file__).parent/"fonts"/"WorkSans-Regular.ttf")

def typ_filter(
    image: Image.Image,
    text: str="batman",
    font_path: str= FONT_PATH,
    canvaswidth: int=1200,
    canvasheight: int=800,
    basefont: int=10,
    lineheight:float=0.9,
    white_threshold: int=255,
    bgbrightnesscutoff: int=210,
    sizecontrast:float=1.0,
    minfont: int=3,
    flatareaskip_probability: float = 0.7,
    random_seed: int | None= None,
    edgepercentile: float = 2.0,
    noisepercentile: float = 10.0,
    backgroundremoval: bool=False,
    background_tolerance: int = 20,
    edgeblur:float=2.0,
    debug: bool=False,
    textcolor: tuple= (0,0,0),
    bgcolor: tuple| None =(255,255,255),
    contrast: float=1.0,
    brightness: float=1.0,
) -> Image.Image:
    
    if bgcolor is None:
        letterboxcolor= (0,0,0)
    else:
        letterboxcolor = tuple(bgcolor[:3])
    
    containedcanvas= Image.new("RGB", (canvaswidth, canvasheight), letterboxcolor)
    containedimage= Image.convert("RGB").copy()
    containedimage.thumbnail((canvaswidth, canvasheight), Image.Resampling.LANCZOS)
    pastepos=((canvaswidth-containedimage.width)//2,(canvasheight-containedimage.height)//2)
    containedcanvas.paste(containedimage, pastepos)
    grayscale= containedcanvas.convert("L")
    grayscale= ImageEnhance.Contrast(grayscale).enhance(contrast)
    grayscale= ImageEnhance.Brightness(grayscale).enhance(brightness)
    brightnessarray=np.asarray(grayscale)
    edgeimg= grayscale.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(radius=edgeblur))
    edgearray= np.asarray(edgeimg)
    noisefloor= np.percentile(edgearray,noisepercentile)
    edgedenoise=np.clip(edgearray.astype(np.float32)-noisefloor,0, None)
    denoisemax= edgedenoise.max()
    edgearray_normal=(edgedenoise/denoisemax if denoisemax>0 else np.zeros_like(edgedenoise))
    edge_threshold= np.percentile(edgearray_normal, edgepercentile)
    
    if backgroundremoval:
        corner_brightness= np.array([brightnessarray[0,0],brightnessarray[0,-1],brightnessarray[-1,0],brightnessarray[-1,-1]],dtype=np.float32)
        bgbrighntess= corner_brightness.mean()
        
    if random_seed is not None:
        random.seed(random_seed)
        
    if bgcolor is None:
        bg = (0,0,0,0)
    elif len(bgcolor) == 3:
        bg= (*bgcolor,255)
    else:
        bg= bgcolor
        
    canvas= Image.new("RGBA", (canvaswidth, canvasheight), bg)
    draw= ImageDraw.Draw(canvas)
    fontcache:dict[int,ImageFont.FreeTypeFont|ImageFont.ImageFont]
    fontfallback=False
    char_idx=0
    textlen=len(text)
    bggrid=0
    contentgrid=0
    
    def getfont(size:int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        nonlocal fontfallback
        if size not in fontcache:
            try:
                fontcache[size]=ImageFont.truetype(font_path, size)
            except(OSError,IOError):
                if not fontfallback:
                    print("Warning: Couldn't load font")
                    fontfallback=True
                fontcache[size]=ImageFont.load_default()
        return fontcache[size]
    
    def next_character() -> str:
        nonlocal char_idx
        character= text[char_idx%textlen]
        char_idx +=1
        return character
    
    y=0
    rowstep= int(basefont*lineheight)
    while y<canvasheight:
        x=0
        while x<canvaswidth:
            yindex= min(max(int(y),0), brightnessarray.shape[0]-1)
            xindex= min(max(int(x),0), brightnessarray.shape[1]-1)
            pixelbrightness= brightnessarray[yindex, xindex]
            maybebg= pixelbrightness>=bgbrightnesscutoff
            if maybebg:
                bggrid+=1
            else:
                contentgrid+=1
                
            matchbg = (backgroundremoval and abs(pixelbrightness-bgbrighntess)<=background_tolerance)
            isbg=(pixelbrightness>=white_threshold or maybebg or matchbg)
            fontsize = 2 if isbg else basefont
            font= getfont(fontsize)
            character= next_character
            
            if len(textcolor)==3:
                color=textcolor
            else:
                color=textcolor[:3]
            alpha=int(255*(1-pixelbrightness/255))
            fill=(*color, alpha)
            characterwidth=draw.textlength(character,font=font)
            draw.text((x,y), character, font=font, fill=fill)
            x+=characterwidth
        y+=rowstep
        
    if debug:
        totalgrid=bggrid+contentgrid
        if totalgrid:
            bgpercent= bggrid/totalgrid*100
        else:
            bgpercent=0.0
            contentpercent=0.0
            
    return canvas

if __name__ == "__main__":
    inputpath= Path(sys.argv[1]) if len(sys.argv) >1 else Path(__file__).parent/ "test.jpg"
    if not inputpath.is_file():
        raise FileNotFoundError("Img not found :( write path")
    outputfile=Path(__file__).parent
    testimg=Image.open(inputpath)
    
    autoresult= typ_filter(testimg, backgroundremoval=True, debug=True)
    autoresult.save(outputfile/"testoutput.png")