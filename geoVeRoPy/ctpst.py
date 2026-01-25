import networkx as nx
import gurobipy as grb
import datetime
import warnings

from .geometry import *
from .common import *
from .plot import *

# NOTE: 暂时先放在这里
def solveCTPST(startPt: pt, endPt: pt, nodes: dict, visitSeq: list, atLeastTimeBtw: list, speed = 1, outputFlag = False):

    model = grb.Model("SOCP")
    model.setParam('OutputFlag', 1 if outputFlag else 0)

    # model.setParam("NumericFocus", 3)
    # model.setParam("BarHomogeneous", 1)

    # Parameters ==============================================================
    # anchor starts from startPt, in between are a list of circles, ends with endPt
    anchor = []
    for k in visitSeq:
        anchor.append(nodes[k]['pt'])

    allX = [startPt[0], endPt[0]]
    allY = [startPt[1], endPt[1]]
    for i in nodes:
        allX.append(nodes[i]['pt'][0] - nodes[i]['radius'])
        allX.append(nodes[i]['pt'][0] + nodes[i]['radius'])
        allY.append(nodes[i]['pt'][1] - nodes[i]['radius'])
        allY.append(nodes[i]['pt'][1] + nodes[i]['radius'])
    lbX = min(allX) - 1
    lbY = min(allY) - 1
    ubX = max(allX) + 1
    ubY = max(allY) + 1

    # len(visitSeq) == len(insideSet) == 2 * len(nodes)
    insideSet = [[]]
    for k in range(1, len(visitSeq) - 1):
        inside = []
        for left in range(k):
            for right in range(k + 1, len(visitSeq)):
                if (visitSeq[left] == visitSeq[right]):
                    inside.append(visitSeq[left])
        insideSet.append(inside)
    insideSet.append([])

    # Decision variables ======================================================
    # (x[i], y[i]) and (x[i + len(nodes)], y[i + len(nodes)]) are two visiting points to start and conclude a visit to node i
    x = {}
    y = {}
    for i in nodes:
        x[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = "x_%s" % i, lb = lbX, ub = ubX)
        y[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = "y_%s" % i, lb = lbY, ub = ubY)
        x[i + len(nodes)] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = "xprime_%s" % i, lb = lbX, ub = ubX)
        y[i + len(nodes)] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = "yprime_%s" % i, lb = lbY, ub = ubY)
    
    # Distance from ((x_{i_k}, y_{i_k})) to (xi, y[i + 1]), 
    # where startPt = (x[i_0], y[i_0]) and endPt = (x[i_{len(visitSeq) + 1}], y[i_{len(visitSeq) + 1]})
    d = {}
    for k in range(len(visitSeq) + 1):
        d[k] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'd_%s' % i, ub = math.sqrt((ubX - lbX) ** 2 + (ubY - lbY) ** 2) + 1)
   
    # Time from ((xi, yi)) to (x[i + 1], y[i + 1]), 
    # where startPt = (x[0], y[0]) and endPt = (x[len(visitSeq) + 1], y[len(visitSeq) + 1])
    t = {}
    for k in range(len(visitSeq) + 1):
        t[k] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 't_%s' % i, ub = max(math.sqrt((ubX - lbX) ** 2 + (ubY - lbY) ** 2) / speed, max(atLeastTimeBtw)) + 1)
    model.setObjective(grb.quicksum(t[k] for k in range(len(visitSeq) + 1)), grb.GRB.MINIMIZE)

    # Aux vars - distance between (x, y)
    dx = {}
    dy = {}
    for k in range(len(visitSeq) + 1):
        dx[k] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'dx_%s' % i, lb = lbX - ubX, ub = ubX - lbX)
        dy[k] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'dy_%s' % i, lb = lbY - ubY, ub = ubY - lbY)

    # Aux vars - distance from (x, y) to the center
    rx = {}
    ry = {}
    for k in range(len(visitSeq)):
        rx[k] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'rx_%s' % i, lb = lbX - ubX, ub = ubX - lbX)
        ry[k] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'ry_%s' % i, lb = lbY - ubY, ub = ubY - lbY)
    
    # Constraints =============================================================
    # Distance between two consecutive visits ---------------------------------
    # Aux constr - dx dy
    model.addConstr(dx[0] == x[visitSeq[0]] - startPt[0])
    model.addConstr(dy[0] == y[visitSeq[0]] - startPt[1])
    for k in range(1, len(visitSeq)):

        isFirstPrimeFlag = False
        for j in range(k):
            if (visitSeq[k] == visitSeq[j]):
                isFirstPrimeFlag = True
                break
        isSecondPrimeFlag = False
        for j in range(k - 1):
            if (visitSeq[k - 1] == visitSeq[j]):
                isSecondPrimeFlag = True
                break

        if (not isFirstPrimeFlag and not isSecondPrimeFlag):
            model.addConstr(dx[k] == x[visitSeq[k]] - x[visitSeq[k - 1]])
            model.addConstr(dy[k] == y[visitSeq[k]] - y[visitSeq[k - 1]])
        elif (isFirstPrimeFlag and not isSecondPrimeFlag):
            model.addConstr(dx[k] == x[visitSeq[k] + len(nodes)] - x[visitSeq[k - 1]])
            model.addConstr(dy[k] == y[visitSeq[k] + len(nodes)] - y[visitSeq[k - 1]])
        elif (not isFirstPrimeFlag and isSecondPrimeFlag):
            model.addConstr(dx[k] == x[visitSeq[k]] - x[visitSeq[k - 1] + len(nodes)])
            model.addConstr(dy[k] == y[visitSeq[k]] - y[visitSeq[k - 1] + len(nodes)])
        else:
            model.addConstr(dx[k] == x[visitSeq[k] + len(nodes)] - x[visitSeq[k - 1] + len(nodes)])
            model.addConstr(dy[k] == y[visitSeq[k] + len(nodes)] - y[visitSeq[k - 1] + len(nodes)])

    model.addConstr(dx[len(visitSeq)] == endPt[0] - x[visitSeq[-1] + len(nodes)])
    model.addConstr(dy[len(visitSeq)] == endPt[1] - y[visitSeq[-1] + len(nodes)])

    # Distance btw visits
    for k in range(len(visitSeq) + 1):
        model.addQConstr(d[k] ** 2 >= dx[k] ** 2 + dy[k] ** 2)
    
    #Travel time btw visits
    for k in range(len(visitSeq) + 1):
        model.addConstr(t[k] >= d[k] / speed)
        model.addConstr(t[k] >= atLeastTimeBtw[k])

    # Distance to centers -----------------------------------------------------
    # Aux constr - rx ry
    for k in range(len(visitSeq)):
        # Check i or iprime
        # NOTE: 如果在visitSeq[0] -> visitSeq[k - 1]里有visitSeq[k]，则是iprime，否则是i

        isPrimeFlag = False
        for j in range(k):
            if (visitSeq[k] == visitSeq[j]):
                isPrimeFlag = True

        if (not isPrimeFlag):
            model.addConstr(rx[k] == x[visitSeq[k]] - anchor[k][0])
            model.addConstr(ry[k] == y[visitSeq[k]] - anchor[k][1])
        else:
            model.addConstr(rx[k] == x[visitSeq[k] + len(nodes)] - anchor[k][0])
            model.addConstr(ry[k] == y[visitSeq[k] + len(nodes)] - anchor[k][1])

    # (x[i], y[i]) to center
    for k in range(len(visitSeq)):
        model.addQConstr(rx[k] ** 2 + ry[k] ** 2 <= nodes[visitSeq[k]]['radius'] ** 2)

    # Distance to overlapping centers -----------------------------------------
    rxj = {}
    ryj = {}
    # (x[i], y[i]) to other centers:
    for k in range(len(visitSeq)):
        for j in range(len(insideSet[k])):
            # 添加辅助决策变量从k到j
            rxj[k] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'rxj_%s' % k, lb = lbX - ubX, ub = ubX - lbX)
            ryj[k] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'ryj_%s' % k, lb = lbY - ubY, ub = ubY - lbY)

            isKPrimeFlag = False
            for m in range(k):
                if (visitSeq[k] == visitSeq[m]):
                    isKPrimeFlag = True
                    break

            if (not isKPrimeFlag):
                model.addConstr(rxj[k] == x[visitSeq[k]] - nodes[insideSet[k][j]]['pt'][0])
                model.addConstr(ryj[k] == y[visitSeq[k]] - nodes[insideSet[k][j]]['pt'][1])
            else:
                model.addConstr(rxj[k] == x[visitSeq[k] + len(nodes)] - nodes[insideSet[k][j]]['pt'][0])
                model.addConstr(ryj[k] == y[visitSeq[k] + len(nodes)] - nodes[insideSet[k][j]]['pt'][1])

            model.addQConstr(rxj[k] ** 2 + ryj[k] ** 2 <= nodes[insideSet[k][j]]['radius'] ** 2)
            # print("Additional: ", "node order - ", k, "node ID - ", visitSeq[k], "inside - ", insideSet[k][j])

    model.update()
    model.modelSense = grb.GRB.MINIMIZE
    model.optimize()

    # Post-processing =========================================================
    ofv = None
    dist = None
    timeStamp = []
    distStamp = []
    trueDistBtw = []
    nodePts = {}
    path = [startPt]
    if (model.status == grb.GRB.status.OPTIMAL):
        solType = 'IP_Optimal'
        ofv = model.getObjective().getValue()

        for k in range(len(visitSeq)):
            isPrimeFlag = False
            for j in range(k):
                if (visitSeq[k] == visitSeq[j]):
                    isPrimeFlag = True
            if (not isPrimeFlag):
                path.append((x[visitSeq[k]].x, y[visitSeq[k]].x))
            else:
                path.append((x[visitSeq[k] + len(nodes)].x, y[visitSeq[k] + len(nodes)].x))
        for k in range(len(visitSeq) + 1):
            timeStamp.append(t[k].x)
            distStamp.append(d[k].x)

        for n in nodes:
            nodePts[n] = {
                'pt': (x[n].x, y[n].x)
            }
            nodePts[n + len(nodes)] = {
                'pt': (x[n + len(nodes)].x, y[n + len(nodes)].x)
            }

        path.append(endPt)
        gap = 0
        lb = ofv
        ub = ofv

        dist = 0
        for i in range(len(path) - 1):
            dist += distEuclideanXY(path[i], path[i + 1])
            trueDistBtw.append(distEuclideanXY(path[i], path[i + 1]))

    elif (model.status == grb.GRB.status.TIME_LIMIT):
        solType = 'IP_TimeLimit'
        ofv = model.ObjVal

        for k in range(len(visitSeq)):
            isPrimeFlag = False
            for j in range(k):
                if (visitSeq[k] == visitSeq[j]):
                    isPrimeFlag = True
            if (not isPrimeFlag):
                path.append((x[visitSeq[k]].x, y[visitSeq[k]].x))
            else:
                path.append((x[visitSeq[k] + len(nodes)].x, y[visitSeq[k] + len(nodes)].x))
        for k in range(len(visitSeq) + 1):
            timeStamp.append(t[k].x)
            distStamp.append(d[k].x)

        path.append(endPt)
        gap = 0
        lb = ofv
        ub = ofv

        dist = 0
        for i in range(len(path) - 1):
            dist += distEuclideanXY(path[i], path[i + 1])
            trueDistBtw.append(distEuclideanXY(path[i], path[i + 1]))

    else:
        print(model.status)

    # print("timeStamp: ", timeStamp)
    # print("distStamp: ", distStamp)
    # print("trueDistBtw: ", trueDistBtw)
    # print("nodePts: ", nodePts)
        
    return {
        'path': path,
        'time': ofv,
        'dist': dist,
        'nodePts': nodePts,
        'runtime': model.Runtime
    }

