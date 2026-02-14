import gurobipy as grb
import networkx as nx

from .geometry import *
from .common import *

# Path touring through polygons ===============================================
def pathRemoveDegen(path: list[pt]):
    """
    Given a sequence of points, returns a subset of points that only includes turning points of the sequence. If there are multiple points overlapped at the same location, keeps one of those points.

    Parameters
    ----------
    path: list[pt], required
        The coordinates of a sequence of points.

    Returns
    -------
    dict
        A new dictionary, in the format of 
        
        >>> {
        ...     'newPath': newPath, 
        ...     'aggNodeList': aggNodeList, 
        ...     'removedFlag': removedFlag, 
        ...     'locatedSeg': locatedSeg
        ... }

        - The 'newPath' returns a new sequence which only has turn points of the origin sequence
        - The 'aggNodeList' is a list of lists, if a point overlaps with its previous/next point, the index of both points will be aggregated into the same list.
        - The 'removedFlag' indicates whether a point is removed as a non-turning point, true if the point is not included in the 'newPath'
        - The 'locatedPath' returns a list of line segments, for each point removed, it returns the line segment it belongs to 

    Examples
    --------
    For the following inputs
        >>> path = [[-1, 0], [0, 0], [0, 0], [1, 0], [2, 0], [2, 1], [1, 1], [1, 0], [1, -1]]
        >>> res = pathRemoveDegen(path)
    The result is as follows
        >>> res = {
        ...     'newPath': [[-1, 0], [2, 0], [2, 1], [1, 1], [1, -1]],
        ...     'aggNodeList': [[0], [1, 2], [3], [4], [5], [6], [7], [8]],
        ...     'removedFlag': [False, True, True, False, False, False, True, False],
        ...     'locatedSeg': [None,
        ...         [[-1, 0], [2, 0]],
        ...         [[-1, 0], [2, 0]],
        ...         None,
        ...         None,
        ...         None,
        ...         [[1, 1], [1, -1]],
        ...         None]
        ... }
    The result shows that, the new sequence is [[-1, 0], [2, 0], [2, 1], [1, 1], [1, -1]], in the new sequence, path[1], path[2], path[6] are not included since they are not turn points.
    path[1] and path[2] are aggregated due to overlaps. Although path[3] and path[6] are overlapped, they are not aggregated because they are not neighboring. 
    For the removed points, 'locatedPath' finds the segment they located.

    """

    # Step 1: 先按是否重合对点进行聚合  
    curPtList = [path[0]]
    curAgg = [0]
    aggNodeList = []
    # 挤香肠算法
    for i in range(1, len(path)):
        # 如果当前点和任意一个挤出来的点足够近，则计入
        samePtFlag = False

        for pt in curPtList:
            if (is2PtsSame(pt, path[i])):
                curAgg.append(i)
                curPtList.append(path[i])
                samePtFlag = True
                break

        # 若不重复，了结
        if (not samePtFlag):
            aggNodeList.append([k for k in curAgg])
            curAgg = [i]
            curPtList = [path[i]]

    aggNodeList.append([k for k in curAgg])

    # Step 2: 对聚合后的点，判断是否为转折点
    # NOTE: removeFlag的长度和aggNodeList一致
    removedFlag = [False]
    for i in range(1, len(aggNodeList) - 1):
        prePt = path[aggNodeList[i - 1] if type(aggNodeList[i - 1]) != list else aggNodeList[i - 1][0]]
        curPt = path[aggNodeList[i] if type(aggNodeList[i]) != list else aggNodeList[i][0]]
        sucPt = path[aggNodeList[i + 1] if type(aggNodeList[i + 1]) != list else aggNodeList[i + 1][0]]

        if (is2PtsSame(prePt, sucPt)):
            removedFlag.append(False)
        elif (distEuclideanXY(prePt, curPt) <= 0.2):
            removedFlag.append(False)
        elif (distEuclideanXY(curPt, sucPt) <= 0.2):
            removedFlag.append(False)
        else:
            dev = distPt2Seg(curPt, [prePt, sucPt])
            if (dev <= ERRTOL['distPt2Seg']):
                removedFlag.append(True)
            else:
                removedFlag.append(False)
    removedFlag.append(False)

    # 得到去掉共线和重合点后的折线
    newPath = []
    for i in range(len(aggNodeList)):
        if (removedFlag[i] == False):
            if (type(aggNodeList[i]) == list):
                newPath.append(path[aggNodeList[i][0]])
            else:
                newPath.append(path[aggNodeList[i]])

    # 对于被移除的共线点，找到其所在的线段
    locatedSeg = []
    # 把没有移除的点的序号记一下
    pathPre = []
    pathSuc = []
    # 查找移除点之前和之后一个removeFlag为False的对应aggNode，得到对应线段
    for i in range(len(removedFlag)):
        # Log the prev that is not removed
        if (removedFlag[i] == False):
            pathPre.append(i)
        else:
            pathPre.append(pathPre[-1])
        # Log the next that is not removed
        if (removedFlag[len(removedFlag) - 1 - i] == False):
            pathSuc.insert(0, len(removedFlag) - 1 - i)
        else:
            pathSuc.insert(0, pathSuc[0])

    for i in range(len(removedFlag)):
        if (removedFlag[i] == False):
            locatedSeg.append(None)
            para = []
        else:
            startPt = None
            if (type(aggNodeList[pathPre[i]]) == list):
                startPt = path[aggNodeList[pathPre[i]][0]]
            else:
                startPt = path[aggNodeList[pathPre[i]]]
            endPt = None
            if (type(aggNodeList[pathSuc[i]]) == list):
                endPt = path[aggNodeList[pathSuc[i]][0]]
            else:
                endPt = path[aggNodeList[pathSuc[i]]]
            locatedSeg.append([startPt, endPt])

    return {
        'newPath': newPath,
        'aggNodeList': aggNodeList,
        'removedFlag': removedFlag,
        'locatedSeg': locatedSeg
    }

