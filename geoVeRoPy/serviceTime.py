import networkx as nx
import gurobipy as grb

from .geometry import *
from .ring import *
from .common import *
from .plot import *

def c2cServicePathAdaptIter(
    startPt: pt, 
    endPt: pt, 
    seq: list, 
    circles: dict, 
    velocity, 
    serviceTime, 
    adaptErr = ERRTOL['deltaDist'], 
    initLod: int = 12):
    # NOTE: seq does not include startPt/endPt

    def getLocByDeg(circle, deg):
        return (
            circle['center'][0] + circle['radius'] * math.cos(math.radians(deg)),
            circle['center'][1] + circle['radius'] * math.sin(math.radians(deg))
        )

    # calculate alphas
    alpha = []
    # 先计算第一个位置是不是在圆内
    if (distEuclideanXY(startPt, circles[seq[0]]['center']) <= circles[seq[0]]['radius']):
        alpha.append(1)
    else:
        alpha.append(0)

    # 再分别计算每个是不是在圆内
    left = []
    right = [i for i in seq]
    for i in range(len(seq) - 1):
        left.append(right[0])
        right.pop(0)

        # 确认每个left里的元素在right里都没有配对
        insideFlag = False
        for k in left:
            if (k in right):
                insideFlag = True
                break
        # 如果在圆内，alpha定为1，否则为0
        if (insideFlag):
            alpha.append(1)
        else:
            alpha.append(0)

    # 计算最后一个位置在不在园内
    if (distEuclideanXY(circles[seq[-1]]['center'], endPt) <= circles[seq[-1]]['radius']):
        alpha.append(1)
    else:
        alpha.append(0)

    # print(alpha)

    # Initialize
    G = nx.Graph()
    circleRings = []
    tau = {}

    # circleRing is keyed by index, valued by [degree, loc]
    for c in seq:
        circleRing = Ring()
        for i in range(initLod):
            deg = i * 360 / initLod
            circleRing.append(RingNode(
                key = i, 
                deg = deg, 
                loc = getLocByDeg(circles[c], deg)))
        circleRings.append(circleRing)

    # startPt to the first polygon
    cur = circleRings[0].head
    while (True):
        d = distEuclideanXY(startPt, cur.loc)
        t = max(alpha[0] * serviceTime, d / velocity)
        G.add_edge('s', (0, seq[0], cur.key), weight = t)
        tau['s', (0, seq[0], cur.key)] = d
        cur = cur.next
        if (cur.key == circleRings[0].head.key):
            break

    # If more than one polygon btw startPt and endPt
    for i in range(len(seq) - 1):
        curI = circleRings[i].head
        while (True):
            curJ = circleRings[i + 1].head
            while (True):
                d = distEuclideanXY(curI.loc, curJ.loc)
                t = max(alpha[i + 1] * serviceTime, d / velocity)
                G.add_edge((i, seq[i], curI.key), (i + 1, seq[i + 1], curJ.key), weight = t)
                tau[(i, seq[i], curI.key), (i + 1, seq[i + 1], curJ.key)] = d
                curJ = curJ.next
                if (curJ.key == circleRings[i + 1].head.key):
                    break
            curI = curI.next
            if (curI.key == circleRings[i].head.key):
                break

    # last polygon to endPt
    cur = circleRings[-1].head
    while (True):
        d = distEuclideanXY(cur.loc, endPt)
        t = max(alpha[-1] * serviceTime, d / velocity)
        G.add_edge((len(seq) - 1, seq[-1], cur.key), 'e', weight = t)
        tau[(len(seq) - 1, seq[-1], cur.key), 'e'] = d
        cur = cur.next
        if (cur.key == circleRings[-1].head.key):
            break

    sp = nx.dijkstra_path(G, 's', 'e')

    # 除了第0项是's'，第-1项是'e'，剩余的第i项
    # sp[i] => (seqIdx, circleIdx, edgeKey)
    # 第一项是在seq中的序号，同时是circleRings的序号
    # 第二项是圆的标号
    # 第三项是边缘上的点的键值

    # print(sp)

    travelTime = 0
    # 第一段
    travelTime += tau['s', sp[1]]
    # 第二段到倒数第二段
    for i in range(1, len(sp) - 2):
        travelTime += tau[sp[i], sp[i + 1]]
    # 最后一段，如果到达点在circles[seq[-1]]内部，则取max，否则取L/v
    travelTime += tau[sp[-2], 'e']

    # Find detailed location
    refineFlag = True
    iterNum = 0
    # while (iterNum <= 10):
    while(refineFlag):
        # sp[0] is startLoc
        # sp[-1] is endLoc
        for i in range(1, len(sp) - 1):
            # Find current shortest intersecting point
            # sp[i] => (seqIdx, circleIdx, edgeKey)
            seqIdx = sp[i][0]
            circleIdx = sp[i][1]
            edgeKey = sp[i][2]

            # Insert two new points before and after this point
            p = circleRings[seqIdx].query(edgeKey)
            pPrev = p.prev
            pNext = p.next

            # Get deg before and after current deg
            pPrevMidDeg = None
            pNextMidDeg = None

            # If p.prev.deg > p.deg => p.prev -= 360
            # If p.next.deg < p.deg => p.next += 360
            pPrevDeg = p.prev.deg if (p.prev.deg < p.deg) else p.prev.deg - 360
            pNextDeg = p.next.deg if (p.next.deg > p.deg) else p.next.deg + 360
            pPrevMidDeg = p.prev.deg + (p.deg - p.prev.deg) / 2
            pNextMidDeg = p.deg + (p.next.deg - p.deg) / 2
            if (pPrevMidDeg < 0):
                pPrevMidDeg += 360
            if (pNextMidDeg > 360):
                pNextMidDeg -= 360

            pPrevMidLoc = getLocByDeg(circles[circleIdx], pPrevMidDeg)
            pNextMidLoc = getLocByDeg(circles[circleIdx], pNextMidDeg)

            pPrevMid = RingNode(circleRings[seqIdx].count, deg = pPrevMidDeg, loc = pPrevMidLoc)
            pNextMid = RingNode(circleRings[seqIdx].count + 1, deg = pNextMidDeg, loc = pNextMidLoc)

            circleRings[seqIdx].insert(p, pNextMid)
            circleRings[seqIdx].insert(pPrev, pPrevMid)

        # New start
        cur = circleRings[0].head
        while (True):
            if (('s', (0, seq[0], p.key)) not in G.edges):
                d = distEuclideanXY(startPt, cur.loc)
                t = max(alpha[0] * serviceTime, d / velocity)
                G.add_edge('s', (0, seq[0], cur.key), weight = t)
                tau['s', (0, seq[0], cur.key)] = d
            cur = cur.next
            if (cur.key == circleRings[0].head.key):
                break

        # In between
        for i in range(len(seq) - 1):
            curI = circleRings[i].head
            while (True):
                curJ = circleRings[i + 1].head
                while (True):
                    if (((i, seq[i], curI.key), (i + 1, seq[i + 1], curJ.key)) not in G.edges):
                        d = distEuclideanXY(curI.loc, curJ.loc)
                        t = max(alpha[i + 1] * serviceTime, d / velocity)
                        G.add_edge((i, seq[i], curI.key), (i + 1, seq[i + 1], curJ.key), weight = t)
                        tau[(i, seq[i], curI.key), (i + 1, seq[i + 1], curJ.key)] = d
                    curJ = curJ.next
                    if (curJ.key == circleRings[i + 1].head.key):
                        break
                curI = curI.next
                if (curI.key == circleRings[i].head.key):
                    break

        cur = circleRings[-1].head
        while (True):
            if (((len(seq) - 1, seq[-1], cur.key), 'e') not in G.edges):
                d = distEuclideanXY(cur.loc, endPt)
                t = max(alpha[-1] * serviceTime, d / velocity)
                G.add_edge((len(seq) - 1, seq[-1], cur.key), 'e', weight = t)
                tau[(len(seq) - 1, seq[-1], cur.key), 'e'] = d
            cur = cur.next
            if (cur.key == circleRings[-1].head.key):
                break

        sp = nx.dijkstra_path(G, 's', 'e')
        # print(sp)

        newTravelTime = 0
        # 第一段
        newTravelTime += tau['s', sp[1]]
        # 第二段到倒数第二段
        for i in range(1, len(sp) - 2):
            newTravelTime += tau[sp[i], sp[i + 1]]
        # 最后一段，如果到达点在circles[seq[-1]]内部，则取max，否则取L/v
        newTravelTime += tau[sp[-2], 'e']

        if (abs(newTravelTime - travelTime) <= adaptErr):
            refineFlag = False

        travelTime = newTravelTime

        # 测试
        # fig, ax = None, None
        # for i in circles:
        #     fig, ax = plotCircle(
        #         fig = fig,
        #         ax = ax,
        #         center = circles[i]['center'],
        #         radius = circles[i]['radius'],
        #         edgeColor = 'black',
        #         fillColor = 'gray',
        #         boundingBox = (-10, 110, -10, 110))
        # locs = [startPt, endPt]
        # for i in circleRings:
        #     for c in i.traverse():
        #         locs.append(c.loc)
        # fig, ax = plotLocs(
        #     fig = fig,
        #     ax = ax,
        #     locs = locs,
        #     locColor = 'red',
        #     locMarkerSize = 3)
        # locSeq = [startPt]
        # for i in range(1, len(sp) - 1):
        #     locSeq.append(circleRings[sp[i][0]].query(sp[i][2]).loc)
        # locSeq.append(endPt)
        # fig, ax = plotLocSeq(
        #     fig = fig,
        #     ax = ax,
        #     locSeq = locSeq,
        #     lineColor = 'blue')
        # fig.savefig(f"Iter_{iterNum}.png")

        iterNum += 1

    path = [startPt]
    for p in sp:
        if (p != 's' and p != 'e'):
            path.append(circleRings[p[0]].query(p[2]).loc)
    path.append(endPt)

    return {
        'path': path,
        'travelTime': travelTime,
        'tau': tau
    }
