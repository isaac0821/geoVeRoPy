import random
import math
import datetime
import functools

try:
    import pickle5 as pickle
except(ImportError):
    import pickle

# Error tolerant
ERRTOL = {
    # The distance between two points to be considered as the same point.
    'distPt2Pt': 0.01, 
    'distPt2Seg': 0.05,
    'distPt2Poly': 0.03,
    'deltaDist': 0.01,
    'collinear': 0.001,
    'slope2Slope': 0.001,
    'vertical': 0.001
}

DEBUG = {
    'DEBUG_WRITE_LOG': False,
    'DEBUG_PRINT_LOG': True,
    'DEBUG_LOG_PATH': "log.log"
}

def configSetError(errorType, err):
    global ERRTOL
    if (errorType in ERRTOL):
        ERRTOL[errorType] = err
    else:
        print(f"ERROR: {errorType} is not a valid ERRTOL parameter")
    return

def configSetLog(param, value):
    global DEBUG
    if (param in DEBUG):
        DEBUG[param] = value
    else:
        print(f"ERROR: {param} is not a valid DEBUG parameter")
    return

# Earth radius
CONST_EARTH_RADIUS_MILES = 3958.8
CONST_EARTH_RADIUS_METERS = 6378137.0

# Type alias
pt = list[float] | tuple[float, float]
pt3D = list[float] | tuple[float, float, float]
poly = list[pt]
polys = list[poly]
timedPoly = list[list[poly, float]]
circle = tuple[pt, float]
line = list[pt]

class UnsupportedInputError(Exception):
    pass

class ZeroVectorError(Exception):
    pass

class InvalidPolygonError(Exception):
    pass

class EmptyError(Exception):
    pass

class MissingParameterError(Exception):
    pass

class KeyExistError(Exception):
    pass

class KeyNotExistError(Exception):
    pass

class OutOfRangeError(Exception):
    pass

class VrpSolverNotAvailableError(Exception):
    pass

def saveDictionary(obj, name: str) -> None:
    """
    Save the dictionary to local file as `.pkl`

    Parameters
    ----------

    obj: dict, required
        The dictionary to be saved
    name: str, required
        The name of local file without `.pkl`
    """
    saveName = name + '.pkl'
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def loadDictionary(name: str) -> None:
    """
    Load a dictionary from a local `.pkl` file

    Parameters
    ----------

    name: str, required
        The name of local file with `.pkl`

    Returns
    -------

    dict
        The dictionary loaded from local

    """

    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)
 
def rndPick(coefficients: list[int|float]) -> int:
    """
    Given a list of coefficients, randomly returns an index of the list by coefficient

    Parameters
    ----------

    coefficient: list, required
        A list of probabilities.

    Returns
    -------

    int
        An index randomly selected

    """

    totalSum = sum(coefficients)
    tmpSum = 0
    rnd = random.uniform(0, totalSum)
    idx = 0
    for i in range(len(coefficients)):
        tmpSum += coefficients[i]
        if rnd <= tmpSum:
            idx = i
            break
    return idx

def rndPickFromDict(coefficients: dict) -> int|str:
    keys = list(coefficients.keys())
    values = list(coefficients.values())
    idx = rndPick(values)
    return keys[idx]

def list2String(l, noCommaFlag=False):
    listString = "["
    if (noCommaFlag==False):
        listString += ', '.join([list2String(elem) if type(elem) == list else str(elem) for elem in l.copy()])
    else:
        listString += ''.join([list2String(elem) if type(elem) == list else str(elem) for elem in l.copy()])
    listString += "]"
    return listString

def list2Tuple(l):
    sortedList = [i for i in l]
    sortedList.sort()
    tp = tuple(sortedList)
    return tp

def hyphenStr(s="", length=75, sym='-'):
    if (s == ""):
        return length * sym
    lenMidS = len(s)
    if (lenMidS + 2 < length):
        lenLeftS = (int)((length - lenMidS - 2) / 2)
        lenRightS = length - lenMidS - lenLeftS - 2
        return (lenLeftS * sym) + " " + s + " " + (lenRightS * sym)
    else:
        return s

def splitList(inputList, binNum):
    listLength = len(inputList)
    perFloor = math.floor(listLength / binNum)
    sizePerBin = [perFloor for i in range(binNum)]
    residual = listLength - sum(sizePerBin)
    for i in range(residual):
        sizePerBin[i] += 1
    bins = []
    acc = 0
    for i in range(len(sizePerBin)):
        bins.append([])
        for k in range(acc, acc + sizePerBin[i]):
            bins[i].append(inputList[k])
        acc += sizePerBin[i]
    return bins

