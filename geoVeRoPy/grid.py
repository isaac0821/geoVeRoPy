import math

from .common import *
from .plot import *
from .geometry import *

def gridSquare(
    center: pt,
    width: float,
    boundingBox: list
    ) -> dict:

    numUp = math.ceil((center[1] - boundingBox[2]) / width)
    numDown = math.ceil((boundingBox[3] - center[1]) / width)
    numLeft = math.ceil((center[0] - boundingBox[0]) / width)
    numRight = math.ceil((boundingBox[1] - center[0]) / width)

    grid = {}

    for i in range(-numLeft, numRight + 1, 1):
        for j in range(-numDown, numUp + 1, 1):
            grid[(i, j)] = {
                'loc': (center[0] + i * width, center[1] + j * width),
                'poly': [
                    (center[0] + i * width - width / 2, center[1] + j * width - width / 2), 
                    (center[0] + i * width - width / 2, center[1] + j * width + width / 2), 
                    (center[0] + i * width + width / 2, center[1] + j * width + width / 2), 
                    (center[0] + i * width + width / 2, center[1] + j * width - width / 2)],
                'label': None
            }

    return grid

def gridHexagon(
    center: pt,
    width: float,
    boundingBox: list
    ) -> dict:

    sqrt3 = math.sqrt(3)

    numUp = math.ceil((center[1] - boundingBox[2]) / (1.5 * width))
    numDown = math.ceil((boundingBox[3] - center[1]) / (1.5 * width))
    numLeft = math.ceil((center[0] - boundingBox[0]) / (sqrt3 * width))
    numRight = math.ceil((boundingBox[1] - center[0]) / (sqrt3 * width))

    grid = {}

    offSet = 0
    for j in range(-numDown, numUp + 1, 1):    
        if (j % 2 == 0):
            offSet = 0
        else:
            offSet = sqrt3 * width / 2        
        for i in range(-numLeft, numRight + 1, 1):
            grid[(i, j)] = {
                'loc': (center[0] + i * sqrt3 * width + offSet, center[1] + j * 1.5 * width),
                'poly': [
                    (center[0] + i * sqrt3 * width + offSet - sqrt3 * width / 2, center[1] + j * 1.5 * width + width / 2),
                    (center[0] + i * sqrt3 * width + offSet, center[1] + j * 1.5 * width + width),
                    (center[0] + i * sqrt3 * width + offSet + sqrt3 * width / 2, center[1] + j * 1.5 * width + width / 2),
                    (center[0] + i * sqrt3 * width + offSet + sqrt3 * width / 2, center[1] + j * 1.5 * width - width / 2),
                    (center[0] + i * sqrt3 * width + offSet, center[1] + j * 1.5 * width - width),
                    (center[0] + i * sqrt3 * width + offSet - sqrt3 * width / 2, center[1] + j * 1.5 * width - width / 2),
                ],
                'label': None
            }

    return grid

def gridIntPolys(
    grid: dict,
    polys: list[poly],
    boundingBox: list = None):

    if (boundingBox == None):
        boundingBox = defaultBoundingBox(polys = polys)

    for g in grid:
        if (grid[g]['label'] == None):
            for p in polys:
                # print(p)
                if (isPolyIntPoly(grid[g]['poly'], p)):
                    grid[g]['label'] = True

    return grid

