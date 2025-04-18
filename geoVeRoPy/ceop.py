import math
import random
import shapely
from shapely.geometry import mapping

from .ring import *
from .common import *
from .geometry import *
from .obj2Obj import *
from .polyTour import *

def solveCEOP(
    startLoc: pt,
    endLoc: pt,
    nodes: dict, # Index from 1
    radius: float | None = None,
    radiusFieldName: str = 'radius',
    timeLimit: int | None = None,
    maxLength: float = None,
    popSize: int = None,
    neighRatio: dict = {},
    stop: dict = {},
    **kwargs
    ) -> dict | None:

    class chromosomeCEOP:
        def __init__(self, startLoc, endLoc, nodes, seq, maxLength):
            # NOTE: seq以depotID开始和结束
            # NOTE: 每个seq都需要补全为一条合法的ceop路径
            
            # 记录nodes的信息
            self.startLoc = startLoc
            self.endLoc = endLoc
            self.nodes = nodes
            self.maxLength = maxLength

            # 原始输入的seq
            self.seq = Ring()
            for i in seq:
                n = RingNode(i)
                self.seq.append(n)
            self.seq.rehead(0)

            # 转折点列表
            self.turning = []
            self.aggTurning = []
            # 穿越点列表
            self.trespass = []
            # 未访问点及距离，暂存用
            self.dist2NotInclude = {}
            # 补全
            self.seq2Path()

        def getPath(self):
            # 需要先得到一组turn point
            circles = []
            seqTra = [n.key for n in self.seq.traverse()]
            seqTra.append(0)
            for i in range(1, len(seqTra) - 1):
                circles.append({
                    'center': self.nodes[seqTra[i]]['loc'],
                    'radius': radius if radius != None else self.nodes[seqTra[i]][radiusFieldName]
                })
            c2c = circle2CirclePath(
                startPt = self.startLoc,
                endPt = self.endLoc,
                circles = circles,
                algo = 'SOCP')
            degen = seqRemoveDegen(seq = c2c['path'])

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
            for i in self.nodes:
                if (i not in self.turning):
                    res = distPt2Seq(
                        pt = self.nodes[i]['loc'], 
                        seq = self.path,
                        closedFlag = True,
                        detailFlag = True)
                    if (res['dist'] <= radius if radius != None else self.nodes[seqTra[i]][radiusFieldName]):
                        self.trespass.append(i)
                        self.score += self.nodes[i]['score']
                    else:
                        self.dist2NotInclude[i] = res
                else:
                    self.score += self.nodes[i]['score']

        def seq2Path(self):
            # 记录历史查找过的路径，如果出现了重复，就调整为上一次的合法路径
            self.getPath()
            pathCalFlag = True # 少进行一次circle2CirclePath()            

            # 现在开始补齐，多退少补
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

                # print(hyphenStr())
                # print("UUID: ", self.chromoID)
                # print("Turning: ", self.turning)
                # print("Trespass: ", self.trespass)
                # print("Dist: ", self.dist)
                # print("Score: ", self.score)
                # print("\n")

                # 判断距离是否有富裕，判断是否能够添加turning
                if (self.dist <= self.maxLength):
                    candi = []
                    coeff = []

                    # DP用来加速
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

                        worthTryFlag = None

                        # 先计算最保守上界估计， 如果加上来还可以满足，那肯定可以试试
                        deltaLength  = distEuclideanXY(prevLoc, nodes[i]['loc'])
                        deltaLength += distEuclideanXY(nextLoc, nodes[i]['loc'])
                        deltaLength -= distPrevNext
                        if (self.dist + deltaLength <= self.maxLength):
                            worthTryFlag = True

                        # 如果最保守的上界超标了，最保守的下界也超标了，那肯定不必要再去算一轮精确点的
                        if (worthTryFlag == None and deltaLength - 2 * nodes[i]['radius'] >= self.maxLength):
                            worthTryFlag = False

                        # 如果最保守的上界和下届都不能用来判断，那就给个更精确的估计
                        # NOTE: 用circle2CirclePath测试太昂贵了
                        if (worthTryFlag == None):
                            pt1 = ptInDistXY(
                                pt = nodes[i]['loc'],
                                direction = headingXY(nodes[i]['loc'], prevLoc),
                                dist = nodes[i]['radius'])
                            pt2 = ptInDistXY(
                                pt = nodes[i]['loc'],
                                direction = headingXY(nodes[i]['loc'], nextLoc),
                                dist = nodes[i]['radius'])
                            midLoc = ptMid([pt1, pt2])
                            edgeLoc = ptInDistXY(
                                pt = nodes[i]['loc'],
                                direction = headingXY(nodes[i]['loc'], midLoc),
                                dist = nodes[i]['radius'])
                            deltaLength  = distEuclideanXY(prevLoc, edgeLoc)
                            deltaLength += distEuclideanXY(nextLoc, edgeLoc)
                            deltaLength -= distPrevNext
                            # NOTE: 0.98 is a magic number, 用来修正估计值
                            if ((self.dist + deltaLength) * 0.98 <= self.maxLength):
                                worthTryFlag = True
                            else:
                                worthTryFlag = False

                        if (worthTryFlag):
                            opt = (i, self.dist2NotInclude[i]['nearestIdx'])
                            if (opt not in tabuOpt):
                                candi.append(opt)
                                tabuOpt.append(opt)
                                coeff.append(self.nodes[i]['score'] / deltaLength)

                    # 如果找到可以加入的candidate，按照性价比抽样，性价比越高的被选中概率越大
                    if (len(candi) > 0):
                        # 随机抽一个
                        insertCandi = candi[rndPick(coeff)]
                        self.aggTurning.insert(insertCandi[1][1], [insertCandi[0]])
                        self.turning = []
                        for k in range(len(self.aggTurning)):
                            self.turning.extend(self.aggTurning[k])
                        # print("Add to turning: ", insertCandi)
                        canAddFlag = True

                # 距离如果大于maxLength，从现有的turning中移除，按照分值加权随机移除
                else:
                    coeff = []
                    for i in self.turning:
                        if (i != 0):
                            coeff.append(1.0 / nodes[i]['score'])
                        else:
                            coeff.append(0)
                    removeID = self.turning[rndPick(coeff)]
                    self.turning.remove(removeID)
                    # print("Remove from turning: ", removeID)
                    needRemoveFlag = True

                # 更新seq为新的turning point
                self.seq = Ring()
                for i in range(len(self.turning) - 1):
                    n = RingNode(self.turning[i])
                    self.seq.append(n)
                self.seq.rehead(0)

    def swap(chromo, idxI):
        seq = [i.key for i in chromo.seq.traverse()]
        if (idxI < len(seq) - 1):
            seq[idxI], seq[idxI + 1] = seq[idxI + 1], seq[idxI]
        else:
            seq[idxI], seq[0] = seq[0], seq[idxI]
        return chromosomeCEOP(startLoc, endLoc, nodes, seq, maxLength)

    def exchange(chromo, idxI, idxJ):
        seq = [i.key for i in chromo.seq.traverse()]
        seq[idxI], seq[idxJ] = seq[idxJ], seq[idxI]
        return chromosomeCEOP(startLoc, endLoc, nodes, seq, maxLength)

    def rotate(chromo, idxI, idxJ):
        seq = [i.key for i in chromo.seq.traverse()]
        if (idxI > idxJ):
            idxI, idxJ = idxJ, idxI
        newSeq = [seq[i] for i in range(idxI)]
        newSeq.extend([seq[idxJ - i] for i in range(idxJ - idxI + 1)])
        newSeq.extend([seq[i] for i in range(idxJ + 1, len(seq))])
        return chromosomeCEOP(startLoc, endLoc, nodes, newSeq, maxLength)
    
    def rndDestroy(chromo):
        seq = [i.key for i in chromo.seq.traverse()]
        numRemove = int(len(seq) * random.random() * 0.3)
        newSeq = [i for i in seq]
        for i in range(numRemove):
            newSeq.remove(newSeq[random.randint(0, len(newSeq) - 1)])
        if (0 not in newSeq):
            newSeq.append(0)
        return chromosomeCEOP(startLoc, endLoc, nodes, newSeq, maxLength)

    def crossover(chromo1, chromo2, idx1I, idx1J, idx2I, idx2J):
        # 原始序列
        seq1 = [i.key for i in chromo1.seq.traverse()]
        seq2 = [i.key for i in chromo2.seq.traverse()]

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
        newSeq1 = [seq2[i] for i in range(idx2I, idx2J)]
        for i in range(idx1J, len(seq1)):
            if (seq1[i] not in newSeq1):
                newSeq1.append(seq1[i])
        for i in range(idx1I):
            if (seq1[i] not in newSeq1):
                newSeq1.append(seq1[i])
        if (0 not in newSeq1):
            newSeq1.append(0)

        newSeq2 = [seq1[i] for i in range(idx1I, idx1J)]
        for i in range(idx2J, len(seq2)):
            if (seq2[i] not in newSeq2):
                newSeq2.append(seq2[i])
        for i in range(idx2I):
            if (seq2[i] not in newSeq2):
                newSeq2.append(seq2[i])
        if (0 not in newSeq2):
            newSeq2.append(0)

        newChromo1 = chromosomeCEOP(startLoc, endLoc, nodes, newSeq1, maxLength)
        newChromo2 = chromosomeCEOP(startLoc, endLoc, nodes, newSeq2, maxLength)
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
        seq = [i for i in nodes]
        seq.append(0)
        random.shuffle(seq)
        popObj.append(chromosomeCEOP(startLoc, endLoc, nodes, seq, maxLength))
        writeLog("New Pop - Score: " + str(popObj[-1].score) + "\tDist: " + str(popObj[-1].dist))

    for chromo in popObj:
        if (chromo.score > dashboard['bestScore'] and chromo.dist <= maxLength):
            dashboard['bestScore'] = chromo.score
            dashboard['bestDist'] = chromo.dist
            dashboard['bestSeq'] = [i.key for i in chromo.seq.traverse()]
            dashboard['bestChromo'] = chromo

    contFlag = True
    iterTotal = 0
    iterNoImp = 0
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

        # Mutation
        # swap
        if ('swap' in neighRatio):
            numSwap = (int)(neighRatio['swap'] * popSize)
            for k in range(numSwap):
                rnd = random.randint(0, len(popObj) - 1)            
                idx = random.randint(0, popObj[rnd].seq.count - 1)
                popObj[rnd] = swap(popObj[rnd], idx)
                writeLog("Swap - Score: " + str(popObj[rnd].score) + "\tDist: " + str(popObj[rnd].dist))
        
        # exchange
        if ('exchange' in neighRatio):
            numExchange = (int)(neighRatio['exchange'] * popSize)
            for k in range(numExchange):
                rnd = random.randint(0, len(popObj) - 1)
                if (popObj[rnd].seq.count > 4):
                    [idxI, idxJ] = random.sample([i for i in range(popObj[rnd].seq.count)], 2)
                    while (abs(idxJ - idxI) <= 2
                        or idxI == 0 and idxJ == popObj[rnd].seq.count - 1
                        or idxI == popObj[rnd].seq.count - 1 and idxJ == 0):
                        [idxI, idxJ] = random.sample([i for i in range(popObj[rnd].seq.count)], 2)
                    popObj[rnd] = exchange(popObj[rnd], idxI, idxJ)
                    writeLog("Exchange - Score: " + str(popObj[rnd].score) + "\tDist: " + str(popObj[rnd].dist))

        # rotate
        if ('rotate' in neighRatio):
            numRotate = (int)(neighRatio['rotate'] * popSize)
            for k in range(numRotate):
                rnd = random.randint(0, len(popObj) - 1)
                if (popObj[rnd].seq.count > 4):
                    [idxI, idxJ] = random.sample([i for i in range(popObj[rnd].seq.count)], 2)
                    while (abs(idxJ - idxI) <= 2
                        or idxI == 0 and idxJ == popObj[rnd].seq.count - 1
                        or idxI == popObj[rnd].seq.count - 1 and idxJ == 0):
                        [idxI, idxJ] = random.sample([i for i in range(popObj[rnd].seq.count)], 2)
                    popObj[rnd] = rotate(popObj[rnd], idxI, idxJ)
                    writeLog("Rotate - Score: " + str(popObj[rnd].score) + "\tDist: " + str(popObj[rnd].dist))

        # random destroy and recreate
        if ('rndDestroy' in neighRatio):
            numRndDestory = (int)(neighRatio['rndDestroy'] * popSize)
            for k in range(numRndDestory):
                rnd = random.randint(0, len(popObj) - 1)
                popObj[rnd] = rndDestroy(popObj[rnd])
                writeLog("Random R&R - Score: " + str(popObj[rnd].score) + "\tDist: " + str(popObj[rnd].dist))

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
                dashboard['bestSeq'] = [i.key for i in chromo.seq.traverse()]
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
                'path': dashboard['bestChromo'].path
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
