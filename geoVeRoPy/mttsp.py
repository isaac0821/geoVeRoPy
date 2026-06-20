import datetime
import heapq
import random
import warnings

from .common import *
from .geometry import *
from .ils import ILS, RawSolnNode
from .otp import solveMTTP


# Moving-target Traveling Salesman Problem
def solveMTTSP(startPt: pt, endPt: pt, nodes: dict, speed: float, nodeIDs: list[int | str] | str = 'All', startTime: float = 0.0, algo: str = 'Metaheuristic', method: str = 'ILS', initSeq: list[int | str] | None = None, initMethod: str = 'NearestStatic', initTemp: float = 100.0, coolRate: float = 0.95, neighRatio: dict | None = None, stop: dict | None = None, seed: int | None = None, outputFlag: bool = False, cacheFlag: bool = True, **kwargs) -> dict:
    """Solve a moving-target TSP.

    The current implementation supports an ILS sequence search. The path
    evaluation for each fixed sequence is delegated to :func:`solveMTTP`.
    """

    # Sanity check ============================================================
    if (startPt == None):
        raise MissingParameterError("ERROR: Missing start location.")
    if (endPt == None):
        raise MissingParameterError("ERROR: Missing end location.")
    if (nodes == None or type(nodes) is not dict):
        raise MissingParameterError("ERROR: Missing required field `nodes`.")
    if (speed <= 0):
        raise OutOfRangeError("ERROR: `speed` should be positive.")

    if (nodeIDs == 'All'):
        nodeIDList = [i for i in nodes]
    elif (type(nodeIDs) is list):
        nodeIDList = [i for i in nodeIDs]
    else:
        raise MissingParameterError("ERROR: `nodeIDs` should be 'All' or a list.")

    nodeIDSet = set(nodeIDList)
    if (len(nodeIDSet) != len(nodeIDList)):
        raise UnsupportedInputError("ERROR: `nodeIDs` should not contain duplicate nodes.")
    for i in nodeIDList:
        if (i not in nodes):
            raise OutOfRangeError("ERROR: Node %s cannot be found in `nodes`." % str(i))
        if ('pt' not in nodes[i]):
            raise MissingParameterError("ERROR: Node %s misses `pt`." % str(i))
        if ('vx' not in nodes[i] or 'vy' not in nodes[i]):
            raise MissingParameterError("ERROR: Node %s misses `vx` or `vy`." % str(i))

    if (initSeq != None):
        visited = set()
        for i in initSeq:
            if (i not in nodeIDSet):
                raise OutOfRangeError("ERROR: Node %s in `initSeq` cannot be found in `nodeIDs`." % str(i))
            if (i in visited):
                raise UnsupportedInputError("ERROR: Node %s appears more than once in `initSeq`." % str(i))
            visited.add(i)

    # MTTSP by different approach ============================================
    if (algo == 'Metaheuristic' and method == 'ILS'):
        if (initTemp <= 0):
            raise OutOfRangeError("ERROR: `initTemp` should be positive.")
        if (coolRate <= 0):
            raise OutOfRangeError("ERROR: `coolRate` should be positive.")
        if (initMethod not in ['Random', 'NearestStatic', 'NearestIntercept']):
            raise UnsupportedInputError("ERROR: Initial construction method is not supported.")
        if ('destroyRatio' in kwargs and (kwargs['destroyRatio'] < 0 or kwargs['destroyRatio'] > 1)):
            raise OutOfRangeError("ERROR: `destroyRatio` should be in [0, 1].")
        if (neighRatio == None):
            warnings.warn("WARNING: Missing ratios of each local search operator, set to be default.")
            neighRatio = {
                'Swap': 1,
                'Exchange': 1,
                'Rotate': 1,
                'Relocate': 1,
                'rndDestroy': 1
            }
        for key, val in neighRatio.items():
            if (key not in ['Swap', 'Exchange', 'Rotate', 'Relocate', 'rndDestroy']):
                raise UnsupportedInputError("ERROR: Neighborhood operator %s is not supported." % str(key))
            if (val < 0):
                raise OutOfRangeError("ERROR: Neighborhood ratio should be nonnegative.")
        if (len(neighRatio) == 0 or max(neighRatio.values()) <= 0):
            raise MissingParameterError("ERROR: No active neighborhood operator.")
        if (stop == None):
            warnings.warn("WARNING: Missing stopping criteria, set to be default.")
            stop = {
                'numIter': 100
            }
        for key, val in stop.items():
            if (key not in ['numIter', 'numNoImprove', 'numNoImproveIter', 'runtime']):
                raise UnsupportedInputError("ERROR: Stopping criterion %s is not supported." % str(key))
            if (val < 0):
                raise OutOfRangeError("ERROR: Stopping criterion should be nonnegative.")
        if ('numNoImproveIter' in stop):
            stop = dict(stop)
            stop['numNoImprove'] = stop.pop('numNoImproveIter')

        mttsp = _solveMTTSPILS(
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            nodeIDs = nodeIDList,
            speed = speed,
            startTime = startTime,
            initSeq = initSeq,
            initMethod = initMethod,
            initTemp = initTemp,
            coolRate = coolRate,
            neighRatio = neighRatio,
            stop = stop,
            seed = seed,
            outputFlag = outputFlag,
            cacheFlag = cacheFlag,
            destroyRatio = kwargs['destroyRatio'] if ('destroyRatio' in kwargs) else 0.3)
    else:
        raise UnsupportedInputError("ERROR: Combination of `algo` and `method` is not supported yet.")

    return mttsp


