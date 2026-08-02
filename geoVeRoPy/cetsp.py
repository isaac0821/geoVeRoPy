import math
import heapq
import networkx as nx
import shapely
from shapely.geometry import mapping

import gurobipy as grb

from .common import *
from .geometry import *
from .travel import *
from .ring import *
from .polyTour import *
from .otp import *
from .tsp import *
from .bnbTree import *
from .ils import *

# Close-enough Travelings Salesman Problem
def solveCETSP(nodes: dict, depotPt: pt = None, startPt: pt = None, endPt: pt = None, neighbor: str = "Circle", dimension: str = 'Euclidean', algo: str = "Exact", method: str = 'BnB', **kwargs):

    """Use MISOCP(GBD)/metaheuristic to find shortest CETSP tour

    Parameters
    ----------

    nodes: dict, required
        The `node` dictionary, must include neighborhood information
    depotPt: pt, optional
        Depot location, where the travel starts from and returns to, required if depotPt is not provided
    startPt: pt, optional
        Start location, required if depotPt is not provided
    endPt: pt, optional
        End location, required if depotPt is not provided
    neighbor: string, optional, default as "Circle"
        Type of neighborhood, options includes, "Circle" and "Poly", each requires different additional inputs

        1) "Circle", disk-shape area on Euclidean space
            - radius: float, the radius of disks if all the radius are the same
            - radiusFieldName: str, the field name in `nodes` for radius, which could be different for different nodes.
        2) "Poly", polygon-shape are on Euclidean space
            - polyFieldName: str, optional, default as 'poly', the field name in `nodes` for neighborhoods.
    
    dimension: string, optional, default as "Euclidean"
        Dimension of the customers, options includes, "Euclidean" and "LatLon"

        1) "Euclidean", area on Euclidean space
        2) "LatLon"， customers describe in Lat/Lon

    algo: string, optional, default as "Metaheuristic"
        Select the algorithm for calculating CETSP. Options and required additional inputs are as follows:

        1) 'Metaheuristic', use metaheuristic to solve CETSP to sub-optimal
            - method: 'GeneticAlgorithm'
            - method: 'ILS'
        2) 'Heuristic', use heuristic to solve CETSP to sub-optimal
            - (Not implemented yet) method: 'SteinerZone'
        2) 'Exact', use exact approach to solve CETSP to optimal

    method: string, optional, default as "ILS"
        Select the method corresponding to `algo`.

    **kwargs: optional
        Provide additional inputs for different `neighbor` options and `algo` options

    """

    # WARNING: This is a separate branch, do no edit further, improved version is in geoVeRoPyPri
    # Sanity check ============================================================
    if (nodes == None or type(nodes) != dict):
        raise MissingParameterError(ERROR_MISSING_NODES)
    # depotPt和startPt/endPt必须有一个，depotPt会覆盖另外俩
    if (depotPt == None and startPt == None and endPt == None):
        raise MissingParameterError("ERROR: Missing depotPt. Use `depotPt` or (`startPt` and `endPt').")
    else:
        if (depotPt != None):
            startPt = depotPt
            endPt = depotPt
        else:
            if (startPt == None):
                raise MissingParameterError("ERROR: Missing start location.")
            if (endPt == None):
                raise MissingParameterError("ERROR: Missing end location.")

    # Check required fields for neighbor options ==============================
    if (neighbor == 'Circle'):
        checkRequiredKeys(kwargs, [('radius', 'radiusFieldName')])
    elif (neighbor == 'Poly'):
        if ('polyFieldName' not in kwargs):
            warnings.warn("WARNING: `polyFieldName` is not provided, set to be default as `neighbor`.")
            kwargs['polyFieldName'] = 'neighbor'
    else:
        raise UnsupportedInputError("ERROR: Neighborhood type is not supported")

    # CETSP by different approach =============================================
    if (dimension == 'Euclidean' and neighbor == "Circle" and algo == "Exact" and method == "BnB"):
        cetsp = _solveCETSPBnBCircle(
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            radius = kwargs['radius'] if 'radius' in kwargs else None,
            radiusFieldName = kwargs['radiusFieldName'] if 'radiusFieldName' in kwargs else None,
            timeLimit = kwargs['timeLimit'] if 'timeLimit' in kwargs else None,
            gapTol = kwargs['gapTol'] if 'gapTol' in kwargs else None,
            subproblemAlgo = kwargs['subproblemAlgo'] if 'subproblemAlgo' in kwargs else 'SOCP')

    elif (dimension == 'Euclidean' and neighbor == "Poly" and algo == "Exact" and method == "BnB"):
        cetsp = _solveCETSPBnBPoly(
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            polyFieldName = kwargs['polyFieldName'],
            timeLimit = kwargs['timeLimit'] if 'timeLimit' in kwargs else None,
            gapTol = kwargs['gapTol'] if 'gapTol' in kwargs else None,
            subproblemAlgo = kwargs['subproblemAlgo'] if 'subproblemAlgo' in kwargs else 'SOCP')

    elif (dimension == 'Euclidean' and neighbor == "Circle" and algo == "Metaheuristic" and method == "ILS"):
        cetsp = _solveCETSPILS(
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            neighbor = neighbor,
            radius = kwargs['radius'] if 'radius' in kwargs else None,
            radiusFieldName = kwargs['radiusFieldName'] if 'radiusFieldName' in kwargs else None,
            initTemp = kwargs['initTemp'] if 'initTemp' in kwargs else None,
            coolRate = kwargs['coolRate'] if 'coolRate' in kwargs else None,
            neighRatio = kwargs['neighRatio'] if 'neighRatio' in kwargs else None,
            stop = kwargs['stop'] if 'stop' in kwargs else None,
            subproblemAlgo = kwargs['subproblemAlgo'] if 'subproblemAlgo' in kwargs else 'SOCP')

    else:
        raise UnsupportedInputError("ERROR: Combination of `dimension`, `neighbor`, `algo`, and `method` is not supported yet.")
    return cetsp

