import networkx as nx
import gurobipy as grb
import datetime

from .geometry import *
from .ring import *
from .curveArc import *
from .common import *
from .plot import *

def poly2PolyPath(startPt: pt, endPt: pt, polys: polys, algo: str = 'SOCP', **kwargs):
    
    """Given a starting point, a list of polys, and an ending point, returns a shortest route that starts from startPt, visits every polys in given order, and returns to the ending point.

    Parameters
    ----------
    startPt: pt, required, default None
        The coordinate which starts the path.
    endPt: pt, required, default None
        The coordinate which ends the path.
    polys: polys, required
        A list of polys to be visited in given sequence
    algo: str, optional, default as 'SOCP'
        Select the algorithm for calculating the shortest path. Options and required additional inputs are as follows:
            
        1) (default) 'SOCP', use Second-order Cone Programing method.
            - solver: str, optional, now only supports 'Gurobi'
            - timeLimit: int|float, additional stopping criteria
            - gapTolerance: int|float, additional stopping criteria
            - outputFlag: bool, True if turn on the log output from solver. Default to be False
        2) 'AdaptIter', use adapt iteration algorithm
            - errorTol: float, optional, error tolerance
    **kwargs: optional
        Provide additional inputs for different `edges` options and `algo` options

    Returns
    -------
    dict
        Two fields in the dictionary, 'dist' indicates the distance of the path, 'path' indicates the travel path.
    """

    # Sanity check ============================================================
    if (algo == 'AdaptIter'):
        adaptErr = ERRTOL['deltaDist']
        if ('adaptErr' in kwargs):
            adaptErr = kwargs['adaptErr']
        res = _poly2PolyPathAdaptIter(startPt, endPt, polys, adaptErr)
    elif (algo == 'SOCP'):
        outputFlag = False
        if ('outputFlag' in kwargs):
            outputFlag = kwargs['outputFlag']
        gapTol = None
        if ('gapTol' in kwargs):
            gapTol = kwargs['gapTol']
        timeLimit = None
        if ('timeLimit' in kwargs):
            timeLimit = kwargs['timeLimit']
        res = _poly2PolyPathGurobi(startPt, endPt, polys, outputFlag, gapTol, timeLimit)
    else:
        raise UnsupportedInputError("ERROR: Not support by vrpSolver for now.")

    return {
        'path': res['path'],
        'dist': res['dist']
    }