def ptSetPath2Poly(path, polygons:dict, polyFieldName = 'polygon', pathDegenedFlag: bool = True):
    """Given a sequence and a dictionary of polygons, finds the intersection points between path and polygons

    Parameters
    ----------
    path: list[pt], required
        A list of points as a sequence
    polygons: dict, required
        A dictionary, each key is the ID of polygon, the field of polygon is in `polyFieldName`
    polyFieldName: string, optional, default 'polygon'
        Default field name for polygon

    Return
    ------
    list of dict
        A list of dictionaries, each includes the information of a segment/point, a list of polygon IDs that the segment belongs to

    """

    if (polygons == None):
        raise MissingParameterError("ERROR: Missing required field 'polygons'.")

    # NOTE: 简化线段，去掉穿越点，如果已经处理过了，就不用重复计算了
    if (not pathDegenedFlag):
        path = pathRemoveDegen(path)['newPath']

    # First, for each leg in the path, find the individual polygons intersect with the leg
    actions = []
    accMileage = 0

    for i in range(len(path) - 1):
        # seg[0]的mileage更小
        seg = [path[i], path[i + 1]]

        # NOTE: 准备用segment tree
        # NOTE: For now use the naive way - checking the bounding box
        for pID in polygons:
            # 根据Seg和poly的相交情况做判断
            segIntPoly = intSeg2Poly(seg = seg, poly = polygons[pID][polyFieldName], detailFlag = True)
            # 如果相交得到多个部分，则分别进行处理

            ints = []
            if (type(segIntPoly) == list):
                for intPart in segIntPoly:
                    ints.append(intPart)
            else:
                ints = [segIntPoly]

            for intPart in ints:
                if (intPart['status'] == 'NoCross'):
                    # No intersection pass
                    pass

                elif (intPart['status'] == 'Cross' and intPart['intersectType'] == 'Point'):
                    intPt = intPart['intersect']

                    # 距离seg[0]有多远，加入mileage
                    m = distEuclideanXY(seg[0], intPt)
                    actions.append({
                        'pt': intPt,
                        'action': 'touch',
                        'polyID': pID,
                        'mileage': accMileage + m
                    })

                elif (intPart['status'] == 'Cross' and intPart['intersectType'] == 'Segment'):

                    # 线段和polygon的两个交点，分别判断是不是在polygon的内部
                    intPt1 = intPart['intersect'][0]
                    intPt2 = intPart['intersect'][1]
                    intPt1InnerFlag = False
                    intPt2InnerFlag = False
                    if (isPtInPoly(intPt1, polygons[pID][polyFieldName], interiorOnly=True)):
                        intPt1InnerFlag = True
                    if (isPtInPoly(intPt2, polygons[pID][polyFieldName], interiorOnly=True)):
                        intPt2InnerFlag = True

                    # 两个端点的mileage
                    m1 = distEuclideanXY(seg[0], intPt1)
                    m2 = distEuclideanXY(seg[0], intPt2)

                    if (m1 > m2):
                        m1, m2 = m2, m1
                        intPt1, intPt2 = intPt2, intPt1
                        intPt1InnerFlag, intPt2InnerFlag = intPt2InnerFlag, intPt1InnerFlag

                    if (abs(m1 - m2) <= ERRTOL['distPt2Pt']):
                        # 交点距离太近可能是误判
                        actions.append({
                            'pt': intPt1,
                            'action': 'touch',
                            'polyID': pID,
                            'mileage': accMileage + m1
                        })
                    else:
                        # 如果第一个点在poly内，第二个在poly外
                        # m1 => inside, m2 => leave
                        if (intPt1InnerFlag and not intPt2InnerFlag):
                            actions.append({
                                'pt': intPt2,
                                'action': 'leave',
                                'polyID': pID,
                                'mileage': accMileage + m2,
                            })

                        # 如果第一个点在poly外，第二个点在poly内
                        # m1 => enter, m2 => inside
                        elif (not intPt1InnerFlag and intPt2InnerFlag):
                            actions.append({
                                'pt': intPt1,
                                'action': 'enter',
                                'polyID': pID,
                                'mileage': accMileage + m1,
                            })

                        # 如果两点都在内部，整段折线都在内部
                        elif (intPt1InnerFlag and intPt2InnerFlag):
                            pass

                        # 如果俩点都在外面，只有可能是两个转折点都在边缘上，一进一出
                        elif (not intPt1InnerFlag and not intPt2InnerFlag):
                            actions.append({
                                'pt': intPt1,
                                'action': 'enter',
                                'polyID': pID,
                                'mileage': accMileage + m1,
                            })
                            actions.append({
                                'pt': intPt2,
                                'action': 'leave',
                                'polyID': pID,
                                'mileage': accMileage + m2,
                            })
    
        accMileage += distEuclideanXY(seg[0], seg[1])

    actions = sorted(actions, key = lambda d: d['mileage'])

    return actions

