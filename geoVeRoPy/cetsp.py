import math
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
        if ('radius' not in kwargs and 'radiusFieldName' not in kwargs):
            raise MissingParameterError("ERROR: Must provide an uniform radius as `radius` or the field name of radius as `radiusFieldName`.")
    elif (neighbor == 'Poly'):
        if ('polyFieldName' not in kwargs):
            warnings.warn("WARNING: `polyFieldName` is not provided, set to be default as `neighbor`.")
            kwargs['polyFieldName'] = 'neighbor'
    else:
        raise UnsupportedInputError("ERROR: Neighborhood type is not supported")

    cetsp = None
    # CETSP by different approach =============================================
    # NOTE: Available options
    # - "Euclidean" + "Circle" + "Exact" + "BnB"
    # - "Euclidean" + "Circle" + "Metaheuristic" + "ILS"
    if (dimension == 'Euclidean' and neighbor == "Circle" and algo == "Exact" and method == "BnB"):
        cetsp = _solveCETSPBnBCircle(
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            radius = kwargs['radius'] if 'radius' in kwargs else None,
            radiusFieldName = kwargs['radiusFieldName'] if 'radiusFieldName' in kwargs else None,
            timeLimit = kwargs['timeLimit'] if 'timeLimit' in kwargs else None)

    elif (dimension == 'Euclidean' and neighbor == "Circle" and algo == "Metaheuristic" and method == "ILS"):
        if ('initTemp' not in kwargs):
            kwargs['initTemp'] = 100
        if ('coolRate' not in kwargs):
            kwargs['coolRate'] = 0.95
        if ('neighRatio' not in kwargs):
            warnings.warn("WARNING: Missing ratios of each local search operator, set to be default.")
            kwargs['neighRatio'] = {
                'Swap': 0.1,
                'Exchange': 0.1,
                'Rotate': 0.3,
                'rndDestroy': 0.4
            }
        if ('stop' not in kwargs):
            warnings.warn("WARNING: Missing stopping criteria, set to be default.")
            kwargs['stop'] = {
                'numNoImproveIter': 200
            }
        cetsp = _solveCETSPILSCircle(
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            radius = kwargs['radius'] if 'radius' in kwargs else None,
            radiusFieldName = kwargs['radiusFieldName'] if 'radiusFieldName' in kwargs else None,
            initTemp = kwargs['initTemp'],
            coolRate = kwargs['coolRate'],
            neighRatio = kwargs['neighRatio'],
            stop = kwargs['stop'])

    else:
        raise UnsupportedInputError("ERROR: Combination of `dimension`, `neighbor`, `algo`, and `method` is not supported yet.")
    return cetsp

def _solveCETSPILSCircle(startPt: pt, endPt: pt, nodes: dict, radius: float | None = None, radiusFieldName: str = 'radius', initTemp: float = 100, coolRate: float = 0.95, neighRatio: dict = { 'Swap': 0.1, 'Exchange': 0.1, 'Rotate': 0.3, 'rndDestroy': 0.4 }, stop: dict = {}, **kwargs) -> dict | None:

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
        distPt2Seg = cetspSortInsertion(n.startPt, n.endPt, n.nodes, n.repPt, n.turning, toInsert, algo = "SOCP")
        n.curRep.insert(heapq.heappop(distPt2Seg)[1], toInsert)
        return

    def cetspCheck(n):
        # 给定一个RawSolnNode，确定是否访问了所有的点
        seq = n.curRep
        checkVisit = cetspCheckVisit(n.startPt, n.endPt, n.nodes, seq, algo = 'SOCP')

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
            rndDestroy])
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