def _poly2PolyPathAdaptIter(startPt: pt, endPt: pt, polys: polys, adaptErr):

    """Given a list of points, each belongs to a neighborhood of a node, find the shortest path between each steps

    Parameters
    ----------

    polys: list of polygons, required
        A list of polygons to be visited
    solver: string, optional, default AVAIL_SOLVER
        The commercial solver used to solve the minimum cost flow problem

    """

    # First, create a ring, to help keying each extreme points of polygons
    tau = {}

    # Initialize
    G = nx.Graph()
    polyRings = []

    for poly in polys:
        polyRing = Ring()
        for i in range(len(poly)):
            polyRing.append(RingNode(i, poly[i]))
        polyRings.append(polyRing)

    # startPt to the first polygon
    cur = polyRings[0].head
    while (True):
        d = distEuclideanXY(startPt, cur.value)
        tau['s', (0, cur.key)] = d
        G.add_edge('s', (0, cur.key), weight = d)
        cur = cur.next
        if (cur.key == polyRings[0].head.key):
            break

    # If more than one polygon btw startPt and endPt
    for i in range(len(polys) - 1):
        curI = polyRings[i].head
        while (True):
            curJ = polyRings[i + 1].head
            while (True):
                d = distEuclideanXY(curI.value, curJ.value)
                tau[(i, curI.key), (i + 1, curJ.key)] = d
                G.add_edge((i, curI.key), (i + 1, curJ.key), weight = d)
                curJ = curJ.next
                if (curJ.key == polyRings[i + 1].head.key):
                    break
            curI = curI.next
            if (curI.key == polyRings[i].head.key):
                break

    # last polygon to endPt
    cur = polyRings[-1].head
    while (True):
        d = distEuclideanXY(cur.value, endPt)
        tau[(len(polys) - 1, cur.key), 'e'] = d
        G.add_edge((len(polys) - 1, cur.key), 'e', weight = d)
        cur = cur.next
        if (cur.key == polyRings[len(polys) - 1].head.key):
            break

    sp = nx.dijkstra_path(G, 's', 'e')

    dist = distEuclideanXY(startPt, polyRings[sp[1][0]].query(sp[1][1]).value)
    for i in range(1, len(sp) - 2):
        dist += tau[(sp[i][0], sp[i][1]), (sp[i + 1][0], sp[i + 1][1])]
    dist += distEuclideanXY(polyRings[sp[-2][0]].query(sp[-2][1]).value, endPt)
    
    # Find detailed location
    refineFlag = True
    iterNum = 0
    while (refineFlag):
        for i in range(1, len(sp) - 1):
            # Find current shortest intersecting point
            polyIdx = sp[i][0]
            exPtIdx = sp[i][1]

            # Insert two new points before and after this point
            p = polyRings[polyIdx].query(exPtIdx)
            pPrev = p.prev
            pNext = p.next

            pPrevMidPt = [(pPrev.value[0] + (p.value[0] - pPrev.value[0]) / 2), (pPrev.value[1] + (p.value[1] - pPrev.value[1]) / 2)]
            pPrevMid = RingNode(polyRings[polyIdx].count, pPrevMidPt)
            pNextMidPt = [(p.value[0] + (pNext.value[0] - p.value[0]) / 2), (p.value[1] + (pNext.value[1] - p.value[1]) / 2)]
            pNextMid = RingNode(polyRings[polyIdx].count + 1, pNextMidPt)

            polyRings[polyIdx].insert(p, pNextMid)
            polyRings[polyIdx].insert(pPrev, pPrevMid)

        # Simplify the graph
        G = nx.Graph()

        # New start
        startPolyPt = polyRings[sp[1][0]].query(sp[1][1])
        startNearPt = [startPolyPt.prev.prev, startPolyPt.prev, startPolyPt, startPolyPt.next, startPolyPt.next.next]
        for p in startNearPt:
            d = distEuclideanXY(startPt, p.value)
            G.add_edge('s', (0, p.key), weight = d)

        # In between
        for i in range(1, len(sp) - 2):
            polyIdx = sp[i][0]
            polyNextIdx = sp[i + 1][0]
            exPtIdx = sp[i][1]
            exPtNextIdx = sp[i + 1][1]

            ptI = polyRings[polyIdx].query(exPtIdx)
            ptNearI = [ptI.prev.prev, ptI.prev, ptI, ptI.next, ptI.next.next]
            ptJ = polyRings[polyNextIdx].query(exPtNextIdx)
            ptNearJ = [ptJ.prev.prev, ptJ.prev, ptJ, ptJ.next, ptJ.next.next]
            for kI in ptNearI:
                for kJ in ptNearJ:
                    d = None
                    if (((polyIdx, kI.key), (polyNextIdx, kJ.key)) in tau):
                        d = tau[((polyIdx, kI.key), (polyNextIdx, kJ.key))]
                    else:
                        d = distEuclideanXY(kI.value, kJ.value)
                        tau[((polyIdx, kI.key), (polyNextIdx, kJ.key))] = d
                    G.add_edge((polyIdx, kI.key), (polyNextIdx, kJ.key), weight = d)

        # New end
        endPolyPt = polyRings[sp[-2][0]].query(sp[-2][1])
        endNearPt = [endPolyPt.prev.prev, endPolyPt.prev, endPolyPt, endPolyPt.next, endPolyPt.next.next]
        for p in endNearPt:
            d = distEuclideanXY(p.value, endPt)
            G.add_edge((len(polys) - 1, p.key), 'e', weight = d)

        sp = nx.dijkstra_path(G, 's', 'e')

        newDist = distEuclideanXY(startPt, polyRings[sp[1][0]].query(sp[1][1]).value)
        for i in range(1, len(sp) - 2):
            newDist += tau[(sp[i][0], sp[i][1]), (sp[i + 1][0], sp[i + 1][1])]
        newDist += distEuclideanXY(polyRings[sp[-2][0]].query(sp[-2][1]).value, endPt)

        if (abs(newDist - dist) <= adaptErr):
            refineFlag = False

        dist = newDist

    path = [startPt]
    for p in sp:
        if (p != 's' and p != 'e'):
            path.append(polyRings[p[0]].query(p[1]).value)
    path.append(endPt)

    return {
        'path': path,
        'dist': dist
    }

