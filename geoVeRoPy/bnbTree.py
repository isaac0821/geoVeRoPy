import math
import random
import heapq

from .tree import *
from .common import *

# # Branch and bound tree objects
class BnBTreeNode(TreeNode):
    # NOTE: rep - 解的输入格式
    # NOTE: 如果有gurobi的对象，传入**kwargs
    def __init__(self, key, rep, funcSolve, funcBranch, funcQuickSolve=None, funcUBEstimate=None, bnbUB=float('inf'), **kwargs):
        # BnB树初始化的时候只有key和表达式rep是已知的
        self.key = key
        self.rep = rep
        self.__dict__.update(kwargs)

        # paraent属性在加入BnB树时补充，当前初始化为空
        self.parent = BnBTreeNilNode()
        # children属性在branch时补充，当前初始化为空数组
        self.treeNodes = [BnBTreeNilNode()] # 存的是list of BnBTreeNode

        # 以下属性在solve()后补充
        self.ofv = None
        self.funcSolve = funcSolve
        self.funcUBEstimate = funcUBEstimate
        self.relaxFlag = None
        self.feasibleFlag = None
        self.solvedFlag = False
        self.soln = None

        # 以下属性在自身或者其他node定界时补充
        self.bnbUB = bnbUB
        self.funcBranch = funcBranch
        self.prunFlag = False
        self.upperBound = float('inf') # 当前node的子树的上界
        self.lowerBound = -float('inf') # 当前node的子树的下界
        return

    def addSelfToNode(self, p):
        if (p.treeNodes[0].isNil):
            p.treeNodes = []
        p.treeNodes.append(self)
        self.parent = p
        self.upperBound = p.upperBound
        self.lowerBound = p.lowerBound

    # 快速求解函数
    # NOTE: 快速估算该节点的目标函数值
    def quickSolve(self):
        self.funcQuickSolve(self)
        self.quickSolvedFlag = True
        return

    # 求解函数
    # NOTE: 真值
    def solve(self):
        self.funcSolve(self)
        self.solvedFlag = True
        if (self.feasibleFlag == False):
            self.prunFlag = True
        return

    def ubEstimate(self):
        self.funcUBEstimate(self)
        return

    # 检查是否因为bounding把自己prun掉
    def bounding(self):
        if (self.prunFlag == False):
            if (self.relaxFlag == True):
                self.lowerBound = self.ofv
                if (self.lowerBound > self.bnbUB):
                    self.prunFlag = True
            else:
                self.upperBound = self.ofv
                self.lowerBound = self.ofv
                if (self.lowerBound > self.bnbUB):
                    self.prunFlag = True
        
    @property
    def isNil(self):
        return False

class BnBTreeNilNode(BnBTreeNode):
    def __init__(self):
        return

    @property
    def isNil(self):
        return True

