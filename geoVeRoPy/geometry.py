import geopy.distance
import heapq
import math
import warnings
import random
import numpy as np
import gurobipy as grb
import sys

import shapely
from shapely.geometry import mapping
from shapely.ops import nearest_points
import networkx as nx

from .common import *
from .tree import *

# Relation between Pts ========================================================
def is2PtsSame(pt1: pt, pt2: pt) -> bool:
    """
    Are two points at the 'same' location?

    Parameters
    ----------
    pt1: pt, required
        Coordinate of the first point
    pt2: pt, required
        Coordinate of the second point

    Return
    ------
    bool
        True if two points are at the same location, False else-wise

    """
    if (len(pt1) != len(pt2)):
        return False
    for k in range(len(pt1)):
        if (abs(pt1[k] - pt2[k]) >= ERRTOL['distPt2Pt']):
            return False
    return True

def is3PtsClockWise(pt1: pt, pt2: pt, pt3: pt) -> bool | None:
    """
    Are three given pts in a clock-wise order, None as they are collinear

    Parameters
    ----------
    pt1: pt, required
        Coordinate of the first point
    pt2: pt, required
        Coordinate of the second point
    pt3: pt, required
        Coordinate of the third point

    Return
    ------
    bool | None
        True if three given points are in a clock-wise order, False if they are in counter-clock-wise order, None if they are collinear
    """
    if (is2PtsSame(pt1, pt2) or is2PtsSame(pt2, pt3) or is2PtsSame(pt1, pt3)):
        # If points are overlapped, return None as collinear
        return None
    [x1, y1] = [pt1[0], pt1[1]]
    [x2, y2] = [pt2[0], pt2[1]]
    [x3, y3] = [pt3[0], pt3[1]]
    ori = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)
    # collinear
    if (abs(ori) <= ERRTOL['collinear']):
        return None
    # clockwise 
    elif (ori < 0):        
        return True
    # counter-clockwise
    else:        
        return False

# Relation between line segments ==============================================
def is2SegsSame(seg1: line, seg2: line) -> bool:
    """
    Given two segments, return True if these two segments are the same.

    Parameters
    ----------
    seg1: line, required
        The first segment
    seg2: line, required
        The second segment

    Return
    ------
    bool
        True if two segments are the same
    """

    if (is2PtsSame(seg1[0], seg2[0]) and is2PtsSame(seg1[1], seg2[1])):
        return True
    elif (is2PtsSame(seg1[0], seg2[1]) and is2PtsSame(seg1[1], seg2[0])):
        return True
    else:
        return False

def is2SegsParallel(seg1: line, seg2: line):
    """
    Given two segment, return true if they are parallel

    Parameters
    ----------
    seg1: line, required
        The first segment
    seg2: line, required
        The second segment

    Return
    ------
    bool
        True if two segments are parallel
    """
    # 计算一堆 dy, dx
    dy1 = seg1[1][1] - seg1[0][1]
    dx1 = seg1[1][0] - seg1[0][0]
    dy2 = seg2[1][1] - seg2[0][1]
    dx2 = seg2[1][0] - seg2[0][0]

    # 先判断是不是水平或者垂直
    isHori1 = (dy1 == 0)
    isHori2 = (dy2 == 0)
    isVert1 = (dx1 == 0)
    isVert2 = (dx2 == 0)

    if (isHori1 and isVert1):
        raise ZeroDivisionError("ERROR: seg1 is a singleton point")
    if (isHori2 and isVert2):
        raise ZeroDivisionError("ERROR: seg2 is a singleton point")

    # 是不是都水平
    if (isHori1 and isHori2):
        return True
    elif (isHori1 and not isHori2):
        return False
    elif (not isHori1 and isHori2):
        return False

    # 是不是都垂直
    if (isVert1 and isVert2):
        return True
    elif (isVert1 and not isVert2):
        return False
    elif (not isVert1 and isVert2):
        return False

    # slope = (y2 - y1) / (x2 - x1)
    slope1 = dy1 / dx1
    slope2 = dy2 / dx2

    if (abs(slop1 - slope2) <= ERRTOL['slope2Slope']):
        return True
    else:
        return False

def is2SegsAffine(seg1: line, seg2: line):
    """
    Given two segment, return true if they are affine

    Parameters
    ----------
    seg1: line, required
        The first segment
    seg2: line, required
        The second segment

    Return
    ------
    bool
        True if two segments are affine
    """

    if (is2SegsParallel(seg1, seg2) and isPtOnLine(seg1[0], seg2)):
        return True
    else:
        return False

def is2SegsOverlap(seg1: line, seg2: line):
    """
    Given two segment, return true if they are overlapped

    Parameters
    ----------
    seg1: line, required
        The first segment
    seg2: line, required
        The second segment

    Return
    ------
    bool
        True if two segments are overlapped
    """

    if (is2SegsParallel(seg1, seg2) and (isPtOnSeg(seg1[0], seg2) or isPtOnSeg(seg1[1], seg2))):
        return True
    else:
        return False

def subSegFromPoly(seg: line, poly: poly=None, polyShapely: shapely.Polygon=None, returnShaplelyObj: bool=False):
    # Sanity check ============================================================
    if (poly == None and polyShapely == None):
        raise MissingParameterError("ERROR: `poly` and `polyShapely` cannot be None at the same time.")

    # get shapely objects =====================================================
    segShapely = shapely.LineString([seg[0], seg[1]])
    if (polyShapely == None):
        polyShapely = shapely.Polygon(poly)
    intShape = shapely.difference(segShapely, polyShapely)

    # If return shapely objects no processing needed ==========================
    if (returnShaplelyObj):
        return intShape

    # 若不相交，返回不相交
    # FIXME: 现在的精度可能有问题，需要计算两者间距离
    if (intShape.is_empty): 
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    elif (isinstance(intShape, shapely.Point)):
        # 都是闭集，不应该交出一个开集来
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    elif (isinstance(intShape, shapely.LineString)):
        return {
            'status': 'Cross',
            'intersect': [tuple(intShape.coords[0]), tuple(intShape.coords[1])],
            'intersectType': 'Segment',
            'interiorFlag': True
        }
    else:
        intSp = []
        for obj in intShape.geoms:
            if (isinstance(obj, shapely.LineString)):
                intSp.append({
                    'status': 'Cross',
                    'intersect': [tuple(obj.coords[0]), tuple(obj.coords[1])],
                    'intersectType': 'Segment',
                    'interiorFlag': True
                })

        return intSp

# Relation between Pt and Objects =============================================
def isPtOnLine(pt: pt, line: line) -> bool:
    """
    Is a pt on the line?

    Parameters
    ----------
    pt: pt, required
        Coordinate of the point
    line: line, required
        Two coordinates to form a line

    Return
    ------
    bool
        True if the point is on the line, False else-wise

    """
    if (is2PtsSame(line[0], line[1])):
        raise ZeroVectorError()
    if (is3PtsClockWise(pt, line[0], line[1]) == None):
        return True
    else:
        return False

def isPtOnSeg(pt: pt, seg: line, interiorOnly: bool=False) -> bool:
    """
    Is a pt on the lines segment?

    Parameters
    ----------
    pt: pt, required
        Coordinate of the point
    seg: line, required
        Two coordinates to form a line segment
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior

    Return
    ------
    bool
        True if the point is on the line segment, False else-wise

    """
    onLine = isPtOnLine(pt, seg)
    if (onLine == False):
        return False
    # Get pts =================================================================
    [x1, y1] = [seg[0][0], seg[0][1]]
    [x2, y2] = [pt[0], pt[1]]
    [x3, y3] = [seg[1][0], seg[1][1]]
    # NOTE: 判断在线段上的标准为到两端点的距离的和等于端点间距离
    onSeg = (
        abs(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) 
        + math.sqrt((x2 - x3) ** 2 + (y2 - y3) ** 2) 
        - math.sqrt((x1 - x3) ** 2 + (y1 - y3) ** 2)) <= ERRTOL['distPt2Pt'])
    # Check if the intersection is in the interior ============================
    if (interiorOnly):
        return onSeg and not is2PtsSame(pt, seg[0]) and not is2PtsSame(pt, seg[1])
    else:
        return onSeg

def isPtOnRay(pt: pt, ray: line, interiorOnly: bool=False) -> bool:
    """
    Is a pt on the ray?

    Parameters
    ----------
    pt: pt, required
        Coordinate of the point
    ray: line, required
        Two coordinates to form a line segment
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior

    Return
    ------
    bool
        True if the point is on the line segment, False else-wise

    """
    onLine = isPtOnLine(pt, ray)
    if (onLine == False):
        return False
    # Get pts =================================================================
    [x1, y1] = [ray[0][0], ray[0][1]]
    [x2, y2] = [pt[0], pt[1]]
    [x3, y3] = [ray[1][0], ray[1][1]]
    onRay = (
        (abs(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) 
            + math.sqrt((x2 - x3) ** 2 + (y2 - y3) ** 2) 
            - math.sqrt((x1 - x3) ** 2 + (y1 - y3) ** 2)) <= ERRTOL['distPt2Pt'])
        or (math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) >= math.sqrt((x2 - x3) ** 2 + (y2 - y3) ** 2)))
    # Check if the intertion is in the interior ===============================
    if (interiorOnly):
        return onRay and not is2PtsSame(pt, ray[0])
    else:
        return onRay

def isPtOnPolyEdge(pt: pt, poly: poly) -> bool:
    """
    Is a pt on the edge of the polygon?

    Parameters
    ----------
    pt: pt, required
        Coordinate of the point
    poly: poly, required
        The polygon

    Return
    ------
    bool
        True if the point is on the line segment, False else-wise
    """

    # Check if the pt is on any of the edge segment ===========================
    for i in range(-1, len(poly) - 1):
        if (isPtOnSeg(pt, [poly[i], poly[i + 1]])):
            return True
    return False

def isPtInPoly(pt: pt, poly: poly, interiorOnly: bool=False) -> bool:
    """
    Is a pt in the polygon?

    Parameters
    ----------
    pt: pt, required
        Coordinate of the point
    poly: poly, required
        The polygon
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior

    Return
    ------
    bool
        True if the point is on the line segment, False else-wise

    """

    x = pt[1]
    y = pt[0]
    inPoly = False
    # NOTE: 忘记这段魔法是从哪里来的了...
    j = len(poly) - 1
    for i in range(len(poly)):
        xi = poly[i][1]
        yi = poly[i][0]
        xj = poly[j][1]
        yj = poly[j][0]
        intersect = (yi > y) != (yj > y)
        if (intersect):
            intersect = (x < (xj - xi) * (y - yi) / float(yj - yi) + xi)
        if (intersect):
            inPoly = not inPoly
        j = i
    # Check if the intertion is in the interior ===============================
    if (interiorOnly):
        return inPoly and not isPtOnPolyEdge(pt, poly)
    else:
        return inPoly

# Object to line-shape ========================================================
def rayPerp2Line(pt: pt, line: line) -> line:
    """
    Given a point and a line, return a ray from that point and perpendicular to the given line

    Parameters
    ----------
    pt: pt, required
        The point where the ray will go through
    line: line Required
        The line which the ray is perpendicular to

    Return
    ------
    line
        A ray that is perpendicular to the line

    """

    if (isPtOnLine(pt, line)):
        raise ZeroVectorError()

    # Heading of line
    heading = headingXY(line[0], line[1])
    heading += 90
    while (heading > 360):
        heading -= 360
    while (heading < 0):
        heading += 360

    # Perp line    
    perp = [pt, ptInDistXY(pt, heading, 10)]
    intPt = intLine2Line(line, perp)
    ray = [pt, intPt['intersect']]

    return ray

# Line-shape intersection =====================================================
def intLine2Line(line1: line, line2: line) -> dict:
    """
    The intersection of a line to another line

    Parameters
    ----------
    line1: line, required
        The first line
    line2: line, required
        The second line

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """
    
    if (is2PtsSame(line1[0], line1[1])):
        raise ZeroVectorError(line1)
    if (is2PtsSame(line2[0], line2[1])):
        raise ZeroVectorError(line2)

    # Get Ax + By + C = 0
    def abc(pt1, pt2):
        x1, y1 = pt1
        x2, y2 = pt2
        a = y1 - y2
        b = x2 - x1
        c = x1 * y2 - x2 * y1
        return a, b, c

    # Calculate intersection
    a1, b1, c1 = abc(line1[0], line1[1])
    a2, b2, c2 = abc(line2[0], line2[1])
    D = a1 * b2 - a2 * b1

    # Check if parallel
    # 共线情形
    if (abs(D) <= ERRTOL['collinear'] and is3PtsClockWise(line1[0], line1[1], line2[0]) == None):
        return {
            'status': 'Collinear',
            'intersect': line1,
            'intersectType': 'Line',
            'interiorFlag': True
        }
    # 平行情形
    elif (abs(D) <= ERRTOL['collinear']):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    # 相交情形
    else:
        x = (b1 * c2 - b2 * c1) / D
        y = (a2 * c1 - a1 * c2) / D
        return {
            'status': 'Cross',
            'intersect': (x, y),
            'intersectType': 'Point',
            'interiorFlag': True
        }

def intLine2Seg(line: line, seg: line) -> dict:
    """
    The intersection of a line to another line segment

    Parameters
    ----------
    line: line, required
        The first line
    seg: line, required
        The second line segment

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """

    intPt = intLine2Line(line, seg)

    # 如果直线不相交，返回不相交
    if (intPt['status'] == 'NoCross'):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': True
        }
    # 如果直线和线段共线，返回线段
    elif (intPt['status'] == 'Collinear'):
        return {
            'status': 'Collinear',
            'intersect': seg,
            'intersectType': 'Segment',
            'interiorFlag': True
        }
    # 若相交点不在线段上，返回不相交
    elif (not isPtOnSeg(intPt['intersect'], seg, interiorOnly=False)):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    # 若相交点在线段端点上，返回相交且不在interior
    elif (is2PtsSame(intPt['intersect'], seg[0]) or is2PtsSame(intPt['intersect'], seg[1])):
        return {
            'status': 'Cross',
            'intersect': intPt['intersect'],
            'intersectType': 'Point',
            'interiorFlag': False
        }
    # 若相交点在线段内，返回相交且在interior内
    else:
        return {
            'status': 'Cross',
            'intersect': intPt['intersect'],
            'intersectType': 'Point',
            'interiorFlag': True
        }

def intLine2Ray(line: line, ray: line) -> dict:
    """
    The intersection of a line to a ray

    Parameters
    ----------
    line: line, required
        The first line
    ray: line, required
        The second ray

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """

    intPt = intLine2Line(line, ray)

    # 若直线不相交，返回不相交
    if (intPt['status'] == 'NoCross'):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    # 若直线与射线共线，返回射线
    elif (intPt == "Collinear"):
        return {
            'status': 'Collinear',
            'intersect': ray,
            'intersectType': 'Ray',
            'interiorFlag': True
        }
    # 若相交点不在射线内，返回不相交
    elif (not isPtOnRay(intPt['intersect'], ray, interiorOnly=False)):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    # 若相交点在射线端点上，返回相交且不在interior
    elif (is2PtsSame(intPt['intersect'], ray[0])):
        return {
            'status': 'Cross',
            'intersect': intPt['intersect'],
            'intersectType': 'Point',
            'interiorFlag': False
        }
    # 若相交点在射线内，返回相交且在interior内
    else:
        return {
            'status': 'Cross',
            'intersect': intPt['intersect'],
            'intersectType': 'Point',
            'interiorFlag': True
        }        

def intSeg2Line(seg: line, line: line) -> dict:
    """
    The intersection of a line segment to another line

    Parameters
    ----------
    seg: line, required
        The first line segment
    line: line, required
        The second line

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """
    return intLine2Seg(line, seg)

def intSeg2Seg(seg1: line, seg2: line) -> dict:
    """
    The intersection of a line segment to another line segment

    Parameters
    ----------
    seg1: line, required
        The first line segment
    seg2: line, required
        The second line segment

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """
    if (is2PtsSame(seg1[0], seg1[1])):
        raise ZeroVectorError(seg1)
    if (is2PtsSame(seg2[0], seg2[1])):
        raise ZeroVectorError(seg2)

    A, B, C, D = seg1[0], seg1[1], seg2[0], seg2[1]
    if (max(C[0], D[0]) < min(A[0], B[0]) 
        or max(A[0], B[0]) < min(C[0], D[0]) 
        or max(C[1], D[1]) < min(A[1], B[1]) 
        or max(A[1], B[1]) < min(C[1], D[1])):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }

    # 判断是否相互跨立
    d1 = is3PtsClockWise(A, B, C)
    d2 = is3PtsClockWise(A, B, D)
    d3 = is3PtsClockWise(C, D, A)
    d4 = is3PtsClockWise(C, D, B)

    # If any of ds is None, that means an end of segment is on the other segment
    if (d1 == None or d2 == None or d3 == None or d4 == None):
        if (interiorOnly):
            return {
                'status': 'NoCross',
                'intersect': None,
                'intersectType': None,
                'interiorFlag': None
            }
        else:
            intPt = intLine2Line(seg1, seg2)
            # 若直线共线，进一步分情况讨论
            if (intPt['status'] == "Collinear"):
                # 线段端点是否在另一条线段上
                seg1aInSeg2Flag = isPtOnSeg(seg1[0], seg2, interiorOnly=False)
                seg1bInSeg2Flag = isPtOnSeg(seg1[1], seg2, interiorOnly=False)
                seg2aInSeg1Flag = isPtOnSeg(seg2[0], seg1, interiorOnly=False)
                seg2bInSeg1Flag = isPtOnSeg(seg2[1], seg1, interiorOnly=False)

                # Case 1: seg1完全在seg2内
                if (seg1aInSeg2Flag and seg1bInSeg2Flag):
                    return {
                        'status': 'Collinear',
                        'intersect': seg1,
                        'intersectType': 'Segment',
                        'interiorFlag': True
                    }
                # Case 2: seg2完全在seg1内
                elif (seg2aInSeg1Flag and seg2bInSeg1Flag):
                    return {
                        'status': 'Collinear',
                        'intersect': seg2,
                        'intersectType': 'Segment',
                        'interiorFlag': True
                    }
                # Case 3: seg1b在seg2内，seg2a在seg1内
                elif (seg1bInSeg2Flag and seg2aInSeg1Flag):
                    # Case 3.1: 相交在端点上
                    if (is2PtsSame(seg1[1], seg2[0])):
                        return {
                            'status': 'Collinear',
                            'intersect': seg1[1],
                            'intersectType': 'Point',
                            'interiorFlag': False
                        }
                    # Case 3.2: 有重合线段
                    else:
                        return {
                            'status': 'Collinear',
                            'intersect': [seg1[1], seg2[0]],
                            'intersectType': 'Segment',
                            'interiorFlag': True
                        }
                # Case 4: seg1a在seg2内，seg2a在seg1内
                elif (seg1aInSeg2Flag and seg2aInSeg1Flag):
                    # Case 4.1: 相交在端点上
                    if (is2PtsSame(seg1[0], seg2[0])):
                        return {
                            'status': 'Collinear',
                            'intersect': seg1[0],
                            'intersectType': 'Point',
                            'interiorFlag': False
                        }
                    # Case 4.2: 有重合线段
                    else:
                        return {
                            'status': 'Collinear',
                            'intersect': [seg1[0], seg2[0]],
                            'intersectType': 'Segment',
                            'interiorFlag': True
                        }
                # Case 5: seg1b在seg2内，seg2b在seg1内
                elif (seg1bInSeg2Flag and seg2bInSeg1Flag):
                    # Case 5.1: 相交在端点上
                    if (is2PtsSame(seg1[1], seg2[1])):
                        return {
                            'status': 'Collinear',
                            'intersect': seg1[1],
                            'intersectType': 'Point',
                            'interiorFlag': False
                        }
                    # Case 5.2: 有重合线段
                    else:
                        return {
                            'status': 'Collinear',
                            'intersect': [seg1[1], seg2[1]],
                            'intersectType': 'Segment',
                            'interiorFlag': True
                        }
                # Case 6: seg1a在seg2内，seg2b在seg1内
                elif (seg1aInSeg2Flag and seg2bInSeg1Flag):
                    # Case 6.1: 相交在端点上
                    if (is2PtsSame(seg1[0], seg2[1])):
                        return {
                            'status': 'Collinear',
                            'intersect': seg1[0],
                            'intersectType': 'Point',
                            'interiorFlag': False
                        }
                    # Case 6.2: 有重合线段
                    else:
                        return {
                            'status': 'Collinear',
                            'intersect': [seg1[0], seg2[1]],
                            'intersectType': 'Segment',
                            'interiorFlag': True
                        }
                # Case 7: 无相交
                else:
                    return {
                        'status': 'Collinear',
                        'intersect': None,
                        'intersectType': None,
                        'interiorFlag': None
                    }
            else:
                return {
                    'status': 'Cross',
                    'intersect': intPt['intersect'],
                    'intersectType': 'Point',
                    'interiorFlag': True
                }

    # Turn T/F to 1/0
    d1Num = 1 if d1 else -1
    d2Num = 1 if d2 else -1
    d3Num = 1 if d3 else -1
    d4Num = 1 if d4 else -1

    if (d1Num * d2Num < 0 and d3Num * d4Num < 0):
        intPt = intLine2Line(seg1, seg2)
        return {
            'status': 'Cross',
            'intersect': intPt['intersect'],
            'intersectType': 'Point',
            'interiorFlag': True
        }
    else:
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }

def intSeg2Ray(seg: line, ray: line) -> dict:
    """
    The intersection of a line segment to a ray

    Parameters
    ----------
    line: line, required
        The first line
    ray: line, required
        The second line

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """

    intPt = intLine2Line(seg, ray)

    # 若直线不相交，返回不相交
    if (intPt['status'] == 'NoCross'):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    # 若直线共线，进一步分情况讨论
    elif (intPt['status'] == "Collinear"):
        # 线段端点是否在射线内
        segAInRayFlag = isPtOnRay(seg[0], ray, interiorOnly=False)
        segBInRayFlag = isPtOnRay(seg[1], ray, interiorOnly=False)
        # Case 1: seg整个在ray内
        if (segAInRayFlag and segBInRayFlag):
            return {
                'status': 'Collinear',
                'intersect': seg,
                'intersectType': 'Segment',
                'interiorFlag': True
            }
        # Case 2: segA在ray内，segB不在ray内
        elif (segAInRayFlag and not segBInRayFlag):
            # Case 2.1: 相交于射线的端点
            if (is2PtsSame(seg[1], ray[0])):
                return {
                    'status': 'Collinear',
                    'intersect': seg[1],
                    'intersectType': 'Point',
                    'interiorFlag': False
                }
            # Case 2.2: 相较于射线内部
            else:
                return {
                    'status': 'Collinear',
                    'intersect': [ray[0], seg[1]],
                    'intersectType': 'Segment',
                    'interiorFlag': True
                }
        # Case 3: segB在ray内，segA不在ray内
        elif (segBInRayFlag and not segAInRayFlag):
            # Case 3.1: 相交于射线的端点
            if (is2PtsSame(seg[0], ray[0])):
                return {
                    'status': 'Collinear',
                    'intersect': seg[0],
                    'intersectType': 'Point',
                    'interiorFlag': False
                }
            # Case 3.2: 相较于射线内部
            else:
                return {
                    'status': 'Collinear',
                    'intersect': [ray[0], seg[0]],
                    'intersectType': 'Segment',
                    'interiorFlag': True
                }
        # Case 4: 无相交
        else:
            return {
                'status': 'Collinear',
                'intersect': None,
                'intersectType': None,
                'interiorFlag': None
            }
    # 若交点不在线段内或不在射线内，不相交
    elif (not isPtOnSeg(intPt['intersect'], seg, interiorOnly=False)
            or not isPtOnRay(intPt['intersect'], ray, interiorOnly=False)):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    # 若交点在线段端点上或者在射线端点上，交于boundary
    elif (is2PtsSame(intPt['intersect'], seg[0])
            or is2PtsSame(intPt['intersect'], seg[1])
            or is2PtsSame(intPt['intersect'], ray[0])):
        return {
            'status': 'Cross',
            'intersect': intPt['intersect'],
            'intersectType': 'Point',
            'interiorFlag': False
        }
    # 若交点在线段内且在射线内，交于interior
    else:
        return {
            'status': 'Cross',
            'intersect': intPt['intersect'],
            'intersectType': 'Point',
            'interiorFlag': True
        }

def intRay2Line(ray: line, line: line) -> dict:
    """
    The intersection of a ray to another line

    Parameters
    ----------
    ray: line, required
        The first line
    line: line, required
        The second line

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """
    return intLine2Ray(line, ray)

def intRay2Seg(ray: line, seg: line) -> dict:
    """
    The intersection of a ray to another line segment

    Parameters
    ----------
    ray: line, required
        The first line
    seg: line, required
        The second line

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """
    return intSeg2Ray(seg, ray)

def intRay2Ray(ray1: line, ray2: line) -> dict:
    """
    The intersection of a ray to another ray

    Parameters
    ----------
    ray1: line, required
        The first line
    ray2: line, required
        The second line

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """

    intPt = intLine2Line(ray1, ray2)

    # 若直线不相交，返回不相交
    if (intPt['status'] == 'NoCross'):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    # 若直线共线，进一步情况讨论
    elif (intPt['status'] == "Collinear"):
        # 射线端点是否在其他射线内
        ray1AInRay2Flag = isPtOnRay(ray1[0], ray2, interiorOnly=False)
        ray2AInRay1Flag = isPtOnRay(ray2[0], ray1, interiorOnly=False)
        # Case 1: ray2a在ray1内，且ray1a在ray2内
        if (ray1AInRay2Flag and ray2AInRay1Flag):
            # Case 1.1: 射线对头相交于端点
            if (is2PtsSame(ray1[0], ray2[0])):
                return {
                    'status': 'Collinear',
                    'intersect': ray1[0],
                    'intersectType': 'Point',
                    'interiorFlag': False
                }
            # Case 1.2: 射线有重合线段
            else:
                return {
                    'status': 'Collinear',
                    'intersect': [ray1[0], ray2[0]],
                    'intersectType': 'Segment',
                    'interiorFlag': True
                }
        # Case 2: ray2a在ray1内，且ray1a不在ray2内
        elif (ray2AInRay1Flag and not ray1AInRay2Flag):
            return {
                'status': 'Collinear',
                'intersect': ray2,
                'intersectType': 'Ray',
                'interiorFlag': True
            }
        # Case 3: ray1a在ray2内，且ray2a不在ray1内
        elif (ray1AInRay2Flag and not ray2AInRay1Flag):
            return {
                'status': 'Collinear',
                'intersect': ray1,
                'intersectType': 'Ray',
                'interiorFlag': True
            }
        # Case 4: 无相交
        else:
            return {
                'status': 'Collinear',
                'intersect': None,
                'intersectType': None,
                'interiorFlag': None
            }
    # 若直线相交点不在任何一个射线上，不相交
    elif (not isPtOnRay(intPt['intersect'], ray1, interiorOnly=False)
            or not isPtOnRay(intPt['intersect'], ray2, interiorOnly=False)):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    # 若相交点在射线的端点上，交于boundary
    elif (is2PtsSame(intPt['intersect'], ray1[0])
            or is2PtsSame(intPt['intersect'], ray2[0])):
        return {
            'status': 'Cross',
            'intersect': intPt['intersect'],
            'intersectType': 'Point',
            'interiorFlag': False
        }
    # 若相交点在射线内，交于interior
    else:
        return {
            'status': 'Cross',
            'intersect': intPt['intersect'],
            'intersectType': 'Point',
            'interiorFlag': True
        }

# Line-shape versus Line-shape ===================================================
def isLineIntLine(line1: line, line2: line) -> bool:
    """
    Is two line intersect with each other?

    Parameters
    ----------
    line1: line, required
        The first line
    line2: line, required
        The second line

    Return
    ------
    bool
        True if intersects
    """
    intPt = intLine2Line(line1, line2)
    if (intPt['intersect'] == None):
        return False
    else:
        return True

def isLineIntSeg(line: line, seg: line, interiorOnly:bool=False) -> bool:
    """
    Is a line intersect with a line segment?

    Parameters
    ----------
    line: line, required
        The first line
    seg: line, required
        The second line segment
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior

    Return
    ------
    bool
        True if intersects
    """
    intPt = intLine2Seg(line, seg)
    # 无相交点
    if (intPt['intersect'] == None):
        return False
    # 需要交于interior但未能交于interiror
    elif (interiorOnly and not intPt['interiorFlag']):
        return False
    # 不需要交于interior或需要且交于interior
    else:
        return True

def isLineIntRay(line: line, ray: line, interiorOnly: bool=False) -> bool:
    """
    Is a line intersect with a ray?

    Parameters
    ----------
    line: line, required
        The first line
    ray: line, required
        The second ray
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior

    Return
    ------
    bool
        True if intersects
    """    
    intPt = intLine2Ray(line, ray)
    # 无相交点
    if (intPt['intersect'] == None):
        return False
    # 需要交于interior但未能交于interiror
    elif (interiorOnly and not intPt['interiorFlag']):
        return False
    # 不需要交于interior或需要且交于interior
    else:
        return True

def isSegIntLine(seg: line, line: line, interiorOnly: bool=False) -> bool:
    """
    Is a line segment intersect with a line?

    Parameters
    ----------
    seg: line, required
        The first line segment
    line: line, required
        The second line
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior
        
    Return
    ------
    bool
        True if intersects
    """   
    return isLineIntSeg(line, seg, interiorOnly)

def isSegIntSeg(seg1: line, seg2: line, interiorOnly: bool=False) -> bool:
    """
    Is a line segment intersect with another line segment?

    Parameters
    ----------
    seg1: line, required
        The first line segment
    seg2: line, required
        The second line
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior
        
    Return
    ------
    bool
        True if intersects
    """ 
    if (is2PtsSame(seg1[0], seg1[1])):
        raise ZeroVectorError(seg1)
    if (is2PtsSame(seg2[0], seg2[1])):
        raise ZeroVectorError(seg2)

    A, B, C, D = seg1[0], seg1[1], seg2[0], seg2[1]
    if (max(C[0], D[0]) < min(A[0], B[0]) 
        or max(A[0], B[0]) < min(C[0], D[0]) 
        or max(C[1], D[1]) < min(A[1], B[1]) 
        or max(A[1], B[1]) < min(C[1], D[1])):
        return False

    # 判断是否相互跨立
    d1 = is3PtsClockWise(A, B, C)
    d2 = is3PtsClockWise(A, B, D)
    d3 = is3PtsClockWise(C, D, A)
    d4 = is3PtsClockWise(C, D, B)

    # If any of ds is None, that means an end of segment is on the other segment
    if (d1 == None or d2 == None or d3 == None or d4 == None):
        if (interiorOnly):
            return False
        else:
            return True

    # Turn T/F to 1/0
    d1Num = 1 if d1 else -1
    d2Num = 1 if d2 else -1
    d3Num = 1 if d3 else -1
    d4Num = 1 if d4 else -1

    if (d1Num * d2Num < 0 and d3Num * d4Num < 0):
        return True
    else:
        return False

def isSegIntRay(seg: line, ray: line, interiorOnly: bool=False) -> bool:
    """
    Is a line segment intersect with a ray?

    Parameters
    ----------
    seg: line, required
        The first line segment
    ray: line, required
        The second line
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior
        
    Return
    ------
    bool
        True if intersects
    """ 
    intPt = intSeg2Ray(seg, ray)
    # 无相交点
    if (intPt['intersect'] == None):
        return False
    # 需要交于interior但未能交于interiror
    elif (interiorOnly and not intPt['interiorFlag']):
        return False
    # 不需要交于interior或需要且交于interior
    else:
        return True

def isSegIntBoundingbox(seg: line, boundingBox: list) -> bool:
    """
    Is a line segment intersect with a given bounding box?

    Parameters
    ----------
    seg: line, required
        The first line segment
    boundingBox: list, required
        A list, in the following format: [minX, maxX, minY, maxY]
        
    Return
    ------
    bool
        True if intersects
    """ 
    if (boundingBox[0] <= seg[0][0] <= boundingBox[2] and boundingBox[1] <= seg[0][1] <= boundingBox[3]):
        return True
    if (boundingBox[0] <= seg[1][0] <= boundingBox[2] and boundingBox[1] <= seg[1][1] <= boundingBox[3]):
        return True

    # If both end is in the same side of bounding box
    if (seg[0][0] <= boundingBox[0] and seg[1][0] <= boundingBox[0]):
        return False
    if (seg[0][0] >= boundingBox[2] and seg[1][0] >= boundingBox[2]):
        return False
    if (seg[0][1] <= boundingBox[1] and seg[1][1] <= boundingBox[1]):
        return False
    if (seg[0][1] >= boundingBox[3] and seg[1][1] >= boundingBox[3]):
        return False

    # Clockwise check
    c1 = is3PtsClockWise(seg[0], seg[1], [boundingBox[0], boundingBox[1]])
    c2 = is3PtsClockWise(seg[0], seg[1], [boundingBox[2], boundingBox[1]])
    if (c1 != c2):
        return True
    c3 = is3PtsClockWise(seg[0], seg[1], [boundingBox[0], boundingBox[3]])
    if (c1 != c3 or c2 != c3):
        return True
    c4 = is3PtsClockWise(seg[0], seg[1], [boundingBox[2], boundingBox[3]])
    if (c1 != c4 or c2 != c4 or c3 != c4):
        return True

    return False

def isRayIntLine(ray: line, line: line, interiorOnly: bool=False) -> bool:
    """
    Is a ray intersect with a line?

    Parameters
    ----------
    ray: line, required
        The first line segment
    line: line, required
        The second line
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior
        
    Return
    ------
    bool
        True if intersects
    """ 
    return isLineIntRay(line, ray, interiorOnly)

def isRayIntSeg(ray: line, seg: line, interiorOnly: bool=False) -> bool:
    """
    Is a ray intersect with a line segment?

    Parameters
    ----------
    ray: line, required
        The first line segment
    seg: line, required
        The second line
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior
        
    Return
    ------
    bool
        True if intersects
    """ 
    return isSegIntRay(seg, ray, interiorOnly)

def isRayIntRay(ray1: line, ray2: line, interiorOnly: bool=False) -> bool:
    """
    Is a ray intersect with a ray?

    Parameters
    ----------
    ray1: line, required
        The first line segment
    ray2: line, required
        The second line
    interiorOnly: bool, optional, default as False
        True if only consider intersecting in the interior
        
    Return
    ------
    bool
        True if intersects
    """ 
    intPt = intRay2Ray(ray1, ray2)
    # 无相交点
    if (intPt['intersect'] == None):
        return False
    # 需要交于interior但未能交于interiror
    elif (interiorOnly and not intPt['interiorFlag']):
        return False
    # 不需要交于interior或需要且交于interior
    else:
        return True

# Line-shape intersect with polygon ===========================================
def intLine2Poly(line: line, poly: poly=None, polyShapely: shapely.Polygon=None, returnShaplelyObj: bool=False) -> dict | list[dict] | shapely.Point | shapely.Polygon | shapely.GeometryCollection:
    """
    The intersection of a line to a polygon

    Parameters
    ----------
    line: line, required
        The first line
    poly: poly, optional, default as None
        The second polygon
    polyShapely: shapely.Polygon, optional, default as None
        The correspond shapely object for polygon. Need to provide one of the following fields: [`poly`, `polyShapely`]
    returnShaplelyObj: bool, optional, default as False
        True if alter the result to be a shapely object        

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """

    # Sanity check
    if (poly == None and polyShapely == None):
        raise MissingParameterError("ERROR: `poly` and `polyShapely` cannot be None at the same time.")

    # Projct points to the line
    projPts = []    
    for pt in poly:
        projPts.append(ptFoot2Line(pt, line))

    # Find two pts on the line that are the farthest away from each other =====
    projPts.sort()
    seg = [projPts[0], projPts[-1]]

    return intSeg2Poly(seg, poly, polyShapely, returnShaplelyObj)

def intSeq2Poly(seq: list[pt], poly: poly):
    # NOTE: 这个函数真的麻烦死了
    # 存储所有的（连续）相交线段组
    inte = []
    # 存储之前连续相交的部分，由于poly可能nonconvex，这个可能有多段
    candiCur = []
    def appendCur2Inte(inte, candiCur, excludeIndex = None):
        # print("inte: ", inte)
        # print("candiCur: ", candiCur)
        # print("\n")
        inteUpdate = [i for i in inte]
        candiCurUpdate = []
        # 如果需要跳过某个不并入inte，就先存起来
        if (excludeIndex != None):
            candiCurUpdate = [candiCur[excludeIndex]]
        for c in range(len(candiCur)):
            if (excludeIndex == None or c != excludeIndex):
                if (len(candiCur[c]) == 0):
                    # 如果之前就没有累计相交过，跳过
                    pass
                elif (len(candiCur[c]) == 1):
                    # 如果之前的那段只交了一个点，记录下来
                    inteUpdate.append({
                        'status': 'Cross',
                        'intersect': candiCur[c][0],
                        'intersectType': 'Point',
                        'interiorFlag': False
                    })
                elif (len(candiCur[c]) > 1):
                    # 如果之前相交的那段超过一个点，记录下来路径
                    inteUpdate.append({
                        'status': 'Cross',
                        'intersect': [k for k in candiCur[c]],
                        'intersectType': 'Segment',
                        'interiorFlag': True
                    })
        return inteUpdate, candiCurUpdate

    # 把seq一段一段拆开分别算相交
    for i in range(len(seq) - 1):
        # 当前的这段
        seg = [seq[i], seq[i + 1]]
        p = intSeg2Poly(seg, poly)

        # Case 1: 如果当前的这段与poly有交集，交集只有一个部分，那么这个部分与已有的其中一个可能相邻接
        if (type(p) != list and p['status'] == 'Cross'):
            # Case 1.1: 如果交集是一个点，判断这个点和之前连续相交的部分的关系
            if (p['intersectType'] == 'Point'):
                # Case 2.1.1: 如果之前没有连续相交的部分，这个点存起来
                if (len(candiCur) == 0):
                    candiCur = [[p['intersect']]]
                # Case 2.1.2: 如果之前有连续相交的部分，判断是否在之前的一个上延续
                else:
                    idInclude = None
                    # 判断相交的这个点是不是和之前的部分重合，只能首或尾
                    for c in range(len(candiCur)):
                        if (is2PtsSame(candiCur[c][0], p['intersect']) or is2PtsSame(candiCur[c][-1], p['intersect'])):
                            idInclude = c
                            break
                    # Case 2.1.2.1: 如果这个交点与之前的都不重合，则重头开始
                    if (idInclude == None):
                        inte, candiCur = appendCur2Inte(inte, candiCur)
                        candiCur = [[p['intersect']]]
                    # Case 2.1.2.2: 否则保留第c个可以继续拼接，其他存入inte
                    else:
                        inte, candiCur = appendCur2Inte(inte, candiCur, idInclude)

            # Case 1.2: 如果交集是一个线段，判断这个线段和之前连续相交的部分的关系
            elif (p['intersectType'] == 'Segment'):
                # Case 2.2.1: 如果之前没有连续相交的部分
                if (len(candiCur) == 0):
                    candiCur = [[k for k in p['intersect']]]
                # Case 2.2.2: 如果之前有连续相交的部分
                else:
                    idLink = None
                    linked = None
                    for c in range(len(candiCur)):
                        linked = seqLinkSeq(candiCur[c], p['intersect'])
                        if (linked != None):
                            idLink = c
                            break
                    # Case 2.2.2.1: 如果这段线段和之前的都不重合，则重头开始
                    if (idLink == None):
                        inte, candiCur = appendCur2Inte(inte, candiCur)
                        candiCur = [[k for k in p['intersect']]]
                    # Case 2.2.2.2: 如果这段线段能接上之前的，则接上
                    else:
                        inte, candiCur = appendCur2Inte(inte, candiCur, idLink)
                        candiCur = [[k for k in linked]]
        
        # Case 2: 如果poly非凸，那么可能有好几个相交部分，每个部分都有可能要和之前的连续相交
        elif (type(p) == list):
            # 先把交出来的点和线段都列出来
            # NOTE: 这里的pts和segs两两不相交
            pts = []
            segs = []
            for k in p:
                if (k['intersectType'] == 'Point'):
                    pts.append(k['intersect'])
                elif (k['intersectType'] == 'Segment'):
                    segs.append([v for v in k['intersect']])

            # 这里的seg和pts要一个一个和cur里的试能不能连上
            # 连不上的每一个都有可能被下一段连上，但是下一段至多只有一个可以连上
            idPt = None
            idInclude = None
            for p in range(len(pts)):
                # 判断相交的这个点是不是和之前的部分重合，只能首或尾
                for c in range(len(candiCur)):
                    if (is2PtsSame(candiCur[c][0], pts[p]) or is2PtsSame(candiCur[c][-1], pts[p])):
                        idInclude = c
                        idPt = p
                        break
            idSeg = None
            idLink = None
            linked = None
            for s in range(len(segs)):
                for c in range(len(candiCur)):
                    tryLink = seqLinkSeq(candiCur[c], segs[s])
                    if (tryLink != None):
                        idLink = c
                        idSeg = s
                        linked = tryLink
                        break

            # Case 2.1: 如果点有可以归属于上一段的，但线段没有的
            if (idInclude != None and idLink == None):
                inte, candiCur = appendCur2Inte(inte, candiCur, idInclude)
                # 除了归属于上一段的点，剩余的点和线段（若有）加入candiCur
                if (len(pts) > 1):
                    for p in range(len(pts)):
                        if (p != idPt):
                            candiCur.append([pts[p]])
                if (len(seg) >= 1):
                    for seg in segs:
                        candiCur.append([v for v in seg])

            # Case 2.2: 如果线段有可以连接到上一段的，但点没有的
            elif (idInclude == None and idLink != None):
                inte, candiCur = appendCur2Inte(inte, candiCur, idLink)
                candiCur = [[k for k in linked]]
                if (len(pts) >= 1):
                    for pt in pts:
                        candiCur.append([pt])
                if (len(seg) > 1):
                    for s in range(len(segs)):
                        if (s != idSeg):
                            candiCur.append([v for v in segs[s]])

            # Case 2.3: 如果线段和点里都没有可以连接到上一段的
            elif (idInclude == None and idLink == None):
                inte, candiCur = appendCur2Inte(inte, candiCur)
                if (len(pts) >= 1):
                    for pt in pts:
                        candiCur.append([pt])
                if (len(seg) >= 1):
                    for seg in segs:
                        candiCur.append([v for v in seg])
                        
            # Case 2.4: 如果有可以都连到上一段的，说明有问题
            else:
                pass

        # Case 3: 如果当前段与poly完全无交集，后续段也不会相交
        elif (p == None or p['status'] == 'NoCross'):
            inte, candiCur = appendCur2Inte(inte, candiCur)

    inte, candiCur = appendCur2Inte(inte, candiCur)

    if (len(inte) == 1):
        return inte[0]
    else:
        return inte

def seqLinkSeq(seq1: list[pt], seq2: list[pt]):
    """
    Given two seqs, link them together if possible, return None if they are separated

    Parameters
    ----------
    seq1: list[pt], required
        The first sequence
    seq2: list[pt], required
        The second sequence

    Return
    ------
    list[pt]
        The sequence connected both seq, or None if two seqs are separated

    """

    head1 = seq1[0]
    tail1 = seq1[-1]
    head2 = seq2[0]
    tail2 = seq2[-1]
    if (is2PtsSame(head1, head2)):
        newSeq = [seq1[len(seq1) - 1 - i] for i in range(len(seq1) - 1)]
        newSeq.extend([i for i in seq2])
        return newSeq

    elif (is2PtsSame(head1, tail2)):
        newSeq = [seq1[len(seq1) - 1 - i] for i in range(len(seq1) - 1)]
        newSeq.extend([seq2[len(seq2) - 1 - i] for i in range(len(seq2))])
        return newSeq

    elif (is2PtsSame(tail1, head2)):
        newSeq = [seq1[i] for i in range(len(seq1) - 1)]
        newSeq.extend([i for i in seq2])
        return newSeq

    elif (is2PtsSame(tail1, tail2)):
        newSeq = [seq1[i] for i in range(len(seq1) - 1)]
        newSeq.extend([seq2[len(seq2) - 1 - i] for i in range(len(seq2))])
        return newSeq

    else:
        return None

def intSeg2Poly(seg: line, poly: poly=None, polyShapely: shapely.Polygon=None, returnShaplelyObj: bool=False) -> dict | list[dict] | shapely.Point | shapely.Polygon | shapely.GeometryCollection:
    """
    The intersection of a line segment to a polygon

    Parameters
    ----------
    seg: line, required
        The first line segment
    poly: poly, optional, default as None
        The second polygon
    polyShapely: shapely.Polygon, optional, default as None
        The correspond shapely object for polygon. Need to provide one of the following fields: [`poly`, `polyShapely`]
    returnShaplelyObj: bool, optional, default as False
        True if alter the result to be a shapely object        

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """

    # WARNING: Results may not be reliable on both ends of the seg.
    # NOTE: 20231103 暂时用了一个stupid way来处理了

    # Sanity check ============================================================
    if (poly == None and polyShapely == None):
        raise MissingParameterError("ERROR: `poly` and `polyShapely` cannot be None at the same time.")

    # get shapely objects =====================================================
    segShapely = shapely.LineString([seg[0], seg[1]])
    if (polyShapely == None):
        polyShapely = shapely.Polygon(poly)
    intShape = shapely.intersection(segShapely, polyShapely)

    # If return shapely objects no processing needed ==========================
    if (returnShaplelyObj):
        return intShape

    # 若不相交，返回不相交
    # FIXME: 现在的精度可能有问题，需要计算两者间距离
    if (intShape.is_empty):
        dist = shapely.distance(segShapely, polyShapely)
        if (dist <= ERRTOL['distPt2Pt']):
            # Case 1: 若两个端点足够近
            end1Dist = distPt2Poly(seg[0], polyShapely = polyShapely)
            if (end1Dist <= ERRTOL['distPt2Poly']):
                return {
                    'status': 'Cross',
                    'intersect': seg[0],
                    'intersectType': 'Point',
                    'interiorFlag': False
                }
            end2Dist = distPt2Poly(seg[1], polyShapely = polyShapely)
            if (end2Dist <= ERRTOL['distPt2Poly']):
                return {
                    'status': 'Cross',
                    'intersect': seg[1],
                    'intersectType': 'Point',
                    'interiorFlag': False
                }
            # Case 2: 相切的情形
            for pt in poly:
                ptDist = distPt2Seg(pt, seg)
                if (ptDist <= ERRTOL['distPt2Seg']):
                    return {
                        'status': 'Cross',
                        'intersect': pt,
                        'intersectType': 'Point',
                        'interiorFlag': False
                    }
        else: 
            return {
                'status': 'NoCross',
                'intersect': None,
                'intersectType': None,
                'interiorFlag': None
            }
    elif (isinstance(intShape, shapely.Point)):
        return {
            'status': 'Cross',
            'intersect': (intShape.x, intShape.y),
            'intersectType': 'Point',
            'interiorFlag': False
        }
    elif (isinstance(intShape, shapely.LineString)):
        seg = [tuple(intShape.coords[0]), tuple(intShape.coords[1])]
        midPt = (seg[0][0] + (seg[1][0] - seg[0][0]) / 2,
                 seg[0][1] + (seg[1][1] - seg[0][1]) / 2)
        interiorFlag = shapely.contains(polyShapely, shapely.Point(midPt))
        # NOTE: 由于精度的问题，实际上是Point的情况可能会返回Segment
        if (distEuclideanXY(seg[0], seg[1]) <= ERRTOL['distPt2Pt']):
            return {
                'status': 'Cross',
                'intersect': seg[0],
                'intersectType': 'Point',
                'interiorFlag': interiorFlag
            }
        else:
            return {
                'status': 'Cross',
                'intersect': seg,
                'intersectType': 'Segment',
                'interiorFlag': interiorFlag
            }
    else:
        intSp = []
        for obj in intShape.geoms:
            if (isinstance(obj, shapely.Point)):
                intSp.append({
                    'status': 'Cross',
                    'intersect': (obj.x, obj.y),
                    'intersectType': 'Point',
                    'interiorFlag': False
                })
            elif (isinstance(obj, shapely.LineString)):
                seg = [tuple(obj.coords[0]), tuple(obj.coords[1])]
                midPt = (seg[0][0] + (seg[1][0] - seg[0][0]) / 2,
                         seg[0][1] + (seg[1][1] - seg[0][1]) / 2)
                interiorFlag = shapely.contains(polyShapely, shapely.Point(midPt))
                # NOTE: 由于精度的问题，实际上是Point的情况可能会返回Segment
                if (distEuclideanXY(seg[0], seg[1]) <= ERRTOL['distPt2Pt']):
                    intSp.append({
                        'status': 'Cross',
                        'intersect': seg[0],
                        'intersectType': 'Point',
                        'interiorFlag': interiorFlag
                    })
                else:
                    intSp.append({
                        'status': 'Cross',
                        'intersect': seg,
                        'intersectType': 'Segment',
                        'interiorFlag': interiorFlag
                    })

        return intSp