def writeLog(string, logPath = None):
    if (DEBUG['DEBUG_WRITE_LOG']):
        if (logPath == None):
            logPath = DEBUG['DEBUG_LOG_PATH']
        f = open(logPath, "a")
        f.write(string + "\n")
        f.close()
    if (DEBUG['DEBUG_PRINT_LOG']):
        print(string)
    return

def printLog(*args):
    if (DEBUG_PRINT_LOG):
        print(*args)
    return

def is2IntervalOverlap(interval1, interval2):
    i = [min(interval1), max(interval1)]
    j = [min(interval2), max(interval2)]

    iA = i[0]
    iB = i[1]
    jA = j[0]
    jB = j[1]

    if (iB < jA):
        return False
    if (jB < iA):
        return False
    return True

def sortListByList(list1, list2):
    """
    Given list2, list1 is a sublist of list2, sort list1 by ordering in list2
    """
    sortedList1 = []
    list1IdxInList2 = []
    for i in list1:
        heapq.heappush(list1IdxInList2, (list2.index(i), i))
    while (len(list1IdxInList2) > 0):
        sortedList1.append(heapq.heappop(list1IdxInList2)[1])
    return sortedList1

def twOverlap(tw1, tw2):
    if (tw1[0] > tw1[1] or tw2[0] > tw2[1]):
        raise UnsupportedInputError("ERROR: Time windows error.")
    if (tw1[0] < tw1[1] < tw2[0] < tw2[1]):
        return False
    if (tw2[0] < tw2[1] < tw1[0] < tw1[1]):
        return False
    return True

def splitIntoSubSeq(inputList, selectFlag):
    if (len(inputList) != len(selectFlag)):
        raise UnsupportedInputError("ERROR: The length of `inputList` should be the same as the length of `selectFlag`")
    splitSub = []
    sub = []
    for i in range(len(selectFlag)):
        if (selectFlag[i] == True):
            sub.append(inputList[i])
        elif (selectFlag[i] == False):
            if (len(sub) > 0):
                splitSub.append([k for k in sub])
                sub = []
    if (len(sub) > 0):
        splitSub.append([k for k in sub])
    return splitSub

globalRuntimeAnalysis = {}
# Support runtime tracking and store in dictionary of at most three level
def runtime(key1, key2=None, key3=None):
    def deco(func):
        @functools.wraps(func)
        def fun(*args, **kwargs):
            t = datetime.datetime.now()
            result = func(*args, **kwargs)
            dt = (datetime.datetime.now() - t).total_seconds()
            global globalRuntimeAnalysis
            if (key1 != None and key2 != None and key3 != None):
                # Store in globalRuntimeAnalysis[key1][key2][key3]
                if (key1 not in globalRuntimeAnalysis):
                    globalRuntimeAnalysis[key1] = {}
                if (key2 not in globalRuntimeAnalysis[key1]):
                    globalRuntimeAnalysis[key1][key2] = {}
                if (key3 not in globalRuntimeAnalysis[key1][key2]):
                    globalRuntimeAnalysis[key1][key2][key3] = [dt, 1]
                else:
                    globalRuntimeAnalysis[key1][key2][key3][0] += dt
                    globalRuntimeAnalysis[key1][key2][key3][1] += 1
            elif (key1 != None and key2 != None and key3 == None):
                # Store in globalRuntimeAnalysis[key1][key2]
                if (key1 not in globalRuntimeAnalysis):
                    globalRuntimeAnalysis[key1] = {}
                if (key2 not in globalRuntimeAnalysis[key1]):
                    globalRuntimeAnalysis[key1][key2] = [dt, 1]
                else:
                    globalRuntimeAnalysis[key1][key2][0] += dt
                    globalRuntimeAnalysis[key1][key2][1] += 1
            elif (key1 != None and key2 == None and key3 == None):
                # Store in globalRuntimeAnalysis[key1]
                if (key1 not in globalRuntimeAnalysis):
                    globalRuntimeAnalysis[key1] = [dt, 1]
                else:
                    globalRuntimeAnalysis[key1][0] += dt
                    globalRuntimeAnalysis[key1][1] += 1
            return result
        return fun
    return deco

def tellRuntime(funcName, indentLevel=0):
    def deco(func):
        @functools.wraps(func)
        def fun(*args, **kwargs):
            t = datetime.datetime.now()
            result = func(*args, **kwargs)
            dt = (datetime.datetime.now() - t).total_seconds()
            indent = "----" * indentLevel
            print(f"**{indent}Func {funcName} runtime: {dt}")
            return result
        return fun
    return deco