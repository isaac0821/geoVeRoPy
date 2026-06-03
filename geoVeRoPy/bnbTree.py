import math

from .tree import *
from .common import *

# # Branch and bound tree objects
class BnBTreeNode(TreeNode):
    # NOTE: rep - 解的输入格式
    # NOTE: 如果有gurobi的对象，传入**kwargs
    # @tellRuntime('bnbTree.py.__init__', indentLevel = 1)
    def __init__(self, key, rep, funcSolve, funcBranch, funcFeasible=None, funcUBEstimate=None, bnbUB=float('inf'), **kwargs):
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
        self.funcSolve = funcSolve # 给定一个node，对node进行求解的函数
        self.funcFeasible = funcFeasible # 给定一个node，确定该node是不是可行解的函数
        self.funcUBEstimate = funcUBEstimate # 给定一个node，快速得到上界的函数，实际上就是启发式
        self.relaxFlag = None # 该节点是否为松弛解
        self.feasibleFlag = None # 该节点是否为可行解
        self.solvedFlag = False # 给节点是否已经求解
        self.soln = None # 该节点的解

        # 以下属性在自身或者其他node定界时补充
        self.bnbUB = bnbUB
        self.funcBranch = funcBranch
        self.prunFlag = False
        self.upperBound = float('inf') # 当前node的子树的上界
        self.lowerBound = -float('inf') # 当前node的子树的下界
        return

    # @tellRuntime('bnbTree.py.addSelfToNode', indentLevel = 1)
    def addSelfToNode(self, p):
        if (p.treeNodes[0].isNil):
            p.treeNodes = []
        p.treeNodes.append(self)
        self.parent = p
        self.upperBound = p.upperBound
        self.lowerBound = p.lowerBound

    # 判断是不是feasib
    # @tellRuntime('bnbTree.py.checkFeasible', indentLevel = 1)
    def checkFeasible(self):
        if (self.funcFeasible != None):
            self.feasibleFlag = self.checkFeasible(self)
        return

    # 求解函数
    # NOTE: 真值
    # @tellRuntime('bnbTree.py.solve', indentLevel = 1)
    def solve(self):
        self.funcSolve(self)
        self.solvedFlag = True
        if (self.feasibleFlag == False):
            self.prunFlag = True
        return

    # @tellRuntime('bnbTree.py.ubEstimate', indentLevel = 1)
    def ubEstimate(self):
        self.funcUBEstimate(self)
        return

    # 检查是否因为bounding把自己prun掉
    # @tellRuntime('bnbTree.py.bounding', indentLevel = 1)
    def bounding(self):
        if self.prunFlag:
            return

        if (self.feasibleFlag == False):
            self.prunFlag = True
            return

        if (self.relaxFlag == True):
            # 松弛解
            self.lowerBound = self.ofv
            if (self.lowerBound > self.bnbUB):
                self.prunFlag = True

        else:
            # 非松弛解
            self.upperBound = self.ofv
            self.lowerBound = self.ofv
            if (self.lowerBound > self.bnbUB):
                self.prunFlag = True
        return
        
    @property
    # @tellRuntime('bnbTree.py.isNil', indentLevel = 1)
    def isNil(self):
        return False

