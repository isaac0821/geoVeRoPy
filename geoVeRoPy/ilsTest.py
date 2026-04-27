import random
import heapq

from .common import *
from .obj2Obj import *
from .ils import *
from .geometry import *
from .cetsp import *

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
    distPt2Seg = cetspSortInsertion(n.startPt, n.endPt, n.nodes, n.repPt, n.turning, toInsert, algo = "AdaptIter")
    n.curRep.insert(heapq.heappop(distPt2Seg)[1], toInsert)
    return

def cetspCheck(n):
    # 给定一个RawSolnNode，确定是否访问了所有的点
    seq = n.curRep
    checkVisit = cetspCheckVisit(n.startPt, n.endPt, n.nodes, seq, algo = 'AdaptIter')

    n.ofv = checkVisit['ofv']
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

    # printLog("Turning: ", n.turning)
    # printLog("Trespass: ", n.trespass)
    # printLog("Missing: ", n.missing)
    
    return n.feasibleFlag

def swap(seq, idxI):
    newSeq = [i for i in seq]
    if (idxI < len(newSeq) - 1):
        newSeq[idxI], newSeq[idxI + 1] = newSeq[idxI + 1], newSeq[idxI]
    else:
        newSeq[idxI], newSeq[0] = newSeq[0], newSeq[idxI]
    return newSeq