def _solveCETSPILS(startPt: pt, endPt: pt, nodes: dict, neighbor: str = 'Circle', radius: float | None = None, radiusFieldName: str = 'radius', polyFieldName: str = 'neighbor', initTemp: float | None = None, coolRate: float | None = None, neighRatio: dict | None = None, stop: dict | None = None, subproblemAlgo: str = 'SOCP', **kwargs) -> dict | None:
    if (neighbor != 'Circle'):
        raise UnsupportedInputError("ERROR: CETSP ILS currently only supports circle neighborhoods.")
    if (initTemp == None):
        initTemp = 100
    if (coolRate == None):
        coolRate = 0.95
    if (neighRatio == None):
        warnings.warn("WARNING: Missing ratios of each local search operator, set to be default.")
        neighRatio = {
            'Swap': 0.1,
            'Exchange': 0.1,
            'Rotate': 0.3,
            'rndDestroy': 0.4
        }
    if (stop == None):
        warnings.warn("WARNING: Missing stopping criteria, set to be default.")
        stop = {
            'numNoImprove': 200
        }
    if ('numNoImproveIter' in stop and 'numNoImprove' not in stop):
        stop['numNoImprove'] = stop['numNoImproveIter']
    cetsp = _solveCETSPILSCircle(startPt = startPt, endPt = endPt, nodes = nodes, radius = radius, radiusFieldName = radiusFieldName, initTemp = initTemp, coolRate = coolRate, neighRatio = neighRatio, stop = stop, subproblemAlgo = subproblemAlgo)
    return cetsp