def intRay2Poly(ray: line, poly: poly=None, polyShapely: shapely.Polygon=None, returnShaplelyObj: bool=False) -> dict | list[dict] | shapely.Point | shapely.Polygon | shapely.GeometryCollection:
    """
    The intersection of a ray to a polygon

    Parameters
    ----------
    ray: line, required
        The first ray
    poly: poly, optional, default as None
        The second polygon
    polyShapely: shapely.Polygon, optional, default as None
        The correspond shapely object for polygon. Need to provide one of the following fields: [`poly`, `polyShapely`]
    returnShaplelyObj: bool, optional, default as False
        True if alter the result to be a shapely object        

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """

    # Sanity check
    if (poly == None and polyShapely == None):
        raise MissingParameterError("ERROR: `poly` and `polyShapely` cannot be None at the same time.")

    # Project points to the line
    projPts = []    
    for pt in poly:
        projPts.append(ptFoot2Line(pt, ray))

    projPts.sort()
    minPt = projPts[0]
    maxPt = projPts[-1]
    
    isMinPtOnRay = isPtOnRay(minPt, ray)
    isMaxPtOnRay = isPtOnRay(maxPt, ray)
    # 若minPt和maxPt均不能投影到射线上，肯定不相交
    if (not isMinPtOnRay and not isMaxPtOnRay):
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }
    # 若两个都在射线上，射线可能的与之相交部分在两点间
    elif (isMinPtOnRay and isMaxPtOnRay):
        seg = [minPt, maxPt]
        return intSeg2Poly(seg, poly, polyShapely, returnShaplelyObj)
    # 若minPt在射线上，maxPt不在
    elif (isMinPtOnRay):
        seg = [ray[0], minPt]
        return intSeg2Poly(seg, poly, polyShapely, returnShaplelyObj)
    # 若maxPt在射线上，minPt不在
    else:
        seg = [ray[0], maxPt]
        return intSeg2Poly(seg, poly, polyShapely, returnShaplelyObj)

def intSeg2Circle(seg: line, circle: dict, detailFlag: bool = True):
    # 先判断会不会相交
    distCenter2Seg = distPt2Seg(pt = circle['center'], seg = seg, detailFlag = True)

    if (distCenter2Seg['dist'] >= circle['radius'] + ERRTOL['distPt2Seg']):
        if (detailFlag):
            return {
                'status': 'NoCross',
                'intersect': None,
                'intersectType': None,
                'interiorFlag': None,
                'mileage': None
            }
        else:
            return None

    if (circle['radius'] + ERRTOL['distPt2Seg'] >= distCenter2Seg['dist'] >= circle['radius'] - ERRTOL['distPt2Seg']):
        if (detailFlag == True):
            return {
                'status': 'Cross',
                'intersect': distCenter2Seg['proj'],
                'intersectType': 'Point',
                'interiorFlag': False,
                'mileage': distEuclideanXY(seg[0], distCenter2Seg['proj'])
            }
        else:
            return distCenter2Seg['proj']

    # 分别看看两个端点是不是在圆内部
    insideAFlag = distEuclideanXY(seg[0], circle['center']) < circle['radius']
    insideBFlag = distEuclideanXY(seg[1], circle['center']) < circle['radius']
    L = distEuclideanXY(seg[0], seg[1])

    # Case 1: 俩端点都在里头，返回整条线段
    # NOTE: 快速计算，不用麻烦
    if (insideAFlag and insideBFlag):
        return {
            'status': 'Cross',
            'intersect': seg,
            'intersectType': 'Segment',
            'interiorFlag': True,
            'mileage': [0, L]
        }

    # Case 2, 3, 4 则是计算 \lambda
    x1, y1 = seg[0]
    x2, y2 = seg[1]
    a, b = circle['center']
    r = circle['radius']

    A = (x2 - x1) ** 2 + (y2 - y1) ** 2
    B = 2 * (x1 - a) * (x2 - x1) + 2 * (y1 - b) * (y2 - y1)
    C = (x1 - a) ** 2 + (y1 - b) ** 2 - r ** 2

    sqDelta = math.sqrt(B ** 2 - 4 * A * C)
    lambda1 = (- B - sqDelta) / (2 * A)
    lambda2 = (- B + sqDelta) / (2 * A)

    pt1 = [x1 + lambda1 * (x2 - x1), y1 + lambda1 * (y2 - y1)]
    pt2 = [x1 + lambda2 * (x2 - x1), y1 + lambda2 * (y2 - y1)]

    L1 = L * lambda1
    L2 = L * lambda2

    # Case 2: A在内部，B不在内部，找到线段上唯一一个圆与线段的交点
    if (insideAFlag and not insideBFlag):
        if (detailFlag):
            return {
                'status': 'Cross',
                'intersect': [seg[0], pt2],
                'intersectType': 'Segment',
                'interiorFlag': True,
                'mileage': [0, L2]
            }
        else:
            return [seg[0], pt2]
    # Case 3: A不在内部，B在内部，找到线段上唯一一个圆与线段的交点
    elif (not insideAFlag and insideBFlag):
        if (detailFlag):
            return {
                'status': 'Cross',
                'intersect': [pt1, seg[1]],
                'intersectType': 'Segment',
                'interiorFlag': True,
                'mileage': [L1, L]
            }
        else:
            return [pt1, seg[1]]
    else:
        if (detailFlag):
            return {
                'status': 'Cross',
                'intersect': [pt1, pt2],
                'intersectType': 'Segment',
                'interiorFlag': True,
                'mileage': [L1, L2]
            }
        else:
            return [pt1, pt2]

# Line-shape versus polygon ===================================================
def isLineIntPoly(line: line, poly: poly=None, polyShapely: shapely.Polygon=None, interiorOnly: bool=False) -> bool:
    """
    Is a line intersects to a polygon?

    Parameters
    ----------
    line: line, required
        The first line
    poly: poly, optional, default as None
        The second polygon
    polyShapely: shapely.Polygon, optional, default as None
        The correspond shapely object for polygon. Need to provide one of the following fields: [`poly`, `polyShapely`]
    returnShaplelyObj: bool, optional, default as False
        True if alter the result to be a shapely object        

    Return
    ------
    bool
        True if intersects
    """
    intSp = intLine2Poly(line, poly, polyShapely)
    # 若只输出了一个字典，按字典判断
    if (isinstance(intSp, dict)):
        return (intSp['status'] == 'Cross' 
            and not (interiorOnly and not intSp['interiorFlag']))
    elif (isinstance(intSp, list)):
        for intPt in intSp:
            trueWhen = (intPt['status'] == 'Cross' 
                and not (interiorOnly and not intPt['interiorFlag']))
            if (trueWhen):
                return True    
        return False

def isSegIntPoly(seg: line, poly: poly, interiorOnly: bool=False) -> bool:
    """
    Is a line segment intersects to a polygon?

    Parameters
    ----------
    seg: line, required
        The first line
    poly: poly, optional, default as None
        The second polygon
    polyShapely: shapely.Polygon, optional, default as None
        The correspond shapely object for polygon. Need to provide one of the following fields: [`poly`, `polyShapely`]
    returnShaplelyObj: bool, optional, default as False
        True if alter the result to be a shapely object        

    Return
    ------
    bool
        True if intersects
    """

    # WARNING: results may not be reliable if `interiorFlag` == False.
    
    """Is a segment intersect with a polygon"""

    # Step 1: Check if the segment is intersect with any edge of polygon
    for i in range(-1, len(poly) - 1):
        edge = [poly[i], poly[i + 1]]
        if (isSegIntSeg(seg, edge, interiorOnly)):
            return True
    # Step 2: If no edge is intersect with seg, see if any end is inside
    # NOTE: 只要看seg[0]就行了
    if (isPtInPoly(ptMid(seg), poly, interiorOnly)):
        return True
    return False

def isRayIntPoly(ray: line, poly: poly=None, polyShapely: shapely.Polygon=None, interiorOnly: bool=False) -> bool:
    """
    Is a ray intersects to a polygon?

    Parameters
    ----------
    ray: line, required
        The first line
    poly: poly, optional, default as None
        The second polygon
    polyShapely: shapely.Polygon, optional, default as None
        The correspond shapely object for polygon. Need to provide one of the following fields: [`poly`, `polyShapely`]
    returnShaplelyObj: bool, optional, default as False
        True if alter the result to be a shapely object        

    Return
    ------
    bool
        True if intersects
    """

    intSp = intRay2Poly(ray, poly, polyShapely)
    # 若只输出了一个字典，按字典判断
    if (isinstance(intSp, dict)):
        return (intSp['status'] == 'Cross' 
            and not (interiorOnly and not intSp['interiorFlag']))
    elif (isinstance(intSp, list)):
        for intPt in intSp:
            trueWhen = (intPt['status'] == 'Cross' 
                and not (interiorOnly and not intPt['interiorFlag']))
            if (trueWhen):
                return True    
        return False

def isSeqIntPoly(seq: list[pt], poly: poly, interiorOnly: bool=False):
    for i in range(len(seq) - 1):
        edge = [seq[i], seq[i + 1]]
        if (isSegIntPoly(edge, poly, interiorOnly)):
            return True
    return False

# Poly vs poly ================================================================
def intPoly2Poly(poly1: poly=None, poly2: poly=None, poly1Shapely: shapely.Polygon=None, poly2Shapely: shapely.Polygon=None):
    """
    Intersection between two polygons

    Parameters
    ----------
    poly1: poly, optional, default as None
        The first polygon
    poly2: poly, optional, default as None
        The second polygon
    poly1Shapely: shapely.Polygon, optional, default as None
        The correspond shapely object for the first polygon. Need to provide one of the following fields: [`poly1`, `poly1Shapely`]
    poly2Shapely: shapely.Polygon, optional, default as None
        The correspond shapely object for the second polygon. Need to provide one of the following fields: [`poly2`, `poly2Shapely`]

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """

    if (poly1Shapely == None):
        poly1Shapely = shapely.Polygon([p for p in poly1])
    if (poly2Shapely == None):
        poly2Shapely = shapely.Polygon([p for p in poly2])

    intShape = shapely.intersection(poly1Shapely, poly2Shapely)
    intType = shapely.get_type_id(intShape)

    # Point
    if (intType == 0):
        return {
            'status': 'Cross',
            'intersect': (intShape.x, intShape.y),
            'intersectType': 'Point',
            'interiorFlag': False
        }
    # LineString
    elif (intType == 1):
        return {
            'status': 'Cross',
            'intersect': [intShape.coords[0], intShape.coords[1]],
            'intersectType': 'Segment',
            'interiorFlag': False
        }
    # Polygon
    elif (intType == 3 and not intShape.is_empty):
        return {
            'status': 'Cross',
            'intersect': [i for i in mapping(intShape)['coordinates'][0]],
            'intersectType': 'Polygon',
            'interiorFlag': True
        }
    # MultiPoint/MultiLineString/MultiPolygon/GeometryCollection
    elif (intType in [4, 5, 6, 7]):
        intSp = []
        for g in intShape.geoms:
            intG = shapely.get_type_id(g)
            # Point
            if (intG == 0):
                intSp.append({
                    'status': 'Cross',
                    'intersect': (g.x, g.y),
                    'intersectType': 'Point',
                    'interiorFlag': False
                })
            # LineString
            elif (intG == 1):
                intSp.append({
                    'status': 'Cross',
                    'intersect': [g.coords[0], g.coords[1]],
                    'intersectType': 'Segment',
                    'interiorFlag': False
                })
            # Polygon
            elif (intG == 3):
                intSp.append({
                    'status': 'Cross',
                    'intersect': [i for i in mapping(g)['coordinates'][0]],
                    'intersectType': 'Polygon',
                    'interiorFlag': True
                })
        return intSp
    else:
        return {
            'status': 'NoCross',
            'intersect': None,
            'intersectType': None,
            'interiorFlag': None
        }

def isPolyIntPoly(poly1: poly=None, poly2: poly=None, poly1Shapely: shapely.Polygon=None, poly2Shapely: shapely.Polygon=None, interiorOnly: bool=False) -> bool:
    """
    Is a polygon intersect to another polygon

    Parameters
    ----------
    poly1: poly, optional, default as None
        The first polygon
    poly2: poly, optional, default as None
        The second polygon
    poly1Shapely: shapely.Polygon, optional, default as None
        The correspond shapely object for the first polygon. Need to provide one of the following fields: [`poly1`, `poly1Shapely`]
    poly2Shapely: shapely.Polygon, optional, default as None
        The correspond shapely object for the second polygon. Need to provide one of the following fields: [`poly2`, `poly2Shapely`]

    Return
    ------
    dict
        >>> {
        ...     'status': 'Cross', # Relations between two objects,
        ...     'intersect': pt, # The intersection,
        ...     'intersectType': 'Point', # Type of intersection
        ...     'interiorFlag': False, # True if the intersection is at the boundary
        ... }
    """

    intSp = intPoly2Poly(poly1, poly2, poly1Shapely, poly2Shapely)
    # 若只输出了一个字典，按字典判断
    if (isinstance(intSp, dict)):
        return (intSp['status'] == 'Cross' 
            and not (interiorOnly and not intSp['interiorFlag']))
    elif (isinstance(intSp, list)):
        for intPt in intSp:
            trueWhen = (intPt['status'] == 'Cross' 
                and not (interiorOnly and not intPt['interiorFlag']))
            if (trueWhen):
                return True    
        return False

def isPolyLegal(poly: poly):
    for i in range(-1, len(poly) - 1):
        for j in range(-1, len(poly) - 1):
            if (i != j):
                segI = [poly[i], poly[i + 1]]
                segJ = [poly[j], poly[j + 1]]
                if (isSegIntSeg(segI, segJ, interiorOnly=True)):
                    return False
    return True

def isPolyConvex(poly: poly):
    if len(poly) < 3:
        return False  # 至少需要3个顶点才能构成多边形        
    def cross_sign(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])    
    n = len(poly)
    if n == 3:
        return True
    sign = 0
    for i in range(n):
        o = poly[i]
        a = poly[(i + 1) % n]
        b = poly[(i + 2) % n]        
        curr_sign = cross_sign(o, a, b)        
        if curr_sign != 0:
            if sign == 0:
                sign = curr_sign
            elif sign * curr_sign < 0:
                return False    
    return True

def isCircleIntCircle(circle1: dict, circle2: dict):
    D = distEuclideanXY(circle1['center'], circle2['center'])
    R1 = circle1['radius']
    R2 = circle2['radius']
    # Case 1: D > R1 + R2
    if (D > R1 + R2):
        return False

    # Case 2: abs(R1 - R2) <= D <= R1 + R2
    if (abs(R1 - R2) <= D <= R1 + R2):
        return True

    # Case 3: abs(R1 - R2) > D
    if (abs(R1 - R2) > D):
        return False

# Distance from Point to Object ===============================================
def distPt2Line(pt: pt, line: line) -> float:
    """
    The distance between a point and a line

    Parameters
    ----------
    pt: pt, required
        The point
    line: line, required
        The line

    Return
    ------
    float
        The distance between two objects

    """

    area = calTriangleAreaXY(pt, line[0], line[1])
    a = distEuclideanXY(line[0], line[1])
    h = 2 * area / a
    return h

def distPt2Seg(pt: pt, seg: line, detailFlag: bool = False) -> float:
    # r = (A->P A->B) / (|AB|^2)
    AP = [pt[0] - seg[0][0], pt[1] - seg[0][1]]
    AB = [seg[1][0] - seg[0][0], seg[1][1] - seg[0][1]]
    r = vecDocProduct(AP, AB) / (AB[0] ** 2 + AB[1] ** 2)

    dist = None
    if (r <= 0):
        dist = distEuclideanXY(seg[0], pt)
    elif (r >= 1):
        dist = distEuclideanXY(seg[1], pt)
    else:
        l = distEuclideanXY(seg[0], seg[1])
        S = calTriangleAreaXY(seg[0], seg[1], pt)
        dist = 2 * S / l

    if (detailFlag == False):
        return dist
    else:
        if (r <= 0):
            return {
                'dist': dist,
                'proj': seg[0],
                'location': 'prev'
            }
        elif (r >= 1):
            return {
                'dist': dist,
                'proj': seg[1],
                'location': 'next'
            }
        else:
            foot = ptFoot2Line(pt, seg)
            return {
                'dist': dist,
                'proj': foot,
                'location': 'inner'
            }

def distPt2Ray(pt: pt, ray: line, detailFlag: bool = False) -> float:
    """
    The distance between a point and a ray

    Parameters
    ----------
    pt: pt, required
        The point
    ray: line, required
        The ray

    Return
    ------
    float
        The distance between two objects

    """

    foot = ptFoot2Line(pt, ray)
    closest = None
    d = None
    if (isPtOnRay(foot)):
        d = distEuclideanXY(pt, foot)
        closest = foot
    else:
        d = distEuclideanXY(pt, ray[0])
        closest = ray[0]

    if (detailFlag):
        return {
            'dist': d,
            'proj': closest
        }
    else:
        return d

