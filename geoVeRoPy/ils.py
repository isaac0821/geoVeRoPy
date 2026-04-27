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

class RawSolnNode:
    # 对于给定一个顺序编码还需要补全的结构
    def __init__(self, key, rawRep, funcCheck, funcFix, **kwargs):
        self.key = key
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

    def check(self):
        self.feasibleFlag = self.funcCheck(self)
        return

    def fix(self):
        if (self.feasibleFlag == None):
            self.check()
        while (self.feasibleFlag == False):
            self.funcFix(self)
            self.check()
        self.solvedFlag = True
        return

class ILS:
    def __init__(self, initRawSoln: RawSolnNode, funcCheck, funcFix, funcfuncNeiOps, **kwargs):
        # 初始化
        self.initNode = initRawSoln
        self.initNode.fix()
        self.funcNeiOps = funcNeiOps

        # 内置一个动态表，用于减少计算
        self.DP = {}
        self.DP[self.initNode.key] = self.initNode

        defaultParam = {
            'initTemp': 100.0,
            'coolRate': 0.95,
            'stopCriteria': {
                'numIter': 100
            },
            'seed': None
        }
        for key, val in defaultParam.items():
            setattr(self, key, val)
        self.__dict__.update(kwargs)

        if (self.seed is not None):
            random.seed(self.seed)
            np.random.seed(self.seed)

        # 获得初始解
        self.currNode = self.initNode
        self.currOFV = self.currNode.ofv

        self.bestNode = self.currNode
        self.bestOFV = self.currOFV

        printLog("ILS initialization completed")
        printLog(f"Initial objective value: {self.currOFV:.4f}")

    def solve(self):
        startTime = datetime.datetime.now()
        convergence = []

        iteration = 0
        noImproveIter = 0
        temp = self.initTemp

        while (True):
            opName = rndPickFromDict(self.funcNeiOps)
            opFunc = self.funcNeiOps[opName][0]

            newRawSeq = opFunc(self.currNode.rawSeq)

            newNode = RawSolnNode(
                key = newRawSeq,
                rawRep = newRawSeq,
                funcFix = self.currNode.funcFix,
                funcSolve = self.currNode.funcSolve,
                **kwargs
            )
            newObj = newNode.ofv

            accept = False
            if (newObj < self.currOFV):
                accept = True
            else:
                delta = newObj - self.currOFV
                prob = np.exp(-delta / temp) if (temp > 0) else 0.0
                if (random.random() < prob):
                    accept = True

            if (accept):
                self.currNode = newNode
                self.currOFV = newObj

            if (newObj < self.bestOFV - 1e-8):
                self.bestNode = newNode
                self.bestOFV = newObj
                noImproveIter = 0
                printLog(f"Iter {iteration}: New best solution found, obj = {self.bestOFV:.6f}")
            else:
                noImproveIter += 1

            temp *= self.coolRate

            runtime = (datetime.datetime.now() - startTime).total_seconds()
            convergence.append({
                'iter': iteration,
                'obj': self.bestOFV,
                'runtime': runtime
            })

            printLog(f"Iter {iteration:5d}")
            printLog(f"Runtime [s]: {runtime:.2f}")
            printLog(f"bestOFV: {self.bestOFV:.6f}")
            printLog(f"currOFV: {self.currOFV:.6f}")
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

        return {
            'bestOFV': self.bestOFV,
            'bestNode': self.bestNode,
            'runtime': totalRuntime,
            'convergence': convergence,
        }

# class ALNS:
