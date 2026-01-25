import networkx as nx
import gurobipy as grb
import datetime
import warnings

from .geometry import *
from .ring import *
from .curveArc import *
from .common import *
from .plot import *

def curveArc2CurveArcPathSaved(startPt: pt, endPt: pt, curveArcs: list[CurveArc], adaptErr = 0.01, atLeastTimeBtw = None, speed = 1):
    
    startTime = datetime.datetime.now()

    tau = {}

    G = nx.Graph()

    if (atLeastTimeBtw == None):
        atLeastTimeBtw = [0 for i in range(len(curveArcs) + 1)]

    # Initial iteration =======================================================
    # startPt to the first curveArc
    M = 0
    for i in range(len(curveArcs) - 1):
        for j in range(i + 1, len(curveArcs)):
            d = distEuclideanXY(curveArcs[i].center, curveArcs[j].center) + curveArcs[i].radius + curveArcs[j].radius
            if (d > M):
                M = d
    M *= 1.2
    cur = curveArcs[0].head
    while (not cur.isNil):
        d = None
        if (('s', (0, cur.key)) not in tau):
            d = distEuclideanXY(startPt, cur.pt)
            tau['s', (0, cur.key)] = d
        else:
            d = tau['s', (0, cur.key)]
        G.add_edge('s', (0, cur.key), weight = max(d / speed, atLeastTimeBtw[0]) * M + d, time = max(d / speed, atLeastTimeBtw[0]))

        cur = cur.next
        if (cur == curveArcs[0].head):
            break

    # Between startPt and endPt
    for i in range(len(curveArcs) - 1):
        curI = curveArcs[i].head
        while (not curI.isNil):
            curJ = curveArcs[i + 1].head
            while (not curJ.isNil):
                d = None
                if (((i, curI.key), (i + 1, curJ.key)) not in tau):
                    d = distEuclideanXY(curI.pt, curJ.pt)
                    tau[(i, curI.key), (i + 1, curJ.key)] = d
                else:
                    d = tau[(i, curI.key), (i + 1, curJ.key)]

                if (d > 0.005):
                    G.add_edge((i, curI.key), (i + 1, curJ.key), weight = max(d / speed, atLeastTimeBtw[i + 1]) * M + d, time = max(d / speed, atLeastTimeBtw[i + 1]))

                curJ = curJ.next
                if (curJ == curveArcs[i + 1].head):
                    break
            curI = curI.next
            if (curI == curveArcs[i].head):
                break

    # last curveArc to endPt
    cur = curveArcs[-1].head
    while (not cur.isNil):
        d = None
        if (((len(curveArcs) - 1, cur.key), 'e') not in tau):
            d = distEuclideanXY(cur.pt, endPt)
            tau[(len(curveArcs) - 1, cur.key), 'e'] = d
        else:
            d = tau[(len(curveArcs) - 1, cur.key), 'e']
        G.add_edge((len(curveArcs) - 1, cur.key), 'e', weight = max(d / speed, atLeastTimeBtw[-1]) * M + d, time = max(d / speed, atLeastTimeBtw[-1]))

        cur = cur.next
        if (cur == curveArcs[-1].head):
            break

    sp = nx.dijkstra_path(G, 's', 'e')
    # print(sp)

    time = 0
    for i in range(1, len(sp)):
        time += G[sp[i - 1]][sp[i]]['time']

    # Refine ==================================================================
    iterNum = 0
    refineFlag = True
    while (refineFlag):
        iterNum += 1

        # 重新起图
        G = nx.Graph()

        byStage = []

        # sp[0] is startPt
        # sp[-1] is endPt
        for i in range(1, len(sp) - 1):
            cvIdx = sp[i][0]
            cvKey = sp[i][1]

            # Insert two pts before and after this cvNode
            n = curveArcs[cvIdx].query(cvKey)
            curveArcs[cvIdx].insertAround(n)

            thisStage = []

            # prev.prev
            if (not n.prev.isNil and not n.prev.prev.isNil):
                thisStage.append(n.prev.prev)
            if (not n.prev.isNil):
                thisStage.append(n.prev)
            thisStage.append(n)
            if (not n.next.isNil):
                thisStage.append(n.next)
            if (not n.next.isNil and not n.next.next.isNil):
                thisStage.append(n.next.next)

            byStage.append(thisStage)

        # StartPt => byStage
        for k in byStage[0]:
            d = None
            if (('s', (0, k.key)) not in tau):
                d = distEuclideanXY(startPt, k.pt)
                tau['s', (0, k.key)] = d
            else:
                d = tau['s', (0, k.key)]
            G.add_edge('s', (0, k.key), weight = max(d / speed, atLeastTimeBtw[0]) * M + d, time = max(d / speed, atLeastTimeBtw[0]))

        # Between byStages
        if (len(byStage) >= 2):
            for i in range(1, len(byStage)):
                for k1 in byStage[i - 1]:
                    for k2 in byStage[i]:
                        d = None
                        if (((i - 1, k1.key), (i, k2.key)) not in tau):
                            d = distEuclideanXY(k1.pt, k2.pt)
                            tau[(i - 1, k1.key), (i, k2.key)] = d
                        else:
                            d = tau[(i - 1, k1.key), (i, k2.key)]
                        G.add_edge((i - 1, k1.key), (i, k2.key), weight = max(d / speed, atLeastTimeBtw[i]) * M + d, time = max(d / speed, atLeastTimeBtw[i]))

        # byStage => EndPt
        for k in byStage[-1]:
            d = None
            if ((((len(curveArcs) - 1, k.key), 'e')) not in tau):
                d = distEuclideanXY(k.pt, endPt)
                tau[(len(curveArcs) - 1, k.key), 'e'] = d
            else:
                d = tau[(len(curveArcs) - 1, k.key), 'e']
            G.add_edge((len(curveArcs) - 1, k.key), 'e', weight = max(d / speed, atLeastTimeBtw[-1]) * M + d, time = max(d / speed, atLeastTimeBtw[-1]))

        newSp = nx.dijkstra_path(G, 's', 'e')
        newTime = 0
        for i in range(1, len(newSp)):
            newTime += G[newSp[i - 1]][newSp[i]]['time']

        if (abs(newTime - time) <= adaptErr):
            refineFlag = False

        time = newTime
        sp = newSp

    # Collect results =========================================================
    dist = 0
    path = [startPt]
    for p in sp:
        if (p != 's' and p != 'e'):
            dist += distEuclideanXY(path[-1], curveArcs[p[0]].query(p[1]).pt)
            path.append(curveArcs[p[0]].query(p[1]).pt)
    dist += distEuclideanXY(path[-1], endPt)
    path.append(endPt)

    # print("New dist: ", dist)
    # print("Adapt Iter Time: ", (datetime.datetime.now() - startTime).total_seconds())
    # print("Adapt Iter Num: ", iterNum)

    return {
        'path': path,
        'time': time,
        'dist': dist,
        'runtime': (datetime.datetime.now() - startTime).total_seconds()
    }