# NOTE: 精度不够
def segSetPath2Circle(path: list, circles: dict, pathDegenedFlag: bool = True):
    if (not pathDegenedFlag):
        path = pathRemoveDegen(path)['newPath']

    # Step 0: turnPts =========================================================
    # NOTE: 只有出现了转折点本身在一个多边形的边缘上才需要记录tangle的形式，否则都会作为seg的一部分
    turnPts = {
        0: {
            'pt': path[0],
            'tangCircle': [],
            'inerCircle': []
        }
    }
    for i in range(1, len(path) - 1):
        pt = path[i]
        tangCircle = []
        inerCircle = []
        for p in circles:
            d2Circle = distEuclideanXY(pt, circles[p]['center'])
            if (d2Circle < circles[p]['radius'] - ERRTOL['distPt2Poly']):
                inerCircle.append(p)            
            if (circles[p]['radius'] + ERRTOL['distPt2Poly'] >= d2Circle >= circles[p]['radius'] - ERRTOL['distPt2Poly']):
                tangCircle.append(p)
                if (p not in inerCircle):
                    inerCircle.append(p)
        turnPts[i] = {
            'pt': path[i],
            'tangCircle': tangCircle,
            'inerCircle': inerCircle,
        }
    turnPts[len(path) - 1] = {
        'pt': path[-1],
        'tangCircle': [],
        'inerCircle': [],
    }

    # Step 1: Initialize ======================================================
    segIntCircle = {}
    accMileage = 0
    for i in range(len(path) - 1):
        segIntCircle[i] = {
            'seg': [path[i], path[i + 1]],
            'startMileage': accMileage,
            'intCircles': [],
            'stTangPt': None,
            'segID': i
        }
        if (len(turnPts[i]['tangCircle']) > 0):
            segIntCircle[i]['stTangPt'] = {
                'shape': path[i],
                'type': 'Point',
                'belong': turnPts[i]['inerCircle'],
                'mileage': accMileage,
                'segID': i
            }
        accMileage += distEuclideanXY(path[i], path[i + 1])
        segIntCircle[i]['endMileage'] = accMileage

    # Step 2: For each segment, gets polygon intersected ======================
    for i in segIntCircle:
        segIntCircle[i]['intMileageList'] = []
        st = segIntCircle[i]['startMileage']
        ed = segIntCircle[i]['endMileage']

        segIntCircle[i]['intMileageList'].append((st, -1, segIntCircle[i]['seg'][0], 'start'))

        for p in circles:
            # 如果有一段距离过短，视作点
            if (is2PtsSame(path[i], path[i + 1])):
                segIntCircle[i]['intMileageList'].append((st, p, path[i], 'tangle'))
            else:
                segInt = intSeg2Circle(seg = [path[i], path[i + 1]], circle = circles[p], detailFlag = True)
                # 如果交出一个线段，计算线段的起始结束mileage
                if (segInt['status'] == 'Cross' and segInt['intersectType'] == 'Segment'):
                    int1 = segInt['intersect'][0]
                    int2 = segInt['intersect'][1]
                    d1 = segInt['mileage'][0]
                    d2 = segInt['mileage'][1]
                    if (d1 < d2):
                        segIntCircle[i]['intMileageList'].append((d1 + st, p, int1, 'enter'))
                        segIntCircle[i]['intMileageList'].append((d2 + st, p, int2, 'leave'))
                    else:
                        segIntCircle[i]['intMileageList'].append((d2 + st, p, int2, 'enter'))
                        segIntCircle[i]['intMileageList'].append((d1 + st, p, int1, 'leave'))
                # 如果交出一个点，计算点的mileage
                elif (segInt['status'] == 'Cross' and segInt['intersectType'] == 'Point'):
                    intP = segInt['intersect']
                    dP = segInt['mileage']
                    segIntCircle[i]['intMileageList'].append((dP + st, p, intP, 'tangle'))

        # 对intMileageList进行排序
        segIntCircle[i]['intMileageList'].sort()
        segIntCircle[i]['intMileageList'].append((ed, -1, segIntCircle[i]['seg'][1], 'end'))

    # Step 3: Restore =========================================================
    segSet = []
    for i in segIntCircle:
        circleInside = []
        segIntCircle[i]['segSet'] = []
        curMileage = segIntCircle[i]['startMileage']
        curPt = segIntCircle[i]['seg'][0]
        if (segIntCircle[i]['stTangPt'] != None):
            segSet.append(segIntCircle[i]['stTangPt'])

        for k in range(len(segIntCircle[i]['intMileageList'])):
            # 下一个点
            newMileage = segIntCircle[i]['intMileageList'][k][0]
            newPt = segIntCircle[i]['intMileageList'][k][2]

            # 如果mileage不增长，则不会单独交一段出来，除非是有tangle
            if (abs(newMileage - curMileage) > ERRTOL['distPt2Pt']):
                segSet.append({
                    'shape': [curPt, newPt],
                    'type': 'Segment',
                    'belong': [k for k in circleInside],
                    'mileage': [curMileage, newMileage],
                    'segID': i
                    })
                curMileage = newMileage
                curPt = newPt

            if (segIntCircle[i]['intMileageList'][k][3] == 'enter'):
                circleInside.append(segIntCircle[i]['intMileageList'][k][1])

            elif (segIntCircle[i]['intMileageList'][k][3] == 'leave'):
                circleInside.remove(segIntCircle[i]['intMileageList'][k][1])

    return segSet