def _poly2PolyPathGurobi(startPt: pt, endPt: pt, polys: polys, outputFlag = False, gapTol = None, timeLimit = None):
    segs = []
    for i in range(len(polys)):
        segs.append([])
        for k in range(-1, len(polys[i]) - 1):
            segs[i].append([polys[i][k], polys[i][k + 1]])
            
    return _seg2SegPathGurobi(
        startPt = startPt, 
        endPt = endPt, 
        segs = segs, 
        outputFlag = outputFlag, 
        gapTol = gapTol, 
        timeLimit = timeLimit)

def _seg2SegPathGurobi(startPt: pt, endPt: pt, segs: list[line], outputFlag = False, gapTol = None, timeLimit = None):
    try:
        import gurobipy as grb
    except(ImportError):
        raise ImportError("ERROR: Cannot find Gurobi")

    model = grb.Model("SOCP")
    model.setParam('OutputFlag', 0 if outputFlag == False else 1)

    if (gapTol != None):
        model.setParam('MIPGap', gapTol)
    if (timeLimit != None):
        model.setParam(grb.GRB.Param.TimeLimit, timeLimit)

    # Parameters ==============================================================
    allX = [startPt[0], endPt[0]]
    allY = [startPt[1], endPt[1]]
    for i in range(len(segs)):
        for j in range(len(segs[i])):
            allX.append(segs[i][j][0][0])
            allY.append(segs[i][j][0][1])
            allX.append(segs[i][j][1][0])
            allY.append(segs[i][j][1][1])
    lbX = min(allX) - 1
    lbY = min(allY) - 1
    ubX = max(allX) + 1
    ubY = max(allY) + 1

    # Decision variables ======================================================
    # (xi, yi) 为第i个seg上的坐标
    # index = 1, 2, ..., len(segs)
    x = {}
    y = {}
    for i in range(len(segs)):
        x[i] = model.addVar(vtype=grb.GRB.CONTINUOUS, name = "x_%s" % i, lb=lbX, ub=ubX)
        y[i] = model.addVar(vtype=grb.GRB.CONTINUOUS, name = "y_%s" % i, lb=lbY, ub=ubY)

    # e[i, j] 为binary，表示(xi, yi)处于第i个seg上的第j段
    # index i = 1, 2, ..., len(segs)
    # index j = 0, ..., len(segs[i]) - 1
    # lam[i, j] 为[0, 1]之间的值，表示第i段是处于对应e[i, j]上的位置，若e[i, j] = 0，则lam[i, j] = 0
    e = {}
    lam = {}    
    for i in range(len(segs)):
        for j in range(len(segs[i])):
            e[i, j] = model.addVar(vtype=grb.GRB.BINARY, name="e_%s_%s" % (i, j))
            lam[i, j] = model.addVar(vtype=grb.GRB.CONTINUOUS, name="lam_%s_%s" % (i, j))

    # d[i] 为第i个到第i+1个坐标的距离, dx[i], dy[i] 为对应辅助变量
    # Distance from ((xi, yi)) to (x[i + 1], y[i + 1]), 
    # where startPt = (x[0], y[0]) and endPt = (x[len(circles) + 1], y[len(circles) + 1])
    d = {}
    for i in range(len(segs) + 1):
        d[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'd_%s' % i)
    model.setObjective(grb.quicksum(d[i] for i in range(len(segs) + 1)), grb.GRB.MINIMIZE)

    # Aux vars - distance between (x, y)
    dx = {}
    dy = {}
    for i in range(len(segs) + 1):
        dx[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'dx_%s' % i, lb = -float('inf'), ub = float('inf'))
        dy[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'dy_%s' % i, lb = -float('inf'), ub = float('inf'))

    # Constraints =============================================================
    # (xi, yi)必须在其中一段上
    for i in range(len(segs)):
        model.addConstr(grb.quicksum(e[i, j] for j in range(len(segs[i]))) == 1)

    # 具体(xi, yi)的位置，lam[i, j]在e[i, j] = 0的段上不激活
    for i in range(len(segs)):
        model.addConstr(x[i] == grb.quicksum(
            e[i, j] * segs[i][j][0][0] + lam[i, j] * (segs[i][j][1][0] - segs[i][j][0][0])
            for j in range(len(segs[i]))))
        model.addConstr(y[i] == grb.quicksum(
            e[i, j] * segs[i][j][0][1] + lam[i, j] * (segs[i][j][1][1] - segs[i][j][0][1])
            for j in range(len(segs[i]))))
    for i in range(len(segs)):
        for j in range(len(segs[i])):
            model.addConstr(lam[i, j] <= e[i, j])

    # Aux constr - dx dy
    model.addConstr(dx[0] == x[0] - startPt[0])
    model.addConstr(dy[0] == y[0] - startPt[1])
    for i in range(len(segs) - 1):
        model.addConstr(dx[i + 1] == x[i + 1] - x[i])
        model.addConstr(dy[i + 1] == y[i + 1] - y[i])
    model.addConstr(dx[len(segs)] == endPt[0] - x[len(segs) - 1])
    model.addConstr(dy[len(segs)] == endPt[1] - y[len(segs) - 1])

    # Distance btw visits
    for i in range(len(segs) + 1):
        model.addQConstr(d[i] ** 2 >= dx[i] ** 2 + dy[i] ** 2)

    # model.write("SOCP.lp")
    model.optimize()

    # Post-processing =========================================================
    ofv = None
    path = [startPt]
    if (model.status == grb.GRB.status.OPTIMAL):
        solType = 'IP_Optimal'
        ofv = model.getObjective().getValue()
        for i in x:
            path.append((x[i].x, y[i].x))
        path.append(endPt)
        gap = 0
        lb = ofv
        ub = ofv
        runtime = model.Runtime
    elif (model.status == grb.GRB.status.TIME_LIMIT):
        solType = 'IP_TimeLimit'
        ofv = model.ObjVal
        for i in x:
            path.append((x[i].x, y[i].x))
        path.append(endPt)
        gap = model.MIPGap
        lb = model.ObjBoundC
        ub = model.ObjVal
        runtime = model.Runtime
    return {
        'path': path,
        'dist': ofv,
        'runtime': runtime
    }