def distPt2Seq(pt: pt, seq: list[pt], closedFlag: bool = False, detailFlag: bool = False) -> float:
    """
    The distance between a point and a sequence of points

    Parameters
    ----------
    pt: pt, required
        The point
    seq: list of pt, required
        A sequence of points
    closedFlag: bool, optional, default False
        True if the sequence is closed

    Return
    ------
    float
        The distance between two objects

    """

    if (len(seq) == 2):
        res = distPt2Seg(pt, seq, detailFlag)
        if (detailFlag):            
            return {
                'dist': res['dist'],
                'proj': res['proj'],
                'nearestSeg': seq,
                'nearestIdx': [0, 1]
            }
        else:
            return res

    # 初始化一个距离
    d = distEuclideanXY(pt, seq[0])
    nearestSeg = [seq[0], seq[1]]
    nearestIdx = [0, 1]
    proj = seq[0]

    # 逐段计算最短路径，如果最短路径可以更新，则更新外接正方形
    for i in range(len(seq) - 1):
        furtherTestFlag = True
        # 快速筛选
        # 1. 如果在外接正方形上方，pass
        if (seq[i][1] >= pt[1] + d and seq[i + 1][1] >= pt[1] + d):
            furtherTestFlag = False
        # 2. 如果在外接正方形下方，pass
        if (furtherTestFlag and seq[i][1] <= pt[1] - d and seq[i + 1][1] <= pt[1] - d):
            furtherTestFlag = False
        # 3. 如果在外接正方形左方，pass
        if (furtherTestFlag and seq[i][0] <= pt[0] - d and seq[i + 1][0] <= pt[0] - d):
            furtherTestFlag = False
        # 4. 如果在外界正方形右方，pass
        if (furtherTestFlag and seq[i][0] >= pt[0] + d and seq[i + 1][0] >= pt[0] + d):
            furtherTestFlag = False
        # NOTE: 还有几种显然可以排除的情形，留待后续
        # 5. 如果不能快速排除，计算距离
        if (furtherTestFlag):
            res = distPt2Seg(pt, [seq[i], seq[i + 1]], detailFlag)
            if (detailFlag):
                if (res['dist'] < d):
                    d = res['dist']
                    proj = res['proj']
                    nearestSeg = [seq[i], seq[i + 1]]
                    nearestIdx = [i, i + 1]
            else:
                if (res < d):
                    d = res
    if (detailFlag):
        return {
            'dist': d,
            'proj': proj,
            'nearestSeg': nearestSeg,
            'nearestIdx': nearestIdx
        }
    else:
        return d

def distPt2Poly(pt: pt, poly: poly=None, polyShapely: shapely.Polygon=None) -> float:
    """
    The distance between a point and a polygon

    Parameters
    ----------
    pt: pt, required
        The point
    poly: poly, optional, default as None
        The polygon
    polyShapely: shapely.Polygon, optional, default as None
        The correspond shapely object for polygon. Need to provide one of the following fields: [`poly`, `polyShapely`]

    Return
    ------
    float
        The distance between two objects

    """

    if (poly == None and polyShapely == None):
        raise MissingParameterError("ERROR: Missing required field `poly` or `polyShapely`")

    if (polyShapely == None):
        polyShapely = shapely.Polygon([p for p in poly])
    ptShapely = shapely.Point(pt)
    return shapely.distance(ptShapely, polyShapely)

def distPoly2Poly(poly1: poly=None, poly2: poly=None, poly1Shapely: shapely.Polygon=None, poly2Shapely: shapely.Polygon=None) -> float:
    """
    The distance between two polys

    Parameters
    ----------
    poly1: poly, optional, default as None
        The first polygon
    poly1Shapely: shapely.Polygon, optional, default as None
        The correspond shapely object for the first polygon. Need to provide one of the following fields: [`poly1`, `poly1Shapely`]
    poly2: poly, optional, default as None
        The second polygon
    poly2Shapely: shapely.Polygon, optional, default as None
        The correspond shapely object for the second polygon. Need to provide one of the following fields: [`poly2`, `poly2Shapely`]

    Return
    ------
    float
        The distance between two objects

    """

    if (poly1 == None and poly1Shapely == None):
        raise MissingParameterError("ERROR: Missing required field `poly1` or `poly1Shapely`")
    if (poly2 == None and poly2Shapely == None):
        raise MissingParameterError("ERROR: Missing required field `poly2` or `poly2Shapely`")

    if (poly1Shapely == None):
        poly1Shapely = shapely.Polygon([p for p in poly1])
    if (poly2Shapely == None):
        poly2Shapely = shapely.Polygon([p for p in poly2])
    return shapely.distance(poly1Shapely, poly2Shapely)

def distPoly2Seq(poly: poly, seq: list[pt], closedFlag: bool = False, detailFlag: bool = False) -> float: 

    # 先实现再优化
    distPerPt = []
    for i in range(len(poly)):
        distPerPt.append(distPt2Seq(pt = poly[i], seq = seq, closedFlag = closedFlag, detailFlag = detailFlag))

    shortest = None
    if (not detailFlag):
        return min(distPerPt)

    return

# Nearest to object ===========================================================
def nearestPtLine2Poly(line: line, poly: poly=None, polyShapely: shapely.Polygon=None) -> dict:
    """
    Find the nearest point between a line and a polygon

    Parameters
    ----------
    line: line, required
        The line
    poly: poly, optional, default as None
        The polygon
    polyShapely: shapely.Polygon, optional, default as None
        The correspond shapely object for polygon. Need to provide one of the following fields: [`poly`, `polyShapely`]

    Return
    ------
    dict
        >>> {
        ...     'ptOnLine': pt, # The point from the line,
        ...     'ptOnPoly': pt, # The point from the polygon,
        ... }

    """

    if (poly == None and polyShapely == None):
        raise MissingParameterError("ERROR: Missing required field `poly` or `polyShapely`")

    if (polyShapely == None):
        polyShapely = shapely.Polygon([p for p in poly])
    lineShapely = shapely.LineString(line)
    nearestPts = nearest_points(lineShapely, polyShapely)
    
    return {
        'ptOnLine': (nearestPts[0].x, nearestPts[0].y),
        'ptOnPoly': (nearestPts[1].x, nearestPts[1].y),
    }

# Dimension mapping ===========================================================
def vecPolar2XY(vecPolar) -> pt:

    """Given vector's norm and its degree to North, convert it into a 2-tuple vector

    Parameters
    ----------
    vecPolar: tuple[float|int, float|int], required
        A 2-tuple (vVal, vDeg), `vVal` is the norm and `vDeg` is the direction, 0 as North, clockwise, in [0, 360)

    Returns
    -------
    tuple[float|int, float|int]
        The XY vector
    """

    # Initialize ==============================================================
    (vVal, vDeg) = vecPolar

    vX = 0
    vY = 0

    while(vDeg < 0):
        vDeg = vDeg + 360

    while(vDeg >= 360):
        vDeg = vDeg - 360

    vX = vVal * math.sin(math.radians(vDeg))
    vY = vVal * math.cos(math.radians(vDeg))

    return (vX, vY)

def vecXY2Polar(vecXY: pt):

    """Given a 2-tuple, convert it into a norm and a direction in degree

    Parameters
    ----------
    vecXY: tuple[float|int, float|int], required
        A 2-tuple (vX, vY), the coordinate of vector

    Returns
    -------
    tuple[float|int, float|int]
        The polar vector
    """    

    (vX, vY) = vecXY    
    vDeg = 0
    vVal = 0
    if (abs(vY) <= ERRTOL['vertical']):
        if (vX >= 0):
            vVal = vX
            vDeg = 90
        elif (vX < 0):
            vVal = -vX
            vDeg = 270
    else:
        vVal = math.sqrt(vX**2 + vY**2)
        # 1st quad
        if (vX >= 0 and vY >= 0):
            vDeg = math.degrees(math.atan(vX / vY))
        # 2nd quad
        elif (vX >= 0 and vY < 0):
            vDeg = 180 + math.degrees(math.atan(vX / vY))
        # 3rd quad
        elif (vX < 0 and vY < 0):
            vDeg = 180 + math.degrees(math.atan(vX / vY))
        # 4th quad
        elif (vX < 0 and vY >= 0):
            vDeg = 360 + math.degrees(math.atan(vX / vY))

    return (vVal, vDeg)

def vecDocProduct(vec1, vec2):
    return vec1[0] * vec2[0] + vec1[1] * vec2[1]

def vecFromSeg(seg, normalizeFlag: bool = False):
    if (normalizeFlag == True):
        L = distEuclideanXY(seg[0], seg[1])
        vec = ((seg[1][0] - seg[0][0]) / L, (seg[1][1] - seg[0][1]) / L)
    else:
        vec = ((seg[1][0] - seg[0][0]), (seg[1][1] - seg[0][1]))
    return vec

def polarAdd(vecPolar1, vecPolar2):
    # Change to 2-tuple vector ================================================
    (v1X, v1Y) = vecPolar2XY(vecPolar1)
    (v2X, v2Y) = vecPolar2XY(vecPolar2)

    # Get v3 ==================================================================
    (v3X, v3Y) = (v1X + v2X, v1Y + v2Y)

    # Get vector norm and direction ===========================================
    (v3Val, v3Deg) = vecXY2Polar((v3X, v3Y))

    return (v3Val, v3Deg)

def polarSubtract(vecPolar1, vecPolar2):
    # Change to 2-tuple vector ================================================
    (v1X, v1Y) = vecPolar2XY(vecPolar1)
    (v2X, v2Y) = vecPolar2XY(vecPolar2)

    # Get v3 ==================================================================
    (v3X, v3Y) = (v1X - v2X, v1Y - v2Y)

    # Get vector norm and direction ===========================================
    v3Val, v3Deg = vecXY2Polar((v3X, v3Y))

    return (v3Val, v3Deg)

# Mercator projection =========================================================
def ptXY2LatLonMercator(ptXY: pt) -> pt:
    """
    Given a point in (x, y), map it to a (lat, lon) coordinate using Mercator projection

    Parameters
    ----------
    ptXY: pt, required
        The coordinate in (x, y)

    Return
    ------
    tuple
        The coordinate in (lat, lon)

    """

    # Ref: https://wiki.openstreetmap.org/wiki/Mercator#Python
    (x, y) = ptXY
    lon = math.degrees(y / CONST_EARTH_RADIUS_METERS)
    lat = math.degrees(2 * math.atan(math.exp(x / CONST_EARTH_RADIUS_METERS)) - math.pi / 2.0)
    ptLatLon = (lat, lon)
    return ptLatLon

def ptLatLon2XYMercator(ptLatLon: pt) -> pt:
    """
    Given a point in (lat, lon), map it to a (x, y) coordinate using Mercator projection

    Parameters
    ----------
    ptLatLon: pt, required
        The coordinate in (lat, lon)

    Return
    ------
    tuple
        The coordinate in (x, y)

    """

    # Ref: https://wiki.openstreetmap.org/wiki/Mercator#Python
    (lat, lon) = ptLatLon
    y = math.radians(lon) * CONST_EARTH_RADIUS_METERS
    x = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * CONST_EARTH_RADIUS_METERS
    ptXY = (x, y)
    return ptXY

def polyXY2LatLonMercator(polyXY: poly) -> poly:
    polyLatLon = []
    for pt in polyXY:
        ptLatLon = ptXY2LatLonMercator(pt)
        polyLatLon.append(ptLatLon)
    return polyLatLon

def polyLatLon2XYMercator(polyLatLon: poly) -> poly:
    polyXY = []
    for pt in polyLatLon:
        ptXY = ptLatLon2XYMercator(pt)
        polyXY.append(ptXY)
    return polyXY

# Get pt ======================================================================
def ptFoot2Line(pt: pt, line: line) -> pt:
    """
    Given a point and a line, return the foot of that point on the line

    Parameters
    ----------
    pt: pt, required
        The point where the foot will go through
    line: line Required
        The line which the foot is perpendicular to

    Return
    ------
    pt
        The foot of that point on the line

    """
    if (isPtOnLine(pt, line)):
        return tuple(pt)
    else:
        ray = rayPerp2Line(pt, line)
        return ray[1]

def ptInSeqMileage(seq: list[pt], dist: int|float, dimension: str = 'XY') -> pt:
    """Given a list of lat/lon coordinates, and a traveling mileage, returns the coordinate"""
    # Initialize ==============================================================
    inPathFlag = False
    accDist = 0
    prePt = []
    nextPt = []
    # Find segment ============================================================
    for i in range(0, len(seq) - 1):
        if (dimension == 'LatLon'):
            accDist += distLatLon(seq[i], seq[i + 1])
        elif (dimension == 'XY'):
            accDist += distEuclideanXY(seq[i], seq[i + 1])
        if (accDist > dist):
            prePt = seq[i]
            nextPt = seq[i + 1]
            inPathFlag = True
            break
    if (inPathFlag == False):
        raise RuntimeError("ERROR: `dist` is longer than the length of `seq`")
    # Find location on the segment ============================================
    remainDist = accDist - dist
    segDist = 0
    if (dimension == 'LatLon'):
        segDist = distLatLon(prePt, nextPt)
    elif (dimension == 'XY'):
        segDist = distEuclideanXY(prePt, nextPt)
    if (segDist <= ERRTOL['distPt2Pt']):
        raise ZeroDivisionError
    x = nextPt[0] + (remainDist / segDist) * (prePt[0] - nextPt[0])
    y = nextPt[1] + (remainDist / segDist) * (prePt[1] - nextPt[1])
    return (x, y)

def mileageInPath(pt: pt, path: list[pt]):
    acc = 0
    for i in range(len(path) - 1):
        if (isPtOnSeg(pt, [path[i], path[i + 1]])):
            acc += distEuclideanXY(path[i], pt)
            break
        else:
            acc += distEuclideanXY(path[i], path[i - 1])
    return acc

def ptMid(seg) -> pt:
    return [
        (seg[0][0] + (seg[1][0] - seg[0][0]) / 2), 
        (seg[0][1] + (seg[1][1] - seg[0][1]) / 2)
    ]

def ptPolyCenter(poly: poly=None, polyShapely: shapely.Polygon=None) -> pt:
    """
    Given a poly, returns the centroid of the poly

    Parameters
    ----------
    poly: poly, optional, default as None
        The polygon
    polyShapely: shapely.Polygon, optional, default as None
        The correspond shapely object for polygon. Need to provide one of the following fields: [`poly`, `polyShapely`]

    Returns
    -------
    pt
        The centroid

    """

    if (poly == None and polyShapely == None):
        raise MissingParameterError("ERROR: Missing required field 'poly' or 'polyShapely'.")
    if (polyShapely == None):
        polyShapely = shapely.Polygon(poly)

    ptShapely = shapely.centroid(polyShapely)
    center = (ptShapely.x, ptShapely.y)
    return center

def minBoundingRect(poly):
    # NOTE: The following codes are copied from
    # https://github.com/dbworth/minimum-area-bounding-rectangle/blob/master/python/min_bounding_rect.py

    hull_points_2d = np.array(poly)

    # Compute edges (x2-x1,y2-y1)
    edges = np.zeros((len(hull_points_2d)-1,2)) # empty 2 column array
    for i in range(len(edges)):
        edge_x = hull_points_2d[i+1,0] - hull_points_2d[i,0]
        edge_y = hull_points_2d[i+1,1] - hull_points_2d[i,1]
        edges[i] = [edge_x,edge_y]

    # Calculate edge angles   atan2(y/x)
    edge_angles = np.zeros((len(edges))) # empty 1 column array
    for i in range(len(edge_angles)):
        edge_angles[i] = math.atan2(edges[i,1], edges[i,0])

    # Check for angles in 1st quadrant
    for i in range(len(edge_angles)):
        edge_angles[i] = abs(edge_angles[i] % (math.pi/2)) # want strictly positive answers

    # Remove duplicate angles
    edge_angles = np.unique(edge_angles)

    # Test each angle to find bounding box with smallest area
    min_bbox = (0, sys.maxsize, 0, 0, 0, 0, 0, 0) # rot_angle, area, width, height, min_x, max_x, min_y, max_y
    for i in range(len(edge_angles)):
        # Create rotation matrix to shift points to baseline
        # R = [cos(theta)      , cos(theta-PI/2)
        #       cos(theta+PI/2) , cos(theta)    ]
        R = np.array([[math.cos(edge_angles[i]), math.cos(edge_angles[i]-(math.pi/2))], [math.cos(edge_angles[i]+(math.pi/2)), math.cos(edge_angles[i])]])

        # Apply this rotation to convex hull points
        rot_points = np.dot(R, np.transpose(hull_points_2d)) # 2x2 * 2xn

        # Find min/max x,y points
        min_x = np.nanmin(rot_points[0], axis=0)
        max_x = np.nanmax(rot_points[0], axis=0)
        min_y = np.nanmin(rot_points[1], axis=0)
        max_y = np.nanmax(rot_points[1], axis=0)

        # Calculate height/width/area of this bounding rectangle
        width = max_x - min_x
        height = max_y - min_y
        area = width*height

        # Store the smallest rect found first (a simple convex hull might have 2 answers with same area)
        if (area < min_bbox[1]):
            min_bbox = (edge_angles[i], area, width, height, min_x, max_x, min_y, max_y)

    # Re-create rotation matrix for smallest rect
    angle = min_bbox[0]   
    R = np.array([[math.cos(angle), math.cos(angle-(math.pi/2))], [math.cos(angle+(math.pi/2)), math.cos(angle)]])

    # Project convex hull points onto rotated frame
    proj_points = np.dot(R, np.transpose(hull_points_2d)) # 2x2 * 2xn

    # min/max x,y points are against baseline
    min_x = min_bbox[4]
    max_x = min_bbox[5]
    min_y = min_bbox[6]
    max_y = min_bbox[7]

    # Calculate corner points and project onto rotated frame
    corner_points = [
        list(np.dot([max_x, min_y], R)),
        list(np.dot([min_x, min_y], R)),
        list(np.dot([min_x, max_y], R)),
        list(np.dot([max_x, max_y], R)),
    ]
    return corner_points