def _solveCETSPILSCircle(startPt: pt, endPt: pt, nodes: dict, radius: float | None = None, radiusFieldName: str = 'radius', initTemp: float = 100, coolRate: float = 0.95, neighRatio: dict = { 'Swap': 0.1, 'Exchange': 0.1, 'Rotate': 0.3, 'rndDestroy': 0.4 }, stop: dict = {}, subproblemAlgo: str = 'SOCP', **kwargs) -> dict | None:

    def cetspNew(startPt, endPt, nodes, funcCheck, funcFix):
        # 找到两个customer，让startPt => cus1 => cus2 => endPt的距离最长
        rawSeq = []
        distFarest = 0
        for i in nodes:
            for j in nodes:
                if (i != j):
                    d = distEuclideanXY(startPt, nodes[i]['pt'])
                    d += distEuclideanXY(nodes[i]['pt'], nodes[j]['pt'])
                    d += distEuclideanXY(nodes[j]['pt'], endPt)
                    if (d > distFarest):
                        distFarest = d
                        rawSeq = [i, j]
        
        # 构造函数
        n = RawSolnNode(
            key = rawSeq,
            rawRep = rawSeq,
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            funcCheck = funcCheck,
            funcFix = funcFix)
        return n

    def cetspFix(n):
        # 随机选中一个missing，看看能插入到最近的位置是哪里
        if (len(n.missing) == 0):
            n.feasibleFlag = True
            return
        toInsert = random.choice(n.missing)
        distPt2Seg = cetspSortInsertion(n.startPt, n.endPt, n.nodes, n.repPt, n.turning, toInsert, neighbor = 'Circle', algo = subproblemAlgo, radius = radius, radiusFieldName = radiusFieldName)
        repairOptions = []
        while (len(distPt2Seg) > 0):
            delta, pos = heapq.heappop(distPt2Seg)
            repairOptions.append({
                'type': 'insert',
                'delta': delta,
                'pos': pos,
                'node': toInsert
            })
        return {
            'repairOptions': repairOptions
        }

    def cetspCheck(n):
        # 给定一个RawSolnNode，确定是否访问了所有的点
        seq = n.curRep
        checkVisit = cetspCheckVisit(n.startPt, n.endPt, n.nodes, seq, neighbor = 'Circle', algo = subproblemAlgo, radius = radius, radiusFieldName = radiusFieldName)

        n.ofv = checkVisit['ofv']
        n.dist = checkVisit['ofv']
        n.path = checkVisit['path']
        n.curRep = checkVisit['turning']

        n.turning = checkVisit['turning']
        n.trespass = checkVisit['trespass']
        n.missing = checkVisit['missing']
        n.repPt = checkVisit['repPt']

        if (len(n.missing) == 0):
            n.feasibleFlag = True
            n.rep = n.curRep
        else:
            n.feasibleFlag = False

        # printLog("Visit Seq: ", seq)
        # printLog("Turning: ", n.turning)
        # printLog("Trespass: ", n.trespass)
        # printLog("Missing: ", n.missing)
        
        return n.feasibleFlag

    def swap(n) -> SolnNode:
        newSeq = [i for i in n.rawRep]
        idxI = random.randint(0, len(newSeq) - 1)
        if (idxI < len(newSeq) - 1):
            newSeq[idxI], newSeq[idxI + 1] = newSeq[idxI + 1], newSeq[idxI]
        else:
            newSeq[idxI], newSeq[0] = newSeq[0], newSeq[idxI]
        return RawSolnNode(
            key = newSeq,
            rawRep = newSeq,
            startPt = n.startPt,
            endPt = n.endPt,
            nodes = n.nodes,
            funcCheck = n.funcCheck,
            funcFix = n.funcFix)

    def exchange(n) -> SolnNode:
        if (len(n.rawRep) > 4):
            newSeq = [i for i in n.rawRep]
            [idxI, idxJ] = random.sample([i for i in range(len(n.rawRep))], 2)
            while (abs(idxJ - idxI) <= 2
                or idxI == 0 and idxJ == len(n.rawRep) - 1
                or idxI == len(n.rawRep) - 1 and idxJ == 0):
                [idxI, idxJ] = random.sample([i for i in range(len(n.rawRep))], 2)
            newSeq[idxI], newSeq[idxJ] = newSeq[idxJ], newSeq[idxI]
        
            return RawSolnNode(
                key = newSeq,
                rawRep = newSeq,
                startPt = n.startPt,
                endPt = n.endPt,
                nodes = n.nodes,
                funcCheck = n.funcCheck,
                funcFix = n.funcFix)
        else:
            return n

    def rotate(n) -> SolnNode:
        if (len(n.rawRep) > 4):
            [idxI, idxJ] = random.sample([i for i in range(len(n.rawRep))], 2)
            while (abs(idxJ - idxI) <= 2
                or idxI == 0 and idxJ == len(n.rawRep) - 1
                or idxI == len(n.rawRep) - 1 and idxJ == 0):
                [idxI, idxJ] = random.sample([i for i in range(len(n.rawRep))], 2)
            if (idxI > idxJ):
                idxI, idxJ = idxJ, idxI

            seq = [i for i in n.rawRep]
            newSeq = [seq[i] for i in range(idxI)]
            newSeq.extend([seq[idxJ - i] for i in range(idxJ - idxI + 1)])
            newSeq.extend([seq[i] for i in range(idxJ + 1, len(seq))])
        
            return RawSolnNode(
                key = newSeq,
                rawRep = newSeq,
                startPt = n.startPt,
                endPt = n.endPt,
                nodes = n.nodes,
                funcCheck = n.funcCheck,
                funcFix = n.funcFix)
        else:
            return n 

    def rndDestroy(n) -> SolnNode:
        seq = [i for i in n.rawRep]
        numRemove = int(len(seq) * random.random() * 0.3)
        newSeq = [i for i in seq]
        for i in range(numRemove):
            newSeq.remove(newSeq[random.randint(0, len(newSeq) - 1)])

        return RawSolnNode(
            key = newSeq,
            rawRep = newSeq,
            startPt = n.startPt,
            endPt = n.endPt,
            nodes = n.nodes,
            funcCheck = n.funcCheck,
            funcFix = n.funcFix)

    solNode = cetspNew(
        startPt = startPt,
        endPt = endPt,
        nodes = nodes,
        funcCheck = cetspCheck,
        funcFix = cetspFix)
    ils = ILS(
        initNode = solNode,
        funcNeiOps = [
            swap,
            exchange,
            rotate,
            rndDestroy],
        initTemp = initTemp,
        coolRate = coolRate,
        stopCriteria = stop)
    ratioByFunc = {
        swap: neighRatio['Swap'] if 'Swap' in neighRatio else 1,
        exchange: neighRatio['Exchange'] if 'Exchange' in neighRatio else 1,
        rotate: neighRatio['Rotate'] if 'Rotate' in neighRatio else 1,
        rndDestroy: neighRatio['rndDestroy'] if 'rndDestroy' in neighRatio else 1
    }
    for func in ratioByFunc:
        ils.roulette[func] = ratioByFunc[func]
    ils.solve()

    return {
        'ofv': ils.bestNode.ofv,
        'dist': ils.bestNode.dist,
        'seq': ils.bestNode.curRep,
        'path': ils.bestNode.path,
        'turning': ils.bestNode.turning,
        'trespass': ils.bestNode.trespass,
        'runtime': ils.runtime,
        'convergence': ils.convergence,
    }