def circle2CirclePath(startPt: pt, endPt: pt, circles: list[dict], algo: str = 'SOCP', **kwargs):
    
    """Given a starting point, a list of circles, and an ending point, returns a shortest route that starts from startPt, visits every polys in given order, and returns to the ending point.

    Parameters
    ----------
    startPt: pt, required, default None
        The coordinate which starts the path.
    endPt: pt, required, default None
        The coordinate which ends the path.
    circles: dict, required
        A list of circles modeled by dictionaries to be visited in given sequence. Each circle is dictionary with two fields: 'radius' and 'center'.
    algo: str, optional, default as 'SOCP'
        Select the algorithm for calculating the shortest path. Options and required additional inputs are as follows:
            
        1) (default) 'SOCP', use Second-order Cone Programing method.
            - solver: str, optional, now supports 'Gurobi' and 'COPT'
            - timeLimit: int|float, additional stopping criteria
            - gapTolerance: int|float, additional stopping criteria
            - outputFlag: bool, True if turn on the log output from solver. Default to be False
    **kwargs: optional
        Provide additional inputs for different `edges` options and `algo` options

    Returns
    -------
    dict
        Two fields in the dictionary, 'dist' indicates the distance of the path, 'path' indicates the travel path.
    """

    # Sanity check ============================================================
    if (algo == None):
        raise MissingParameterError("ERROR: Missing required field `algo`.")

    if (algo == 'AdaptIter'):
        adaptErr = ERRTOL['deltaDist']
        if ('adaptErr' in kwargs):
            adaptErr = kwargs['adaptErr']
        initLod = 12
        if ('initLod' in kwargs):
            initLod = kwargs['initLod']
        res = _circle2CirclePathAdaptIter(startPt, endPt, circles, adaptErr, initLod)
    elif (algo == 'SOCP'):
        if ('solver' not in kwargs or kwargs['solver'] == 'Gurobi'):
            outputFlag = False
            if ('outputFlag' in kwargs):
                outputFlag = kwargs['outputFlag']
            # print(circles)
            res = _circle2CirclePathGurobi(startPt, endPt, circles, outputFlag)
        elif (kwargs['solver'] == 'COPT'):
            outputFlag = False
            if ('outputFlag' in kwargs):
                outputFlag = kwargs['outputFlag']
            res = _circle2CirclePathCOPT(startPt, endPt, circles, outputFlag)
    else:
        raise UnsupportedInputError("ERROR: Not support by vrpSolver for now.")

    return {
        'path': res['path'],
        'dist': res['dist']
    }