# Vectors =====================================================================
def rndVec(norm: float = 1):
    deg = random.random() * 360
    vec = ptInDistXY((0, 0), deg, norm)
    return vec

# Polys =======================================================================
def polysUnion(polys:polys=None, polysShapely:list[shapely.Polygon]=None, returnShaplelyObj:bool=False) -> list:
    """
    Given a list of polygons which could be intersecting to each other, return unioned polygons that are not intersecting

    Parameters
    ----------
    polys: poly, optional, default as None
        A list of polygons
    polysShapely: shapely.Polygon, optional, default as None
        The correspond shapely objects for polygons. Need to provide one of the following fields: [`polys`, `polysShapely`]
    returnShaplelyObj: bool, optional, default as False
        True if alter the result to be a shapely object

    Return
    ------
    list of polys
        A list of polygons
    """
    if (polys == None and polysShapely == None):
        raise MissingParameterError("ERROR: Missing required field 'polys' or 'polysShapely'.")
    if (polysShapely == None):
        polysShapely = []
        for p in polys:
            polysShapely.append(shapely.Polygon(p))
    unionAll = shapely.union_all(polysShapely)
    if (returnShaplelyObj):
        return unionAll

    unionPolys = []
    if (isinstance(unionAll, shapely.geometry.polygon.Polygon)):
        unionPolys = [[[i[0], i[1]] for i in list(unionAll.exterior.coords)]]
    elif (isinstance(unionAll, shapely.geometry.multipolygon.MultiPolygon)):
        for p in unionAll.geoms:
            unionPolys.append([[i[0], i[1]] for i in list(p.exterior.coords)])
    for k in range(len(unionPolys)):
        unionPolys[k] = [unionPolys[k][i] for i in range(len(unionPolys[k])) if distEuclideanXY(unionPolys[k][i], unionPolys[k][i - 1]) > ERRTOL['distPt2Pt']]
        if (distEuclideanXY(unionPolys[k][0], unionPolys[k][-1]) <= ERRTOL['distPt2Pt']):
            unionPolys[k] = unionPolys[k][:-1]
    return unionPolys

def polysSubtract(polys:polys=None, polysShapely:list[shapely.Polygon]=None, subPolys:polys=None, subPolysShapely: list[shapely.Polygon]=None, returnShaplelyObj:bool=False) -> list:
    """
    Given a list of polygons, subtract a list of polygon from the first list of polygons

    Parameters
    ----------
    polys: poly, optional, default as None
        A list of polygons
    polysShapely: shapely.Polygon, optional, default as None
        The correspond shapely objects for polygons. Need to provide one of the following fields: [`polys`, `polysShapely`]
    subPolys: poly, optional, default as None
        A list of polygons to substract
    subPolysShapely: shapely.Polygon, optional, default as None
        The correspond shapely objects for polygons. Need to provide one of the following fields: [`subPolys`, `subPolysShapely`]    

    returnShaplelyObj: bool, optional, default as False
        True if alter the result to be a shapely object

    Return
    ------
    list of polys
        A list of polygons
    """

    if (polys == None and polysShapely == None):
        raise MissingParameterError("ERROR: Missing required field 'polys' or 'polysShapely'.")
    if (subPolys == None and subPolysShapely == None):
        raise MissingParameterError("ERROR: Missing required field 'subPolys' or 'subPolysShapely'.")
    unionAll = None
    if (polysShapely == None):
        polysShapely = []
        for p in polys:
            if (unionAll == None):
                unionAll = shapely.Polygon(p)
                unionAll = unionAll.buffer(0.01)
            else:
                unionAll = shapely.union(unionAll, shapely.Polygon(p))
                unionAll = unionAll.buffer(0.01)
    
    diffShapely = unionAll
    if (subPolysShapely == None):
        subPolysShapely = []
        for p in subPolys:
            diffShapely = shapely.difference(unionAll, shapely.Polygon(p))
            diffShapely = diffShapely.buffer(0.01)

    if (returnShaplelyObj):
        return diffShapely

    diffPolys = []
    if (isinstance(diffShapely, shapely.geometry.polygon.Polygon)):
        diffPolys = [[[i[0], i[1]] for i in list(diffShapely.exterior.coords)]]
    elif (isinstance(diffShapely, shapely.geometry.multipolygon.MultiPolygon)):
        for p in diffShapely.geoms:
            diffPolys.append([[i[0], i[1]] for i in list(p.exterior.coords)])
    for k in range(len(diffPolys)):
        diffPolys[k] = [diffPolys[k][i] for i in range(len(diffPolys[k])) if distEuclideanXY(diffPolys[k][i], diffPolys[k][i - 1]) > ERRTOL['distPt2Pt']]
        if (distEuclideanXY(diffPolys[k][0], diffPolys[k][-1]) <= ERRTOL['distPt2Pt']):
            diffPolys[k] = diffPolys[k][:-1]
    return diffPolys

def polysIntersect(polys: polys=None, polysShapely:list[shapely.Polygon]=None, returnShaplelyObj:bool=False) -> list:
    """
    Given a list of polygons which could be intersecting to each other, return the intersecting polygons

    Parameters
    ----------
    polys: poly, optional, default as None
        A list of polygons
    polysShapely: shapely.Polygon, optional, default as None
        The correspond shapely objects for polygons. Need to provide one of the following fields: [`polys`, `polysShapely`]
    returnShaplelyObj: bool, optional, default as False
        True if alter the result to be a shapely object

    Return
    ------
    list of polys
        A list of polygons
    """

    if (polys == None and polysShapely == None):
        raise MissingParameterError("ERROR: Missing required field 'polys' or 'polysShapely'.")
    if (polysShapely == None):
        polysShapely = []
        for p in polys:
            polysShapely.append(shapely.Polygon(p))
    intersectionAll = shapely.intersection_all(polysShapely)

    if (returnShaplelyObj):
        return intersectionAll

    intersectionPoly = []
    if (isinstance(intersectionAll, shapely.geometry.polygon.Polygon)):
        intersectionPoly = [[[i[0], i[1]] for i in list(intersectionAll.exterior.coords)]]
    elif (isinstance(intersectionAll, shapely.geometry.multipolygon.MultiPolygon)):
        for p in intersectionAll.geoms:
            intersectionPoly.append([[i[0], i[1]] for i in list(p.exterior.coords)])
    for k in range(len(intersectionPoly)):
        intersectionPoly[k] = [intersectionPoly[k][i] for i in range(len(intersectionPoly[k])) if distEuclideanXY(intersectionPoly[k][i], intersectionPoly[k][i - 1]) > ERRTOL['distPt2Pt']]
        if (distEuclideanXY(intersectionPoly[k][0], intersectionPoly[k][-1]) <= ERRTOL['distPt2Pt']):
            intersectionPoly[k] = intersectionPoly[k][:-1]
    return intersectionPoly

def polyClockWise(poly) -> bool:
    """
    Given a poly, return True if the poly is clockwise, False otherwise

    Parameters
    ----------
    poly: poly, required
        The poly

    Returns
    -------
    bool
        True if clockwise, false otherwise

    """
    numCW = 0
    numCCW = 0

    for i in range(len(poly)):
        pt1 = poly[i]
        pt2 = None
        pt3 = None
        if (i == len(poly) - 1):
            pt2 = poly[0]
            pt3 = poly[1]
        elif (i == len(poly) - 2):
            pt2 = poly[i + 1]
            pt3 = poly[0]
        else:
            pt2 = poly[i + 1]
            pt3 = poly[i + 2]
        cwFlag = is3PtsClockWise(pt1, pt2, pt3)
        if (cwFlag == True):
            numCW += 1
        elif (cwFlag == False):
            numCCW += 1
    if (numCW > numCCW):
        return True
    else:
        return False

def poly2CW(poly) -> poly:
    if (polyClockWise(poly)):
        return poly
    else:
        return [poly[len(poly) - 1 - i] for i in range(len(poly))]

def poly2CCW(poly) -> poly:
    if (polyClockWise(poly)):
        return [poly[len(poly) - 1 - i] for i in range(len(poly))]
    else:
        return poly

def polyConvexHull(pts: list[pt]) -> poly:
    geo = shapely.MultiPoint([p for p in pts])
    cvxShapley = shapely.convex_hull(geo)
    cvx = [[i[0], i[1]] for i in list(cvxShapley.exterior.coords)]
    noRepeatCvx = []
    for i in cvx:
        if (i not in noRepeatCvx):
            noRepeatCvx.append(i)
    return noRepeatCvx

# Visibility check ============================================================
def polysVisibleGraph(polys:polys) -> dict:
    """
    Create a visual graph for given polys.

    Parameters
    ----------
    polys: polys, required
        The polys to create visual graph

    Return
    ------
    dict
        Each polygon has a index p, each point in the polygon has a index e, therefore, a (p, e) pair defines a location. The visual graph returns use (p, e) as keys, collects the location of (p, e) in 'pt', and finds the set of visible (p, e) in 'visible'

    """

    vg = {}
    for p in range(len(polys)):
        for e in range(len(polys[p])):
            vg[(p, e)] = {'pt': polys[p][e], 'visible': []}
            W = _visPtAmongPolys((p, e), polys, knownVG=vg)
            # print(p, e, W)
            for w in W:
                vg[(p, e)]['visible'].append(w)
    return vg

def _visPtAmongPolys(v:int|str|tuple, polys:polys, standalonePts:dict|None=None, knownVG:dict={}) -> list:
    # NOTE: 该函数不需要使用shapely
    vertices = {}
    polyVertices = []
    for p in range(len(polys)):
        for e in range(len(polys[p])):
            vertices[(p, e)] = {
                'pt': polys[p][e],
                'visible': []
            }
            polyVertices.append((p, e))
    if (standalonePts != None):
        if (v not in standalonePts):
            raise MissingParameterError("ERROR: Cannot find `v` in `polys` or `standalonePts`")
        else:
            vertices[v] = {
                'pt': standalonePts[v]['pt'],
                'visible': []
            }

    # 把所有的poly vertices按到v的距离排序，从而给每个点得到一个可排序的唯一编码
    verticeDistIndex = {}
    sortedSeq = nodeSeqByDist(
        nodes = vertices,
        refPt = vertices[v]['pt'],
        nodeIDs = polyVertices)
    for i in range(len(sortedSeq)):
        verticeDistIndex[sortedSeq[i]] = i
    # 把所有的poly vertices按到v的角度排序，从x轴正方向开始，从而得到后续可视性检查的顺序
    sweepSeq = nodeSeqBySweeping(
        nodes = vertices,
        nodeIDs = polyVertices,
        refPt = vertices[v]['pt'],
        initDeg = 90)

    # 用一个红黑树来维护射线通过的边，边的键值用(closer-index, further-index)，这样排序的时候无论如何都能保持距离关系
    def rayIntersectPolyEdges(ray, polys) -> RedBlackTree:
        T = RedBlackTree()
        # FIXME: 这个显然需要用线段树来优化，在这里就先实现再说吧
        for p in range(len(polys)):
            for i in range(-1, len(polys[p]) - 1):
                edge = [polys[p][i], polys[p][i + 1]]
                # NOTE: 注意，这里射线可以与线段交于端点上
                if (isSegIntRay(edge, ray, interiorOnly=True)):
                    # NOTE: 防止数组溢出
                    k = i
                    if (i == -1):
                        k = len(polys[p]) - 1
                    vIdx1 = verticeDistIndex[(p, k)]
                    vIdx2 = verticeDistIndex[(p, i + 1)]
                    T.insert(RedBlackTreeNode(
                        key = (min(vIdx1, vIdx2), max(vIdx1, vIdx2)), 
                        value = [(p, k), (p, i + 1)]))
        return T

    # 初始射线方向为x-轴正方向
    xAxisRay = [vertices[v]['pt'], (vertices[v]['pt'][0] + 1, vertices[v]['pt'][1])]
    T = rayIntersectPolyEdges(xAxisRay, polys)

    # 给定一个障碍物的顶点w_i，确定v是否可以见到w_i
    # NOTE: 这里的wi, wim（也就是w_{i-1})得是polys的顶点
    def visible(wi, wim, polys):
        # 如果wiv已经确定可视，直接返回True
        if (wi in knownVG and v in knownVG[wi]['visible']):
            # print("Time saved")
            return True

        # 所在的polygon的编号
        polyV = polys[v[0]] if len(v) == 2 else None
        polyW = polys[wi[0]]
        vwi = [vertices[v]['pt'], vertices[wi]['pt']]

        vNext = None
        vPrev = None
        if (len(v) == 2):
            vNext = (v[0], v[1] + 1 if v[1] < len(polys[v[0]]) - 1 else 0)
            vPrev = (v[0], v[1] - 1 if v[1] > 0 else len(polys[v[0]]) - 1)
        wiNext = (wi[0], wi[1] + 1 if wi[1] < len(polys[wi[0]]) - 1 else 0)
        wiPrev = (wi[0], wi[1] - 1 if wi[1] > 0 else len(polys[wi[0]]) - 1)        

        # 判断是否是相邻节点，相邻节点直接返回可见
        if (polyV == polyW and (wi == vNext or wi == vPrev)):
            # print("Visible by neighboring: ", v, wi)
            return True

        # 需要w_{i-1}不存在，或者w_{i-1}不在线段vwi上
        notOnlineFlag = False
        if (wim == None or not isPtOnSeg(wim, vwi)):
            notOnlineFlag = True

        # 若T非空，查有没有阻拦线段
        noSegBlockFlag = True
        if (notOnlineFlag and not T.isEmpty and not T.min(T.root).isNil):
            for edge in T.traverse():
                if (isSegIntSeg(
                        seg1 = [vertices[edge.value[0]]['pt'], vertices[edge.value[1]]['pt']], 
                        seg2 = vwi, 
                        interiorOnly = True)):
                    noSegBlockFlag = False
                    break

        # 如果visibleFlag，查交点上是否相切
        int2PolyVTangenFlag = False
        int2PolyWTangenFlag = False
        if (noSegBlockFlag):
            # Check point V
            if (polyV == None):
                int2PolyVTangenFlag = True
            else:
                segV = [vertices[vNext]['pt'], vertices[vPrev]['pt']]
                int2PolyVTangenFlag = not isLineIntSeg(vwi, segV, interiorOnly=True)
        if (int2PolyVTangenFlag):
            # Check point W
            segW = [vertices[wiNext]['pt'], vertices[wiPrev]['pt']]
            int2PolyWTangenFlag = not isLineIntSeg(vwi, segW, interiorOnly=True)
        bothEndTangenFlag = int2PolyVTangenFlag and int2PolyWTangenFlag

        # 如果没有阻挡线段，查是不是在多边形内部
        # NOTE: 似乎可以通过查中点确定是不是在多边形内部
        visibleFlag = False
        if (noSegBlockFlag and bothEndTangenFlag and not isSegIntPoly(
                seg = vwi,
                poly = polyW,
                interiorOnly = True)):
            # print("No blocking: ", v, wi)
            visibleFlag = True        

        if (visibleFlag):
            return True

        # 前面任何一关不通过，则不可视
        return False

    W = []
    for i in range(len(sweepSeq)):
        wi = sweepSeq[i]
        wim = sweepSeq[i - 1] if i > 1 else None
        # print(T)
        if (not is2PtsSame(vertices[v]['pt'], vertices[wi]['pt']) and visible(wi, wim, polys)):
            W.append(wi)

        # 将wi的边加入/移出平衡树T
        # wi所在的poly编号
        polyIdx = wi[0]
        # wi在poly内的编号
        idInPoly = wi[1]

        # Edge 1: wi -> wi.next
        wiNext = (wi[0], wi[1] + 1 if wi[1] < len(polys[wi[0]]) - 1 else 0)
        # Edge 2: wi.prev -> wi
        wiPrev = (wi[0], wi[1] - 1 if wi[1] > 0 else len(polys[wi[0]]) - 1)

        # 判断edgeNext
        vIdxWi = verticeDistIndex[wi]
        vIdxWiNext = verticeDistIndex[wiNext]
        vIdxWiPrev = verticeDistIndex[wiPrev]
        if (is3PtsClockWise(vertices[v]['pt'], vertices[wi]['pt'], vertices[wiNext]['pt'])):
            if (T.query((min(vIdxWi, vIdxWiNext), max(vIdxWi, vIdxWiNext))).isNil):
                T.insert(RedBlackTreeNode(
                    key = (min(vIdxWi, vIdxWiNext), max(vIdxWi, vIdxWiNext)), 
                    value = [wi, wiNext]))
        else:
            if (not T.query((min(vIdxWi, vIdxWiNext), max(vIdxWi, vIdxWiNext))).isNil):
                T.delete((min(vIdxWi, vIdxWiNext), max(vIdxWi, vIdxWiNext)))        
        if (is3PtsClockWise(vertices[v]['pt'], vertices[wi]['pt'], vertices[wiPrev]['pt'])):
            if (T.query((min(vIdxWiPrev, vIdxWi), max(vIdxWiPrev, vIdxWi))).isNil):
                T.insert(RedBlackTreeNode(
                    key = (min(vIdxWiPrev, vIdxWi), max(vIdxWiPrev, vIdxWi)), 
                    value = [wiPrev, wi]))
        else:
            if (not T.query((min(vIdxWiPrev, vIdxWi), max(vIdxWiPrev, vIdxWi))).isNil):
                T.delete((min(vIdxWiPrev, vIdxWi), max(vIdxWiPrev, vIdxWi)))
    return W