class BnBTree(Tree):
    # FIXME: 现在固定写的是最小树

    # BnB树有以下操作：
    # 1. 分支 branch: 指定一个node，根据一定的规则，生成一组子node，返回值是一组子node
    # 2. 试算 quick-solve: 指定一组node，用快速试算函数估计其目标函数值，更新一系列的
    # 3. 定界 bounding/solve: （以最小化为例，如果不算最小化，则目标函数取反）指定一个node，计算目标函数值，
    #                   判断结果是不是relax解，如果是relax解，则更新lowerBound
    #                   如果结算结果是incumbent，则更新upperBound
    # 4. 剪枝 pruning: 当一个新的lb/ub出现，搜索整个树，进行剪枝操作
    # 构造函数，初始化时需要传入一个根节点的问题
    def __init__(self, root, **kwargs):
        self.nil = BnBTreeNilNode()
        self.root = self.nil
        self.__dict__.update(kwargs)

        self.insert(root)

        # BB树的上下界，实际上就是root的上下界
        self.upperBound = float('inf')
        self.lowerBound = -float('inf')

        self.convergence = []
        self.best = None

        self.tabu = {}

    # 分支定界法主函数
    def bnb(self, timeLimit=None):
        # 算法框架（以最小化为例）
        continueFlag = True

        startTime = datetime.datetime.now()

        numIter = 0
        while(continueFlag):
            continueFlag = False
            numIter += 1

            printLog(hyphenStr(s="Iter: " + str(numIter)))

            # Step 1: 选择一个unsolved node，如果找不到unsolved，结束
            curNode = self.choose()
            if (abs(self.lowerBound - self.upperBound) <= 0.01):
                printLog("Iteration ends by gap.")
                break
            if (curNode == None):
                printLog("Iteration ends by enumeration.")
                break

            if (timeLimit != None and (datetime.datetime.now() - startTime).total_seconds() > timeLimit):
                printLog("Reach time limit!")
                break

            printLog("Select: ", curNode.rep)
            if (curNode != None):
                continueFlag = True

            # Step 2: 求解
            curNode.solve()
            printLog("Turning: ", curNode.turning)
            printLog("Trespass: ", curNode.trespass)
            printLog("Missing: ", curNode.missing)

            # Step 2.1: 如果没有上界，启发式的给一个上界
            if (self.upperBound == float('inf') and curNode.funcUBEstimate != None):
                curNode.ubEstimate()
                self.upperBound = curNode.upperBound
                printLog("Est UB: ", curNode.upperBound)

                
            # Step 3: 定界
            curNode.bnbUB = self.upperBound            
            curNode.bounding()
            if (curNode.prunFlag):
                printLog("Current node pruned by upper bound.")  
            printLog("OFV: ", curNode.ofv)
            printLog("Node LB: ", curNode.lowerBound)
            printLog("Node UB: ", curNode.upperBound)

            # Step 4: 更新上下界
            self.updateBounds()
            if (curNode.prunFlag == False and curNode.upperBound < self.upperBound):
                self.upperBound = curNode.upperBound
                self.best = curNode
            printLog("Global LB: ", self.lowerBound)
            printLog("Global UB: ", self.upperBound)
            self.convergence.append((self.upperBound, self.lowerBound, (datetime.datetime.now() - startTime).total_seconds()))

            # Step 5: 剪枝
            self.pruning(self.upperBound)

            # Step 6: 如果curNode没有被prun，分支
            if (not curNode.prunFlag):
                self.branch(curNode)

        self.ofv = self.best.ofv
        self.soln = self.best.soln
        self.runtime = (datetime.datetime.now() - startTime).total_seconds()
        return

    # 返回一个node，该node具有最低的可能的lower bound，并对该node求解
    def choose(self):
        # ret = chooseByNode(self.root)
        # FIXME: Test
        children = self.traverseChildren()
        children = [i for i in children if i.solvedFlag == False]

        lowestLB = float('inf')
        lowestIdx = None

        for i in range(len(children)):
            if (children[i].lowerBound < lowestLB):
                lowestLB = children[i].lowerBound
                lowestIdx = i

        printLog("Candidate #: ", len(children))
        if (len(children) == 0):
            return None

        return children[lowestIdx]

    # 从n的子树里返回node中lb最低的未求解节点
    def chooseByNode(self, n):
        ret = None
        # 如果n已经被prun了，不会返回东西
        if (n.prunFlag == True):
            return None
        else:
            # 如果n没有被prun，看有没有被solved
            if (n.solvedFlag == True):
                # 遍历子节点，如果有，逐个猜下界
                for child in n.treeNodes:
                    pass

    def updateBounds(self):
        # traverse整棵树，返回树的最低的下界和上界
        self.updateBoundsByNode(self.root)
        self.lowerBound = self.root.lowerBound
        return

    def updateBoundsByNode(self, n):
        # 如果该node为Nil，或者该node已经被prun，或者还没算过，不更新lb
        if (n.isNil or n.prunFlag):
            return
        # 否则递归
        else:
            # Case 1: 如果自己是unsolved，则继承父节点的bound
            if (n.solvedFlag == False and not n.parent.isNil):
                n.lowerBound = n.parent.lowerBound
            # Case 2: 如果自己是solved，则看自己有没有子节点
            else:
                # Case 2.1: 如果自己没有子节点
                if (len(n.treeNodes) == 0 or (len(n.treeNodes) == 1 and n.treeNodes[0].isNil)):
                    n.lowerBound = n.ofv
                # Case 2.2: 如果自己有子节点
                else:
                    # Case 2.2.1: 如果所有的子节点都是solved，则更新自己，如果有一个以上是unsolved，则不更新
                    for child in n.treeNodes:
                        self.updateBoundsByNode(child)
                    allSolvedFlag = True
                    newLB = float('inf')
                    for child in n.treeNodes:
                        if (child.solvedFlag == False):
                            allSolvedFlag = False
                            break
                        if (child.prunFlag == False):
                            if (child.lowerBound < newLB):
                                newLB = child.lowerBound                    
                    if (allSolvedFlag):                        
                        n.lowerBound = newLB
                    return

    # 剪枝
    # NOTE: 给定一个父节点p，和一个子节点n，把n放入
    def pruning(self, ub):
        self.pruningByNode(self.root, ub)
        return
        
    def pruningByNode(self, n, ub):
        # 只有该node没有被prun才有必要
        if (n.prunFlag == False):
            # 如果n的lb比ub还要高，说明n没必要算下去了，prun掉吧
            if (n.lowerBound > ub):
                n.prunFlag = True
                printLog("Prune: ", n.rep)
            # 否则的话递归地看n的每个子节点
            else:
                for child in n.treeNodes:
                    if (not child.isNil):
                        self.pruningByNode(child, ub)
        return

    def branch(self, n):
        children = n.funcBranch(n)
        for child in children:
            # if (self.query(child.key)):
            #     printLog("Exists! - ", child.key)
            # else:
            #     child.addSelfToNode(n)
            if (tuple(child.key) not in self.tabu):
                child.addSelfToNode(n)
                self.tabu[tuple(child.key)] = True
            else:
                printLog("Prune by repetition - ", child.key)
        return

    def traverseChildren(self):
        if (self.root.isNil):
            return []
        else:
            if (self.root.isChildren):
                return [self.root]
        children = self._traverseChildren(self.root)
        return children

    def _traverseChildren(self, n):
        tra = []
        if (n.prunFlag == False):
            for treeNode in n.treeNodes:
                if (treeNode.isChildren):
                    tra.append(treeNode)
            for treeNode in n.treeNodes:
                if (not treeNode.isChildren):
                    tra.extend(self._traverseChildren(treeNode))
        return tra