def _solveCETSPBnBCircle(startPt: pt, endPt: pt, nodes: dict, radius: float | None = None, radiusFieldName: str = 'radius', timeLimit: int | None = None, gapTol: float | None = None, subproblemAlgo: str = 'SOCP') -> dict | None:
    if (nodes == None or type(nodes) != dict):
        raise MissingParameterError(ERROR_MISSING_NODES)
    if (radius == None and radiusFieldName == None):
        raise MissingParameterError("ERROR: Circle neighborhood requires `radius` or `radiusFieldName`.")
    bnbParam = {
        'neighbor': 'Circle',
        'radius': radius,
        'radiusFieldName': radiusFieldName,
        'timeLimit': timeLimit,
        'gapTol': gapTol,
        'subproblemAlgo': subproblemAlgo
    }
    cetsp = _solveCETSPBnB(startPt = startPt, endPt = endPt, nodes = nodes, **bnbParam)
    return cetsp

def _solveCETSPBnBPoly(startPt: pt, endPt: pt, nodes: dict, polyFieldName: str = 'neighbor', timeLimit: int | None = None, gapTol: float | None = None, subproblemAlgo: str = 'SOCP') -> dict | None:
    if (nodes == None or type(nodes) != dict):
        raise MissingParameterError(ERROR_MISSING_NODES)
    if (polyFieldName == None):
        raise MissingParameterError("ERROR: Poly neighborhood requires `polyFieldName`.")
    bnbParam = {
        'neighbor': 'Poly',
        'polyFieldName': polyFieldName,
        'timeLimit': timeLimit,
        'gapTol': gapTol,
        'subproblemAlgo': subproblemAlgo
    }
    cetsp = _solveCETSPBnB(startPt = startPt, endPt = endPt, nodes = nodes, **bnbParam)
    return cetsp