# Time seq related ============================================================
def snapInTimedSeq(timedSeq: list[tuple[pt, float]], t: float) -> dict:
    """
    Given a timedSeq, return the location, speed, and trajectory at time t

    Parameters
    ----------

    timedSeq: timedSeq, required
        The timed sequence
    t: float, required
        The snapshot timestamp

    Return
    ------
    dict
        >>> {
        ...     'pt': location,
        ...     'speed': speed,
        ...     'trajectory': trajectory
        ... }

    """

    for i in range(len(timedSeq) - 1):
        if (timedSeq[i][1] > timedSeq[i + 1][1]):
            raise UnsupportedInputError("ERROR: `timedSeq` should be a non-descending sequence.")
        if (timedSeq[i][1] == timedSeq[i + 1][1] 
            and (abs(timedSeq[i][0][0] - timedSeq[i + 1][0][0]) >= ERRTOL['distPt2Pt']
                or abs(timedSeq[i][0][1] - timedSeq[i + 1][0][1]) >= ERRTOL['distPt2Pt'])):
            raise UnsupportedInputError("ERROR: an object cannot be two places at the same time.")

    curPtX = None
    curPtY = None
    curSpeed = None
    curTrajectory = None

    if (t <= timedSeq[0][1]):
        return {
            'pt': timedSeq[0][0],
            'speed': 0,
            'trajectory': None
        }
    if (t >= timedSeq[-1][1]):
        return {
            'pt': timedSeq[-1][0],
            'speed': 0,
            'trajectory': None
        }

    for i in range(len(timedSeq) - 1):
        if (timedSeq[i][1] <= t < timedSeq[i + 1][1]):
            dist = distEuclideanXY(timedSeq[i][0], timedSeq[i + 1][0])
            if (dist > 0):
                dt = (t - timedSeq[i][1]) / (timedSeq[i + 1][1] - timedSeq[i][1])                
                curPtX = timedSeq[i][0][0] + (timedSeq[i + 1][0][0] - timedSeq[i][0][0]) * dt
                curPtY = timedSeq[i][0][1] + (timedSeq[i + 1][0][1] - timedSeq[i][0][1]) * dt
                curSpeed = dist / (timedSeq[i + 1][1] - timedSeq[i][1])
                trajX = (timedSeq[i + 1][0][0] - timedSeq[i][0][0]) / dist
                trajY = (timedSeq[i + 1][0][1] - timedSeq[i][0][1]) / dist
                curTrajectory = [(curPtX, curPtY), (curPtX + trajX, curPtY + trajY)]
            else:
                curPtX = timedSeq[i][0][0]
                curPtY = timedSeq[i][0][1]
                curSpeed = 0
                curTrajectory = None
            break
    return {
        'pt': [curPtX, curPtY],
        'speed': curSpeed,
        'trajectory': curTrajectory
    }

def traceInTimedSeq(timedSeq: list[tuple[pt, float]], ts: float, te: float) -> list[pt]:
    """
    Given a timedSeq, a start time and an end time, returns the trace between start time and end time.

    Parameters
    ----------

    timedSeq: timedSeq, required
        The timed sequence
    ts: float, required
        The start time
    te: float, required
        The end time

    Return
    ------
    list
        The line segment sequence between start time and end time in the timedSeq

    """

    for i in range(len(timedSeq) - 1):
        if (timedSeq[i][1] > timedSeq[i + 1][1]):
            raise UnsupportedInputError("ERROR: `timedSeq` should be a non-descending sequence.")
        if (timedSeq[i][1] == timedSeq[i + 1][1] 
            and (abs(timedSeq[i][0][0] - timedSeq[i + 1][0][0]) >= ERRTOL['distPt2Pt']
                or abs(timedSeq[i][0][1] - timedSeq[i + 1][0][1]) >= ERRTOL['distPt2Pt'])):
            raise UnsupportedInputError("ERROR: an object cannot be two places at the same time.")
    
    trace = []

    if (ts >= te):
        raise UnsupportedInputError("ERROR: `ts` should be earlier than `te`")
    if (ts <= timedSeq[0][1] and te >= timedSeq[-1][1]):
        return [timedSeq[i][0] for i in range(len(timedSeq))]
    if (ts >= timedSeq[-1][1]):
        return []
    if (te <= timedSeq[0][1]):
        return []

    tsIndex = -1
    teIndex = -1
    tsPt = []
    tePt = []

    if (ts <= timedSeq[0][1]):
        tsIndex = 0
        ts = timedSeq[0][1]
        tsPt = timedSeq[0][0]
    if (te >= timedSeq[-1][1]):
        teIndex = len(timedSeq) - 1
        te = timedSeq[-1][1]
        tePt = timedSeq[-1][0]

    for i in range(len(timedSeq) - 1):
        if (timedSeq[i][1] <= ts < timedSeq[i + 1][1]):
            tsIndex = i
            dTs = (ts - timedSeq[i][1]) / (timedSeq[i + 1][1] - timedSeq[i][1])
            tsX = timedSeq[i][0][0] + (timedSeq[i + 1][0][0] - timedSeq[i][0][0]) * dTs
            tsY = timedSeq[i][0][1] + (timedSeq[i + 1][0][1] - timedSeq[i][0][1]) * dTs
            tsPt = [tsX, tsY]
            for j in range(tsIndex, len(timedSeq) - 1):
                if (timedSeq[j][1] <= te < timedSeq[j + 1][1]):
                    teIndex = j
                    dTe = (te - timedSeq[j][1]) / (timedSeq[j + 1][1] - timedSeq[j][1])
                    teX = timedSeq[j][0][0] + (timedSeq[j + 1][0][0] - timedSeq[j][0][0]) * dTe
                    teY = timedSeq[j][0][1] + (timedSeq[j + 1][0][1] - timedSeq[j][0][1]) * dTe
                    tePt = [teX, teY]

    if (tsIndex == teIndex):
        trace = [tsPt, tePt]
    elif (tsIndex + 1 == teIndex):
        trace.append(tsPt)
        trace.append(timedSeq[tsIndex + 1][0])
        trace.append(tePt)
    else:
        trace.append(tsPt)
        for i in range(tsIndex + 1, teIndex + 1):
            trace.append(timedSeq[i][0])
        trace.append(tePt)

    return trace

def seq2TimedSeq(seq: list[pt], vehSpeed: float, timeEachStop: float = 0, startTime: float = 0):
    timedSeq = []
    accTime = startTime
    for i in range(len(seq) - 1):
        timedSeq.append((seq[i], accTime))
        if (timeEachStop > 0):
            accTime += timeEachStop
            timedSeq.append((seq[i], accTime))
        accTime += (distEuclideanXY(seq[i], seq[i + 1])) / vehSpeed
    timedSeq.append((seq[-1], accTime))
    return timedSeq

# Triangulation ===============================================================
def polyTriangulation(poly: poly):
    triangles = []
    remain = [i for i in range(len(poly))]
    for k in range(len(remain) - 2):
        rndStart = random.randint(0, len(remain) - 2)
        for i in range(1, len(remain) - 1):
            canCutEar = True
            A = (i - 1 + rndStart) if (i - 1 + rndStart) < len(remain) else (i - 1 + rndStart - len(remain))
            B = (i + rndStart) if (i + rndStart) < len(remain) else (i + rndStart - len(remain))
            C = (i + 1 + rndStart) if (i + 1 + rndStart) < len(remain) else (i + 1 + rndStart - len(remain))
            tri = [poly[remain[A]], poly[remain[B]], poly[remain[C]]]
            center = [(tri[0][0] + tri[1][0] + tri[2][0]) / 3, (tri[0][1] + tri[1][1] + tri[2][1]) / 3]
            if (not isPtInPoly(pt = center, poly = [poly[k] for k in remain])):
                canCutEar = False
                continue
            for j in range(1, len(remain) - 1):
                if (j != A and j != B and j != C and isPtInPoly(pt = poly[remain[j]], poly = tri)):
                    canCutEar = False
                    break
            if (canCutEar):
                triangles.append(tri)
                remain.pop(B)
                break
            else:
                continue
    return triangles

# Area calculation ============================================================
def calTriangleAreaEdge(a: float, b: float, c: float) -> float:
    
    s = (a / 2 + b / 2 + c / 2)
    area = math.sqrt(s * (s - a) * (s - b) * (s - c))
    return area

def calTriangleAreaXY(pt1: pt, pt2: pt, pt3: pt) -> float:
    
    [x1, y1] = pt1
    [x2, y2] = pt2
    [x3, y3] = pt3
    val = (x2 * y3 + x3 * y1 + x1 * y2) - (x2 * y1 + x3 * y2 + x1 * y3)
    area = abs(val) / 2
    return area

def calPolyAreaXY(poly: poly) -> float:
    lstTriangle = polyTriangulation(poly)
    area = 0
    for i in range(len(lstTriangle)):
        area += calTriangleAreaXY(lstTriangle[i][0], lstTriangle[i][1], lstTriangle[i][2])
    return area

def calPolyAreaLatLon(polyLatLon: poly) -> float:
    """Returns the area surrounded by polyLatLon on the Earth"""
    try:
        from pyproj import Geod
    except:
        raise ImportError

    # NOTE: shapely is in [lon, lat] format
    rev = []
    for p in polyLatLon:
        rev.append((p[1], p[0]))
    polygon = shapely.Polygon(rev)

    # Using pyproj to calculate
    # Ref: https://hypc.github.io/2020/03/16/python-geo-area/
    geod = Geod(ellps = "WGS84")
    area = abs(geod.geometry_area_perimeter(polygon)[0])

    return area

def calPolyPerimeterXY(poly: poly) -> float:
    p = 0
    for i in range(-1, len(poly) - 1):
        p += distEuclideanXY(poly[i], poly[i + 1])
    return p

# Location of points ==========================================================
def headingXY(pt1: pt, pt2: pt) -> float:
    """
    Given two points, returns the direction from the first point to the second point

    Parameters
    ----------
    pt1: pt, required
        The first point
    pt2: pt, required
        The second point

    Return
    ------
    float
        The direction from pt1 to pt2, north as 0, clock-wise

    """
    vec = (pt2[0] - pt1[0], pt2[1] - pt1[1])
    (_, vDeg) = vecXY2Polar(vec)
    return vDeg

def headingLatLon(pt1: pt, pt2: pt) -> float:
    """
    Given current location and a goal location, calculate the heading. North is 0-degrees, clock-wise

    Parameters
    ----------
    pt1: pt, required
        The first point
    pt2: pt, required
        The second point

    Return
    ------
    float
        The direction from pt1 to pt2, north as 0, clock-wise

    """

    # Ref: https://github.com/manuelbieh/Geolib/issues/28
    (lat1, lon1) = pt1
    (lat2, lon2) = pt2
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    dLon = lon2 - lon1
    if abs(dLon) > math.pi:
        if dLon > 0.0:
            dLon = -(2.0 * math.pi - dLon)
        else:
            dLon = (2.0 * math.pi + dLon)
    tan1 = math.tan(lat1 / 2.0 + math.pi / 4.0)
    tan2 = math.tan(lat2 / 2.0 + math.pi / 4.0)
    phi = math.log(tan2 / tan1)
    deg = (math.degrees(math.atan2(dLon, phi)) + 360.0) % 360.0
    return deg

def ptInDistVec(pt: pt, vec: list, dist: int|float = 1, vecNormalizeFlag: bool = False) -> pt:
    L = 1
    if (not vecNormalizeFlag):
        L = math.sqrt(vec[0] ** 2 + vec[1] ** 2)
    x = pt[0] + vec[0] / L * dist
    y = pt[1] + vec[1] / L * dist
    return (x, y)

def ptInDistXY(pt: pt, direction: int|float, dist: int|float) -> pt:
    """
    A location in distance with given direction.

    Parameters
    ----------
    pt: pt, required
        The origin point
    direction: float, required
        The direction from origin point
    dist: float, required

    Returns
    -------
    pt
        The new location

    """
    x = pt[0] + dist * math.sin(math.radians(direction))
    y = pt[1] + dist * math.cos(math.radians(direction))
    return (x, y)

def ptInDistLatLon(pt: pt, direction: int|float, distMeters: int|float) -> pt:
    """
    A location in distance with given direction in lat/lon.

    Parameters
    ----------
    pt: pt, required
        The origin point
    direction: float, required
        The direction from origin point
    dist: float, required

    Returns
    -------
    pt
        The new location

    """
    # Bearing in degrees: 0 – North, 90 – East, 180 – South, 270 or -90 – West.
    newPt = list(geopy.distance.distance(meters=distMeters).destination(point=pt, bearing=direction))[:2]
    return newPt

def circleByCenterLatLon(center: pt, radius: int|float, lod: int = 30) -> poly:
    """
    Create a circle by the center and a radius. The circle is approximated by a x-gon, e.g., 30-gon polygon.

    Parameters
    ----------
    center: pt, required
        The center of the circle
    radius: float, required
        The radius of the circle
    lod: int, optional, default as 30
        Level of details. The circle is approximated as a x-gon. E.g. 30-gon

    Return
    ------
    poly
        A polygon that approximates the circle.

    """
    circle = []
    for i in range(lod):
        deg = float(360 * i) / float(lod)
        pt = ptInDistLatLon(pt = center, direction = deg, distMeters = radius)
        circle.append(pt)
    return circle

def circleByCenterXY(center: pt, radius: int|float, lod: int = 30) -> poly:
    """
    Create a circle by the center and a radius. The circle is approximated by a x-gon, e.g., 30-gon polygon.

    Parameters
    ----------
    center: pt, required
        The center of the circle
    radius: float, required
        The radius of the circle
    lod: int, optional, default as 30
        Level of details. The circle is approximated as a x-gon. E.g. 30-gon

    Return
    ------
    poly
        A polygon that approximates the circle.

    """
    circle = []
    for i in range(lod):
        deg = float(360 * i) / float(lod)
        pt = ptInDistXY(pt = center, direction = deg, dist = radius)
        circle.append(pt)
    return circle

# Sort nodes ==================================================================
def nodeSeqByDist(nodes: dict, nodeIDs: list|str = 'All', ptFieldName = 'pt', refPt: pt|None = None, refNodeID: int|str|None = None) -> list:
    # Define nodeIDs
    if (type(nodeIDs) is not list):
        if (nodeIDs == 'All'):
            nodeIDs = []
            for i in nodes:
                nodeIDs.append(i)

    # Define refPt
    if (refPt == None):
        if (refNodeID == None):
            raise MissingParameterError("ERROR: Missing reference location")
        elif (refNodeID not in nodeIDs):
            raise OutOfRangeError("ERROR: `refNodeID` cannot be found.")
        else:
            refPt = nodes[refNodeID][ptFieldName]

    # Sort distance
    sortedSeq = []
    sortedSeqHeap = []
    for n in nodeIDs:
        dist = distEuclideanXY(refPt, nodes[n][ptFieldName])
        heapq.heappush(sortedSeqHeap, (dist, n))
    while (len(sortedSeqHeap) > 0):
        sortedSeq.append(heapq.heappop(sortedSeqHeap)[1])  

    return sortedSeq