def _solveCETSPBnBCircle(startPt: pt, endPt: pt, nodes: dict, radius: float | None = None, radiusFieldName: str = 'radius', timeLimit: int | None = None) -> dict | None:

    def cetspNew(startPt, endPt, nodes, funcSolve, funcBranch, funcUBEstimate):
        seq = []
        # 找到两个customer，让startPt => cus1 => cus2 => endPt的距离最长
        distFarest = 0
        for i in nodes:
            for j in nodes:
                if (i != j):
                    d = distEuclideanXY(startPt, nodes[i]['pt'])
                    d += distEuclideanXY(nodes[i]['pt'], nodes[j]['pt'])
                    d += distEuclideanXY(nodes[j]['pt'], endPt)
                    if (d > distFarest):
                        distFarest = d
                        seq = [i, j]
        n = BnBTreeNode(
            key = seq,
            rep = seq,
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            funcSolve = funcSolve,
            funcBranch = funcBranch,
            funcUBEstimate = funcUBEstimate,
            turning = [],
            trespass = [],
            missing = [],
            path = [],
            repPt = {})
        return n

    def cetspSolve(n: BnBTreeNode):
        '''Given ordering of nodes, returns the path of CETSP'''
        seq = n.rep
        checkVisit = cetspCheckVisit(n.startPt, n.endPt, n.nodes, seq)

        n.ofv = checkVisit['ofv']
        n.path = checkVisit['path']
        n.turning = checkVisit['turning']
        n.trespass = checkVisit['trespass']
        n.missing = checkVisit['missing']
        n.repPt = checkVisit['repPt']
        if (len(n.missing) > 0):
            n.relaxFlag = True
        else:
            n.relaxFlag = False

        printLog("Turning: ", n.turning)
        printLog("Trespass: ", n.trespass)
        printLog("Missing: ", n.missing)
        return

    def cetspBranch(n: BnBTreeNode):
        # 防错
        if (len(n.missing) == 0):
            return []

        children = []
        # FIXME 先按简单的来，随机选一个未被分配的，然后按照可能的顺序进行分配
        toInsert = random.choice(n.missing)
        distPt2Seg = cetspSortInsertion(n.startPt, n.endPt, n.nodes, n.repPt, n.turning, toInsert)

        while(len(distPt2Seg) > 0):
            newSeq = [k for k in n.turning]
            newSeq.insert(heapq.heappop(distPt2Seg)[1], toInsert)

            children.append(BnBTreeNode(
                key = newSeq,
                rep = newSeq,
                startPt = n.startPt,
                endPt = n.endPt,
                nodes = n.nodes,
                funcSolve = n.funcSolve,
                funcBranch = n.funcBranch,
                bnbUB = n.bnbUB,
                turning = [],
                trespass = [],
                missing = [],
                path = []))

        return children

    def cetspUBEstimate(n: BnBTreeNode):

        if (len(n.missing) == 0):
            return

        seq = n.turning
        missing = n.missing
        repPt = n.repPt
        path = n.path
        ofv = n.ofv

        while (len(missing) > 0):

            toInsert = random.choice(missing)
            d2s = cetspSortInsertion(n.startPt, n.endPt, n.nodes, repPt, seq, toInsert)
            closest = heapq.heappop(d2s)

            seq = [k for k in seq]
            seq.insert(closest[1], toInsert)

            update = cetspCheckVisit(n.startPt, n.endPt, n.nodes, seq)

            seq = update['turning']
            missing = update['missing']
            repPt = update['repPt']
            path = update['path']
            ofv = update['ofv']

        n.upperBound = ofv + 1

        return

    bnbNode = cetspNew(
        startPt = startPt,
        endPt = endPt,
        nodes = nodes,
        funcSolve = cetspSolve,
        funcBranch = cetspBranch,
        funcUBEstimate = cetspUBEstimate)
    bnbTree = BnBTree(root = bnbNode)
    bnbTree.bnb(timeLimit)

    return {
        'ofv': bnbTree.ofv,
        'dist': bnbTree.ofv,
        'seq': bnbTree.best.rep,
        'path': bnbTree.best.path,
        'gap': (bnbTree.upperBound - bnbTree.lowerBound) / bnbTree.lowerBound,
        'solType': 'Optimal' if (abs(bnbTree.lowerBound - bnbTree.upperBound) < 0.001) else 'Sub_Optimal',
        'lowerBound': bnbTree.lowerBound,
        'upperBound': bnbTree.upperBound,
        'runtime': bnbTree.convergence[-1][2],
        'convergence': bnbTree.convergence,
    }