def _solveCETSPBnB(startPt: pt, endPt: pt, nodes: dict, neighbor: str = 'Circle', radius: float | None = None, radiusFieldName: str = 'radius', polyFieldName: str = 'neighbor', timeLimit: int | None = None, gapTol: float | None = None, subproblemAlgo: str = 'SOCP') -> dict | None:
    def cetspNew(startPt, endPt, nodes, funcSolve, funcBranch, funcUBEstimate):
        seq = _cetspBuildInitialSeq(startPt = startPt, endPt = endPt, nodes = nodes, neighbor = neighbor, radius = radius, radiusFieldName = radiusFieldName, polyFieldName = polyFieldName)
        n = BnBTreeNode(key = seq, rep = seq, startPt = startPt, endPt = endPt, nodes = nodes, neighbor = neighbor, radius = radius, radiusFieldName = radiusFieldName, polyFieldName = polyFieldName, subproblemAlgo = subproblemAlgo, funcSolve = funcSolve, funcBranch = funcBranch, funcUBEstimate = funcUBEstimate, turning = [], trespass = [], missing = [], path = [], repPt = {}, branchInfo = None)
        return n

    def cetspSolve(n: BnBTreeNode):
        seq = n.rep
        checkVisit = cetspCheckVisit(n.startPt, n.endPt, n.nodes, seq, neighbor = n.neighbor, algo = n.subproblemAlgo, radius = n.radius, radiusFieldName = n.radiusFieldName, polyFieldName = n.polyFieldName)
        n.ofv = checkVisit['ofv']
        n.path = checkVisit['path']
        n.turning = checkVisit['turning']
        n.trespass = checkVisit['trespass']
        n.missing = checkVisit['missing']
        n.repPt = checkVisit['repPt']
        n.feasibleFlag = checkVisit['reachable']
        n.relaxFlag = True if (n.feasibleFlag == True and len(n.missing) > 0) else False
        if (n.feasibleFlag == False):
            n.pruneReason = 'subproblem_infeasible'
        printLog("Turning: ", n.turning)
        printLog("Trespass: ", n.trespass)
        printLog("Missing: ", n.missing)
        return

    def cetspBranch(n: BnBTreeNode):
        children = []
        if (len(n.missing) == 0):
            return children
        toInsert = random.choice(n.missing)
        distPt2Seg = cetspSortInsertion(n.startPt, n.endPt, n.nodes, n.repPt, n.turning, toInsert, neighbor = n.neighbor, algo = n.subproblemAlgo, radius = n.radius, radiusFieldName = n.radiusFieldName, polyFieldName = n.polyFieldName)
        while (len(distPt2Seg) > 0):
            closest = heapq.heappop(distPt2Seg)
            newSeq = [k for k in n.turning]
            newSeq.insert(closest[1], toInsert)
            child = BnBTreeNode(key = newSeq, rep = newSeq, startPt = n.startPt, endPt = n.endPt, nodes = n.nodes, neighbor = n.neighbor, radius = n.radius, radiusFieldName = n.radiusFieldName, polyFieldName = n.polyFieldName, subproblemAlgo = n.subproblemAlgo, funcSolve = n.funcSolve, funcBranch = n.funcBranch, funcUBEstimate = n.funcUBEstimate, bnbUB = n.bnbUB, turning = [], trespass = [], missing = [], path = [], repPt = {}, branchInfo = {'toInsert': toInsert, 'pos': closest[1], 'delta': closest[0], 'parentLowerBound': n.lowerBound})
            children.append(child)
        return children

    def cetspUBEstimate(n: BnBTreeNode):
        seq = [i for i in n.turning]
        missing = [i for i in n.missing]
        repPt = dict(n.repPt)
        ofv = n.ofv
        while (len(missing) > 0):
            bestMove = None
            for toInsert in missing:
                d2s = cetspSortInsertion(n.startPt, n.endPt, n.nodes, repPt, seq, toInsert, neighbor = n.neighbor, algo = n.subproblemAlgo, radius = n.radius, radiusFieldName = n.radiusFieldName, polyFieldName = n.polyFieldName)
                if (len(d2s) > 0):
                    candidate = heapq.heappop(d2s)
                    if (bestMove == None or candidate[0] < bestMove['delta']):
                        bestMove = {'node': toInsert, 'delta': candidate[0], 'pos': candidate[1]}
            if (bestMove == None):
                n.upperBound = float('inf')
                return
            seq = [k for k in seq]
            seq.insert(bestMove['pos'], bestMove['node'])
            update = cetspCheckVisit(n.startPt, n.endPt, n.nodes, seq, neighbor = n.neighbor, algo = n.subproblemAlgo, radius = n.radius, radiusFieldName = n.radiusFieldName, polyFieldName = n.polyFieldName)
            if (update['reachable'] == False):
                n.upperBound = float('inf')
                return
            seq = update['turning']
            missing = update['missing']
            repPt = update['repPt']
            ofv = update['ofv']
        n.upperBound = ofv
        return

    def cetspChoose(children: list[BnBTreeNode]):
        bestChild = None
        bestKey = None
        for child in children:
            lowerBound = child.lowerBound
            if (lowerBound == None or math.isinf(lowerBound)):
                lowerBound = -float('inf')
            missingList = getattr(child, 'missing', [])
            missingCnt = len(missingList) if (type(missingList) is list) else len(nodes)
            childKey = (lowerBound, missingCnt, len(child.rep))
            if (bestKey == None or childKey < bestKey):
                bestKey = childKey
                bestChild = child
        return bestChild

    bnbNode = cetspNew(startPt = startPt, endPt = endPt, nodes = nodes, funcSolve = cetspSolve, funcBranch = cetspBranch, funcUBEstimate = cetspUBEstimate)
    bnbTree = BnBTree(root = bnbNode, funcChoose = cetspChoose, timeLimit = timeLimit, gapTol = gapTol)
    bnbTree.bnb()
    if (bnbTree.best == None):
        result = {'ofv': None, 'dist': None, 'seq': None, 'path': None, 'gap': None, 'solType': 'Time_Limit' if (getattr(bnbTree, 'terminationStatus', None) == 'Time_Limit') else 'Infeasible', 'lowerBound': bnbTree.lowerBound, 'upperBound': bnbTree.upperBound, 'runtime': bnbTree.runtime, 'convergence': bnbTree.convergence, 'nodeCnt': bnbTree.count}
        return result
    if (bnbTree.lowerBound == None or abs(bnbTree.lowerBound) <= ERRTOL['vertical'] or math.isinf(bnbTree.lowerBound)):
        gap = None
    else:
        gap = (bnbTree.upperBound - bnbTree.lowerBound) / abs(bnbTree.lowerBound)
    result = {'ofv': bnbTree.ofv, 'dist': bnbTree.ofv, 'seq': bnbTree.best.rep, 'path': bnbTree.best.path, 'gap': gap, 'solType': 'Optimal' if (abs(bnbTree.lowerBound - bnbTree.upperBound) < 0.001) else 'Sub_Optimal', 'lowerBound': bnbTree.lowerBound, 'upperBound': bnbTree.upperBound, 'runtime': bnbTree.runtime, 'convergence': bnbTree.convergence, 'nodeCnt': bnbTree.count, 'bnbTree': bnbTree}
    return result