def _circle2CirclePathAdaptIter(startPt: pt, endPt: pt, circles: list[dict], adaptErr, initLod: int = 4):

    def getPtByDeg(circle, deg):
        return (
            circle['center'][0] + circle['radius'] * math.cos(math.radians(deg)),
            circle['center'][1] + circle['radius'] * math.sin(math.radians(deg))
        )

    G = nx.Graph()
    circleRings = []

    # circleRing is keyed by index, valued by [degree, pt]
    for c in circles:
        circleRing = Ring()
        for i in range(initLod):
            deg = i * 360 / initLod
            circleRing.append(RingNode(
                key = i, 
                deg = deg, 
                pt = getPtByDeg(c, deg)))
        circleRings.append(circleRing)

    # startPt to the first polygon
    cur = circleRings[0].head
    while (True):
        d = distEuclideanXY(startPt, cur.pt)
        G.add_edge('s', (0, cur.key), weight = d)
        cur = cur.next
        if (cur.key == circleRings[0].head.key):
            break

    # If more than one polygon btw startPt and endPt
    for i in range(len(circles) - 1):
        curI = circleRings[i].head
        while (True):
            curJ = circleRings[i + 1].head
            while (True):
                d = distEuclideanXY(curI.pt, curJ.pt)
                G.add_edge((i, curI.key), (i + 1, curJ.key), weight = d)
                curJ = curJ.next
                if (curJ.key == circleRings[i + 1].head.key):
                    break
            curI = curI.next
            if (curI.key == circleRings[i].head.key):
                break

    # last polygon to endPt
    cur = circleRings[-1].head
    while (True):
        d = distEuclideanXY(cur.pt, endPt)
        G.add_edge((len(circles) - 1, cur.key), 'e', weight = d)
        cur = cur.next
        if (cur.key == circleRings[len(circles) - 1].head.key):
            break

    sp = nx.dijkstra_path(G, 's', 'e')

    # sp[i] => (circleIdx, curKey)

    dist = distEuclideanXY(startPt, circleRings[sp[1][0]].query(sp[1][1]).pt)
    for i in range(1, len(sp) - 2):
        dist += distEuclideanXY(
            circleRings[sp[i][0]].query(sp[i][1]).pt,
            circleRings[sp[i + 1][0]].query(sp[i + 1][1]).pt)
    dist += distEuclideanXY(circleRings[sp[-2][0]].query(sp[-2][1]).pt, endPt)
    
    iterNum = 0

    # Find detailed location
    refineFlag = True
    iterNum = 0
    # while (iterNum <= 10):
    while(refineFlag):
        # sp[0] is startPt
        # sp[-1] is endPt
        for i in range(1, len(sp) - 1):
            # Find current shortest intersecting point
            circIdx = sp[i][0]
            inteKey = sp[i][1]

            # Insert two new points before and after this point
            p = circleRings[circIdx].query(inteKey)
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

            pPrevMidPt = getPtByDeg(circles[circIdx], pPrevMidDeg)
            pNextMidPt = getPtByDeg(circles[circIdx], pNextMidDeg)

            pPrevMid = RingNode(circleRings[circIdx].count, deg = pPrevMidDeg, pt = pPrevMidPt)
            pNextMid = RingNode(circleRings[circIdx].count + 1, deg = pNextMidDeg, pt = pNextMidPt)

            circleRings[circIdx].insert(p, pNextMid)
            circleRings[circIdx].insert(pPrev, pPrevMid)

        # New start
        for p in circleRings[sp[1][0]].traverse():
            if (('s', (0, p.key)) not in G.edges):
                d = distEuclideanXY(startPt, p.pt)
                G.add_edge('s', (0, p.key), weight = d)
        # In between
        for i in range(1, len(sp) - 2):
            circIdx = sp[i][0]
            circNextIdx = sp[i + 1][0]
            for kI in circleRings[circIdx].traverse():
                for kJ in circleRings[circNextIdx].traverse():
                    if (((circIdx, kI.key), (circNextIdx, kJ.key)) not in G.edges):
                        d = distEuclideanXY(kI.pt, kJ.pt)
                        G.add_edge((circIdx, kI.key), (circNextIdx, kJ.key), weight = d)
        for p in circleRings[sp[-2][0]].traverse():
            if (((len(circles) - 1, p.key), 'e') not in G.edges):
                d = distEuclideanXY(p.pt, endPt)
                G.add_edge((len(circles) - 1, p.key), 'e', weight = d)

        sp = nx.dijkstra_path(G, 's', 'e')

        newDist = distEuclideanXY(startPt, circleRings[sp[1][0]].query(sp[1][1]).pt)
        for i in range(1, len(sp) - 2):
            newDist += distEuclideanXY(
                circleRings[sp[i][0]].query(sp[i][1]).pt,
                circleRings[sp[i + 1][0]].query(sp[i + 1][1]).pt)
        newDist += distEuclideanXY(circleRings[sp[-2][0]].query(sp[-2][1]).pt, endPt)

        if (abs(newDist - dist) <= adaptErr):
            refineFlag = False

        dist = newDist

        iterNum += 1

    path = [startPt]
    for p in sp:
        if (p != 's' and p != 'e'):
            path.append(circleRings[p[0]].query(p[1]).pt)
    path.append(endPt)
    # print("Num of iter: ", iterNum)

    return {
        'path': path,
        'dist': dist
    }

