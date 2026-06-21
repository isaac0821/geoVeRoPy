import random
import datetime
import numpy as np

from .common import *

class SolnNode:
    # 对于给定一个顺序编码就可以直接求解的结构
    def __init__(self, key, rep, funcSolve, **kwargs):
        self.key = key
        self.rep = rep
        self.__dict__.update(kwargs)

        self.funcSolve = funcSolve
        self.ofv = None

        self.solvedFlag = False
        self.feasibleFlag = None
        self.soln = None
        return

    def solve(self):
        self.funcSolve(self)
        self.solvedFlag = True
        return

class RawSolnNode(SolnNode):
    # 对于给定一个顺序编码还需要补全的结构
    def __init__(self, key, rawRep, funcCheck, funcFix, **kwargs):
        self.key = key
        self.rep = rawRep
        self.rawRep = rawRep
        self.curRep = rawRep
        self.__dict__.update(kwargs)

        self.funcCheck = funcCheck # Function to check if feasible
        self.funcFix = funcFix # Function to fix (by one step) towards feasibility
        self.ofv = None

        self.solvedFlag = False
        self.feasibleFlag = None
        self.soln = None
        return

    def solve(self):
        if (self.feasibleFlag == None):
            self.check()
        while (self.feasibleFlag == False):
            self.fix()
            self.check()
        self.solvedFlag = True
        return

    def check(self):
        self.feasibleFlag = self.funcCheck(self)
        return

    def fix(self):
        self.funcFix(self)
        return

class ILS:
    def __init__(self, initNode: SolnNode, funcNeiOps: list, **kwargs):
        # 初始化
        self.initNode = initNode
        self.initNode.solve()
        self.funcNeiOps = funcNeiOps

        # 内置一个动态表，用于减少计算
        # self.DP = {}
        # self.DP[self.initNode.key] = self.initNode

        # 设置默认的参数，并把多余的参数存起来
        defaultParam = {
            'initTemp': 100.0,
            'coolRate': 0.95,
            'stopCriteria': {
                'numIter': 100
            },
            'seed': None,
            'objSense': 'Min',
            'objFieldName': 'ofv',
            'printFieldNames': []
        }
        for key, val in defaultParam.items():
            setattr(self, key, val)
        self.__dict__.update(kwargs)
        if (self.objSense not in ['Min', 'Max']):
            raise UnsupportedInputError("ERROR: `objSense` should be 'Min' or 'Max'.")
        if (type(self.printFieldNames) is str):
            self.printFieldNames = [self.printFieldNames]
        if (self.seed is not None):
            random.seed(self.seed)

        self.roulette = {}
        for func in funcNeiOps:
            self.roulette[func] = 1

        # 获得初始解
        self.currNode = self.initNode
        self.currOFV = getattr(self.currNode, self.objFieldName)
        self.bestNode = self.currNode
        self.bestOFV = self.currOFV

        self.runtime = None
        self.convergence = []

        printLog("ILS initialization completed")
        printLog(f"Initial objective value: {self.currOFV:.4f}")
        for fieldName in self.printFieldNames:
            printLog(f"Initial {fieldName}: {getattr(self.currNode, fieldName, None)}")
        return

    def solve(self):
        startTime = datetime.datetime.now()
        convergence = []

        iteration = 0
        noImproveIter = 0
        temp = self.initTemp

        while (True):
            # 随机选择一个算子
            opFunc = rndPickFromDict(self.roulette)
            newNode = opFunc(self.currNode)
            newNode.solve()
            newObj = getattr(newNode, self.objFieldName)
            printLog(f"Operator selected: {opFunc.__name__}")

            accept = False
            if ((self.objSense == 'Min' and newObj < self.currOFV) or (self.objSense == 'Max' and newObj > self.currOFV)):
                accept = True
                self.roulette[opFunc] += 2
            else:
                if (self.objSense == 'Min'):
                    delta = newObj - self.currOFV
                else:
                    delta = self.currOFV - newObj
                prob = np.exp(-delta / temp) if (temp > 0) else 0.0
                if (random.random() < prob):
                    accept = True
                    self.roulette[opFunc] += 1

            if (accept):
                self.currNode = newNode
                self.currOFV = newObj

            if ((self.objSense == 'Min' and newObj < self.bestOFV - 1e-8) or (self.objSense == 'Max' and newObj > self.bestOFV + 1e-8)):
                self.bestNode = newNode
                self.bestOFV = newObj
                noImproveIter = 0
                printLog(f"Iter {iteration}: New best solution found, obj = {self.bestOFV:.6f}")
            else:
                noImproveIter += 1

            temp *= self.coolRate

            runtime = (datetime.datetime.now() - startTime).total_seconds()
            convergenceItem = {
                'iter': iteration,
                'obj': self.bestOFV,
                'runtime': runtime
            }
            for fieldName in self.printFieldNames:
                convergenceItem[fieldName] = getattr(self.bestNode, fieldName, None)
            convergence.append(convergenceItem)

            # printLog("\n")
            printLog(hyphenStr())
            printLog(f"Iter {iteration:5d}")
            printLog(f"Runtime [s]: {runtime:.2f}")
            printLog(f"bestOFV: {self.bestOFV:.6f}")
            printLog(f"currOFV: {self.currOFV:.6f}")
            for fieldName in self.printFieldNames:
                if (len(fieldName) == 0):
                    continue
                fieldLabel = fieldName[0].upper() + fieldName[1:]
                printLog(f"best{fieldLabel}: {getattr(self.bestNode, fieldName, None)}")
                printLog(f"curr{fieldLabel}: {getattr(self.currNode, fieldName, None)}")
            printLog(f"Temperature: {temp:.3f}")

            if (('numIter' in self.stopCriteria) and (iteration >= self.stopCriteria['numIter'])):
                printLog(f"Reached max iterations {self.stopCriteria['numIter']}, stopping")
                break
            if (('numNoImprove' in self.stopCriteria) and (noImproveIter >= self.stopCriteria['numNoImprove'])):
                printLog(f"No improvement for {noImproveIter} iterations, stopping")
                break
            if (('runtime' in self.stopCriteria) and (runtime >= self.stopCriteria['runtime'])):
                printLog(f"Reached runtime limit {self.stopCriteria['runtime']} seconds, stopping")
                break

            iteration += 1

        totalRuntime = (datetime.datetime.now() - startTime).total_seconds()
        printLog(f"\nILS finished. Best objective: {self.bestOFV:.6f}, total time: {totalRuntime:.2f}s")

        self.runtime = totalRuntime
        self.convergence = convergence

        return