def segSetPath2Poly(path: list, polygons: dict, polyFieldName: str = 'polygon', pathDegenedFlag: bool = True):
    """Given a sequence and a dictionary of polygons, finds the intersection between path and polygons

    Parameters
    ----------
    path: list[pt], required
        A list of points as a sequence
    polygons: dict, required
        A dictionary, each key is the ID of polygon, the field of polygon is in `polyFieldName`
    polyFieldName: string, optional, default 'polygon'
        Default field name for polygon
    pathDegenedFlag: boolean, optional, default False
        True if the sequence has already been processed to remove degenerated points.

    Return
    ------
    list of dict
        A list of dictionaries, each includes the information of a segment/point, a list of polygon IDs that the segment belongs to

    """

    # NOTE: 简化线段，去掉穿越点，如果已经处理过了，就不用重复计算了
    if (not pathDegenedFlag):
        path = pathRemoveDegen(path)['newPath']

    # Step 0: turnPts =========================================================
    # NOTE: 每个poly都需要至少一个seg
    # NOTE: 只有出现了转折点本身在一个多边形的边缘上才需要记录tangle的形式，否则都会作为seg的一部分
    turnPts = {}
    for i in range(len(path)):
        pt = path[i]
        # 记录到每个polygon的距离，找到最近的那个，得是它的交点
        tansPolys = []
        inerPolys = []  
        closestIdx = None
        closestDist = float('inf')
        foundClosest = False
        for p in polygons:
            d2Edge = distPt2Path(pt = pt, path = polygons[p][polyFieldName], closedFlag = True)
            # 找到最近的
            if (d2Edge < closestDist):
                closestDist = d2Edge
                closestIdx = p
            if (d2Edge <= ERRTOL['distPt2Poly']):
                tansPolys.append(p)
                foundClosest = True
                inerPolys.append(p)
            if (p not in inerPolys and isPtInPoly(pt=pt, poly=polygons[p][polyFieldName])):
                inerPolys.append(p)
        if (foundClosest == False):
            warnings.warn(f"WARNING: Distance exceeds error: {closestDist}")
            tansPolys.append(closestIdx)
            inerPolys.append(closestIdx)
        turnPts[i] = {
            'pt': path[i],
            'tansPolys': tansPolys,
            'inerPolys': inerPolys
        }

    # Step 1: Initialize ======================================================
    segIntPoly = {}
    accMileage = 0
    for i in range(len(path) - 1):
        segIntPoly[i] = {
            'seg': [path[i], path[i + 1]],
            'startMileage': accMileage,
            'intPolys': [],
            'stTangPt': None,
        }
        if (len(turnPts[i]['tansPolys']) > 0):
            segIntPoly[i]['stTangPt'] = {
                'shape': path[i],
                'type': 'Point',
                'belong': turnPts[i]['inerPolys'],
                'mileage': accMileage
            }
        accMileage += distEuclideanXY(path[i], path[i + 1])
        segIntPoly[i]['endMileage'] = accMileage

    # Step 2: For each segment, gets polygon intersected ======================
    for i in segIntPoly:
        segIntPoly[i]['intMileageList'] = []
        st = segIntPoly[i]['startMileage']
        ed = segIntPoly[i]['endMileage']

        segIntPoly[i]['intMileageList'].append((st, -1, segIntPoly[i]['seg'][0], 'start'))

        for p in polygons:
            segInt = intSeg2Poly([path[i], path[i + 1]], polygons[p][polyFieldName])
            # 如果交出多个来的话，分别计算
            if (type(segInt) == list):
                for s in segInt:
                    # 如果交出一个线段，计算线段的起始结束mileage
                    if (s['status'] == 'Cross' and s['intersectType'] == 'Segment'):
                        int1 = s['intersect'][0]
                        int2 = s['intersect'][1]
                        d1 = distEuclideanXY(segIntPoly[i]['seg'][0], int1)
                        d2 = distEuclideanXY(segIntPoly[i]['seg'][0], int2)
                        if (d1 < d2):
                            segIntPoly[i]['intMileageList'].append((d1 + st, p, int1, 'enter'))
                            segIntPoly[i]['intMileageList'].append((d2 + st, p, int2, 'leave'))
                        else:
                            segIntPoly[i]['intMileageList'].append((d2 + st, p, int2, 'enter'))
                            segIntPoly[i]['intMileageList'].append((d1 + st, p, int1, 'leave'))
                            
                    # 如果交出一个点，计算点的mileage, 这个点不能是两边端点
                    elif (s['status'] == 'Cross' and s['intersectType'] == 'Point'):
                        intP = s['intersect']
                        if (not is2PtsSame(intP, segIntPoly[i]['seg'][0]) and not is2PtsSame(intP, segIntPoly[i]['seg'][1])):
                            dP = distEuclideanXY(segIntPoly[i]['seg'][0], intP)
                            segIntPoly[i]['intMileageList'].append((dP + st, p, intP, 'tangle'))

            # 如果交出一个线段，计算线段的起始结束mileage
            elif (segInt['status'] == 'Cross' and segInt['intersectType'] == 'Segment'):
                int1 = segInt['intersect'][0]
                int2 = segInt['intersect'][1]
                d1 = distEuclideanXY(segIntPoly[i]['seg'][0], int1)
                d2 = distEuclideanXY(segIntPoly[i]['seg'][0], int2)
                if (d1 < d2):
                    segIntPoly[i]['intMileageList'].append((d1 + st, p, int1, 'enter'))
                    segIntPoly[i]['intMileageList'].append((d2 + st, p, int2, 'leave'))
                else:
                    segIntPoly[i]['intMileageList'].append((d2 + st, p, int2, 'enter'))
                    segIntPoly[i]['intMileageList'].append((d1 + st, p, int1, 'leave'))
            # 如果交出一个点，计算点的mileage
            elif (segInt['status'] == 'Cross' and segInt['intersectType'] == 'Point'):
                intP = segInt['intersect']
                dP = distEuclideanXY(segIntPoly[i]['seg'][0], intP)
                segIntPoly[i]['intMileageList'].append((dP + st, p, intP, 'tangle'))

        # 对intMileageList进行排序
        segIntPoly[i]['intMileageList'].sort()
        segIntPoly[i]['intMileageList'].append((ed, -1, segIntPoly[i]['seg'][1], 'end'))

    # Step 3: Restore =========================================================
    segSet = []
    for i in segIntPoly:
        polyInside = []
        segIntPoly[i]['segSet'] = []
        curMileage = segIntPoly[i]['startMileage']
        curPt = segIntPoly[i]['seg'][0]
        if (segIntPoly[i]['stTangPt'] != None):
            segSet.append(segIntPoly[i]['stTangPt'])

        for k in range(len(segIntPoly[i]['intMileageList'])):
            # 下一个点
            newMileage = segIntPoly[i]['intMileageList'][k][0]
            newPt = segIntPoly[i]['intMileageList'][k][2]

            # 如果mileage不增长，则不会单独交一段出来，除非是有tangle
            if (abs(newMileage - curMileage) > ERRTOL['distPt2Pt']):
                segSet.append({
                    'shape': [curPt, newPt],
                    'type': 'Segment',
                    'belong': [k for k in polyInside],
                    'mileage': [curMileage, newMileage]
                    })
                curMileage = newMileage
                curPt = newPt

            if (segIntPoly[i]['intMileageList'][k][3] == 'enter'):
                polyInside.append(segIntPoly[i]['intMileageList'][k][1])

            elif (segIntPoly[i]['intMileageList'][k][3] == 'leave'):
                polyInside.remove(segIntPoly[i]['intMileageList'][k][1])

    return segSet