def _circle2CirclePathGurobi(startPt: pt, endPt: pt, circles: list[dict], outputFlag: bool = False):

    model = grb.Model("SOCP")
    model.setParam('OutputFlag', 1 if outputFlag else 0)
    model.setParam('BarHomogeneous', 1)
    # model.setParam('BarConvTol', 1e-3)
    # model.setParam('PreSolve', 0)

    # Parameters ==============================================================
    # anchor starts from startPt, in between are a list of circles, ends with endPt
    anchor = [startPt]
    for i in range(len(circles)):
        anchor.append(circles[i]['center'])
    anchor.append(endPt)

    allX = [startPt[0], endPt[0]]
    allY = [startPt[1], endPt[1]]
    for i in range(len(circles)):
        allX.append(circles[i]['center'][0] - circles[i]['radius'])
        allX.append(circles[i]['center'][0] + circles[i]['radius'])
        allY.append(circles[i]['center'][1] - circles[i]['radius'])
        allY.append(circles[i]['center'][1] + circles[i]['radius'])
    lbX = min(allX) - 1
    lbY = min(allY) - 1
    ubX = max(allX) + 1
    ubY = max(allY) + 1

    # Decision variables ======================================================
    # NOTE: x, y index starts by 1
    x = {}
    y = {}
    for i in range(1, len(circles) + 1):
        x[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = "x_%s" % i, lb = lbX, ub = ubX)
        y[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = "y_%s" % i, lb = lbY, ub = ubY)
    # Distance from ((xi, yi)) to (x[i + 1], y[i + 1]), 
    # where startPt = (x[0], y[0]) and endPt = (x[len(circles) + 1], y[len(circles) + 1])
    d = {}
    for i in range(len(circles) + 1):
        d[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'd_%s' % i)
    model.setObjective(grb.quicksum(d[i] for i in range(len(circles) + 1)), grb.GRB.MINIMIZE)

    # Aux vars - distance between (x, y)
    dx = {}
    dy = {}
    for i in range(len(circles) + 1):
        dx[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'dx_%s' % i, lb = -float('inf'), ub = float('inf'))
        dy[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'dy_%s' % i, lb = -float('inf'), ub = float('inf'))
    # Aux vars - distance from (x, y) to the center
    rx = {}
    ry = {}
    for i in range(1, len(circles) + 1):
        rx[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'rx_%s' % i, lb = -float('inf'), ub = float('inf'))
        ry[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'ry_%s' % i, lb = -float('inf'), ub = float('inf'))

    # Constraints =============================================================
    # Aux constr - dx dy
    model.addConstr(dx[0] == x[1] - anchor[0][0])
    model.addConstr(dy[0] == y[1] - anchor[0][1])
    for i in range(1, len(circles)):
        model.addConstr(dx[i] == x[i + 1] - x[i])
        model.addConstr(dy[i] == y[i + 1] - y[i])
    model.addConstr(dx[len(circles)] == anchor[-1][0] - x[len(circles)])
    model.addConstr(dy[len(circles)] == anchor[-1][1] - y[len(circles)])

    # Aux constr - rx ry
    for i in range(1, len(circles) + 1):
        model.addConstr(rx[i] == x[i] - anchor[i][0])
        model.addConstr(ry[i] == y[i] - anchor[i][1])

    # Distance btw visits
    for i in range(len(circles) + 1):
        model.addQConstr(d[i] ** 2 >= dx[i] ** 2 + dy[i] ** 2)
        # model.addQConstr(dx[i] ** 2 + dy[i] ** 2 >= 0.1)

    for i in range(1, len(circles) + 1):
        model.addQConstr(rx[i] ** 2 + ry[i] ** 2 <= circles[i - 1]['radius'] ** 2)

    model.modelSense = grb.GRB.MINIMIZE
    # model.write("SOCP.lp")
    model.optimize()

    # Post-processing =========================================================
    ofv = None
    path = [startPt]
    if (model.status == grb.GRB.status.OPTIMAL):
        solType = 'IP_Optimal'
        ofv = model.getObjective().getValue()
        for i in x:
            path.append((x[i].x, y[i].x))
        path.append(endPt)
        gap = 0
        lb = ofv
        ub = ofv
    elif (model.status == grb.GRB.status.TIME_LIMIT):
        solType = 'IP_TimeLimit'
        ofv = model.ObjVal
        for i in x:
            path.append((x[i].x, y[i].x))
        path.append(endPt)
        gap = model.MIPGap
        lb = model.ObjBoundC
        ub = model.ObjVal
    else:
        print("HERE")
        print(model.status)
        
    return {
        'path': path,
        'dist': ofv,
        'runtime': model.Runtime
    }
 
