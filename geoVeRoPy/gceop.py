import math
import random
import shapely
from shapely.geometry import mapping

from .ds import *
from .common import *
from .geometry import *
from .obj2Obj import *
from .polyTour import *

def solveGCEOP(
    startLoc: pt,
    endLoc: pt,
    nodes: dict, # Index from 1
    radiusList: list | None = None,
    radiusListFieldName: str = 'radiusList',
    timeLimit: int | None = None,
    maxLength: float = None,
    popSize: int = None,
    neighRatio: dict = {},
    stop: dict = {},
    **kwargs
    ) -> dict | None:

    DP = {}

    class chromosomeGCEOP:
        def __init__(self, startLoc, endLoc, nodes, seq, maxLength):
            # NOTE: seq以depotID开始和结束
            # NOTE: 每个seq都需要补全为一条合法的gceop路径
            # NOTE: seq的格式为[(nodeID, radiusIdx), (nodeID, radiusIdx), ...]
            
            # 记录nodes的信息
            self.startLoc = startLoc
            self.endLoc = endLoc
            self.nodes = nodes
            self.maxLength = maxLength

            # 原始输入的seq
            self.seq = Ring()
            for i in seq:
                n = RingNode(key = i[0], value = i[1])
                self.seq.append(n)
            self.seq.rehead(0)

            # 转折点列表
            self.turning = [] # Format: [(nodeID, radiusIdx), (nodeID, radiusIdx), ...]
            self.aggTurning = [] # Format: [[(nodeID, radiusIdx)], [(nodeID, radiusIdx), (nodeID, radiusIdx)], ...]
            # 穿越点列表
            self.trespass = [] # Format: [(nodeID, radiusIdx), (nodeID, radiusIdx), ...]
            # 未访问点及距离，暂存用，这里保存的是距离
            self.dist2NotInclude = {}
            # 补全
            self.seq2Path()
        
        def getPath(self):
            # 需要先得到一组seq
            circles = []
            seqTra = [[n.key, n.value] for n in self.seq.traverse()]
            seqTra.append([0, 0])

            hashSeqTra = (tuple(i) for i in seqTra)

            c2c = None
            degen = None
            if (hashSeqTra in DP):
                c2c = DP[hashSeqTra]['c2c']
                degen = DP[hashSeqTra]['degen']
            else:
                for i in range(1, len(seqTra) - 1):
                    nodeID = seqTra[i][0]
                    radiusIdx = seqTra[i][1]
                    circles.append({
                        'center': self.nodes[nodeID]['loc'],
                        'radius': radiusList[radiusIdx] if radiusList != None else self.nodes[nodeID][radiusListFieldName][radiusIdx]
                    })
                c2c = circle2CirclePath(
                    startPt = self.startLoc,
                    endPt = self.endLoc,
                    circles = circles,
                    algo = 'SOCP')
                degen = seqRemoveDegen(seq = c2c['path'])
                DP[hashSeqTra] = {
                    'c2c': c2c,
                    'degen': degen
                }

            # 找turn point
            self.turning = []
            self.aggTurning = []
            for i in range(len(degen['aggNodeList'])):
                if (degen['removedFlag'][i] == False):
                    self.turning.extend([seqTra[k] for k in degen['aggNodeList'][i]])
                    self.aggTurning.append([seqTra[k] for k in degen['aggNodeList'][i]])
            self.path = degen['newSeq']
            self.dist = c2c['dist']

            self.trespass = []
            self.dist2NotInclude = {}
            self.score = 0
            # 先判断每个点是不是trespass点，collect score
            nodesInTurning = []
            for k in self.turning:
                nodesInTurning.append(k[0])
            for i in self.nodes:
                # 假如(i, x)都不在self.turning里，就计算下距离
                if (i not in nodesInTurning):
                    res = distPt2Seq(
                        pt = self.nodes[i]['loc'], 
                        seq = self.path,
                        closedFlag = True,
                        detailFlag = True)
                    # 判断有没有一环相交，从最内环到最外环
                    inteFlag = False
                    # radiusList4I得是从小到大
                    radiusList4I = radiusList if radiusList != None else self.nodes[i][radiusListFieldName]
                    for k in range(len(radiusList4I)):
                        if (res['dist'] <= radiusList4I[k]):
                            self.trespass.append((i, k))
                            self.score += self.nodes[i]['scoreList'][k]
                            inteFlag = True
                            break
                    if (not inteFlag):
                        self.dist2NotInclude[i] = res
            # 搜集turning上的score
            for (i, k) in self.turning:
                if (i != 0): # 0是depot
                    self.score += self.nodes[i]['scoreList'][k]

        def seq2Path(self):
            # 记录历史查找过的路径，如果出现了重复，就调整为上一次的合法路径
            self.getPath()
            pathCalFlag = True # 少进行一次circle2CirclePath()            

            # 现在开始补齐，多退少补
            # Add有两种情况：
            # 1. 完全不相交的邻域加入序列
            # 2. 序列中的领域缩小相交的环
            # Remove也有两种情况：
            # 1. 完全移除一个turning
            # 2. 外移一个turning的相交环
            canAddFlag = True
            needRemoveFlag = True
            tabuOpt = []
            while (canAddFlag or needRemoveFlag):
                canAddFlag = False
                needRemoveFlag = False

                # 先按照turnpoint构造一个路径
                if (pathCalFlag):
                    pathCalFlag = False
                else:
                    self.getPath()

                # 判断距离是否有富余，判断是否能够添加turning，或者更改半径增加
                if (self.dist <= self.maxLength):
                    candi = []
                    coeff = []

                    # 先尝试插入新的邻域的方式
                    projTo = {}
                    for i in self.dist2NotInclude:
                        # 上一个点和下一个点的位置，使用DP尽量减少一些计算
                        if (self.dist2NotInclude[i]['nearestIdx'][0] not in projTo):
                            projTo[self.dist2NotInclude[i]['nearestIdx'][0]] = {
                                'prevLoc': self.dist2NotInclude[i]['nearestSeg'][0],
                                'nextLoc': self.dist2NotInclude[i]['nearestSeg'][1],
                                'distPrevNext': distEuclideanXY(
                                    self.dist2NotInclude[i]['nearestSeg'][0], 
                                    self.dist2NotInclude[i]['nearestSeg'][1])
                            }
                        prevLoc = projTo[self.dist2NotInclude[i]['nearestIdx'][0]]['prevLoc']
                        nextLoc = projTo[self.dist2NotInclude[i]['nearestIdx'][0]]['nextLoc']
                        distPrevNext = projTo[self.dist2NotInclude[i]['nearestIdx'][0]]['distPrevNext']

                        # 1. 如果最保守的上界估计都可以被加入，则candi为最内圈的那个
                        # 2. 如果最保守的下界也加不进来，那就放不到candi里
                        # 3. 如果介于最保守的上下界之间，那么就从内到外逐圈进行估计，最里面的那个可满足的
                        worthTryFlag = None
                        candiForNode = None

                        # 半径列表
                        # 0 - 最小半径，-1 - 最大半径
                        radiusList4I = radiusList if radiusList != None else self.nodes[i][radiusListFieldName]

                        # 先计算最保守上界估计， 如果加上来还可以满足，那肯定可以试试，直接插入最内环
                        deltaLength  = distEuclideanXY(prevLoc, self.nodes[i]['loc'])
                        deltaLength += distEuclideanXY(nextLoc, self.nodes[i]['loc'])
                        deltaLength -= distPrevNext
                        if (self.dist + deltaLength <= self.maxLength):
                            worthTryFlag = True
                            candiForNode = ('Add', i, 0, self.dist2NotInclude[i]['nearestIdx'])

                        # 如果最保守的上界超标了，最保守的下界也超标了，那肯定不必要再去算一轮精确点的
                        if (worthTryFlag == None and deltaLength - 2 * radiusList4I[-1] >= self.maxLength):
                            worthTryFlag = False

                        # 如果最保守的上界和下届都不能用来判断，那就给个更精确的估计
                        # NOTE: 用circle2CirclePath测试太昂贵了，这边用的是角平分线于neighbor边缘的交点进行的估计
                        if (worthTryFlag == None):
                            worthTryFlag = False
                            # 计算角平分线
                            pt1 = ptInDistXY(
                                pt = self.nodes[i]['loc'],
                                direction = headingXY(self.nodes[i]['loc'], prevLoc),
                                dist = radiusList4I[-1])
                            pt2 = ptInDistXY(
                                pt = self.nodes[i]['loc'],
                                direction = headingXY(self.nodes[i]['loc'], nextLoc),
                                dist = radiusList4I[-1])
                            midLoc = ptMid([pt1, pt2])

                            # 从内到外尝试看看哪个可能可以
                            # radiusList4I得是从小到大
                            for k in range(len(radiusList4I)):
                                edgeLoc = ptInDistXY(
                                    pt = self.nodes[i]['loc'],
                                    direction = headingXY(self.nodes[i]['loc'], midLoc),
                                    dist = radiusList4I[k])
                                deltaLength  = distEuclideanXY(prevLoc, edgeLoc)
                                deltaLength += distEuclideanXY(nextLoc, edgeLoc)
                                deltaLength -= distPrevNext
                                # NOTE: 0.98 is a magic number, 用来修正估计值
                                if ((self.dist + deltaLength) * 0.98 <= self.maxLength):
                                    worthTryFlag = True
                                    candiForNode = ('Add', i, k, self.dist2NotInclude[i]['nearestIdx'])
                                    break

                        if (worthTryFlag):
                            opt = candiForNode
                            if (opt not in tabuOpt):
                                candi.append(opt)
                                tabuOpt.append(opt)
                                coeff.append(self.nodes[i]['scoreList'][candiForNode[2]] / deltaLength)

                    # 再尝试更改turning的访问位置的方法，只往里移动一格，不要移到最里头
                    for i in range(1, len(self.aggTurning) - 1):
                        # Case 1: 如果aggTurning[i]上只有一个点，且还没移动到最内部，那么简单地，往里移动的交点在当前交点和圆心的连线上，往里一格
                        if (len(self.aggTurning[i]) == 1 and self.aggTurning[i][0][1] > 0):
                            curNodeID = self.aggTurning[i][0][0]
                            curRadiusList = radiusList if radiusList != None else self.nodes[curNodeID][radiusListFieldName]
                            curRadiusIdx = self.aggTurning[i][0][1]
                            newRadius = curRadiusList[curRadiusIdx - 1]
                            curScore = self.nodes[curNodeID]['scoreList'][curRadiusIdx]
                            newScore = self.nodes[curNodeID]['scoreList'][curRadiusIdx - 1]

                            prevLoc = self.path[i - 1]
                            nextLoc = self.path[i + 1]
                            currLoc = self.path[i]
                            newLoc = ptInDistXY(
                                pt = self.nodes[curNodeID]['loc'],
                                direction = headingXY(self.nodes[curNodeID]['loc'], currLoc),
                                dist = newRadius)
                            deltaLength  = distEuclideanXY(prevLoc, newLoc)
                            deltaLength += distEuclideanXY(nextLoc, newLoc)
                            deltaLength -= distEuclideanXY(prevLoc, currLoc)
                            deltaLength -= distEuclideanXY(prevLoc, currLoc)

                            if ((self.dist + deltaLength) * 0.98 <= self.maxLength):
                                opt = ('Shrink', curNodeID, curRadiusIdx - 1)
                                if (opt not in tabuOpt):
                                    candi.append(opt)
                                    tabuOpt.append(opt)
                                    coeff.append((newScore - curScore) / deltaLength)

                        # Case 2: 如果转折点对应多于一个点，则分别试着往内侧移动一格，如果不在最内圈的话
                        elif (len(self.aggTurning[i]) > 1):
                            prevLoc = self.path[i - 1]
                            nextLoc = self.path[i + 1]
                            currLoc = self.path[i]

                            # 对于该转折点上的每一个turning，都试试，如果不在最内圈的话
                            for j in range(len(self.aggTurning[i])):
                                if (self.aggTurning[i][j][1] > 0):
                                    curNodeID = self.aggTurning[i][j][0]
                                    curRadiusList = radiusList if radiusList != None else self.nodes[curNodeID][radiusListFieldName]
                                    curRadiusIdx = self.aggTurning[i][j][1]
                                    newRadius = curRadiusList[curRadiusIdx - 1]
                                    curScore = self.nodes[curNodeID]['scoreList'][curRadiusIdx]
                                    newScore = self.nodes[curNodeID]['scoreList'][curRadiusIdx - 1]

                                    newLoc = ptInDistXY(
                                        pt = self.nodes[curNodeID]['loc'],
                                        direction = headingXY(self.nodes[curNodeID]['loc'], currLoc),
                                        dist = newRadius)

                                    # 有两种可能的方式改变路径，取其中短的那条来估计deltaLength：
                                    # 1. deltaLen1: prevLoc -> currLoc -> newLoc -> nextLoc
                                    # 2. deltaLen2: prevLoc -> newLoc -> currLoc -> nextLoc
                                    L1 = distEuclideanXY(prevLoc, currLoc)
                                    L2 = distEuclideanXY(nextLoc, currLoc)
                                    L3 = distEuclideanXY(newLoc, currLoc)
                                    L4 = distEuclideanXY(prevLoc, newLoc)
                                    L5 = distEuclideanXY(prevLoc, newLoc)
                                    deltaLen1 = L3 + L4 - L1
                                    deltaLen2 = L3 + L5 - L2
                                    deltaLength = min(deltaLen1, deltaLen2)

                                    if ((self.dist + deltaLength) * 0.98 <= self.maxLength):
                                        opt = ('Shrink', curNodeID, curRadiusIdx - 1)
                                        if (opt not in tabuOpt):
                                            candi.append(opt)
                                            tabuOpt.append(opt)
                                            coeff.append((newScore - curScore) / deltaLength)

                    # 如果找到可以加入的candidate，按照性价比抽样，性价比越高的被选中概率越大
                    if (len(candi) > 0):
                        # 随机抽一个，按照权重
                        insertCandi = candi[rndPick(coeff)]
                        if (insertCandi[0] == 'Add'):
                            self.aggTurning.insert(insertCandi[3][1], [[insertCandi[1], insertCandi[2]]])
                            self.turning = []
                            for k in range(len(self.aggTurning)):
                                self.turning.extend(self.aggTurning[k])
                        elif (insertCandi[0] == 'Shrink'):
                            self.turning = []
                            for k in range(len(self.aggTurning)):
                                self.turning.extend(self.aggTurning[k])
                            for i in range(len(self.turning)):
                                if (self.turning[i][0] == insertCandi[1]):
                                    self.turning[i][1] = insertCandi[2]
                        canAddFlag = True

                # 距离如果大于maxLength，从现有的turning中试图逐个扩大圈移除，或者扩大访问领域的半径，按照分值加权随机移除
                else:
                    # 计算移除turning的score
                    candi = []
                    coeff = []
                    for i in self.turning:
                        if (i[0] != 0):
                            curNodeID = i[0]
                            curRadiusList = radiusList if radiusList != None else self.nodes[curNodeID][radiusListFieldName]
                            curRadiusIdx = i[1]
                            curScore = self.nodes[curNodeID]['scoreList'][curRadiusIdx]

                            # 如果是最外圈，只能删除
                            if (curRadiusIdx == len(curRadiusList) - 1):
                                candi.append(('Remove', curNodeID, i))
                                coeff.append(1 / curScore)
                            # 否则外移一圈
                            else:
                                newScore = self.nodes[curNodeID]['scoreList'][curRadiusIdx + 1]
                                candi.append(('Expand', curNodeID, curRadiusIdx + 1))
                                coeff.append(1 / (curScore - newScore))

                    # 随机抽一个，按照权重
                    removeCandi = candi[rndPick(coeff)]
                    if (removeCandi[0] == 'Remove'):
                        self.turning.remove(removeCandi[2])
                    elif (removeCandi[0] == 'Expand'):
                        self.turning = []
                        for k in range(len(self.aggTurning)):
                            self.turning.extend(self.aggTurning[k])
                        for i in range(len(self.turning)):
                            if (self.turning[i][0] == removeCandi[1]):
                                self.turning[i][1] = removeCandi[2]
                    needRemoveFlag = True

                # 更新seq为新的turning point
                self.seq = Ring()
                for i in range(len(self.turning) - 1):
                    n = RingNode(key = self.turning[i][0], value = self.turning[i][1])
                    self.seq.append(n)
                self.seq.rehead(0)

    def intraSwap(chromo):
        # 每个点随机重新选择邻域圈层
        seq = [[i.key, i.value] for i in chromo.seq.traverse()]
        numSwap = int(len(seq) * random.random() * 0.8)
        swapList = random.sample([i for i in range(len(seq))], numSwap)
        for i in swapList:
            if (seq[i][0] != 0):
                seq[i][1] = random.randint(0, len(radiusList if radiusList != None else nodes[seq[i][0]][radiusListFieldName]) - 1)
        return chromosomeGCEOP(startLoc, endLoc, nodes, seq, maxLength)

    def interSwap(chromo, idxI):
        seq = [[i.key, i.value] for i in chromo.seq.traverse()]
        if (idxI < len(seq) - 1):
            seq[idxI], seq[idxI + 1] = seq[idxI + 1], seq[idxI]
        else:
            seq[idxI], seq[0] = seq[0], seq[idxI]
        return chromosomeGCEOP(startLoc, endLoc, nodes, seq, maxLength)

    def exchange(chromo, idxI, idxJ):
        seq = [[i.key, i.value] for i in chromo.seq.traverse()]
        seq[idxI], seq[idxJ] = seq[idxJ], seq[idxI]
        return chromosomeGCEOP(startLoc, endLoc, nodes, seq, maxLength)

    def rndDestroy(chromo):
        seq = [[i.key, i.value] for i in chromo.seq.traverse()]
        numRemove = int(len(seq) * random.random() * 0.3)
        newSeq = [i for i in seq]
        for i in range(numRemove):
            newSeq.remove(newSeq[random.randint(0, len(newSeq) - 1)])
        if ([0, 0] not in newSeq):
            newSeq.append([0, 0])
        return chromosomeGCEOP(startLoc, endLoc, nodes, newSeq, maxLength)

    def rotate(chromo, idxI, idxJ):
        seq = [[i.key, i.value] for i in chromo.seq.traverse()]
        if (idxI > idxJ):
            idxI, idxJ = idxJ, idxI
        newSeq = [seq[i] for i in range(idxI)]
        newSeq.extend([seq[idxJ - i] for i in range(idxJ - idxI + 1)])
        newSeq.extend([seq[i] for i in range(idxJ + 1, len(seq))])
        return chromosomeGCEOP(startLoc, endLoc, nodes, newSeq, maxLength)
    
    def crossover(chromo1, chromo2, idx1I, idx1J, idx2I, idx2J):
        # 原始序列
        seq1 = [[i.key, i.value] for i in chromo1.seq.traverse()]
        seq2 = [[i.key, i.value] for i in chromo2.seq.traverse()]

        # 把idxI和idxJ排个序换一下，保证idxI在前面
        if (idx1I > idx1J):
            idx1I, idx1J = idx1J, idx1I
        if (idx2I > idx2J):
            idx2I, idx2J = idx2J, idx2I
        # Before:
        # = = = idx1I.prev idx1I - - - idx1J idx1J.next = = =
        # = = = idx2I.prev idx2I - - - idx2J idx2J.next = = =
        # After:
        # = = = idx1I.prev idx2I - - - idx2J idx1J.next = = =
        # = = = idx2I.prev idx1I - - - idx1J idx2J.next = = =
        
        # 构造新序列
        nodeInSeq1 = [seq2[i][0] for i in range(idx2I, idx2J)]
        newSeq1 = [seq2[i] for i in range(idx2I, idx2J)]
        for i in range(idx1J, len(seq1)):
            if (seq1[i][0] not in nodeInSeq1):
                newSeq1.append(seq1[i])
                nodeInSeq1.append(seq1[i])
        for i in range(idx1I):
            if (seq1[i][0] not in nodeInSeq1):
                newSeq1.append(seq1[i])
                nodeInSeq1.append(seq1[i])
        if ([0, 0] not in newSeq1):
            newSeq1.append([0, 0])

        nodeInSeq2 = [seq1[i][0] for i in range(idx1I, idx1J)]
        newSeq2 = [seq1[i] for i in range(idx1I, idx1J)]
        for i in range(idx2J, len(seq2)):
            if (seq2[i][0] not in nodeInSeq2):
                newSeq2.append(seq2[i])
                nodeInSeq2.append(seq2[i])
        for i in range(idx2I):
            if (seq2[i][0] not in nodeInSeq2):
                newSeq2.append(seq2[i])
                nodeInSeq2.append(seq2[i])
        if ([0, 0] not in newSeq2):
            newSeq2.append([0, 0])

        newChromo1 = chromosomeGCEOP(startLoc, endLoc, nodes, newSeq1, maxLength)
        newChromo2 = chromosomeGCEOP(startLoc, endLoc, nodes, newSeq2, maxLength)
        return newChromo1, newChromo2

    # Initialize ==============================================================
    dashboard = {
        'bestScore': 0,
        'bestChromo': None
    }
    startTime = datetime.datetime.now()
    convergence = []

    # Initialize population by randomization ==================================
    popObj = []
    for k in range(popSize):
        seq = [[i, random.randint(0, len(radiusList if radiusList != None else nodes[i][radiusListFieldName]) - 1)] for i in nodes]
        seq.append([0, 0])
        random.shuffle(seq) # 没事，会rehead
        popObj.append(chromosomeGCEOP(startLoc, endLoc, nodes, seq, maxLength))
        writeLog("New Pop - Score: " + str(popObj[-1].score) + "\tDist: " + str(popObj[-1].dist))

    for chromo in popObj:
        if (chromo.score > dashboard['bestScore'] and chromo.dist <= maxLength):
            dashboard['bestScore'] = chromo.score
            dashboard['bestDist'] = chromo.dist
            dashboard['bestSeq'] = [[i.key, i.value] for i in chromo.seq.traverse()]
            dashboard['bestChromo'] = chromo

    contFlag = True
    iterTotal = 0
    iterNoImp = 0

    adaptMutation = {
        'numIntraSwap': (int)(neighRatio['intraSwap'] * popSize),
        'numInterSwap': (int)(neighRatio['interSwap'] * popSize),
        'numExchange': (int)(neighRatio['exchange'] * popSize),
        'numRotate': (int)(neighRatio['rotate'] * popSize),
        'numRndDestory': (int)(neighRatio['rndDestroy'] * popSize),
    }
    while (contFlag):

        # Crossover and create offspring
        while (len(popObj) <= (int)((1 + neighRatio['crossover']) * popSize)):
            # Randomly select two genes, the better gene has better chance to have offspring            
            rnd1 = None
            rnd2 = None
            while (rnd1 == None or rnd2 == None or rnd1 == rnd2):
                coeff = []
                for i in range(len(popObj)):
                    coeff.append(popObj[i].score)
                rnd1 = rndPick(coeff)
                rnd2 = rndPick(coeff)
            # Randomly select a window from the first chromo and the second chromo
            [idx1I, idx1J] = random.sample([i for i in range(popObj[rnd1].seq.count)], 2)
            [idx2I, idx2J] = random.sample([i for i in range(popObj[rnd2].seq.count)], 2)
            newSeq1, newSeq2 = crossover(popObj[rnd1], popObj[rnd2], idx1I, idx1J, idx2I, idx2J)
            popObj.append(newSeq1)
            popObj.append(newSeq2)
            writeLog("Create offspring - Score: " + str(newSeq1.score) + "\tDist: " + str(newSeq1.dist))
            writeLog("Create offspring - Score: " + str(newSeq2.score) + "\tDist: " + str(newSeq2.dist))

        # intraSwap
        if ('intraSwap' in neighRatio):
            for k in range(adaptMutation['numIntraSwap']):
                rnd = random.randint(0, len(popObj) - 1)
                scoreBefore = popObj[rnd].score
                popObj[rnd] = intraSwap(popObj[rnd])
                scoreAfter = popObj[rnd].score
                writeLog("IntraSwap - Score: " + str(scoreBefore) + " => " + str(popObj[rnd].score) + "\tDist: " + str(popObj[rnd].dist))

        # interSwap
        if ('interSwap' in neighRatio):
            for k in range(adaptMutation['numInterSwap']):
                rnd = random.randint(0, len(popObj) - 1)            
                idx = random.randint(0, popObj[rnd].seq.count - 1)
                scoreBefore = popObj[rnd].score
                popObj[rnd] = interSwap(popObj[rnd], idx)
                scoreAfter = popObj[rnd].score
                writeLog("InterSwap - Score: " + str(scoreBefore) + " => " + str(popObj[rnd].score) + "\tDist: " + str(popObj[rnd].dist))

        # exchange
        if ('exchange' in neighRatio):
            for k in range(adaptMutation['numExchange']):
                rnd = random.randint(0, len(popObj) - 1)
                if (popObj[rnd].seq.count > 4):
                    [idxI, idxJ] = random.sample([i for i in range(popObj[rnd].seq.count)], 2)
                    while (abs(idxJ - idxI) <= 2
                        or idxI == 0 and idxJ == popObj[rnd].seq.count - 1
                        or idxI == popObj[rnd].seq.count - 1 and idxJ == 0):
                        [idxI, idxJ] = random.sample([i for i in range(popObj[rnd].seq.count)], 2)
                    scoreBefore = popObj[rnd].score
                    popObj[rnd] = exchange(popObj[rnd], idxI, idxJ)
                    scoreAfter = popObj[rnd].score
                    writeLog("Exchange - Score: " + str(scoreBefore) + " => " + str(popObj[rnd].score) + "\tDist: " + str(popObj[rnd].dist))

        # rotate
        if ('rotate' in neighRatio):
            for k in range(adaptMutation['numRotate']):
                rnd = random.randint(0, len(popObj) - 1)
                if (popObj[rnd].seq.count > 4):
                    [idxI, idxJ] = random.sample([i for i in range(popObj[rnd].seq.count)], 2)
                    while (abs(idxJ - idxI) <= 2
                        or idxI == 0 and idxJ == popObj[rnd].seq.count - 1
                        or idxI == popObj[rnd].seq.count - 1 and idxJ == 0):
                        [idxI, idxJ] = random.sample([i for i in range(popObj[rnd].seq.count)], 2)
                    scoreBefore = popObj[rnd].score
                    popObj[rnd] = rotate(popObj[rnd], idxI, idxJ)
                    scoreAfter = popObj[rnd].score
                    writeLog("Rotate - Score: " + str(scoreBefore) + " => " + str(popObj[rnd].score) + "\tDist: " + str(popObj[rnd].dist))

        # random destroy and recreate
        if ('rndDestroy' in neighRatio):
            for k in range(adaptMutation['numRndDestory']):
                rnd = random.randint(0, len(popObj) - 1)
                scoreBefore = popObj[rnd].score
                popObj[rnd] = rndDestroy(popObj[rnd])
                scoreAfter = popObj[rnd].score
                writeLog("Random R&R - Score: " + str(scoreBefore) + " => " + str(popObj[rnd].score) + "\tDist: " + str(popObj[rnd].dist))

        # Tournament
        while (len(popObj) > popSize):
            # Randomly select two genes
            rnd1 = None
            rnd2 = None
            while (rnd1 == None or rnd2 == None or rnd1 == rnd2):
                rnd1 = random.randint(0, len(popObj) - 1)
                rnd2 = random.randint(0, len(popObj) - 1)
            # kill the loser
            if (popObj[rnd1].score < popObj[rnd2].score):
                writeLog("Remove - Score: " + str(popObj[rnd1].score) + "\tDist: " + str(popObj[rnd1].dist))
                del popObj[rnd1]
            else:
                writeLog("Remove - Score: " + str(popObj[rnd2].score) + "\tDist: " + str(popObj[rnd2].dist))
                del popObj[rnd2]

        # Update dashboard
        newOfvFound = False
        for chromo in popObj:
            if (chromo.score > dashboard['bestScore'] and chromo.dist <= maxLength):
                newOfvFound = True
                dashboard['bestScore'] = chromo.score
                dashboard['bestDist'] = chromo.dist
                dashboard['bestSeq'] = [[i.key, i.value] for i in chromo.seq.traverse()]
                dashboard['bestChromo'] = chromo
        writeLog(hyphenStr())
        writeLog("Iter: " + str(iterTotal) + 
            "\nRuntime [s]: " + str(round((datetime.datetime.now() - startTime).total_seconds(), 2)) + 
            "\nDist: " + str(dashboard['bestDist']) + 
            "\nScore: " + str(dashboard['bestScore']))
        if (newOfvFound):
            iterNoImp = 0
        else:
            iterNoImp += 1
        iterTotal += 1

        convergence.append({
            'score': dashboard['bestScore'],
            'dist': dashboard['bestDist'],
            'seq': dashboard['bestSeq'],
            'path': dashboard['bestChromo'].path,
            'runtime': (datetime.datetime.now() - startTime).total_seconds()
        })

        # Check stopping criteria
        if ('numNoImproveIter' in stop):
            if (iterNoImp > stop['numNoImproveIter']):
                contFlag = False
                break
        if ('numIter' in stop):
            if (iterTotal > stop['numIter']):
                contFlag = False
                break
        if ('runtime' in stop):
            if ((datetime.datetime.now() - startTime).total_seconds() > stop['runtime']):
                contFlag = False
                break

    return {
        'ofv': dashboard['bestScore'],
        'score': dashboard['bestScore'],
        'dist': dashboard['bestDist'],
        'seq': dashboard['bestSeq'],
        'chromo': dashboard['bestChromo'],
        'path': dashboard['bestChromo'].path,
        'runtime': runtime,
        'convergence': convergence,
        'popObj': popObj
    }
