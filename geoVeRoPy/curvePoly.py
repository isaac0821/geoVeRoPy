import math

from .ring import *
from .curveArc import *
from .geometry import *

class Bow(object):
    # NOTE: Consists of a curveArc and a cord
    def __init__(self, startPt, endPt, radius=None, center=None, clockwiseFlag = True, lod = 3):
        # Case 0: 没有提供radius和center
        if (radius == None and center == None):
            self.curveArc = None
            self.clockwiseFlag = True

        # Case 1: 提供了radius，没有提供center
        elif (radius != None and center == None):
            midPt = ptMid([startPt, endPt])

        # Case 2: 提供了center，没有提供radius

        self.curveArc = CurveArc()
        self.clockwiseFlag = clockwiseFlag
        

class CurvePoly(Ring):
    # NOTE: Consists of a sequence of consecutive curveArcs
    # NOTE: By default as clockwise
    def __init__(self, bows: list[Bow]):

        return

    def splitCurveArcOnCurve(self, pt):
        return

    