def curveArc2CurveArcPath(startPt: pt, endPt: pt, curveArcs: list[CurveArc], adaptErr = 0.01, atLeastTimeBtw = None, speed = 1):
    
    startTime = datetime.datetime.now()

    tau = {}

    G = nx.Graph()

    if (atLeastTimeBtw == None):
        atLeastTimeBtw = [0 for i in range(len(curveArcs) + 1)]

    # Initial iteration =======================================================
    # startPt to the first curveArc
    M = 0
    for i in range(len(curveArcs) - 1):
        for j in range(i + 1, len(curveArcs)):
            d = distEuclideanXY(curveArcs[i].center, curveArcs[j].center) + curveArcs[i].radius + curveArcs[j].radius
            if (d > M):
                M = d
    M *= 1.2
    cur = curveArcs[0].head
    while (not cur.isNil):
        d = None
        if (('s', (0, cur.key)) not in tau):
            d = distEuclideanXY(startPt, cur.pt)
            tau['s', (0, cur.key)] = d
        else:
            d = tau['s', (0, cur.key)]
        G.add_edge('s', (0, cur.key), weight = max(d / speed, atLeastTimeBtw[0]) * M + d, time = max(d / speed, atLeastTimeBtw[0]))

        cur = cur.next
        if (cur == curveArcs[0].head):
            break

    # Between startPt and endPt
    for i in range(len(curveArcs) - 1):
        curI = curveArcs[i].head
        while (not curI.isNil):
            curJ = curveArcs[i + 1].head
            while (not curJ.isNil):
                d = None
                if (((i, curI.key), (i + 1, curJ.key)) not in tau):
                    d = distEuclideanXY(curI.pt, curJ.pt)
                    tau[(i, curI.key), (i + 1, curJ.key)] = d
                else:
                    d = tau[(i, curI.key), (i + 1, curJ.key)]

                if (d > 0.005):
                    G.add_edge((i, curI.key), (i + 1, curJ.key), weight = max(d / speed, atLeastTimeBtw[i + 1]) * M + d, time = max(d / speed, atLeastTimeBtw[i + 1]))

                curJ = curJ.next
                if (curJ == curveArcs[i + 1].head):
                    break
            curI = curI.next
            if (curI == curveArcs[i].head):
                break

    # last curveArc to endPt
    cur = curveArcs[-1].head
    while (not cur.isNil):
        d = None
        if (((len(curveArcs) - 1, cur.key), 'e') not in tau):
            d = distEuclideanXY(cur.pt, endPt)
            tau[(len(curveArcs) - 1, cur.key), 'e'] = d
        else:
            d = tau[(len(curveArcs) - 1, cur.key), 'e']
        G.add_edge((len(curveArcs) - 1, cur.key), 'e', weight = max(d / speed, atLeastTimeBtw[-1]) * M + d, time = max(d / speed, atLeastTimeBtw[-1]))

        cur = cur.next
        if (cur == curveArcs[-1].head):
            break

    sp = nx.dijkstra_path(G, 's', 'e')
    # print(sp)

    time = 0
    for i in range(1, len(sp)):
        time += G[sp[i - 1]][sp[i]]['time']

    # Refine ==================================================================
    iterNum = 0
    refineFlag = True
    while (refineFlag):
        iterNum += 1

        # 重新起图
        G = nx.Graph()

        byStage = []

        # sp[0] is startPt
        # sp[-1] is endPt
        for i in range(1, len(sp) - 1):
            cvIdx = sp[i][0]
            cvKey = sp[i][1]

            # Insert two pts before and after this cvNode
            n = curveArcs[cvIdx].query(cvKey)
            curveArcs[cvIdx].insertAround(n)

            thisStage = []

            # prev.prev
            if (not n.prev.isNil and not n.prev.prev.isNil):
                thisStage.append(n.prev.prev)
            if (not n.prev.isNil):
                thisStage.append(n.prev)
            thisStage.append(n)
            if (not n.next.isNil):
                thisStage.append(n.next)
            if (not n.next.isNil and not n.next.next.isNil):
                thisStage.append(n.next.next)

            byStage.append(thisStage)

        # StartPt => byStage
        for k in byStage[0]:
            d = None
            if (('s', (0, k.key)) not in tau):
                d = distEuclideanXY(startPt, k.pt)
                tau['s', (0, k.key)] = d
            else:
                d = tau['s', (0, k.key)]
            G.add_edge('s', (0, k.key), weight = max(d / speed, atLeastTimeBtw[0]) * M + d, time = max(d / speed, atLeastTimeBtw[0]))

        # Between byStages
        if (len(byStage) >= 2):
            for i in range(1, len(byStage)):
                for k1 in byStage[i - 1]:
                    for k2 in byStage[i]:
                        d = None
                        if (((i - 1, k1.key), (i, k2.key)) not in tau):
                            d = distEuclideanXY(k1.pt, k2.pt)
                            tau[(i - 1, k1.key), (i, k2.key)] = d
                        else:
                            d = tau[(i - 1, k1.key), (i, k2.key)]
                        G.add_edge((i - 1, k1.key), (i, k2.key), weight = max(d / speed, atLeastTimeBtw[i]) * M + d, time = max(d / speed, atLeastTimeBtw[i]))

        # byStage => EndPt
        for k in byStage[-1]:
            d = None
            if ((((len(curveArcs) - 1, k.key), 'e')) not in tau):
                d = distEuclideanXY(k.pt, endPt)
                tau[(len(curveArcs) - 1, k.key), 'e'] = d
            else:
                d = tau[(len(curveArcs) - 1, k.key), 'e']
            G.add_edge((len(curveArcs) - 1, k.key), 'e', weight = max(d / speed, atLeastTimeBtw[-1]) * M + d, time = max(d / speed, atLeastTimeBtw[-1]))

        newSp = nx.dijkstra_path(G, 's', 'e')
        newTime = 0
        for i in range(1, len(newSp)):
            newTime += G[newSp[i - 1]][newSp[i]]['time']

        if (abs(newTime - time) <= adaptErr):
            refineFlag = False

        time = newTime
        sp = newSp

    # Collect results =========================================================
    dist = 0
    path = [startPt]
    for p in sp:
        if (p != 's' and p != 'e'):
            dist += distEuclideanXY(path[-1], curveArcs[p[0]].query(p[1]).pt)
            path.append(curveArcs[p[0]].query(p[1]).pt)
    dist += distEuclideanXY(path[-1], endPt)
    path.append(endPt)

    # print("New dist: ", dist)
    # print("Adapt Iter Time: ", (datetime.datetime.now() - startTime).total_seconds())
    # print("Adapt Iter Num: ", iterNum)

    return {
        'path': path,
        'time': time,
        'dist': dist,
        'runtime': (datetime.datetime.now() - startTime).total_seconds()
    }