def _solveMTTSPILS(startPt: pt, endPt: pt, nodes: dict, nodeIDs: list[int | str], speed: float, startTime: float = 0.0, initSeq: list[int | str] | None = None, initMethod: str = 'NearestStatic', initTemp: float = 100.0, coolRate: float = 0.95, neighRatio: dict | None = None, stop: dict | None = None, seed: int | None = None, outputFlag: bool = False, cacheFlag: bool = True, destroyRatio: float = 0.3) -> dict:
    def mttspEvaluateSeq(startPt, endPt, nodes, seq, speed, startTime, cache, outputFlag):
        seq = [i for i in seq]
        seqKey = tuple(seq)
        if (cache != None and seqKey in cache):
            return cache[seqKey]

        mttp = solveMTTP(
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            seq = seq,
            speed = speed,
            startTime = startTime,
            outputFlag = outputFlag)
        soln = {
            'ofv': mttp['time'],
            'time': mttp['time'],
            'dist': mttp['dist'],
            'path3D': mttp['path3D'],
            'repPt': mttp['repPt'],
            'mttpSolType': mttp['solType']
        }
        if (cache != None):
            cache[seqKey] = soln
        return soln

    def mttspValidateSeq(seq, nodeIDs):
        newSeq = []
        visited = set()
        nodeIDSet = set(nodeIDs)
        for i in seq:
            if (i not in nodeIDSet):
                raise OutOfRangeError("ERROR: Node %s in sequence cannot be found in `nodeIDs`." % str(i))
            if (i in visited):
                raise UnsupportedInputError("ERROR: Node %s appears more than once in the sequence." % str(i))
            newSeq.append(i)
            visited.add(i)
        return newSeq

    def mttspBuildInitialSeq(startPt, endPt, nodes, nodeIDs, speed, startTime, initSeq, initMethod, cache, outputFlag):
        if (initSeq != None):
            return mttspValidateSeq(initSeq, nodeIDs)

        seq = []
        unvisited = [i for i in nodeIDs]

        if (initMethod == 'Random'):
            random.shuffle(unvisited)
            return unvisited

        if (initMethod == 'NearestStatic'):
            curPt = startPt
            while (len(unvisited) > 0):
                nextID = min(unvisited, key = lambda i: distEuclideanXY(curPt, nodes[i]['pt']))
                seq.append(nextID)
                unvisited.remove(nextID)
                curPt = nodes[nextID]['pt']
            return seq

        if (initMethod == 'NearestIntercept'):
            while (len(unvisited) > 0):
                candidate = []
                heapq.heapify(candidate)
                for i in unvisited:
                    trialSeq = [j for j in seq]
                    trialSeq.append(i)
                    trialSoln = mttspEvaluateSeq(startPt, endPt, nodes, trialSeq, speed, startTime, cache, outputFlag)
                    heapq.heappush(candidate, (trialSoln['ofv'], i))
                nextID = heapq.heappop(candidate)[1]
                seq.append(nextID)
                unvisited.remove(nextID)
            return seq

        raise UnsupportedInputError("ERROR: Initial construction method is not supported.")

    def mttspSortInsertion(n, toInsert):
        seq = [i for i in n.curRep]
        baseSoln = mttspEvaluateSeq(n.startPt, n.endPt, n.nodes, seq, n.speed, n.startTime, n.cache, n.outputFlag)
        insertion = []
        heapq.heapify(insertion)
        for pos in range(len(seq) + 1):
            newSeq = [i for i in seq]
            newSeq.insert(pos, toInsert)
            newSoln = mttspEvaluateSeq(n.startPt, n.endPt, n.nodes, newSeq, n.speed, n.startTime, n.cache, n.outputFlag)
            heapq.heappush(insertion, (newSoln['ofv'] - baseSoln['ofv'], pos))
        return insertion

    def mttspCheck(n):
        seq = mttspValidateSeq(n.curRep, n.nodeIDs)
        n.curRep = seq
        n.missing = [i for i in n.nodeIDs if (i not in seq)]

        soln = mttspEvaluateSeq(n.startPt, n.endPt, n.nodes, seq, n.speed, n.startTime, n.cache, n.outputFlag)
        n.soln = soln
        n.ofv = soln['ofv']
        n.time = soln['time']
        n.dist = soln['dist']
        n.path3D = soln['path3D']
        n.repPt = soln['repPt']
        n.mttpSolType = soln['mttpSolType']

        if (len(n.missing) == 0):
            n.feasibleFlag = True
            n.rep = [i for i in n.curRep]
            n.rawRep = [i for i in n.curRep]
        else:
            n.feasibleFlag = False
        return n.feasibleFlag

    def mttspFix(n):
        if (len(n.missing) == 0):
            n.feasibleFlag = True
            return

        toInsert = random.choice(n.missing)
        insertion = mttspSortInsertion(n, toInsert)
        insertPos = heapq.heappop(insertion)[1]
        n.curRep.insert(insertPos, toInsert)
        return

    def mttspRawNode(seq, n = None):
        if (n != None):
            return RawSolnNode(
                key = tuple(seq),
                rawRep = [i for i in seq],
                startPt = n.startPt,
                endPt = n.endPt,
                nodes = n.nodes,
                nodeIDs = n.nodeIDs,
                speed = n.speed,
                startTime = n.startTime,
                cache = n.cache,
                outputFlag = n.outputFlag,
                funcCheck = n.funcCheck,
                funcFix = n.funcFix)
        return RawSolnNode(
            key = tuple(seq),
            rawRep = [i for i in seq],
            startPt = startPt,
            endPt = endPt,
            nodes = nodes,
            nodeIDs = nodeIDs,
            speed = speed,
            startTime = startTime,
            cache = cache,
            outputFlag = outputFlag,
            funcCheck = mttspCheck,
            funcFix = mttspFix)

    def swap(n):
        seq = [i for i in n.rawRep]
        if (len(seq) <= 1):
            return n
        idxI = random.randint(0, len(seq) - 1)
        if (idxI < len(seq) - 1):
            seq[idxI], seq[idxI + 1] = seq[idxI + 1], seq[idxI]
        else:
            seq[idxI], seq[0] = seq[0], seq[idxI]
        return mttspRawNode(seq, n)

    def exchange(n):
        seq = [i for i in n.rawRep]
        if (len(seq) <= 3):
            return n
        idxI, idxJ = random.sample([i for i in range(len(seq))], 2)
        seq[idxI], seq[idxJ] = seq[idxJ], seq[idxI]
        return mttspRawNode(seq, n)

    def rotate(n):
        seq = [i for i in n.rawRep]
        if (len(seq) <= 3):
            return n
        idxI, idxJ = sorted(random.sample([i for i in range(len(seq))], 2))
        if (idxI == idxJ):
            return n
        seq[idxI:idxJ + 1] = list(reversed(seq[idxI:idxJ + 1]))
        return mttspRawNode(seq, n)

    def relocate(n):
        seq = [i for i in n.rawRep]
        if (len(seq) <= 2):
            return n
        idxI, idxJ = random.sample([i for i in range(len(seq))], 2)
        movingID = seq.pop(idxI)
        seq.insert(idxJ, movingID)
        return mttspRawNode(seq, n)

    def rndDestroy(n):
        seq = [i for i in n.rawRep]
        if (len(seq) <= 2 or destroyRatio <= 0):
            return n
        maxRemove = max(1, int(len(seq) * destroyRatio))
        numRemove = random.randint(1, maxRemove)
        for i in range(numRemove):
            if (len(seq) <= 1):
                break
            seq.pop(random.randint(0, len(seq) - 1))
        return mttspRawNode(seq, n)

    if (seed != None):
        random.seed(seed)

    cache = {} if (cacheFlag == True) else None
    initSeq = mttspBuildInitialSeq(startPt, endPt, nodes, nodeIDs, speed, startTime, initSeq, initMethod, cache, outputFlag)
    solNode = mttspRawNode(initSeq)

    opDict = {
        'Swap': swap,
        'Exchange': exchange,
        'Rotate': rotate,
        'Relocate': relocate,
        'rndDestroy': rndDestroy
    }
    funcNeiOps = [opDict[i] for i in opDict if (i in neighRatio and neighRatio[i] > 0)]
    if (len(funcNeiOps) == 0):
        raise MissingParameterError("ERROR: No active neighborhood operator.")

    startClockTime = datetime.datetime.now()
    ils = ILS(
        initNode = solNode,
        funcNeiOps = funcNeiOps,
        initTemp = initTemp,
        coolRate = coolRate,
        stopCriteria = stop,
        seed = seed)
    for opName, opFunc in opDict.items():
        if (opFunc in ils.roulette and opName in neighRatio):
            ils.roulette[opFunc] = neighRatio[opName]
    ils.solve()
    runtime = (datetime.datetime.now() - startClockTime).total_seconds()

    return {
        'ofv': ils.bestNode.ofv,
        'time': ils.bestNode.time,
        'dist': ils.bestNode.dist,
        'seq': [i for i in ils.bestNode.curRep],
        'path3D': ils.bestNode.path3D,
        'repPt': ils.bestNode.repPt,
        'solType': 'ILS',
        'mttpSolType': ils.bestNode.mttpSolType,
        'runtime': runtime,
        'convergence': ils.convergence,
        'cacheSize': len(cache) if (cache != None) else None
    }
