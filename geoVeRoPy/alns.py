import random
import datetime
import numpy as np

from .common import *
from .ils import SolnNode, RawSolnNode

__all__ = ['ALNS']


class ALNS:
    def __init__(self, initNode: SolnNode, funcDestroyOps=None, funcRepairOps=None, **kwargs):
        """Generic Adaptive Large Neighborhood Search framework.

        Parameters
        ----------
        initNode: SolnNode, required
            Initial solution node. It must implement solve() and expose the
            objective field specified by objFieldName after being solved.
        funcDestroyOps: list|dict, required
            Destroy operators. Each operator receives the current node and
            returns a partially destroyed node or a complete neighbor node.
            If a dictionary is used, values are treated as initial weights.
        funcRepairOps: list|dict, optional
            Repair operators. Each operator receives the destroyed node and
            returns a complete candidate node. If omitted, destroy operators
            are treated as complete neighborhood operators.
        **kwargs: optional
            Additional ALNS parameters.
        """
        defaultParam = {
            'initTemp': 100.0,
            'coolRate': 0.95,
            'stopCriteria': {
                'numIter': 100
            },
            'seed': None,
            'objSense': 'Min',
            'objFieldName': 'ofv',
            'printFieldNames': [],
            'operatorSelector': 'Roulette',
            'minOperatorProb': 0.03,
            'operatorLearningRate': 0.20,
            'operatorRewardScale': 1.00,
            'contextualBanditAlpha': 0.75,
            'contextualBanditEps': 0.05,
            'contextualBanditLambda': 1.00,
            'contextualBanditRewardClip': 20.00,
            'rewardBest': 10.0,
            'rewardImprove': 5.0,
            'rewardAccept': 1.0,
            'rewardReject': 0.1,
            'weightLowerBound': 1e-6,
            'weightUpperBound': 1e6,
            'candidateSolveFlag': True,
            'destroyedSolveFlag': False,
            'verboseFlag': True
        }
        for key, val in defaultParam.items():
            setattr(self, key, val)
        self.__dict__.update(kwargs)
        if (self.objSense not in ['Min', 'Max']):
            raise UnsupportedInputError("ERROR: `objSense` should be 'Min' or 'Max'.")
        if (self.operatorSelector not in ['Roulette', 'ContextualBandit']):
            raise UnsupportedInputError("ERROR: `operatorSelector` should be 'Roulette' or 'ContextualBandit'.")
        if (type(self.printFieldNames) is str):
            self.printFieldNames = [self.printFieldNames]
        if (self.seed is not None):
            random.seed(self.seed)

        if (funcDestroyOps == None and 'funcNeiOps' in kwargs):
            funcDestroyOps = kwargs['funcNeiOps']
        if (funcDestroyOps == None):
            raise MissingParameterError("ERROR: Missing required field `funcDestroyOps`.")
        if (callable(funcDestroyOps)):
            funcDestroyOps = [funcDestroyOps]
        if (callable(funcRepairOps)):
            funcRepairOps = [funcRepairOps]

        self.initNode = initNode
        self.initNode.solve()
        self.currNode = self.initNode
        self.currOFV = getattr(self.currNode, self.objFieldName)
        self.bestNode = self.currNode
        self.bestOFV = self.currOFV

        self.funcDestroyOps = [func for func in funcDestroyOps] if (type(funcDestroyOps) is dict) else [func for func in funcDestroyOps]
        self.destroyWeights = {}
        if (type(funcDestroyOps) is dict):
            for func in funcDestroyOps:
                self.destroyWeights[func] = max(float(funcDestroyOps[func]), self.weightLowerBound)
        else:
            for func in self.funcDestroyOps:
                self.destroyWeights[func] = 1.0

        if (funcRepairOps == None):
            self.funcRepairOps = [None]
            self.repairWeights = {None: 1.0}
        else:
            self.funcRepairOps = [func for func in funcRepairOps] if (type(funcRepairOps) is dict) else [func for func in funcRepairOps]
            self.repairWeights = {}
            if (type(funcRepairOps) is dict):
                for func in funcRepairOps:
                    self.repairWeights[func] = max(float(funcRepairOps[func]), self.weightLowerBound)
            else:
                for func in self.funcRepairOps:
                    self.repairWeights[func] = 1.0

        if (len(self.funcDestroyOps) == 0):
            raise UnsupportedInputError("ERROR: `funcDestroyOps` should not be empty.")
        if (len(self.funcRepairOps) == 0):
            raise UnsupportedInputError("ERROR: `funcRepairOps` should not be empty.")

        self.banditFeatureDim = 8
        self.banditActions = []
        self.banditModels = {}
        if (self.operatorSelector == 'ContextualBandit'):
            for destroyFunc in self.funcDestroyOps:
                for repairFunc in self.funcRepairOps:
                    actionKey = (destroyFunc, repairFunc)
                    self.banditActions.append(actionKey)
                    self.banditModels[actionKey] = {
                        'a': self.contextualBanditLambda * np.eye(self.banditFeatureDim),
                        'b': np.zeros(self.banditFeatureDim),
                        'count': 0,
                        'rewardSum': 0.0
                    }

        self.runtime = None
        self.convergence = []

        if (self.verboseFlag):
            printLog("ALNS initialization completed")
            printLog(f"Initial obj: {self.currOFV:.4f}")
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
            banditScore = None
            banditExploreFlag = False
            contextVec = None
            if (self.operatorSelector == 'ContextualBandit'):
                currNode = self.currNode
                currDist = float(getattr(currNode, 'dist', 0.0) or 0.0)
                currMaxLength = float(getattr(currNode, 'maxLength', 0.0) or 0.0)
                slackRatio = (currMaxLength - currDist) / max(abs(currMaxLength), 1.0) if (currMaxLength > 0) else 0.0
                objScale = max(abs(self.currOFV), abs(self.bestOFV), 1.0)
                objRatio = self.currOFV / objScale
                curRep = getattr(currNode, 'curRep', getattr(currNode, 'rep', []))
                routeLen = len(curRep) if (type(curRep) in [list, tuple]) else 0
                customerIDs = getattr(currNode, 'customerIDs', [])
                customerCount = len(customerIDs) if (type(customerIDs) in [list, tuple, set]) else 0
                routeRatio = routeLen / max(customerCount, 1)
                missing = getattr(currNode, 'missing', [])
                missingLen = len(missing) if (type(missing) in [list, tuple, set, dict]) else 0
                missingRatio = missingLen / max(customerCount, 1)
                tempRatio = temp / max(abs(self.initTemp), 1.0)
                maxIter = self.stopCriteria['numIter'] if ('numIter' in self.stopCriteria) else max(iteration + 1, 1)
                iterRatio = iteration / max(maxIter, 1)
                maxNoImprove = self.stopCriteria['numNoImprove'] if ('numNoImprove' in self.stopCriteria) else max(noImproveIter + 1, 1)
                noImproveRatio = noImproveIter / max(maxNoImprove, 1)
                contextVec = np.array([1.0, objRatio, slackRatio, routeRatio, missingRatio, tempRatio, iterRatio, noImproveRatio], dtype = float)
                exploreProb = min(max(max(self.minOperatorProb, self.contextualBanditEps), 0.0), 1.0)
                if (random.random() < exploreProb):
                    destroyFunc, repairFunc = random.choice(self.banditActions)
                    banditExploreFlag = True
                    banditScore = None
                else:
                    bestScore = -float('inf')
                    bestActions = []
                    for actionKey in self.banditActions:
                        model = self.banditModels[actionKey]
                        try:
                            theta = np.linalg.solve(model['a'], model['b'])
                            aInvX = np.linalg.solve(model['a'], contextVec)
                        except np.linalg.LinAlgError:
                            aInv = np.linalg.pinv(model['a'])
                            theta = aInv @ model['b']
                            aInvX = aInv @ contextVec
                        predReward = float(theta @ contextVec)
                        uncertainty = float(np.sqrt(max(contextVec @ aInvX, 0.0)))
                        curScore = predReward + self.contextualBanditAlpha * uncertainty
                        if (curScore > bestScore + 1e-12):
                            bestScore = curScore
                            bestActions = [actionKey]
                        elif (abs(curScore - bestScore) <= 1e-12):
                            bestActions.append(actionKey)
                    destroyFunc, repairFunc = random.choice(bestActions)
                    banditScore = bestScore
            else:
                minDestroyProb = min(max(self.minOperatorProb, 0), 0.5 / max(len(self.destroyWeights), 1))
                totalDestroyWeight = sum([max(self.destroyWeights[func], self.weightLowerBound) for func in self.destroyWeights])
                destroyRoulette = {}
                for func in self.destroyWeights:
                    baseProb = max(self.destroyWeights[func], self.weightLowerBound) / totalDestroyWeight
                    destroyRoulette[func] = minDestroyProb + (1 - minDestroyProb * len(self.destroyWeights)) * baseProb

                minRepairProb = min(max(self.minOperatorProb, 0), 0.5 / max(len(self.repairWeights), 1))
                totalRepairWeight = sum([max(self.repairWeights[func], self.weightLowerBound) for func in self.repairWeights])
                repairRoulette = {}
                for func in self.repairWeights:
                    baseProb = max(self.repairWeights[func], self.weightLowerBound) / totalRepairWeight
                    repairRoulette[func] = minRepairProb + (1 - minRepairProb * len(self.repairWeights)) * baseProb

                destroyFunc = rndPickFromDict(destroyRoulette)
                repairFunc = rndPickFromDict(repairRoulette)
            opStartTime = datetime.datetime.now()

            destroyedNode = destroyFunc(self.currNode)
            if (destroyedNode == None):
                newNode = None
            else:
                if (self.destroyedSolveFlag):
                    destroyedNode.solve()
                if (repairFunc == None):
                    newNode = destroyedNode
                else:
                    newNode = repairFunc(destroyedNode)
            if (newNode == None):
                newNode = self.currNode
            if (self.candidateSolveFlag):
                newNode.solve()

            opRuntime = max((datetime.datetime.now() - opStartTime).total_seconds(), 1e-6)
            newObj = getattr(newNode, self.objFieldName)
            accept = False
            if ((self.objSense == 'Min' and newObj < self.currOFV) or (self.objSense == 'Max' and newObj > self.currOFV)):
                accept = True
            else:
                if (self.objSense == 'Min'):
                    delta = newObj - self.currOFV
                else:
                    delta = self.currOFV - newObj
                prob = np.exp(-delta / temp) if (temp > 0) else 0.0
                if (random.random() < prob):
                    accept = True

            newBestFlag = ((self.objSense == 'Min' and newObj < self.bestOFV - 1e-8) or (self.objSense == 'Max' and newObj > self.bestOFV + 1e-8))
            improveFlag = ((self.objSense == 'Min' and newObj < self.currOFV - 1e-8) or (self.objSense == 'Max' and newObj > self.currOFV + 1e-8))
            if (newBestFlag):
                reward = self.rewardBest
            elif (improveFlag):
                reward = self.rewardImprove
            elif (accept):
                reward = self.rewardAccept
            else:
                reward = -abs(self.rewardReject) if (self.operatorSelector == 'ContextualBandit') else self.rewardReject

            learningRate = min(max(self.operatorLearningRate, 0), 1)
            if (self.operatorSelector == 'ContextualBandit'):
                actionKey = (destroyFunc, repairFunc)
                banditReward = min(max(reward * self.operatorRewardScale, -self.contextualBanditRewardClip), self.contextualBanditRewardClip)
                self.banditModels[actionKey]['a'] += np.outer(contextVec, contextVec)
                self.banditModels[actionKey]['b'] += banditReward * contextVec
                self.banditModels[actionKey]['count'] += 1
                self.banditModels[actionKey]['rewardSum'] += banditReward
                self.destroyWeights[destroyFunc] = max((1 - learningRate) * self.destroyWeights[destroyFunc] + learningRate * max(banditReward, self.weightLowerBound), self.weightLowerBound)
                self.repairWeights[repairFunc] = max((1 - learningRate) * self.repairWeights[repairFunc] + learningRate * max(banditReward, self.weightLowerBound), self.weightLowerBound)
            else:
                banditReward = None
                scaledReward = min(max(reward * self.operatorRewardScale / opRuntime, self.weightLowerBound), self.weightUpperBound)
                self.destroyWeights[destroyFunc] = max((1 - learningRate) * self.destroyWeights[destroyFunc] + learningRate * scaledReward, self.weightLowerBound)
                self.repairWeights[repairFunc] = max((1 - learningRate) * self.repairWeights[repairFunc] + learningRate * scaledReward, self.weightLowerBound)

            if (accept):
                self.currNode = newNode
                self.currOFV = newObj
            if (newBestFlag):
                self.bestNode = newNode
                self.bestOFV = newObj
                noImproveIter = 0
                if (self.verboseFlag):
                    printLog(f"Iter {iteration}: New best solution found, obj = {self.bestOFV:.6f}")
            else:
                noImproveIter += 1

            temp *= self.coolRate
            runtime = (datetime.datetime.now() - startTime).total_seconds()
            destroyName = destroyFunc.__name__ if (destroyFunc != None and hasattr(destroyFunc, '__name__')) else str(destroyFunc)
            repairName = repairFunc.__name__ if (repairFunc != None and hasattr(repairFunc, '__name__')) else str(repairFunc)
            convergenceItem = {
                'iter': iteration,
                'obj': self.bestOFV,
                'currObj': self.currOFV,
                'accepted': accept,
                'destroyOp': destroyName,
                'repairOp': repairName,
                'operatorSelector': self.operatorSelector,
                'reward': reward,
                'banditReward': banditReward,
                'banditScore': banditScore,
                'banditExploreFlag': banditExploreFlag,
                'runtime': runtime
            }
            for fieldName in self.printFieldNames:
                convergenceItem[fieldName] = getattr(self.bestNode, fieldName, None)
            convergence.append(convergenceItem)

            if (self.verboseFlag):
                printLog(hyphenStr())
                printLog(f"Iter {iteration:5d}")
                printLog(f"Runtime [s]: {runtime:.2f}")
                printLog(f"Destroy operator: {destroyName}")
                printLog(f"Repair operator: {repairName}")
                printLog(f"Operator selector: {self.operatorSelector}")
                if (self.operatorSelector == 'ContextualBandit'):
                    printLog(f"Bandit explore: {banditExploreFlag}")
                    printLog(f"Bandit reward: {banditReward}")
                printLog(f"Accepted: {accept}")
                printLog(f"bestObj: {self.bestOFV:.6f}")
                printLog(f"currObj: {self.currOFV:.6f}")
                for fieldName in self.printFieldNames:
                    if (len(fieldName) == 0):
                        continue
                    fieldLabel = fieldName[0].upper() + fieldName[1:]
                    printLog(f"best{fieldLabel}: {getattr(self.bestNode, fieldName, None)}")
                    printLog(f"curr{fieldLabel}: {getattr(self.currNode, fieldName, None)}")
                printLog(f"Temperature: {temp:.3f}")

            if (('numIter' in self.stopCriteria) and (iteration >= self.stopCriteria['numIter'])):
                if (self.verboseFlag):
                    printLog(f"Reached max iterations {self.stopCriteria['numIter']}, stopping")
                break
            if (('numNoImprove' in self.stopCriteria) and (noImproveIter >= self.stopCriteria['numNoImprove'])):
                if (self.verboseFlag):
                    printLog(f"No improvement for {noImproveIter} iterations, stopping")
                break
            if (('runtime' in self.stopCriteria) and (runtime >= self.stopCriteria['runtime'])):
                if (self.verboseFlag):
                    printLog(f"Reached runtime limit {self.stopCriteria['runtime']} seconds, stopping")
                break

            iteration += 1

        totalRuntime = (datetime.datetime.now() - startTime).total_seconds()
        if (self.verboseFlag):
            printLog(f"\nALNS finished. Best obj: {self.bestOFV:.6f}, total time: {totalRuntime:.2f}s")

        self.runtime = totalRuntime
        self.convergence = convergence
        return
