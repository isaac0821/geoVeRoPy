import random
import datetime
import numpy as np

from .common import *

class ILSNode:
    def __init__(self, rawSeq, funcFix, funcFeasible, funcSolve, **kwargs):
        self.rawSeq = rawSeq
        self.funcFix = funcFix
        self.funcFeasible = funcFeasible
        self.funcSolve = funcSolve
        self.__dict__.update(kwargs)

        self.fixedSeq = None
        self.ofv = None

        self.funcFix(self)
        while not self.funcFeasible(self):
            self.funcFix(self)
        self.funcSolve(self)

class ILS:
    def __init__(self, initialNode, neighborhood, **kwargs):
        self.initialNode = initialNode
        self.neighborhood = neighborhood

        default_params = {
            'initTemp': 100.0,
            'coolRate': 0.95,
            'stopCriteria': {},
            'randomSeed': None
        }
        for key, val in default_params.items():
            setattr(self, key, val)
        self.__dict__.update(kwargs)

        if (self.randomSeed is not None):
            random.seed(self.randomSeed)
            np.random.seed(self.randomSeed)

        self.currentNode = initialNode
        self.currentObj = self.currentNode.ofv
        self.bestNode = self.currentNode
        self.bestObj = self.currentObj

        printLog("ILS initialization completed")
        printLog(f"Initial objective value: {self.currentObj:.4f}")

    def solve(self):
        startTime = datetime.datetime.now()
        convergence = []

        iteration = 0
        noImproveIter = 0
        temp = self.initTemp

        while (True):
            opName = rndPickFromDict(self.neighborhood)
            opFunc = self.neighborhood[opName][0]

            newRawSeq = opFunc(self.currentNode.rawSeq)

            exclude_keys = {'rawSeq', 'funcFix', 'funcFeasible', 'funcSolve', 'fixedSeq', 'ofv'}
            params = {k: v for k, v in self.currentNode.__dict__.items() if (k not in exclude_keys)}

            newNode = ILSNode(
                rawSeq=newRawSeq,
                funcFix=self.currentNode.funcFix,
                funcFeasible=self.currentNode.funcFeasible,
                funcSolve=self.currentNode.funcSolve,
                **params
            )
            newObj = newNode.ofv

            accept = False
            if (newObj < self.currentObj):
                accept = True
            else:
                delta = newObj - self.currentObj
                prob = np.exp(-delta / temp) if (temp > 0) else 0.0
                if (random.random() < prob):
                    accept = True

            if (accept):
                self.currentNode = newNode
                self.currentObj = newObj

            if (newObj < self.bestObj - 1e-8):
                self.bestNode = newNode
                self.bestObj = newObj
                noImproveIter = 0
                printLog(f"Iter {iteration}: New best solution found, obj = {self.bestObj:.6f}")
            else:
                noImproveIter += 1

            temp *= self.coolRate

            runtime = (datetime.datetime.now() - startTime).total_seconds()
            convergence.append({
                'iter': iteration,
                'obj': self.bestObj,
                'runtime': runtime
            })

            printLog(f"Iter {iteration:5d}")
            printLog(f"Runtime [s]: {runtime:.2f}")
            printLog(f"bestOFV: {self.bestObj:.6f}")
            printLog(f"currOFV: {self.currentObj:.6f}")
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
        printLog(f"\nILS finished. Best objective: {self.bestObj:.6f}, total time: {totalRuntime:.2f}s")

        return {
            'bestObj': self.bestObj,
            'bestNode': self.bestNode,
            'runtime': totalRuntime,
            'convergence': convergence,
        }