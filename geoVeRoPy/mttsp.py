import math
import networkx as nx
import shapely
from shapely.geometry import mapping

import gurobipy as grb

from .common import *
from .geometry import *
from .obj2Obj import *

def solveMTTSP(
    startLoc: pt,
    endLoc: pt,
    nodes: dict, # 1 => n
    vehSpeed: float,
    timeLimit: None|float = None
    ) -> dict | None:

    # Model initialization ====================================================
    MTTSP = grb.Model("MTTSP")
    MTTSP.setParam('OutputFlag', 0)
    if (timeLimit != None):
        MTTSP.setParam(grb.GRB.Param.TimeLimit, timeLimit)
    convergence = []
    repSeqHis = {}
    cutCount = {
        'subtour': 0,
        'gbc': 0
    }
    GBDCuts = []

    startTime = datetime.datetime.now()

    # Define sets
    startID = 0
    endID = len(nodes) + 1
    nodeAll = [i for i in range(0, len(nodes) + 2)]
    nodeFrom = [i for i in range(0, len(nodes) + 1)]
    nodeTo = [i for i in range(1, len(nodes) + 2)]

    # Parameters ==============================================================
    # 从i到j最短的距离
    # FIXME: 这部分要优化
    zBar = {}
    for i in nodes:
        for j in nodes:
            if (i != j):
                zBar[i, j] = 0#shortestDist
    for i in nodes:
        zBar[startID, i] = 0
        zBar[i, endID] = 0
    zBar[startID, endID] = 0
    zBar[endID, startID] = 0

    # Decision variables ======================================================
    # e[i,j] == 1 if target i is visited instantly prior to j
    e = {}
    for i in nodeFrom:
        for j in nodeTo:
            if (i != j):
                e[i, j] = MTTSP.addVar(
                    vtype = grb.GRB.BINARY, 
                    obj = zBar[i, j],
                    name = 'e_%s_%s' % (i, j))
    e[endID, startID] = MTTSP.addVar(vtype = grb.GRB.BINARY, obj = 0)

    theta = MTTSP.addVar(
        vtype = grb.GRB.CONTINUOUS, 
        obj = 1,
        name = 'theta')

    # Objective function ======================================================
    MTTSP.modelSense = grb.GRB.MINIMIZE
    MTTSP.Params.lazyConstraints = 1
    MTTSP.update()

    # TSP constraints =========================================================
    for i in nodeFrom:
        MTTSP.addConstr(grb.quicksum(e[i, j] for j in nodeTo if i != j and (i, j) in e) == 1)
    for i in nodeTo:
        MTTSP.addConstr(grb.quicksum(e[j, i] for j in nodeFrom if i != j and (j, i) in e) == 1)
    MTTSP.addConstr(e[endID, startID] == 1)

    # a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    # for i in range(len(a) - 1):
    #     MTTSP.addConstr(e[a[i], a[i + 1]] == 1)

    MTTSP._e = e
    MTTSP._theta = theta
    def GBDCutInfo(coeff, dvSeq, note) -> str:
        cutInfo = "Add %s: - theta >= " % note
        for i in range(len(dvSeq)):
            cutInfo += "%s * e[%s, %s] + " % (
                round((coeff[i] - zBar[dvSeq[i]]), 3), dvSeq[i][0], dvSeq[i][1]) 
        cutInfo = cutInfo[:-3] 
        return cutInfo

    def callbackCuts(model, where):
        if (where == grb.GRB.Callback.MIPSOL):
            TSPFeasibleFlag = True

            # Get visiting sequence -------------------------------------------
            e_sol = model.cbGetSolution(model._e)
            G = nx.Graph()
            for (i, j) in e.keys():
                if (e_sol[i, j] > 0.9):
                    G.add_edge(i, j)

            # Subtour elimination ---------------------------------------------
            components = [list(c) for c in nx.connected_components(G)]
            if (len(components) > 1):
                writeLog("\n")
                writeLog("Subtour detected")
                writeLog(hyphenStr())
                writeLog("Theta: %s" % model.cbGetSolution(model._theta))
            for component in components:
                if (len(component) < len(nodes) + 2):
                    TSPFeasibleFlag = False
                    writeLog("Component - " + list2String(component))
                    cutCount['subtour'] += 1
                    model.cbLazy(grb.quicksum(e[i, j] for i in component for j in component if i != j and (i, j) in e) <= len(component) - 1)

            # Benders cut -----------------------------------------------------      
            if (TSPFeasibleFlag):
                # 还原访问顺序
                repArc = []
                for (i, j) in e.keys():
                    if (e_sol[i, j] > 0.9):
                        repArc.append([i, j])
                repSeq = []
                currentNode = startID
                repSeq.append(currentNode)
                while (len(repArc) > 0):
                    for i in range(len(repArc)):
                        if (repArc[i][0] == currentNode):
                            currentNode = repArc[i][1]
                            repSeq.append(currentNode)
                            repArc.pop(i)
                            break
                repSeq = repSeq[:-1]

                writeLog("\n")
                writeLog(list2String(repSeq))
                writeLog(hyphenStr())
                writeLog("Theta: %s" % model.cbGetSolution(model._theta))

                maxTheta = 0
                maxCut = None
                for c  in GBDCuts:
                    thisTheta = 0
                    for k in range(len(c['dvSeq'])):
                        if (c['dvSeq'][k] in e.keys() and e_sol[c['dvSeq'][k]] > 0.9):
                            thisTheta += c['coeff'][k] - zBar[c['dvSeq'][k]]
                    if (thisTheta > maxTheta):
                        maxTheta = thisTheta
                        maxCut = c

                vecs = []
                for i in range(1, len(repSeq) - 1):
                    vecs.append({
                        'loc': nodes[repSeq[i]]['loc'],
                        'vec': nodes[repSeq[i]]['vec']
                    })
                v2v = vec2VecPath(startLoc, endLoc, vecs, vehSpeed)

                minDist = float('inf')
                for seq in repSeqHis:
                    if (repSeqHis[seq] < minDist):
                        minDist = repSeqHis[seq]

                # Cut preparing
                residual = v2v['dist']
                for i in range(len(repSeq) - 1):
                    residual -= zBar[repSeq[i], repSeq[i + 1]]
                writeLog("Residual: %s" % residual)

                repSeqHis[tuple([i for i in repSeq])] = v2v['dist']

                coeff = []
                dvSeq = []
                for i in range(len(repSeq) - 1):
                    coeff.append(distEuclideanXY(v2v['path'][i], v2v['path'][i + 1]))
                    dvSeq.append((repSeq[i], repSeq[i + 1]))
                writeLog(GBDCutInfo(coeff, dvSeq, "default cut"))
                model.cbLazy(theta >= grb.quicksum(
                    e[dvSeq[i]] * (coeff[i] - zBar[dvSeq[i]]) for i in range(len(dvSeq))))
                cutCount['gbc'] += 1

                GBDCuts.append({
                        'coeff': [i for i in coeff],
                        'dvSeq': [i for i in dvSeq]
                    })


                objBound = model.cbGet(grb.GRB.Callback.MIPSOL_OBJBND)
                objIncum = model.cbGet(grb.GRB.Callback.MIPSOL_OBJBST)
                timePassed = round((datetime.datetime.now() - startTime).total_seconds(), 2)
                writeLog("Time Pass: " + str(timePassed) + "[s]"
                    + "\nCut: subtour - %s, gbc - %s" % (cutCount['subtour'], cutCount['gbc'])
                    + "\nSo far Best Dist: " + str(minDist)
                    + "\nCurrSol Dist: " + str(v2v['dist'])
                    + "\nCurrObj: " + str(objIncum)
                    + "\nCurrBound: " + str(objBound))
                convergence.append((v2v['dist'], objIncum, objBound, timePassed))             

    # TSP with no callback ====================================================
    MTTSP.update()
    MTTSP.optimize(callbackCuts)

    # Reconstruct solution ====================================================
    ofv = None
    seq = []
    activeX = []
    solType = None
    gap = None
    lb = None
    ub = None
    runtime = None

    ofv = MTTSP.getObjective().getValue()
    for i, j in e: 
        if (e[i, j].x > 0.5):
            activeX.append([i, j])
    currentNode = startID
    seq.append(currentNode)
    while (len(activeX) > 0):
        for i in range(len(activeX)):
            if (activeX[i][0] == currentNode):
                currentNode = activeX[i][1]
                seq.append(currentNode)
                activeX.pop(i)
                break
    seq = seq[:-1]
    vecs = []
    for i in range(1, len(seq) - 1):
        vecs.append({
            'loc': nodes[seq[i]]['loc'],
            'vec': nodes[seq[i]]['vec'] 
        })
    v2v = vec2VecPath(startLoc, endLoc, vecs, vehSpeed)
    timedSeq = seq2TimedSeq(seq = v2v['path'], vehSpeed = vehSpeed)

    if (MTTSP.status == grb.GRB.status.OPTIMAL):
        solType = 'IP_Optimal'
        gap = 0
        lb = ofv
        ub = ofv
        runtime = MTTSP.Runtime
    elif (MTTSP.status == grb.GRB.status.TIME_LIMIT):
        solType = 'IP_TimeLimit'
        gap = MTTSP.MIPGap
        lb = MTTSP.ObjBoundC
        ub = MTTSP.ObjVal
        runtime = MTTSP.Runtime
    else:
        return None

    return {
        'ofv': ofv,
        'theta': theta.x,
        'dist': v2v['dist'],
        'seq': seq,
        'timedSeq': timedSeq,
        'path': v2v['path'],
        'gap': gap,
        'solType': solType,
        'lowerBound': lb,
        'upperBound': ub,
        'runtime': runtime,
        'convergence': convergence,
        'cutCount': cutCount,
        'zBar': zBar
    }