def _circle2CirclePathCOPT(startPt: pt, endPt: pt, circles: dict, outputFlag: bool = False):
    env = None
    try:
        import coptpy as cp
        envconfig = cp.EnvrConfig()
        envconfig.set('nobanner', '1')
        AVAIL_SOLVER = 'COPT'
        if (env == None):
            env = cp.Envr(envconfig)
    except(ImportError):
        print("ERROR: Cannot find COPT")
        return

    model = env.createModel("SOCP")
    model.setParam(cp.COPT.Param.Logging, 1 if outputFlag else 0)
    model.setParam(cp.COPT.Param.LogToConsole, 1 if outputFlag else 0)

    # Decision variables ======================================================
    # anchor starts from startPt, in between are a list of circles, ends with endPt
    anchor = [startPt]
    for i in range(len(circles)):
        anchor.append(circles[i]['center'])
    anchor.append(endPt)

    allX = [startPt[0], endPt[0]]
    allY = [startPt[1], endPt[1]]
    for i in range(len(circles)):
        allX.append(circles[i]['center'][0] - circles[i]['radius'])
        allX.append(circles[i]['center'][0] + circles[i]['radius'])
        allY.append(circles[i]['center'][1] - circles[i]['radius'])
        allY.append(circles[i]['center'][1] + circles[i]['radius'])
    lbX = min(allX) - 1
    lbY = min(allY) - 1
    ubX = max(allX) + 1
    ubY = max(allY) + 1

    # Decision variables ======================================================
    # NOTE: x, y index starts by 1
    x = {}
    y = {}
    for i in range(1, len(circles) + 1):
        x[i] = model.addVar(vtype = cp.COPT.CONTINUOUS, name = "x_%s" % i, lb = lbX, ub = ubX)
        y[i] = model.addVar(vtype = cp.COPT.CONTINUOUS, name = "y_%s" % i, lb = lbY, ub = ubY)
    # Distance from ((xi, yi)) to (x[i + 1], y[i + 1]), 
    # where startPt = (x[0], y[0]) and endPt = (x[len(circles) + 1], y[len(circles) + 1])
    d = {}
    for i in range(len(circles) + 1):
        d[i] = model.addVar(vtype = cp.COPT.CONTINUOUS, name = 'd_%s' % i)
    # Aux vars - distance between (x, y)
    dx = {}
    dy = {}
    for i in range(len(circles) + 1):
        dx[i] = model.addVar(vtype = cp.COPT.CONTINUOUS, name = 'dx_%s' % i, lb = -float('inf'), ub = float('inf'))
        dy[i] = model.addVar(vtype = cp.COPT.CONTINUOUS, name = 'dy_%s' % i, lb = -float('inf'), ub = float('inf'))
    # Aux vars - distance from (x, y) to the center
    rx = {}
    ry = {}
    for i in range(1, len(circles) + 1):
        rx[i] = model.addVar(vtype = cp.COPT.CONTINUOUS, name = 'rx_%s' % i, lb = -float('inf'), ub = float('inf'))
        ry[i] = model.addVar(vtype = cp.COPT.CONTINUOUS, name = 'ry_%s' % i, lb = -float('inf'), ub = float('inf'))

    model.setObjective(cp.quicksum(d[i] for i in range(len(circles) + 1)), cp.COPT.MINIMIZE)

    # Distance constraints ====================================================
    # Aux constr - dx dy
    model.addConstr(dx[0] == x[1] - anchor[0][0])
    model.addConstr(dy[0] == y[1] - anchor[0][1])
    for i in range(1, len(circles)):
        model.addConstr(dx[i] == x[i] - x[i + 1])
        model.addConstr(dy[i] == y[i] - y[i + 1])
    model.addConstr(dx[len(circles)] == anchor[-1][0] - x[len(circles)])
    model.addConstr(dy[len(circles)] == anchor[-1][1] - y[len(circles)])
    # Aux constr - rx ry
    for i in range(1, len(circles) + 1):
        model.addConstr(rx[i] == x[i] - anchor[i][0])
        model.addConstr(ry[i] == y[i] - anchor[i][1])

    # Distance btw visits
    for i in range(len(circles) + 1):
        model.addQConstr(d[i] ** 2 >= dx[i] ** 2 + dy[i] ** 2)

    for i in range(1, len(circles) + 1):
        model.addQConstr(rx[i] ** 2 + ry[i] ** 2 <= circles[i - 1]['radius'] ** 2)

    # model.write("SOCP.lp")
    model.solve()

    # Post-processing =========================================================
    ofv = None
    path = [startPt]
    if (model.status == cp.COPT.OPTIMAL):
        solType = 'IP_Optimal'
        ofv = model.getObjective().getValue()
        for i in x:
            path.append((x[i].x, y[i].x))
        path.append(endPt)
        gap = 0
        lb = ofv
        ub = ofv
        runtime = model.SolvingTime
    elif (model.status == cp.COPT.TIMEOUT):
        solType = 'IP_TimeLimit'
        ofv = model.ObjVal
        for i in x:
            path.append((x[i].x, y[i].x))
        path.append(endPt)
        gap = model.BestGap
        lb = model.BestBnd
        ub = model.BestObj
        runtime = model.SolvingTime
    realDist = 0

    return {
        'path': path,
        'dist': ofv
    }