def _cetspBuildInitialSeq(startPt, endPt, nodes, neighbor = 'Circle', radius = None, radiusFieldName = 'radius', polyFieldName = 'neighbor'):
    nodeIDs = [i for i in nodes]
    if (len(nodeIDs) <= 1):
        result = [i for i in nodeIDs]
        return result
    seq = [nodeIDs[0], nodeIDs[1]]
    distFarest = -float('inf')
    for i in nodeIDs:
        for j in nodeIDs:
            if (i != j):
                ptI = _cetspNodeReferencePt(nodes, i, neighbor, radius, radiusFieldName, polyFieldName)
                ptJ = _cetspNodeReferencePt(nodes, j, neighbor, radius, radiusFieldName, polyFieldName)
                dist = distEuclideanXY(startPt, ptI) + distEuclideanXY(ptI, ptJ) + distEuclideanXY(ptJ, endPt)
                if (dist > distFarest):
                    distFarest = dist
                    seq = [i, j]
    result = seq
    return result

def _cetspNodeReferencePt(nodes, nodeID, neighbor = 'Circle', radius = None, radiusFieldName = 'radius', polyFieldName = 'neighbor'):
    if (neighbor == 'Circle'):
        if ('pt' not in nodes[nodeID]):
            raise MissingParameterError("ERROR: Circle neighborhood requires `pt` in nodes.")
        result = nodes[nodeID]['pt']
    elif (neighbor == 'Poly'):
        poly = _cetspNodePoly(nodes, nodeID, polyFieldName)
        try:
            result = ptPolyCenter(poly = poly)
        except Exception:
            polyShape = shapely.Polygon(poly)
            center = shapely.centroid(polyShape)
            result = (center.x, center.y)
    else:
        raise UnsupportedInputError("ERROR: Neighborhood type is not supported")
    return result

