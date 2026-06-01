import datetime
from .common import *
from .geometry import *
from .travel import *
from .tsp import solveTSP


def solveDTSP(
    nodes: dict,
    depotID: int | str = 0,
    customerIDs: list[int | str] | str = 'All',
    releaseTimeFieldName: str = 'releaseTime',
    reoptimizeInterval: float = 1,
    startTime: float = 0,
    endTime: float | None = None,
    vehicles: dict | None = None,
    vehicleID: int | str = 0,
    serviceTime: float = 0,
    edges: str = 'Euclidean',
    algo: str = 'Exact',
    returnToDepotFlag: bool = True,
    ptFieldName: str = 'pt',
    metaFlag: bool = False,
    **kwargs
    ) -> dict:

    """Solve a dynamic TSP with fixed-interval rolling-horizon re-optimization.

    Customers are provided in `nodes`. Each customer appears when
    `nodes[customerID][releaseTimeFieldName]` is no greater than the current
    re-optimization time. At every `reoptimizeInterval`, the framework calls
    :func:`solveTSP` on currently available customers and commits to the new
    planned sequence until the next re-optimization tick.
    """

    # Local subroutines =======================================================
    def distBetween(nodeID1, nodeID2, pt1 = None, pt2 = None):
        if (nodeID1 != None and nodeID2 != None and (nodeID1, nodeID2) in tau):
            return tau[nodeID1, nodeID2]
        if (edges == 'Dictionary'):
            raise UnsupportedInputError(
                "ERROR: `edges='Dictionary'` cannot re-optimize from an in-transit vehicle position.")
        tmpNodes = {
            '__from_position__': {'pt': pt1},
            '__to_position__': {'pt': pt2}
        }
        tmpTau = matrixDist(
            nodes = tmpNodes,
            nodeIDs = ['__from_position__', '__to_position__'],
            edges = edges,
            ptFieldName = 'pt',
            **kwargs)
        return tmpTau['__from_position__', '__to_position__']

    def extractPlan(solSeq, curKey, availableCustomerIDs):
        if (solSeq == None or len(solSeq) == 0):
            return []
        if (curKey in solSeq):
            startIndex = solSeq.index(curKey)
            orderedSeq = solSeq[startIndex + 1:] + solSeq[:startIndex]
        else:
            orderedSeq = solSeq
        plan = []
        for i in orderedSeq:
            if (i in availableCustomerIDs and i not in plan):
                plan.append(i)
        return plan

    def optimizeFromCurrentPosition(curTime, curPt, curNodeID, unserved):
        availableCustomerIDs = [
            i for i in unserved
            if (nodes[i][releaseTimeFieldName] <= curTime)
        ]
        if (len(availableCustomerIDs) == 0):
            return [], None, availableCustomerIDs

        curKey = curNodeID
        tspNodes = {}
        if (curKey == None):
            curKey = '__current_position__'
            tspNodes[curKey] = {'pt': curPt}
        else:
            tspNodes[curKey] = dict(nodes[curKey])
            if (ptFieldName != 'pt'):
                tspNodes[curKey]['pt'] = nodes[curKey][ptFieldName]

        for i in availableCustomerIDs:
            tspNodes[i] = dict(nodes[i])
            if (ptFieldName != 'pt'):
                tspNodes[i]['pt'] = nodes[i][ptFieldName]

        if (depotID not in tspNodes):
            tspNodes[depotID] = dict(nodes[depotID])
            if (ptFieldName != 'pt'):
                tspNodes[depotID]['pt'] = nodes[depotID][ptFieldName]

        tspNodeIDs = [curKey]
        for i in availableCustomerIDs:
            if (i not in tspNodeIDs):
                tspNodeIDs.append(i)
        if (depotID not in tspNodeIDs):
            tspNodeIDs.append(depotID)

        tspTau = {}
        if (curNodeID == None):
            localTau = matrixDist(
                nodes = tspNodes,
                nodeIDs = tspNodeIDs,
                edges = edges,
                ptFieldName = 'pt',
                **kwargs)
            for p in localTau:
                tspTau[p] = localTau[p]
        else:
            for i in tspNodeIDs:
                for j in tspNodeIDs:
                    if ((i, j) in tau):
                        tspTau[i, j] = tau[i, j]

        if (len(availableCustomerIDs) == 1):
            nextID = availableCustomerIDs[0]
            tspSol = {
                'ofv': tspTau[curKey, nextID] + tspTau[nextID, depotID],
                'seq': [curKey, nextID, depotID]
            }
            plan = [nextID]
        else:
            if (curKey == depotID):
                tspSol = solveTSP(
                    nodes = tspNodes,
                    depotID = depotID,
                    nodeIDs = tspNodeIDs,
                    vehicles = vehicles,
                    vehicleID = vehicleID,
                    serviceTime = serviceTime,
                    edges = 'Dictionary',
                    algo = algo,
                    tau = tspTau,
                    metaFlag = metaFlag,
                    **solverKwargs)
            else:
                tspSol = solveTSP(
                    nodes = tspNodes,
                    depotID = None,
                    startID = curKey,
                    endID = depotID,
                    nodeIDs = tspNodeIDs,
                    vehicles = vehicles,
                    vehicleID = vehicleID,
                    serviceTime = serviceTime,
                    edges = 'Dictionary',
                    algo = algo,
                    tau = tspTau,
                    metaFlag = metaFlag,
                    **solverKwargs)
            plan = extractPlan(tspSol['seq'], curKey, availableCustomerIDs)
            if (len(plan) == 0 and len(availableCustomerIDs) > 0):
                nextID = min(availableCustomerIDs, key = lambda i: tspTau[curKey, i])
                plan = [nextID]
                writeLog("WARNING: Empty TSP route plan, fallback to nearest customer %s." % nextID)

        return plan, tspSol, availableCustomerIDs

    # Sanity check ============================================================
    if (nodes == None or type(nodes) != dict):
        raise MissingParameterError("ERROR: Missing required field `nodes`.")
    if (depotID not in nodes):
        raise OutOfRangeError("ERROR: Cannot find `depotID` in `nodes`.")
    for i in nodes:
        if (ptFieldName not in nodes[i]):
            raise MissingParameterError("ERROR: missing location information in `nodes`.")

    if (vehicles == None):
        vehicles = {0: {'speed': 1}}
    if (vehicleID not in vehicles):
        raise MissingParameterError("ERROR: Cannot find `vehicleID` in `vehicles`.")
    if ('speed' not in vehicles[vehicleID] or vehicles[vehicleID]['speed'] <= 0):
        raise OutOfRangeError("ERROR: Vehicle speed must be positive.")
    if (reoptimizeInterval <= 0):
        raise OutOfRangeError("ERROR: `reoptimizeInterval` should be positive.")

    if (customerIDs == 'All'):
        customerIDs = [i for i in nodes if i != depotID]
    elif (type(customerIDs) is not list):
        raise MissingParameterError("ERROR: `customerIDs` should be 'All' or a list.")

    candidateCustomerIDs = []
    ignoredCustomerIDs = []
    for i in customerIDs:
        if (i not in nodes):
            raise OutOfRangeError("ERROR: Customer %s is not in `nodes`." % i)
        if (i == depotID):
            raise OutOfRangeError("ERROR: `customerIDs` should not include `depotID`.")
        if (releaseTimeFieldName not in nodes[i]):
            raise MissingParameterError("ERROR: Customer %s does not specify `%s`." % (i, releaseTimeFieldName))
        if (endTime != None and nodes[i][releaseTimeFieldName] > endTime):
            ignoredCustomerIDs.append(i)
        else:
            candidateCustomerIDs.append(i)

    tau = matrixDist(
        nodes = nodes,
        nodeIDs = [depotID] + candidateCustomerIDs,
        edges = edges,
        ptFieldName = ptFieldName,
        **kwargs)

    solverKwargs = dict(kwargs)
    solverKwargs.pop('tau', None)
    solverKwargs.pop('path', None)

    # Rolling horizon simulation =============================================
    startClockTime = datetime.datetime.now()
    speed = vehicles[vehicleID]['speed']

    decisionTime = startTime
    curPt = nodes[depotID][ptFieldName]
    curNodeID = depotID
    routePlan = []
    unserved = [i for i in candidateCustomerIDs]
    served = []
    customerStatus = {i: 'unreleased' for i in candidateCustomerIDs}
    seq = [depotID]
    events = []
    planHistory = []
    timedPt = [[tuple(curPt), float(startTime)]]
    totalTravelCost = 0
    totalWaitTime = 0
    totalServiceTime = 0
    lastEventTime = startTime
    pendingServiceID = None
    serviceRemaining = 0

    while (len(unserved) > 0):
        if (endTime != None and decisionTime > endTime):
            break

        intervalStart = decisionTime
        intervalEnd = decisionTime + reoptimizeInterval
        simTime = intervalStart
        timeLeft = reoptimizeInterval

        for i in unserved:
            if (i == pendingServiceID):
                customerStatus[i] = 'serving'
            elif (nodes[i][releaseTimeFieldName] <= decisionTime):
                customerStatus[i] = 'available'
            else:
                customerStatus[i] = 'unreleased'

        if (pendingServiceID == None):
            routePlan, tspSol, availableCustomerIDs = optimizeFromCurrentPosition(
                curTime = decisionTime,
                curPt = curPt,
                curNodeID = curNodeID,
                unserved = unserved)
        else:
            tspSol = None
            availableCustomerIDs = []
            routePlan = []

        writeLog(hyphenStr())
        writeLog("Rolling Horizon reoptimize @ %s" % decisionTime)
        writeLog("Customers considered: %s" % str(availableCustomerIDs))
        writeLog("Customers completed: %s" % str(served))

        planHistory.append({
            'time': decisionTime,
            'currentID': curNodeID,
            'currentPt': curPt,
            'availableCustomerIDs': [i for i in availableCustomerIDs],
            'plannedSeq': [] if tspSol == None else tspSol['seq'],
            'routePlan': [i for i in routePlan],
            'ofv': None if tspSol == None else tspSol['ofv'],
            'customerStatus': dict(customerStatus)
        })

        while (timeLeft > ERRTOL['deltaDist']):
            if (pendingServiceID != None):
                dt = min(serviceRemaining, timeLeft)
                events.append({
                    'type': 'service',
                    'nodeID': pendingServiceID,
                    'startTime': simTime,
                    'endTime': simTime + dt,
                    'serviceTime': dt
                })
                totalServiceTime += dt
                serviceRemaining -= dt
                simTime += dt
                timeLeft -= dt
                timedPt.append([tuple(curPt), float(simTime)])
                lastEventTime = simTime
                if (serviceRemaining <= ERRTOL['deltaDist']):
                    served.append(pendingServiceID)
                    seq.append(pendingServiceID)
                    unserved.remove(pendingServiceID)
                    customerStatus[pendingServiceID] = 'completed'
                    pendingServiceID = None
                else:
                    break
                continue

            while (len(routePlan) > 0 and routePlan[0] not in unserved):
                routePlan.pop(0)

            if (len(routePlan) == 0):
                events.append({
                    'type': 'idle',
                    'startTime': simTime,
                    'endTime': intervalEnd,
                    'pt': curPt
                })
                simTime = intervalEnd
                timeLeft = 0
                break

            nextID = routePlan[0]
            nextPt = nodes[nextID][ptFieldName]
            legCost = distBetween(curNodeID, nextID, curPt, nextPt)
            legTime = legCost / speed

            if (legTime > timeLeft + ERRTOL['deltaDist']):
                ratio = 0 if legTime <= ERRTOL['deltaDist'] else timeLeft / legTime
                newPt = interpolatePt(curPt, nextPt, ratio)
                events.append({
                    'type': 'travel',
                    'from': curNodeID,
                    'to': nextID,
                    'startTime': simTime,
                    'endTime': intervalEnd,
                    'startPt': curPt,
                    'endPt': newPt,
                    'travelCost': timeLeft * speed,
                    'interruptedByReoptimizeFlag': True
                })
                totalTravelCost += timeLeft * speed
                curPt = newPt
                curNodeID = None
                simTime = intervalEnd
                timedPt.append([tuple(curPt), float(simTime)])
                lastEventTime = simTime
                timeLeft = 0
                break

            arrivalTime = simTime + legTime
            events.append({
                'type': 'travel',
                'from': curNodeID,
                'to': nextID,
                'startTime': simTime,
                'endTime': arrivalTime,
                'startPt': curPt,
                'endPt': nextPt,
                'travelCost': legCost,
                'interruptedByReoptimizeFlag': False
            })
            totalTravelCost += legCost
            simTime = arrivalTime
            timeLeft -= legTime
            curPt = nextPt
            curNodeID = nextID
            timedPt.append([tuple(curPt), float(simTime)])
            lastEventTime = simTime

            releaseTime = nodes[nextID][releaseTimeFieldName]
            if (releaseTime > simTime + ERRTOL['deltaDist']):
                dt = min(releaseTime - simTime, timeLeft)
                events.append({
                    'type': 'wait',
                    'nodeID': nextID,
                    'startTime': simTime,
                    'endTime': simTime + dt
                })
                totalWaitTime += dt
                simTime += dt
                timeLeft -= dt
                timedPt.append([tuple(curPt), float(simTime)])
                lastEventTime = simTime
                if (simTime < releaseTime - ERRTOL['deltaDist']):
                    break

            nodeServiceTime = nodes[nextID]['serviceTime'] if 'serviceTime' in nodes[nextID] else serviceTime
            routePlan.pop(0)
            if (nodeServiceTime <= ERRTOL['deltaDist']):
                served.append(nextID)
                seq.append(nextID)
                unserved.remove(nextID)
                customerStatus[nextID] = 'completed'
                continue

            dt = min(nodeServiceTime, timeLeft)
            if (dt > ERRTOL['deltaDist']):
                events.append({
                    'type': 'service',
                    'nodeID': nextID,
                    'startTime': simTime,
                    'endTime': simTime + dt,
                    'serviceTime': dt
                })
                totalServiceTime += dt
                simTime += dt
                timeLeft -= dt
                timedPt.append([tuple(curPt), float(simTime)])
                lastEventTime = simTime
            if (dt < nodeServiceTime - ERRTOL['deltaDist']):
                pendingServiceID = nextID
                serviceRemaining = nodeServiceTime - dt
                customerStatus[nextID] = 'serving'
                break
            served.append(nextID)
            seq.append(nextID)
            unserved.remove(nextID)
            customerStatus[nextID] = 'completed'

        decisionTime += reoptimizeInterval

    completionTime = lastEventTime

    if (returnToDepotFlag and not is2PtsSame(curPt, nodes[depotID][ptFieldName])):
        depotPt = nodes[depotID][ptFieldName]
        travelCost = distBetween(curNodeID, depotID, curPt, depotPt)
        travelTime = travelCost / speed
        returnStartTime = completionTime
        events.append({
            'type': 'return',
            'from': curNodeID,
            'to': depotID,
            'startTime': returnStartTime,
            'endTime': returnStartTime + travelTime,
            'startPt': curPt,
            'endPt': depotPt,
            'travelCost': travelCost
        })
        totalTravelCost += travelCost
        completionTime = returnStartTime + travelTime
        curPt = depotPt
        curNodeID = depotID
        timedPt.append([tuple(curPt), float(completionTime)])
        seq.append(depotID)

    res = {
        'ofv': completionTime,
        'travelCost': totalTravelCost,
        'waitTime': totalWaitTime,
        'serviceTime': totalServiceTime,
        'completionTime': completionTime,
        'timedPt': timedPt,
        'seq': seq,
        'servedCustomerIDs': served,
        'unservedCustomerIDs': unserved,
        'customerStatus': customerStatus,
        'events': events,
        'planHistory': planHistory,
        'runtime': (datetime.datetime.now() - startClockTime).total_seconds()
    }

    if (metaFlag):
        res['framework'] = 'RollingHorizon'
        res['algo'] = algo
        res['reoptimizeInterval'] = reoptimizeInterval
        res['releaseTimeFieldName'] = releaseTimeFieldName
        res['ignoredCustomerIDs'] = ignoredCustomerIDs

    return res
