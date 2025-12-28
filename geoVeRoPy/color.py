import random
import numpy as np

def rndColor() -> str:
    color = "#%06x" % random.randint(0, 0xFFFFFF)
    return color

def rndRed() -> str:
    color = "#FF00%02x" % random.randint(0, 0xFF)
    return color

def colorComplement(hexColor):
    (r, g, b) = hex2RGB(hexColor)
    def hilo(a, b, c):
        if c < b: b, c = c, b
        if b < a: a, b = b, a
        if c < b: b, c = c, b
        return a + c
    k = hilo(r, g, b)
    (revR, revG, revB) = tuple(k - u for u in (r, g, b))
    return RGB2Hex((revR, revG, revB))

def hex2RGB(colorHex):
    colorHex = colorHex.lstrip('#')
    lv = len(colorHex)
    return tuple(int(colorHex[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

def getBWText(hexColor):
    (r, g, b) = hex2RGB(hexColor)
    
    # 直接计算相对亮度（Rec. 709标准）
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    # 根据亮度决定文字颜色
    if luminance >= 186:  # 较亮的背景用黑色文字
        return 'black'
    else:                 # 较暗的背景用白色文字
        return 'white'

def RGB2Hex(colorRGB):
    return '#%02x%02x%02x' % colorRGB