def _cetspNodeRadius(nodes, nodeID, radius = None, radiusFieldName = 'radius'):
    if (radiusFieldName != None and radiusFieldName in nodes[nodeID]):
        result = nodes[nodeID][radiusFieldName]
    elif ('radius' in nodes[nodeID]):
        result = nodes[nodeID]['radius']
    elif (radius != None):
        result = radius
    else:
        raise MissingParameterError("ERROR: Circle neighborhood requires `radius` or `radiusFieldName`.")
    if (result < 0):
        raise OutOfRangeError("ERROR: Circle radius should be nonnegative.")
    return result

def _cetspNodePoly(nodes, nodeID, polyFieldName = 'neighbor'):
    if (polyFieldName != None and polyFieldName in nodes[nodeID]):
        result = nodes[nodeID][polyFieldName]
    elif ('poly' in nodes[nodeID]):
        result = nodes[nodeID]['poly']
    elif ('neighbor' in nodes[nodeID]):
        result = nodes[nodeID]['neighbor']
    else:
        raise MissingParameterError("ERROR: Poly neighborhood requires polygon information in nodes.")
    if (result == None or len(result) < 3):
        raise InvalidPolygonError("ERROR: Poly neighborhood should include at least three points.")
    return result

def _cetspSolveSubproblem(startPt, endPt, nodes, seq, neighbor = 'Circle', algo = 'SOCP', radius = None, radiusFieldName = 'radius', polyFieldName = 'neighbor', **kwargs):
    if (len(seq) == 0):
        result = {
            'path': [startPt, endPt],
            'dist': distEuclideanXY(startPt, endPt)
        }
    elif (neighbor == 'Circle'):
        circles = []
        for i in seq:
            circles.append({'center': nodes[i]['pt'], 'radius': _cetspNodeRadius(nodes, i, radius, radiusFieldName)})
        result = solveCTP(startPt = startPt, endPt = endPt, circles = circles, algo = algo, **kwargs)
    elif (neighbor == 'Poly'):
        polys = []
        for i in seq:
            polys.append(_cetspNodePoly(nodes, i, polyFieldName))
        result = solvePTP(startPt = startPt, endPt = endPt, polys = polys, algo = algo, **kwargs)
    else:
        raise UnsupportedInputError("ERROR: Neighborhood type is not supported")
    return result

def _cetspSegTrespassNode(seg, nodes, nodeID, neighbor = 'Circle', radius = None, radiusFieldName = 'radius', polyFieldName = 'neighbor'):
    if (neighbor == 'Circle'):
        dist2Seg = distPt2Seg(pt = nodes[nodeID]['pt'], seg = seg)
        result = dist2Seg <= _cetspNodeRadius(nodes, nodeID, radius, radiusFieldName) + ERRTOL['distPt2Seg']
    elif (neighbor == 'Poly'):
        poly = _cetspNodePoly(nodes, nodeID, polyFieldName)
        segShape = shapely.LineString([seg[0], seg[1]])
        polyShape = shapely.Polygon(poly)
        if (polyShape.is_valid == False):
            polyShape = polyShape.buffer(0)
        result = segShape.intersects(polyShape) or segShape.distance(polyShape) <= ERRTOL['distPt2Poly']
    else:
        raise UnsupportedInputError("ERROR: Neighborhood type is not supported")
    return result

