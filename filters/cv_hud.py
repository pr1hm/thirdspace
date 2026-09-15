from __future__ import annotations
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

NAME= "Computer Vision Filter"
DESCRIPTION= "Adds a neon rectangle with detailed targets"

HUD_COLOR= (0,255,65)
mintargetedge=18.0

def drawcircle(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    radius: int,
    fill: tuple[int,int,int,int],
    width: int,
    dash: int=12,
    gap: int=8
) -> None:
    if radius <= 0:
        return
    left= center[0]- radius
    top= center[1]-radius
    right= center[0]-radius
    bottom= center[1]+radius
    angle=-90
    while angle <270:
        end = min(angle+dash,270)
        draw.arc((left,top,right,bottom), angle, end, fill=fill, width=width)
        angle+=dash+gap
        
def dashedline(
    draw:ImageDraw.ImageDraw,
    start:tuple[int,int],
    end:tuple[int,int],
    fill:tuple[int,int,int,int],
    width: int,
    dashlen:int,
    gaplen:int,
) -> None:
    startx, starty= start
    endx, endy = end
    deltax = endx-startx
    deltay = endy-starty
    distance = math.hypot(deltax,deltay)
    if distance == 0:
        return
    
    unitx=deltax/distance
    unity=deltay/distance
    position= 0.0
    while position< distance:
        dashend=min(position+dashlen,distance)
        draw.line((startx+unitx*position,starty+unity*position,startx+unitx*dashend,starty+unity*dashend),fill=fill,width=width)
        position+=dashlen+gaplen
        
def cells(edges:Image.Image,columns:int=8,rows:int=8)-> list[list[float]]:
    width,height= edges.size
    densities: list[list[float]] = []
    for row in range(rows):
        rowval: list[float]= []
        top = row* height//rows
        bottom= max(top+1,(row+1)*height//rows)
        for column in range(columns):
            left = column*width//columns
            right= max(left+1, (column+1)*width//columns)
            cell= edges.crop((left,top,right,bottom))
            rowval.append(sum(cell.getdata())/ max(1, cell.width* cell.height))
            densities.append(rowval)
        return densities

def findpoints(
    edges: Image.Image,
    maxtarget: int
)-> tuple[tuple[int,int], list[tuple[int,int]]]:
    width,height=edges.size
    columns= min(8, max(2, width))
    rows= min(8,max(2,height))
    densities = cells(edges,columns,rows)
    cells= sorted((densities[row][column],column,row) for row in range(rows) for column in range(columns))
    centercolumn, centerrow = cells[-1]
    centerdensity= densities[centerrow][centercolumn]
    center=((centercolumn*2+1)*width//(columns*2),(centerrow*2+1)*height//(rows*2))
    targets: list[tuple[int,int]]=[]
    maxtargetdistance= min(width,height)*0.42
    targetdensity= max(mintargetedge, centerdensity*0.45)
    for density, column, row in reversed(cells[:-1]):
        point=((column*2+1)*width//(columns*2),(row*2+1)*height//(rows*2))
        if (density>=targetdensity and min(width,height)*0.12<math.dist(center,point)<=maxtargetdistance):
            targets.append(point)
        if len(targets)== maxtarget:
            break
    return center,targets

def process(
    image:Image.Image,
    intensity:float=100,
    maxtarget: int=6,
    **kwargs: object,
)-> Image.Image:
    del kwargs
    try:
        targetlimit=int(maxtarget)
    except(TypeError,ValueError) as exc:
        raise ValueError("maxtargets must be positive") from exc
    if targetlimit<0:
        raise ValueError("maxtargets must be positive")
    if intensity== 0:
        return image.copy()
    
    grayscale=ImageOps.autocontrast(image.convert("L"))
    edges=grayscale.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.0))
    center,targetpoints= findpoints(edges,targetlimit)
    overlay= Image.new("RGBA", image.size, (0,0,0,0))
    draw= ImageDraw.Draw(overlay)
    alpha= round(215*intensity)
    mainfill= (*HUD_COLOR,alpha)
    faintfill= (*HUD_COLOR, round(80*intensity))
    radius= max(1,round(min(image.size)*0.30))
    linewidth= max(1,round(min(image.size)/350))
    drawcircle(draw,center,radius,mainfill,linewidth)
    dashedline(draw, (center[0]-radius, center[1]),(center[0]+radius, center[1]), faintfill, linewidth, 18,12)
    dashedline(draw, (center[0], center[1]-radius), (center[0], center[1]+radius), faintfill, linewidth, 18,12)
    draw.ellipse((center[0]-3, center[1]-3, center[0]+3, center[1]+3), outline=mainfill, width=linewidth)
    font= ImageFont.load_default()
    boxsize= max(1, min(100, max(40, round(min(image.size)*0.12))))
    boxsize= min(boxsize, max(1,min(image.size)//2))
    
    for index, point in enumerate(targetpoints):
        left = max(0, min(image.width - boxsize, point[0]-boxsize//2))
        top= max(0, min(image.height - boxsize, point[1]- boxsize//2))
        right= left+boxsize
        bottom=top+boxsize
        draw.rectangle((left,top,right,bottom), outline=mainfill, width=linewidth)
        corner= max(3, boxsize//5)
        draw.line((left,top,left+corner,top),fill=mainfill,width=linewidth+1)
        draw.line((left,top,left,top+corner),fill=mainfill,width=linewidth+1)
        textx=min(image.width-1,right+max(4,boxsize//10))
        texty=max(0, top-font.getbbox("CONF:0.86")[1])
        confidence=0.86/(1.0+index*0.08)
        lines = (f"CONF: {confidence:.3f}",f"ID: 0x{0x9A4F + index * 0x31:04X}","TYPE: PATTERN" if index == 0 else "TYPE: DETAIL",f"SCAN RAD: {radius}px",)
        for linenum, text in enumerate(lines):
            draw.text((textx, texty+linenum*10), text, font=font, fill=mainfill)
    
    result = Image.alpha_composite(image.convert("RGBA"), overlay)
    if "A" not in image.getbands():
        return result.convert("RGB")
    return result