from .ds import *
from .common import *

def solveTDPMS(
    M: int,
    jobs: dict,
    jobIDs: list[int|str]|"All": "All",
    initSch: list|None = None,
    stop: dict = {}
    ) -> "Time-Dependent Parallel Machine Scheduling, Pm|p_j = f(S_j), d_bar|C_max":
    # Initialize ==============================================================
    schedule = {}
    toInsert = [i for i in jobIDs]
    toRemove = []
    for mID in range(numMachine):
        schedule[mID] = JobSeq(jobs)
    if (initSch != None):
        # FIXME: This is a terrible op
        # Make a copy from initSch
        for mID in range(numMachine):
            # Clone from the initial schedule
            # NOTE: 1. Still, this will be a bottleneck
            # NOTE: 2. Find and amend differences
            #       - toRemove: Find jobs in schedule but not in jobIDs
            #       - toInsert: Find jobs not in schedule but in jobIDs
            schedule[mID] = initSch[mID].clone()
            mJobs = schedule[mID].traverseKey()
            exInMID = listSetMinus(mJobs, jobIDs)
            for j in exInMID:
                toRemove.append((mID, j))
            toInsert = listSetMinus(toInsert, mJobs)

    # Amend phase =============================================================
    if (len(toRemove) > 0):
        for remove in toRemove:
            (mID, jID) = remove
            schedule[mID].remove(jID)

    curMakespan = max([schedule[mID].makespan for mID in range(numMachine)])

    # Insertion phase  ========================================================
    def _constructionMachine(jobSeq):
        for jID in jobSeq:
            bestMakespan = None
            bestMID = None
            for mID in range(numMachine):
                # append to mID
                schedule[mID].cheapInsert(jID)
                if (bestMakespan == None or bestMakespan > schedule[mID].makespan):
                    bestMakespan = schedule[mID].makespan
                    bestMID = mID
            for mID in range(numMachine):
                if (mID != bestMID):
                    # remove from mID                    
                    schedule[mID].remove(jID)
            # print("After inserting ", jID)
            # for mID in range(numMachine):
                # print("mID %s: -> " % mID, schedule[mID].traverseKey(), "makespan: ", schedule[mID].makespan)
        return
    _constructionMachine(toInsert)
    curMakespan = max([schedule[mID].makespan for mID in range(numMachine)])
    consOfv = curMakespan
    def _evalWorstDev(mID):
        dev = []
        for job in [i for i in schedule[mID].traverse()]:
            procT = job.te - job.ts
            bestT = jobs[job.jID]['bestT']
            worstT = jobs[job.jID]['worstT']
            dev.append(((procT - bestT) / (worstT - bestT)) if (worstT > bestT) else 0)
        return max(dev) if len(dev) > 0 else 0

    # Local improvement phase =================================================
    def _intraMachineSwap(mID, earlyEndMakespan=None):
        improvedFlag = False
        canSwapFlag = True
        while (canSwapFlag):
            canSwapFlag = False
            # 1. First attempt - 1 swap
            # Old: = = = i j k l m n = = = | -> swap(i, j) 
            # 2. Follow-up attempts
            # New: = = = j i k l m n = = = | -> swap(i, k) -> swap(j, k)
            # New: = = = k j i l m n = = = | -> swap(i, l) -> swap(k, l)
            # New: = = = l j k i m n = = = | -> swap(i, m) -> swap(l, m)
            # New: = = = m j k l i n = = = | -> swap(i, n) -> swap(m, n)
            # 3. Recover to initial status
            # New: = = = n j k l m i = = = | -> swap(i, n)
            # Old: = = = i j k l m n = = = 
            jobInMID = schedule[mID].traverseKey()
            # print("Start: ", mID, jobInMID, oldMakespan)
            for i in range(len(jobInMID) - 1):
                jobInMID = schedule[mID].traverseKey()
                findImproveForI = False
                jIDI = jobInMID[i]
                oldMakespan = schedule[mID].makespan
                # print("MID: %s -> Initial:" % mID, jobInMID)
                # schedule[mID].print()
                # print("MID: %s -> Try to improve by swap %s with other job" % (mID, jIDI), "oldMakespan: ", oldMakespan)
                # 1. First attempt
                jIDJ = jobInMID[i + 1]
                # print("MID: %s -> Try: " % mID, (jIDI, jIDJ))
                schedule[mID].swap(jIDI, jIDJ)
                newMakespan = schedule[mID].makespan
                if (newMakespan + CONST_EPSILON < oldMakespan):
                    canSwapFlag = True
                    findImproveForI = True
                    # print("MID: %s -> Succeed - Swap " % mID, (jIDI, jIDJ), "-", oldMakespan, "=>", newMakespan)
                    # print("MID: %s -> Succeed:" % mID, schedule[mID].traverseKey())
                    improvedFlag = True
                    if (earlyEndMakespan != None and schedule[mID].makespan < earlyEndMakespan):
                        # print("MID: %s -> Early break - second longest is now longest" % mID)
                        return improvedFlag
                # 2. Follow-up attempts
                for j in range(i + 2, len(jobInMID)):
                    if (not findImproveForI):
                        # print("MID: %s -> Try: " % mID, (jIDI, jobInMID[j]), (jobInMID[j - 1], jobInMID[j]))
                        # NOTE: LazyUpdate will increase 75% of runtime, not worthy
                        schedule[mID].swap(jIDI, jobInMID[j])
                        schedule[mID].swap(jobInMID[j - 1], jobInMID[j])                        
                        newMakespan = schedule[mID].makespan
                        if (newMakespan + CONST_EPSILON < oldMakespan):
                            canSwapFlag = True
                            findImproveForI = True
                            # print("MID: %s -> Succeed - Swap " % mID, (jIDI, jobInMID[j]), "-", oldMakespan, "=>", newMakespan)
                            # print("MID: %s -> Succeed:" % mID, schedule[mID].traverseKey())
                            improvedFlag = True
                            if (earlyEndMakespan != None and schedule[mID].makespan < earlyEndMakespan):
                                # print("MID: %s -> Early break - second longest is now longest" % mID)
                                return improvedFlag
                # 3. Recover if not improved
                if (not findImproveForI):
                    schedule[mID].swap(jIDI, jobInMID[-1])
                    # print("MID: %s -> Recover: " % mID, jobInMID)
                    # schedule[mID].print()
        return improvedFlag

    def _interMachineSwap(mIDI, mIDJ, earlyEndMakespan=None):
        improvedFlag = False
        canSwapFlag = True
        while (canSwapFlag):
            canSwapFlag = False
            oriJobMIDI = schedule[mIDI].traverseKey()
            oriJobMIDJ = schedule[mIDJ].traverseKey()
            # print("Start: ", mIDI, oriJobMIDI, schedule[mIDI].makespan)
            # print("       ", mIDJ, oriJobMIDJ, schedule[mIDJ].makespan)
            for i in range(len(oriJobMIDI) - 1, -1, -1):
                oriJobMIDI = schedule[mIDI].traverseKey()
                oriJobMIDJ = schedule[mIDJ].traverseKey()
                # print("MID: %s -> Initial:" % mIDI, oriJobMIDI)
                # print("MID: %s -> Initial:" % mIDJ, oriJobMIDJ)
                lastTryJ = None
                findImproveForI = False
                oldMakespan = max(schedule[mIDI].makespan, schedule[mIDJ].makespan)
                oldMakespanI = schedule[mIDI].makespan
                oldMakespanJ = schedule[mIDJ].makespan
                for j in range(len(oriJobMIDJ) - 1, -1, -1):
                    # Swap jobInMIDI[i] and jobInMIDJ[j]
                    trySwapFlag = True
                    # Length of two jobs should not be too unequal
                    worstTI = jobs[oriJobMIDI[i]]['worstT']
                    worstTJ = jobs[oriJobMIDJ[j]]['worstT']
                    bestTI = jobs[oriJobMIDI[i]]['bestT']
                    bestTJ = jobs[oriJobMIDJ[j]]['bestT']
                    if (worstTI > 1.5 * worstTJ 
                            or worstTJ > 1.5 * worstTI
                            or bestTI > 1.5 * bestTJ 
                            or bestTJ > 1.5 * bestTI):
                        tryImproveFlag = False
                    # Do swapping
                    if (trySwapFlag and not findImproveForI):
                        if (lastTryJ == None):
                            schedule[mIDI].replace(oriJobMIDI[i], oriJobMIDJ[j])
                            schedule[mIDJ].replace(oriJobMIDJ[j], oriJobMIDI[i])
                            lastTryJ = j
                            # print("MID: %s, %s -> Try: (%s, %s), j = %s" % (mIDI, mIDJ, oriJobMIDI[i], oriJobMIDJ[j], lastTryJ))
                            # print("MID: %s -> Tried:" % mIDI, schedule[mIDI].traverseKey())
                            # print("MID: %s -> Tried:" % mIDJ, schedule[mIDJ].traverseKey())
                        else:
                            # 对于mIDI, 上一次换入的是lastTryJ
                            schedule[mIDI].replace(oriJobMIDJ[lastTryJ], oriJobMIDJ[j])
                            # 对于mIDJ, 上一次oriJobMIDJ[lastTryJ]被换回, 第j位再次被oriJobMIDI[i]取代
                            schedule[mIDJ].replace(oriJobMIDI[i], oriJobMIDJ[lastTryJ])
                            schedule[mIDJ].replace(oriJobMIDJ[j], oriJobMIDI[i])
                            lastTryJ = j
                            # print("MID: %s, %s -> Try: (%s, %s), j = %s" % (mIDI, mIDJ, oriJobMIDI[i], oriJobMIDJ[j], lastTryJ))
                            # print("MID: %s -> Tried:" % mIDI, schedule[mIDI].traverseKey())
                            # print("MID: %s -> Tried:" % mIDJ, schedule[mIDJ].traverseKey())

                        # 若找到有进展的swap, i步进一位
                        newMakespan = max(schedule[mIDI].makespan, schedule[mIDJ].makespan)
                        # print("Makespan: %s: (%s, %s)-> %s: (%s, %s)" % (
                        #     oldMakespan, oldMakespanI, oldMakespanJ, newMakespan, schedule[mIDI].makespan, schedule[mIDJ].makespan))
                        # print("mIDI: %s" % mIDI)
                        # schedule[mIDI].print()
                        # print("mIDJ: %s" % mIDJ)
                        # schedule[mIDJ].print()
                        betterOverallMakespan = (newMakespan + CONST_EPSILON < oldMakespan)
                        betterMIDIMakespan = (schedule[mIDI].makespan < oldMakespanI 
                                            and schedule[mIDJ].makespan <= oldMakespanJ)
                        betterMIDJMakespan = (schedule[mIDI].makespan <= oldMakespanI 
                                            and schedule[mIDJ].makespan < oldMakespanJ)
                        if (betterOverallMakespan or betterMIDIMakespan or betterMIDJMakespan):
                            canSwapFlag = True
                            improvedFlag = True
                            findImproveForI = True
                            if (earlyEndMakespan != None and 
                                (schedule[mIDI].makespan < earlyEndMakespan
                                    or schedule[mIDJ].makespan < earlyEndMakespan)):
                                # print("MID: %s, %s -> Early break - second longest is now third longest" % (mIDI, mIDJ))
                                return improvedFlag
                            # print("MID: %s, %s -> Succeed:" % (mIDI, mIDJ))
                # 若无法通过更换i达到优化, 还原成oriJobMIDI, oriJobMIDJ, i步进一位
                if (not findImproveForI and lastTryJ != None):
                    schedule[mIDI].replace(oriJobMIDJ[lastTryJ], oriJobMIDI[i])
                    schedule[mIDJ].replace(oriJobMIDI[i], oriJobMIDJ[lastTryJ])
                    # print("MID: %s -> Recover:" % mIDI, schedule[mIDI].traverseKey())
                    # print("MID: %s -> Recover:" % mIDJ, schedule[mIDJ].traverseKey())
        return improvedFlag
        
    def _interMachineMove(mIDI, mIDJ, earlyEndMakespan=None):
        improvedFlag = False
        oriJobMIDI = schedule[mIDI].traverseKey()
        oriJobMIDJ = schedule[mIDJ].traverseKey()
        # print("Start: ", mIDI, oriJobMIDI, schedule[mIDI].makespan)
        # print("       ", mIDJ, oriJobMIDJ, schedule[mIDJ].makespan)
        # 一次次尝试将mIDI中的元素move到mIDJ中
        for i in range(len(oriJobMIDI)):
            oldMakespanI = schedule[mIDI].makespan
            oldMakespanJ = schedule[mIDJ].makespan
            
            # Move i from mIDI to mIDJ to see if it can improve
            schedule[mIDI].remove(oriJobMIDI[i])
            schedule[mIDJ].cheapInsert(oriJobMIDI[i])
            # print("mIDI %s: Move %s -> mIDJ： %s" % (mIDI, oriJobMIDI[i], mIDJ))
            # print("Try move: ", mIDI, schedule[mIDI].traverseKey(), schedule[mIDI].makespan)
            # print("          ", mIDJ, schedule[mIDJ].traverseKey(), schedule[mIDJ].makespan)
            newMakespanI = schedule[mIDI].makespan
            newMakespanJ = schedule[mIDJ].makespan

            if (max(newMakespanI, newMakespanJ) + CONST_EPSILON < max(oldMakespanI, oldMakespanJ)):
                # If improved, return now
                canMoveFlag = True
                improvedFlag = True
                # print("Succeed: mIDI %s: Move %s -> mIDJ： %s" % (mIDI, oriJobMIDI[i], mIDJ))
            else:
                # If not improved, recover
                if (i < len(oriJobMIDI) - 1):
                    schedule[mIDI].insert(oriJobMIDI[i + 1], oriJobMIDI[i])
                else:
                    schedule[mIDI].append(oriJobMIDI[i])
                schedule[mIDJ].remove(oriJobMIDI[i])
                # print("mIDI %s: Move %s -> mIDJ： %s" % (mIDI, oriJobMIDI[i], mIDJ))
                # print("Recover: ", mIDI, schedule[mIDI].traverseKey(), schedule[mIDI].makespan)
                # print("         ", mIDJ, schedule[mIDJ].traverseKey(), schedule[mIDJ].makespan)
        return improvedFlag

    tryImproveFlag = True
    preInterSwappedI = None
    preInterSwappedJ = None
    iterNum = 0
    while (tryImproveFlag and allowIter != 0):
        tryImproveFlag = False

        if (allowIter != None and iterNum >= allowIter):
            break
        if (earlyEndMakespan != None 
            and max([schedule[mID].makespan for mID in range(numMachine)]) < earlyEndMakespan):
            break

        if (not tryImproveFlag):
            for mID in schedule:
                worstDev = _evalWorstDev(mID)
                if (worstDev > 0.05):
                    interSwapFlag = _intraMachineSwap(mID)
                    if (interSwapFlag):
                        tryImproveFlag = True

        if (not tryImproveFlag):
            for mIDI in range(numMachine):
                for mIDJ in range(numMachine):
                    if (mIDI != mIDJ and schedule[mIDI].makespan > 1.03 * schedule[mIDJ].makespan):
                        improvedFlag = _interMachineSwap(mIDI, mIDJ)
                        if (improvedFlag):
                            tryImproveFlag = True

        if (not tryImproveFlag):
            for mIDI in range(numMachine - 1):
                for mIDJ in range(mIDI + 1, numMachine):
                    improvedFlag = _interMachineSwap(mIDI, mIDJ)
                    if (improvedFlag):
                        tryImproveFlag = True
        iterNum += 1

    curMakespan = max([schedule[mID].makespan for mID in range(numMachine)])      
    ofv = curMakespan

    return {
        'ofv': ofv,
        'schedule': schedule,
        'consOfv': consOfv,
    }