def cetspCheckVisit(startPt, endPt, nodes, seq, neighbor = 'Circle', algo = 'SOCP', radius = None, radiusFieldName = 'radius', polyFieldName = 'neighbor', **kwargs):
    turning = []
    trespass = []
    missing = []
    subproblem = _cetspSolveSubproblem(startPt = startPt, endPt = endPt, nodes = nodes, seq = seq, neighbor = neighbor, algo = algo, radius = radius, radiusFieldName = radiusFieldName, polyFieldName = polyFieldName, **kwargs)
    if (subproblem['dist'] == None):
        result = {'reachable': False, 'ofv': None, 'path': None, 'turning': None, 'trespass': None, 'missing': None, 'repPt': None}
        return result
    repPt = {}
    for i in range(1, len(subproblem['path']) - 1):
        repPt[seq[i - 1]] = subproblem['path'][i]
    degen = pathRemoveDegen(path = subproblem['path'])
    seqTra = [-1]
    seqTra.extend(seq)
    seqTra.append(-1)
    for i in range(len(degen['aggNodeList'])):
        if (degen['removedFlag'][i] == False):
            turning.extend([seqTra[k] for k in degen['aggNodeList'][i]])
    path = degen['newPath']
    ofv = subproblem['dist']
    for i in range(len(path) - 1):
        seg = [path[i], path[i + 1]]
        for j in nodes:
            if (j not in turning and j not in trespass):
                if (j not in seq):
                    if (_cetspSegTrespassNode(seg, nodes, j, neighbor, radius, radiusFieldName, polyFieldName) == True):
                        trespass.append(j)
                else:
                    trespass.append(j)
    turning = turning[1:-1]
    for j in nodes:
        if (j not in turning and j not in trespass):
            missing.append(j)
    result = {'reachable': True, 'ofv': ofv, 'path': path, 'turning': turning, 'trespass': trespass, 'missing': missing, 'repPt': repPt}
    return result

def cetspSortInsertion(startPt, endPt, nodes, repPt, turning, toInsert, neighbor = 'Circle', algo = 'SOCP', radius = None, radiusFieldName = 'radius', polyFieldName = 'neighbor', **kwargs):
    distPt2SegHeap = []
    heapq.heapify(distPt2SegHeap)
    if (len(turning) == 0):
        subproblem = _cetspSolveSubproblem(startPt = startPt, endPt = endPt, nodes = nodes, seq = [toInsert], neighbor = neighbor, algo = algo, radius = radius, radiusFieldName = radiusFieldName, polyFieldName = polyFieldName, **kwargs)
        if (subproblem['dist'] != None):
            delta = subproblem['dist'] - distEuclideanXY(startPt, endPt)
            heapq.heappush(distPt2SegHeap, (delta, 0))
        return distPt2SegHeap
    endpointPairs = [(startPt, repPt[turning[0]], 0)]
    for i in range(len(turning) - 1):
        endpointPairs.append((repPt[turning[i]], repPt[turning[i + 1]], i + 1))
    endpointPairs.append((repPt[turning[-1]], endPt, len(turning)))
    for endpointPair in endpointPairs:
        pt1, pt2, pos = endpointPair
        subproblem = _cetspSolveSubproblem(startPt = pt1, endPt = pt2, nodes = nodes, seq = [toInsert], neighbor = neighbor, algo = algo, radius = radius, radiusFieldName = radiusFieldName, polyFieldName = polyFieldName, **kwargs)
        if (subproblem['dist'] != None):
            delta = subproblem['dist'] - distEuclideanXY(pt1, pt2)
            heapq.heappush(distPt2SegHeap, (delta, pos))
    return distPt2SegHeap