def cetspCheckVisit(startPt, endPt, nodes, seq, algo = 'SOCP'):
    turning = []
    trespass = []
    missing = []

    # 需要先得到一组turn point
    # 当前的序列
    circles = []
    for i in seq:
        circles.append({
            'center': nodes[i]['pt'],
            'radius': nodes[i]['radius']
        })

    # 计算SOCP
    c2c = solveCTP(
        startPt = startPt,
        endPt = endPt,
        circles = circles,
        algo = algo
    )
    repPt = {}
    for i in range(1, len(c2c['path']) - 1):
        repPt[seq[i - 1]] = c2c['path'][i]

    degen = pathRemoveDegen(path = c2c['path'])

    seqTra = [-1]
    seqTra.extend(seq)
    seqTra.append(-1)
    for i in range(len(degen['aggNodeList'])):
        if (degen['removedFlag'][i] == False):
            turning.extend([seqTra[k] for k in degen['aggNodeList'][i]])

    path = degen['newPath']
    ofv = c2c['dist']

    for i in range(len(path) - 1):
        # 分段的线段
        seg = [path[i], path[i + 1]]    
        # 对于每个线段，测试哪些圆是经过了的
        for j in nodes:
            if (j not in turning and j not in trespass):
                if (j not in seq):
                    dist2Seg = distPt2Seg(
                        pt = nodes[j]['pt'],
                        seg = seg)
                    if (dist2Seg <= nodes[j]['radius']):
                        trespass.append(j)
                else:
                    trespass.append(j)

    # 注意，turning中不包括startPt和endPt
    turning = turning[1:-1]
    for j in nodes:
        if (j not in turning and j not in trespass):
            missing.append(j)

    return {
        'ofv': ofv,
        'path': path,
        'turning': turning,
        'trespass': trespass,
        'missing': missing,
        'repPt': repPt
    }

def cetspSortInsertion(startPt, endPt, nodes, repPt, turning, toInsert, algo = "SOCP"):
    # 计算toInsert到turning上的每一段的距离
    distPt2Seg = []
    heapq.heapify(distPt2Seg)

    # 第一段
    seg = [startPt, repPt[turning[0]]]
    delta = solveCTP(
        startPt = startPt,
        endPt = repPt[turning[0]],
        circles = [{
            'center': nodes[toInsert]['pt'],
            'radius': nodes[toInsert]['radius']
        }],
        algo = algo)['dist'] - distEuclideanXY(seg[0], seg[1])
    heapq.heappush(distPt2Seg, (delta, 0))

    # 中间部分
    for i in range(len(turning) - 1):
        seg = [repPt[turning[i]], repPt[turning[i + 1]]]
        delta = solveCTP(
            startPt = repPt[turning[i]],
            endPt = repPt[turning[i + 1]],
            circles = [{
                'center': nodes[toInsert]['pt'],
                'radius': nodes[toInsert]['radius']
            }],
            algo = algo)['dist'] - distEuclideanXY(seg[0], seg[1])
        heapq.heappush(distPt2Seg, (delta, i + 1))

    # 最后一段
    seg = [repPt[turning[-1]], endPt]
    delta = solveCTP(
        startPt = repPt[turning[-1]],
        endPt = endPt,
        circles = [{
            'center': nodes[toInsert]['pt'],
            'radius': nodes[toInsert]['radius']
        }],
        algo = algo)['dist'] - distEuclideanXY(seg[0], seg[1])
    heapq.heappush(distPt2Seg, (delta, len(turning)))
    return distPt2Seg 