def curveArc2CurveArcPathBak(startPt: pt, endPt: pt, curveArcs: list[CurveArc], adaptErr = 0.01, atLeastTimeBtw = None, speed = 1, outputFlag = False):
    
    model = grb.Model("SOCP")
    model.setParam('OutputFlag', 1 if outputFlag else 0)

    # Parameters ==============================================================
    # anchor starts from startPt, in between are a list of circles, ends with endPt
    anchor = [startPt]
    for i in range(len(curveArcs)):
        anchor.append(curveArcs[i].center)
    anchor.append(endPt)

    allX = [startPt[0], endPt[0]]
    allY = [startPt[1], endPt[1]]
    for i in range(len(curveArcs)):
        allX.append(curveArcs[i].center[0] - curveArcs[i].radius)
        allX.append(curveArcs[i].center[0] + curveArcs[i].radius)
        allY.append(curveArcs[i].center[1] - curveArcs[i].radius)
        allY.append(curveArcs[i].center[1] + curveArcs[i].radius)
    lbX = min(allX) - 1
    lbY = min(allY) - 1
    ubX = max(allX) + 1
    ubY = max(allY) + 1

    # Decision variables ======================================================
    # NOTE: x, y index starts by 1
    x = {}
    y = {}
    for i in range(1, len(curveArcs) + 1):
        x[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = "x_%s" % i, lb = lbX, ub = ubX)
        y[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = "y_%s" % i, lb = lbY, ub = ubY)
    # Distance from ((xi, yi)) to (x[i + 1], y[i + 1]), 
    # where startPt = (x[0], y[0]) and endPt = (x[len(curveArcs) + 1], y[len(curveArcs) + 1])
    d = {}
    for i in range(len(curveArcs) + 1):
        d[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'd_%s' % i)
    # model.setObjective(grb.quicksum(d[i] for i in range(len(curveArcs) + 1)), grb.GRB.MINIMIZE, priority = 1)

    # Time from ((xi, yi)) to (x[i + 1], y[i + 1]), 
    # where startPt = (x[0], y[0]) and endPt = (x[len(curveArcs) + 1], y[len(curveArcs) + 1])
    t = {}
    for i in range(len(curveArcs) + 1):
        t[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 't_%s' % i)
    model.setObjective(grb.quicksum(t[i] for i in range(len(curveArcs) + 1)), grb.GRB.MINIMIZE)

    # Aux vars - distance between (x, y)
    dx = {}
    dy = {}
    for i in range(len(curveArcs) + 1):
        dx[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'dx_%s' % i, lb = -float('inf'), ub = float('inf'))
        dy[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'dy_%s' % i, lb = -float('inf'), ub = float('inf'))
    # Aux vars - distance from (x, y) to the center
    rx = {}
    ry = {}
    for i in range(1, len(curveArcs) + 1):
        rx[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'rx_%s' % i, lb = -float('inf'), ub = float('inf'))
        ry[i] = model.addVar(vtype = grb.GRB.CONTINUOUS, name = 'ry_%s' % i, lb = -float('inf'), ub = float('inf'))

    # Constraints =============================================================
    # Aux constr - dx dy
    model.addConstr(dx[0] == x[1] - anchor[0][0])
    model.addConstr(dy[0] == y[1] - anchor[0][1])
    for i in range(1, len(curveArcs)):
        model.addConstr(dx[i] == x[i + 1] - x[i])
        model.addConstr(dy[i] == y[i + 1] - y[i])
    model.addConstr(dx[len(curveArcs)] == anchor[-1][0] - x[len(curveArcs)])
    model.addConstr(dy[len(curveArcs)] == anchor[-1][1] - y[len(curveArcs)])

    # Aux constr - rx ry
    for i in range(1, len(curveArcs) + 1):
        model.addConstr(rx[i] == x[i] - anchor[i][0])
        model.addConstr(ry[i] == y[i] - anchor[i][1])

    # Distance btw visits
    for i in range(len(curveArcs) + 1):
        model.addQConstr(d[i] ** 2 >= dx[i] ** 2 + dy[i] ** 2)
    
    #Travel time btw visits
    for i in range(len(curveArcs) + 1):
        model.addConstr(t[i] >= d[i] / speed)
        if (atLeastTimeBtw != None):
            model.addConstr(t[i] >= atLeastTimeBtw[i])

    # (x[i], y[i]) to center
    for i in range(1, len(curveArcs) + 1):
        model.addQConstr(rx[i] ** 2 + ry[i] ** 2 <= curveArcs[i - 1].radius ** 2)

    # Curve boundary
    for i in range(1, len(curveArcs) + 1):
        cut = curveArcs[i - 1].cutGen()
        if (cut != None):
            if (cut['sign'] == "<="):
                model.addConstr(cut['a'] * x[i] + cut['b'] * y[i] <= cut['c'])
            else:
                model.addConstr(cut['a'] * x[i] + cut['b'] * y[i] >= cut['c'])

    model.modelSense = grb.GRB.MINIMIZE
    model.optimize()

    # Post-processing =========================================================
    ofv = None
    dist = None
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

        dist = 0
        for i in range(len(path) - 1):
            dist += distEuclideanXY(path[i], path[i + 1])

    elif (model.status == grb.GRB.status.TIME_LIMIT):
        solType = 'IP_TimeLimit'
        ofv = model.ObjVal
        for i in x:
            path.append((x[i].x, y[i].x))
        path.append(endPt)
        gap = model.MIPGap
        lb = model.ObjBoundC
        ub = model.ObjVal

        dist = 0
        for i in range(len(path) - 1):
            dist += distEuclideanXY(path[i], path[i + 1])

    else:
        print(model.status)
        
    return {
        'path': path,
        'time': ofv,
        'dist': dist,
        'runtime': model.Runtime
    }