def nodeSeqBySweeping(nodes: dict, nodeIDs: list|str = 'All', ptFieldName = 'pt', refPt: None|pt = None, refNodeID: int|str|None = None, isClockwise: bool = True, initDeg: float = 0) -> list:
    """Given a set of locations, and a center point, gets the sequence from sweeping"""
    # Define nodeIDs
    if (type(nodeIDs) is not list):
        if (nodeIDs == 'All'):
            nodeIDs = []
            for i in nodes:
                nodeIDs.append(i)

    # Initialize centroid
    if (refPt == None):
        lstNodePt = []
        for n in nodeIDs:
            lstNodePt.append(shapely.Point(nodes[n][ptFieldName][0], nodes[n][ptFieldName][1]))
        refPt = list(shapely.centroid(shapely.MultiPoint(points = lstNodePt)))

    # Initialize heap
    degHeap = []
    refPtNodes = []
    
    # Build heap
    for n in nodeIDs:
        dist = distEuclideanXY(nodes[n][ptFieldName], refPt)
        # If the nodes are too close, separate it/them
        if (dist <= ERRTOL['distPt2Pt']):
            refPtNodes.append(n)
        else:
            dx = nodes[n][ptFieldName][0] - refPt[0]
            dy = nodes[n][ptFieldName][1] - refPt[1]
            (_, deg) = vecXY2Polar((dx, dy))
            # Calculate angles
            evalDeg = None
            if (isClockwise):
                evalDeg = deg - initDeg
            else:
                evalDeg = initDeg - deg
            while(evalDeg > 360):
                evalDeg -= 360
            while(evalDeg < 0):
                evalDeg += 360
            heapq.heappush(degHeap, (evalDeg, dist, n))

    # Sweep
    sweepSeq = []
    while (len(degHeap)):
        sweepSeq.append(heapq.heappop(degHeap)[2])
    sweepSeq.extend(refPtNodes)

    return sweepSeq

def nodesInIsochrone(nodes: dict, nodeIDs: list|str = 'All', ptFieldName = 'pt', refPt: pt|None = None, refNodeID: int|str|None = None, isoRange: float = None, sortFlag: bool = False) -> list: 
    # FIXME: Need an algorithm to filter out locations that are clearly too far from refPt
    # Define nodeIDs
    if (type(nodeIDs) is not list):
        if (nodeIDs == 'All'):
            nodeIDs = []
            for i in nodes:
                nodeIDs.append(i)

    # Define refPt
    if (refPt == None):
        if (refNodeID == None):
            raise MissingParameterError("ERROR: Missing reference location")
        elif (refNodeID not in nodeIDs):
            raise OutOfRangeError("ERROR: `refNodeID` cannot be found.")
        else:
            refPt = nodes[refNodeID][ptFieldName]

    # Sort distance
    if (isoRange == None):
        raise MissingParameterError("ERROR: Missing required field `isoRange`.")
    nearSet = []
    nearest = None
    nearestDist = float('inf')
    if (sortFlag):
        nearSetHeap = []
        for n in nodeIDs:
            dist = scaleDist(pt1 = refPt, pt2 = nodes[n][ptFieldName], edges = 'Euclidean')
            if (dist <= isoRange):
                heapq.heappush(nearSetHeap, (dist, n))
        while (len(nearSetHeap) > 0):
            nearSet.append(heapq.heappop(nearSetHeap)[1])
        nearest = nearSet[0]
    else:
        for n in nodeIDs:
            dist = scaleDist(pt1 = refPt, pt2 = nodes[n][ptFieldName], edges = 'Euclidean')
            if (dist <= isoRange):
                nearSet.append(n)
            if (dist <= nearestDist):
                nearest = n
                nearestDist = dist
    return {
        'nearSet': nearSet,
        'nearest': nearest
    }

# Distance calculation ========================================================
def distEuclideanXY(pt1: pt, pt2: pt) -> dict:
    """
    Gives a Euclidean distance based on two coords.

    Parameters
    ----------
    pt1: pt, required
        The first location
    pt2: pt, required
        The second location

    Returns
    -------
    dict
        A dictionary, with the distance in 'dist', and the path in 'path'
    """
    if (len(pt1) == 2):
        return math.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)
    elif (len(pt1) == 3):
        return math.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2 + (pt1[2] - pt2[2]) ** 2)

def distManhattenXY(pt1: pt, pt2: pt, detailFlag: bool=False) -> dict:
    """
    Gives a Manhatten distance based on two coords.

    Parameters
    ----------
    pt1: pt, required
        The first location
    pt2: pt, required
        The second location

    Returns
    -------
    dict
        A dictionary, with the distance in 'dist', and the path in 'path'
    """

    dist = abs(pt1[0] - pt2[0]) + abs(pt1[1] - pt2[1])
    if (detailFlag):
        return {
            'dist': dist,
            'path': path
        }
    else:
        return dist

def distBtwPolysXY(pt1:pt, pt2:pt, polys:polys, polyVG: dict = None, detailFlag: bool=False) -> dict:
    """
    Gives a Manhatten distance based on two coords.

    Parameters
    ----------
    pt1: pt, required
        The first location
    pt2: pt, required
        The second location
    polys: polys, required
        The polygons as barriers.
    polyVG: dict, optional, default as None
        The pre-calculated visual-graph using :func:`~polysVisibleGraph()`. To avoid repeated calculation

    Returns
    -------
    dict
        A dictionary, with the distance in 'dist', and the path in 'path'
    """

    # Reference: Computational Geometry: Algorithms and Applications Third Edition
    # By Mark de Berg et al. Page 326 - 330
    # With some modifications

    # First check if start pt or end pt is in one of the polygons =============
    for poly in polys:
        if (isPtInPoly(pt1, poly, interiorOnly = True)):
            raise OutOfRangeError("Point (%s, %s) is inside `polys` when it is not suppose to." % (pt1[0], pt1[1]))
        if (isPtInPoly(pt2, poly, interiorOnly = True)):
            raise OutOfRangeError("Point (%s, %s) is inside `polys` when it is not suppose to." % (pt2[0], pt2[1]))

    # Quick checkout ==========================================================
    visibleDirectly = True
    for poly in polys:
        if (isSegIntPoly([pt1, pt2], poly, interiorOnly=True)):
            visibleDirectly = False
            break
    if (visibleDirectly):
        if (detailFlag):
            return {
                'dist': distEuclideanXY(pt1, pt2),
                'path': [pt1, pt2]
            }
        else:
            return distEuclideanXY(pt1, pt2)

    # Create visible graph for polys ==========================================
    if (polyVG == None):      
        for p in range(len(polys)):
            polys[p] = [polys[p][i] for i in range(len(polys[p])) if distEuclideanXY(polys[p][i], polys[p][i - 1]) > ERRTOL['distPt2Pt']]
        polyVG = polysVisibleGraph(polys)

    # Create a visible graph ==================================================
    # NOTE: startPt可视的vertices将不需要测试是不是相互之间可视，同样地，可视endPt的vertices之间也不需要可视
    vertices = {}
    for p in polyVG:
        vertices[p] = {
            'pt': polyVG[p]['pt'],
            'visible': [i for i in polyVG[p]['visible']]
        }
    vertices['s'] = {'pt': pt1, 'visible': []}
    Ws = _visPtAmongPolys('s', polys, {'s': {'pt': pt1, 'visible': []}})
    vertices['s']['visible'] = Ws
    vertices['e'] = {'pt': pt2, 'visible': []}
    We = _visPtAmongPolys('e', polys, {'e': {'pt': pt2, 'visible': []}})
    vertices['e']['visible'] = We

    # Find shortest path ======================================================
    vg = nx.Graph()
    for v in vertices:
        vg.add_node(v)
    for v in vertices:
        for e in vertices[v]['visible']:
            vg.add_edge(v, e, weight=distEuclideanXY(vertices[v]['pt'], vertices[e]['pt']))
    try:
        sp = nx.dijkstra_path(vg, 's', 'e')
    except:
        print("ERROR: No path.")
        return None

    dist = 0
    for i in range(len(sp) - 1):
        dist += distEuclideanXY(vertices[sp[i]]['pt'], vertices[sp[i + 1]]['pt'])

    if (detailFlag):
        return {
            'dist': dist,
            'path': [vertices[wp]['pt'] for wp in sp]
        }
    else:
        return dist

def distLatLon(pt1: pt, pt2: pt, distUnit: str = 'meter') -> dict:
    """
    Gives a distance based on two lat/lon coords.

    Parameters
    ----------
    pt1: pt, required
        The first location
    pt2: pt, required
        The second location

    Returns
    -------
    dict
        A dictionary, with the distance in 'dist', and the path in 'path'
    """
    
    # Get radius as in distUnit ===============================================
    R = None
    if (distUnit in ['mile', 'mi']):
        R = CONST_EARTH_RADIUS_MILES
    elif (distUnit in ['meter', 'm']):
        R = CONST_EARTH_RADIUS_METERS
    elif (distUnit in ['kilometer', 'km']):
        R = CONST_EARTH_RADIUS_METERS / 1000
    else:
        raise UnsupportedInputError("ERROR: Unrecognized distance unit, options are 'mile', 'meter', 'kilometer'")

    # Calculate distance ======================================================
    (lat1, lon1) = pt1
    (lat2, lon2) = pt2
    phi1, phi2 = math.radians(lat1), math.radians(lat2) 
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def distOnGrid(pt1: pt, pt2: pt, column, row, barriers = [], algo: str = 'A*', detailFlag:bool = False, **kwargs) -> dict:
    """
    Given two coordinates on the grid, finds the 'shortest' path to travel

    Parameters
    ----------

    pt1: pt, required
        Starting location on the grid
    pt2: pt, required
        Ending location on the grid 
    column: int, required
        Number of columns
    row: int, required
        Number of rows
    barriers: list[pt], optional, default as []
        A list of coordinates as barriers on the grid.
    algo: dict, required, default as 'A*'
        The algorithm configuration. For example

        1) A*, use the A star algorithm, additional information needed is as follows
            - measure: str, optional, default as 'Manhatten'            
    **kwargs: optional
        Provide additional inputs for different `algo` options

    Returns
    -------
    dict
        A dictionary, with the distance in 'dist', and the path in 'path'
    """

    res = None
    if (algo == 'A*'):
        measure = None
        if ('measure' not in kwargs or kwargs['measure'] not in ['Manhatten', 'Euclidean']):
            warnings.warn("WARNING: Set distance measurement to be default as 'Manhatten")
            measure = 'Manhatten'
        else:
            measure = kwargs['measure']
        res = _distOnGridAStar(column, row, barriers, pt1, pt2, measure)
    else:
        raise UnsupportedInputError("Error: Incorrect or not available grid path finding option!")
    
    if (detailFlag):
        return res
    else:
        return res['dist']

def _distOnGridAStar(column, row, barriers, pt1, pt2, distMeasure):
    # Heuristic measure ==================================================-
    def _calManhattenDist(coord1, coord2):
        return abs(coord1[0] - coord2[0]) + abs(coord1[1] - coord2[1])
    def _calEuclideanDist(coord1, coord2):
        return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

    # Initialize grid ====================================================-
    # Evaluate value f(n) = g(n) + h(n)
    gridStatus = {}
    for col in range(column):
        for ro in range(row):
            if ((col, ro) not in barriers):
                # Content in the dictionary (g(n), h(n), fromCoord)
                # At this stage, no need to calculate h(n) 
                gridStatus[(col, ro)] = (None, None, None)
            else:
                gridStatus[(col, ro)] = 'block'
    if (distMeasure == 'Manhatten'):
        gridStatus[pt1] = (0, _calManhattenDist(pt1, pt2), None)
    elif (distMeasure == 'Euclidean'):
        gridStatus[pt1] = (0, _calEuclideanDist(pt1, pt2), None)
    gridStatus[pt2] = (None, 0, None)

    # Open/close set ======================================================
    openList = [pt1]
    closeList = [i for i in barriers]

    # Find smallest Fn ====================================================
    def _findSmallestFnGrid():
        bestFn = None
        bestCoord = None
        for coord in openList:
            if (gridStatus[coord] != None
                and gridStatus[coord] != 'block' 
                and (bestFn == None or gridStatus[coord][0] + gridStatus[coord][1] < bestFn)):
                bestFn = gridStatus[coord][0] + gridStatus[coord][1]
                bestCoord = coord
        if (bestCoord != None):
            return bestCoord
        else:
            raise

    # For each grid in open set, update g(n) ==============================
    while (len(openList) > 0):
        tmpOpenList = []
        coord = _findSmallestFnGrid()
        # Up
        upCoord = (coord[0], coord[1] + 1)
        if (coord[1] + 1 < row and gridStatus[upCoord] != None and gridStatus[upCoord] != 'block' and upCoord not in closeList):
            if (gridStatus[upCoord][0] == None or gridStatus[upCoord][0] > gridStatus[coord][0] + 1):
                if (distMeasure == 'Manhatten'):
                    gridStatus[upCoord] = (gridStatus[coord][0] + 1, _calManhattenDist(upCoord, pt2), coord)
                if (distMeasure == 'Euclidean'):
                    gridStatus[upCoord] = (gridStatus[coord][0] + 1, _calEuclideanDist(upCoord, pt2), coord)
                if (upCoord == pt2):
                    break
                else:
                    tmpOpenList.append(upCoord)
        # Down
        downCoord = (coord[0], coord[1] - 1)
        if (coord[1] - 1 >= 0 and gridStatus[downCoord] != None and gridStatus[downCoord] != 'block' and downCoord not in closeList):
            if (gridStatus[downCoord][0] == None or gridStatus[downCoord][0] > gridStatus[coord][0] + 1):
                if (distMeasure == 'Manhatten'):
                    gridStatus[downCoord] = (gridStatus[coord][0] + 1, _calManhattenDist(downCoord, pt2), coord)
                if (distMeasure == 'Euclidean'):
                    gridStatus[downCoord] = (gridStatus[coord][0] + 1, _calEuclideanDist(downCoord, pt2), coord)
                if (downCoord == pt2):
                    break
                else:
                    tmpOpenList.append(downCoord)
        # Left
        leftCoord = (coord[0] - 1, coord[1])
        if (coord[0] - 1 >= 0 and gridStatus[leftCoord] != None and gridStatus[leftCoord] != 'block' and leftCoord not in closeList):
            if (gridStatus[leftCoord][0] == None or gridStatus[leftCoord][0] > gridStatus[coord][0] + 1):
                if (distMeasure == 'Manhatten'):
                    gridStatus[leftCoord] = (gridStatus[coord][0] + 1, _calManhattenDist(leftCoord, pt2), coord)
                if (distMeasure == 'Euclidean'):
                    gridStatus[leftCoord] = (gridStatus[coord][0] + 1, _calEuclideanDist(leftCoord, pt2), coord)
                if (leftCoord == pt2):
                    break
                else:
                    tmpOpenList.append(leftCoord)
        # Right
        rightCoord = (coord[0] + 1, coord[1])
        if (coord[0] + 1 < column and gridStatus[rightCoord] != None and gridStatus[rightCoord] != 'block' and rightCoord not in closeList):
            if (gridStatus[rightCoord][0] == None or gridStatus[rightCoord][0] > gridStatus[coord][0] + 1):
                if (distMeasure == 'Manhatten'):
                    gridStatus[rightCoord] = (gridStatus[coord][0] + 1, _calManhattenDist(rightCoord, pt2), coord)
                if (distMeasure == 'Euclidean'):
                    gridStatus[rightCoord] = (gridStatus[coord][0] + 1, _calEuclideanDist(rightCoord, pt2), coord)
                if (rightCoord == pt2):
                    break
                else:
                    tmpOpenList.append(rightCoord)
        openList.remove(coord)
        openList.extend(tmpOpenList)
        closeList.append(coord)

    # Recover path ========================================================
    path = []
    curCoord = pt2
    finishReconstructFlag = True
    while (finishReconstructFlag):
        finishReconstructFlag = False
        path.insert(0, curCoord)
        curCoord = gridStatus[curCoord][2]
        if (curCoord != None):
            finishReconstructFlag = True
    return {
        'dist': len(path) - 1,
        'path': path
    }