class BnBTreeNilNode(BnBTreeNode):
    # @tellRuntime('bnbTree.py.__init__', indentLevel = 1)
    def __init__(self):
        return

    @property
    # @tellRuntime('bnbTree.py.isNil', indentLevel = 1)
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
    # @tellRuntime('bnbTree.py.__init__', indentLevel = 1)
    def __init__(self, root, funcChoose, timeLimit = None, gapTol = None, **kwargs):
        self.nil = BnBTreeNilNode()
        self.root = self.nil
        self.__dict__.update(kwargs)

        self.timeLimit = timeLimit
        self.gapTol = gapTol

        self.funcChoose = funcChoose

        self.insert(root)

        # BB树的上下界，实际上就是root的上下界
        self.upperBound = float('inf')
        self.lowerBound = -float('inf')
        self.convergence = []
        self.best = None
        self.tabu = {}

        return

    # 分支定界法主函数
    # @tellRuntime('bnbTree.py.bnb', indentLevel = 1)
    def bnb(self):
        # 算法框架（以最小化为例）
        startTime = datetime.datetime.now()

        numIter = 0
        while(True):
            numIter += 1

            printLog(hyphenStr(s="Iter: " + str(numIter)))

            # Step 1: 选择一个unsolved node，如果找不到unsolved，结束
            curNode = self.choose()
            if (self.gapTol != None and abs(self.upperBound) > ERRTOL['vertical'] and not math.isinf(self.upperBound) and abs(self.upperBound - self.lowerBound) / abs(self.upperBound) <= self.gapTol):
                printLog(f"Iteration ends by gap: {abs(self.upperBound - self.lowerBound) * 100 / abs(self.upperBound)}%")
                break
            if (curNode == None):
                if (not math.isinf(self.upperBound)):
                    self.lowerBound = self.upperBound
                printLog("Iteration ends by enumeration.")
                break
            if (self.timeLimit != None and (datetime.datetime.now() - startTime).total_seconds() > self.timeLimit):
                printLog(f"Reach time limit: {(datetime.datetime.now() - startTime).total_seconds()} seconds")
                break

            printLog("Select: ", curNode.rep)

            # Step 2: 求解
            curNode.bnbUB = self.upperBound
            curNode.solve()

            # Step 2.1: 如果没有上界，启发式的给一个上界，注意，必须保证该上界至少大于一个incumbent
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

        if (self.best == None):
            self.ofv = None
            self.soln = None
            self.runtime = (datetime.datetime.now() - startTime).total_seconds()
            return

        self.ofv = self.best.ofv
        self.soln = self.best.soln
        self.runtime = (datetime.datetime.now() - startTime).total_seconds()
        return

    # 返回一个node，该node具有最低的可能的lower bound，并对该node求解
    # @tellRuntime('bnbTree.py.choose', indentLevel = 1)
    def choose(self):
        # ret = chooseByNode(self.root)
        # FIXME: Test
        children = self.traverseChildren()
        children = [i for i in children if i.solvedFlag == False]

        printLog("Candidate #: ", len(children))
        if (len(children) == 0):
            return None
        else:
            for child in children:
                child.bnbUB = self.upperBound
            return self.funcChoose(children)

    # @tellRuntime('bnbTree.py.updateBounds', indentLevel = 1)
    def updateBounds(self):
        # traverse整棵树，返回树的最低的下界和上界
        self.updateBoundsByNode(self.root)
        self.lowerBound = self.root.lowerBound
        return

    # @tellRuntime('bnbTree.py.updateBoundsByNode', indentLevel = 1)
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
    # @tellRuntime('bnbTree.py.pruning', indentLevel = 1)
    def pruning(self, ub):
        self.pruningByNode(self.root, ub)
        return
        
    # @tellRuntime('bnbTree.py.pruningByNode', indentLevel = 1)
    def pruningByNode(self, n, ub):
        # 只有该node没有被prun才有必要
        if (n.prunFlag == False):
            # 如果n的lb比ub还要高，说明n没必要算下去了，prune掉吧
            if (n.lowerBound > ub):
                n.prunFlag = True
                printLog("Prune: ", n.rep)
            # 否则的话递归地看n的每个子节点
            else:
                for child in n.treeNodes:
                    if (not child.isNil):
                        self.pruningByNode(child, ub)
        return

    # @tellRuntime('bnbTree.py.branch', indentLevel = 1)
    def branch(self, n):
        children = n.funcBranch(n)
        for child in children:
            if (tuple(child.key) not in self.tabu):
                child.addSelfToNode(n)
                self.tabu[tuple(child.key)] = True
            else:
                printLog("Prune by repetition - ", child.key)
        return

    # @tellRuntime('bnbTree.py.traverseChildren', indentLevel = 1)
    def traverseChildren(self):
        if (self.root.isNil):
            return []
        else:
            if (self.root.isChildren):
                return [self.root]
        children = self._traverseChildren(self.root)
        return children

    # @tellRuntime('bnbTree.py._traverseChildren', indentLevel = 1)
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
