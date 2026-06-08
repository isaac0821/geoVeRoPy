import math
import heapq
import networkx as nx
from .common import *
from .geometry import *

class TriGridSurface(object):
    # @tellRuntime('gridSurface.py.__init__', indentLevel = 1)
    def __init__(self, timedPoly, startTime=None, endTime=None):
        # 初始化
        self.triFacets = {}
        self.triCenters = {}
        self.timedPoly = timedPoly
        self.startTime = timedPoly[0][1] if startTime == None else startTime
        self.endTime = timedPoly[-1][1] if endTime == None else endTime
        self.surfaceGraph = nx.Graph()

        self.buildFacets(timedPoly)
        self.extendNeighbor()

        # Total projection
        self.unionProj = self.buildUnionProfile()
        self.coreProj = self.buildCoreProfile()

        # 构造上下底面
        self.bottomPoly = None
        if (startTime == None or startTime <= timedPoly[0][1]):
            self.bottomPoly = timedPoly[0][0]
            startTime = timedPoly[0][1]
        else:
            self.bottomPoly = self.buildZProfile(startTime)
        bottom = polyTriangulation(self.bottomPoly)

        self.topPoly = None
        if (endTime == None or endTime >= timedPoly[-1][1]):
            self.topPoly = timedPoly[-1][0]
            endTime = timedPoly[-1][1]
        else:
            self.topPoly = self.buildZProfile(endTime)
        top = polyTriangulation(self.topPoly)

        self.tris = []
        for t in bottom:
            self.tris.append([
                (t[0][0], t[0][1], startTime), 
                (t[1][0], t[1][1], startTime),
                (t[2][0], t[2][1], startTime)])
        for k in self.triFacets:
            self.tris.append(self.triFacets[k])
        for t in top:
            self.tris.append([
                (t[0][0], t[0][1], endTime), 
                (t[1][0], t[1][1], endTime),
                (t[2][0], t[2][1], endTime)])
             
        return

    # @tellRuntime('gridSurface.py.buildFacets', indentLevel = 1)
    def buildFacets(self, timedPoly):
        for m in range(len(timedPoly) - 1):
            lowerPoly = [list(pt) for pt in timedPoly[m][0]]
            upperPoly = [list(pt) for pt in timedPoly[m + 1][0]]
            if (len(lowerPoly) < 3 or len(upperPoly) < 3):
                continue

            lowerArea = 0
            for i in range(len(lowerPoly)):
                lowerArea += lowerPoly[i][0] * lowerPoly[(i + 1) % len(lowerPoly)][1] - lowerPoly[(i + 1) % len(lowerPoly)][0] * lowerPoly[i][1]
            upperArea = 0
            for i in range(len(upperPoly)):
                upperArea += upperPoly[i][0] * upperPoly[(i + 1) % len(upperPoly)][1] - upperPoly[(i + 1) % len(upperPoly)][0] * upperPoly[i][1]
            if (lowerArea * upperArea < 0):
                upperPoly.reverse()

            nearestID = 0
            nearestDist = float('inf')
            for i in range(len(upperPoly)):
                d = distEuclideanXY(lowerPoly[0], upperPoly[i])
                if (d < nearestDist):
                    nearestDist = d
                    nearestID = i
            upperPoly = [upperPoly[(nearestID + i) % len(upperPoly)] for i in range(len(upperPoly))]

            lowerParams = [0]
            lowerPerim = 0
            for i in range(len(lowerPoly)):
                lowerPerim += distEuclideanXY(lowerPoly[i], lowerPoly[(i + 1) % len(lowerPoly)])
            upperParams = [0]
            upperPerim = 0
            for i in range(len(upperPoly)):
                upperPerim += distEuclideanXY(upperPoly[i], upperPoly[(i + 1) % len(upperPoly)])
            if (lowerPerim <= ERRTOL['distPt2Pt'] or upperPerim <= ERRTOL['distPt2Pt']):
                continue

            accDist = 0
            for i in range(1, len(lowerPoly)):
                accDist += distEuclideanXY(lowerPoly[i - 1], lowerPoly[i])
                lowerParams.append(accDist / lowerPerim)
            accDist = 0
            for i in range(1, len(upperPoly)):
                accDist += distEuclideanXY(upperPoly[i - 1], upperPoly[i])
                upperParams.append(accDist / upperPerim)

            params = []
            for tau in lowerParams + upperParams:
                addFlag = True
                for existTau in params:
                    if (abs(tau - existTau) <= ERRTOL['vertical']):
                        addFlag = False
                        break
                if (addFlag and tau < 1 - ERRTOL['vertical']):
                    params.append(tau)
            params = sorted(params)
            if (len(params) < 3):
                continue

            lowerSync = []
            upperSync = []
            for tau in params:
                for poly, polyParams, sync in [(lowerPoly, lowerParams, lowerSync), (upperPoly, upperParams, upperSync)]:
                    for i in range(len(poly)):
                        tau0 = polyParams[i]
                        tau1 = polyParams[i + 1] if i < len(poly) - 1 else 1
                        if (tau0 - ERRTOL['vertical'] <= tau <= tau1 + ERRTOL['vertical']):
                            ratio = 0 if abs(tau1 - tau0) <= ERRTOL['vertical'] else (tau - tau0) / (tau1 - tau0)
                            sync.append([
                                poly[i][0] + (poly[(i + 1) % len(poly)][0] - poly[i][0]) * ratio,
                                poly[i][1] + (poly[(i + 1) % len(poly)][1] - poly[i][1]) * ratio])
                            break

            ringIDs = []
            for i in range(len(params)):
                j = (i + 1) % len(params)
                triList = [
                    [(lowerSync[i][0], lowerSync[i][1], timedPoly[m][1]), (lowerSync[j][0], lowerSync[j][1], timedPoly[m][1]), (upperSync[i][0], upperSync[i][1], timedPoly[m + 1][1])],
                    [(upperSync[i][0], upperSync[i][1], timedPoly[m + 1][1]), (upperSync[j][0], upperSync[j][1], timedPoly[m + 1][1]), (lowerSync[j][0], lowerSync[j][1], timedPoly[m][1])]]
                for tri in triList:
                    if (is2PtsSame(tri[0], tri[1]) or is2PtsSame(tri[0], tri[2]) or is2PtsSame(tri[1], tri[2])):
                        continue
                    key = (m, len(ringIDs))
                    adjTo = []
                    if (len(ringIDs) > 0):
                        adjTo.append(ringIDs[-1])
                    if (i == len(params) - 1 and (m, 0) in self.triFacets):
                        adjTo.append((m, 0))
                    if (m > 0):
                        for prevID in [k for k in self.triFacets if k[0] == m - 1]:
                            sameCnt = 0
                            for a in self.triFacets[prevID]:
                                for b in tri:
                                    if (is2PtsSame(a, b)):
                                        sameCnt += 1
                            if (sameCnt == 1 or sameCnt == 2):
                                adjTo.append(prevID)
                    self.addFacet(
                        key = key,
                        adjTo = adjTo,
                        tri = tri)
                    ringIDs.append(key)

        return

    # @tellRuntime('gridSurface.py.addFacet', indentLevel = 1)
    def addFacet(self, key, adjTo, tri):
        self.surfaceGraph.add_node(key)
        self.triFacets[key] = tri
        # x, y, z是三个timedPt
        [x, y, z] = tri

        # 存入几何中心
        self.triCenters[key] = [[(x[0] + y[0] + z[0]) / 3, (x[1] + y[1] + z[1]) / 3], (x[2] + y[2] + z[2]) / 3]

        for nei in adjTo:
            # Check if a neighborhood is feasible
            adjFlag = False
            if (is2PtsSame(x, y) or is2PtsSame(y, z) or is2PtsSame(x, z)):
                raise ZeroVectorError(f"ERROR: invalid facet - {tri}")

            # 找到相同的点
            sameMat = [
                [0, 0, 0], 
                [0, 0, 0], 
                [0, 0, 0]]
            for i in range(3):
                for j in range(3):
                    if (is2PtsSame(self.triFacets[nei][i], tri[j])):
                        sameMat[i][j] += 1
            if (sum([sum(sameMat[i]) for i in range(len(sameMat))]) == 2):
                adjFlag = True
            elif (sum([sum(sameMat[i]) for i in range(len(sameMat))]) == 1):
                adjFlag = True
            else:
                raise ZeroVectorError("ERROR: facet does not match")

            self.surfaceGraph.add_edge(nei, key)

    # @tellRuntime('gridSurface.py.truncateByTime', indentLevel = 1)
    def truncateByTime(self, t):
        # Truncate from time t.
        if (t < self.timedPoly[0][1] - ERRTOL['vertical'] or t > self.timedPoly[-1][1] + ERRTOL['vertical']):
            raise OutOfRangeError("ERROR: t is out of range")

        oldTimedPoly = self.timedPoly
        newTimedPoly = []
        cutLayerID = None
        cutInBtwFlag = False
        for i in range(len(self.timedPoly)):
            if (self.timedPoly[i][1] < t - ERRTOL['vertical']):
                newTimedPoly.append(self.timedPoly[i])
            elif (abs(self.timedPoly[i][1] - t) <= ERRTOL['vertical']):
                newTimedPoly.append(self.timedPoly[i])
                cutLayerID = i
                break
            else:
                newTimedPoly.append([self.buildZProfile(t), t])
                cutLayerID = i - 1
                cutInBtwFlag = True
                break

        removeFacetIDs = []
        for facetID in self.triFacets:
            zMax = max([self.triFacets[facetID][k][2] for k in range(3)])
            if (zMax > t + ERRTOL['vertical']):
                removeFacetIDs.append(facetID)

        for facetID in removeFacetIDs:
            tri = self.triFacets[facetID]
            if (facetID in self.triFacets):
                del self.triFacets[facetID]
            if (facetID in self.triCenters):
                del self.triCenters[facetID]
            if (self.surfaceGraph.has_node(facetID)):
                self.surfaceGraph.remove_node(facetID)
            self.tris = [i for i in self.tris if i != tri]

        self.tris = [i for i in self.tris if max([j[2] for j in i]) <= t + ERRTOL['vertical']]
        self.timedPoly = newTimedPoly
        self.endTime = t

        if (cutInBtwFlag and cutLayerID != None):
            m = cutLayerID
            rebuildTimedPoly = []
            for i in range(m):
                rebuildTimedPoly.append([[], oldTimedPoly[0][1]])
            rebuildTimedPoly.append(oldTimedPoly[cutLayerID])
            rebuildTimedPoly.append(newTimedPoly[-1])
            self.buildFacets(rebuildTimedPoly)

            for facetID in self.triFacets:
                if (facetID[0] == m):
                    self.tris.append(self.triFacets[facetID])

            self.extendNeighbor()
        self.topPoly = newTimedPoly[-1][0]
        if (t > self.startTime + ERRTOL['vertical']):
            self.tris = [i for i in self.tris if min([j[2] for j in i]) < t - ERRTOL['vertical'] or max([j[2] for j in i]) > t + ERRTOL['vertical']]
        top = polyTriangulation(self.topPoly)
        for tri in top:
            self.tris.append([
                (tri[0][0], tri[0][1], t),
                (tri[1][0], tri[1][1], t),
                (tri[2][0], tri[2][1], t)])

        self.unionProj = self.buildUnionProfile()
        self.coreProj = self.buildCoreProfile()
        return

    # @tellRuntime('gridSurface.py.appendByTimedPoly', indentLevel = 1)
    def appendByTimedPoly(self, t, timedPoly):
        self.truncateByTime(t)

        if (t < timedPoly[0][1] - ERRTOL['vertical'] or t > timedPoly[-1][1] + ERRTOL['vertical']):
            raise OutOfRangeError("ERROR: t is out of range")

        appendedTimedPoly = []
        appendStartFound = False
        for i in range(len(timedPoly)):
            if (abs(timedPoly[i][1] - t) <= ERRTOL['vertical']):
                appendedTimedPoly.append(timedPoly[i])
                appendStartFound = True
            elif (timedPoly[i][1] > t + ERRTOL['vertical']):
                if (not appendStartFound):
                    oldTimedPoly = self.timedPoly
                    self.timedPoly = timedPoly
                    appendedTimedPoly.append([self.buildZProfile(t), t])
                    self.timedPoly = oldTimedPoly
                    appendStartFound = True
                appendedTimedPoly.append(timedPoly[i])

        if (len(appendedTimedPoly) == 0):
            return

        self.timedPoly[-1] = appendedTimedPoly[0]
        for i in range(1, len(appendedTimedPoly)):
            m = len(self.timedPoly) - 1
            rebuildTimedPoly = []
            for j in range(m):
                rebuildTimedPoly.append([[], self.timedPoly[0][1]])
            rebuildTimedPoly.append(self.timedPoly[-1])
            rebuildTimedPoly.append(appendedTimedPoly[i])
            self.buildFacets(rebuildTimedPoly)

            for facetID in self.triFacets:
                if (facetID[0] == m):
                    self.tris.append(self.triFacets[facetID])

            self.timedPoly.append(appendedTimedPoly[i])
        self.extendNeighbor()
        self.endTime = self.timedPoly[-1][1]
        self.topPoly = self.timedPoly[-1][0]
        if (t > self.startTime + ERRTOL['vertical']):
            self.tris = [i for i in self.tris if min([j[2] for j in i]) < t - ERRTOL['vertical'] or max([j[2] for j in i]) > t + ERRTOL['vertical']]
        top = polyTriangulation(self.topPoly)
        for tri in top:
            self.tris.append([
                (tri[0][0], tri[0][1], self.endTime),
                (tri[1][0], tri[1][1], self.endTime),
                (tri[2][0], tri[2][1], self.endTime)])
        self.unionProj = self.buildUnionProfile()
        self.coreProj = self.buildCoreProfile()
        return

    # @tellRuntime('gridSurface.py.removeUnreachableFromPt', indentLevel = 1)
    def removeUnreachableFromPt(self, pt, z, speed):
        if (speed <= 0):
            raise UnsupportedInputError("ERROR: speed must be positive")

        removeFacetIDs = []
        for facetID in self.triFacets:
            zMax = max([self.triFacets[facetID][k][2] for k in range(3)])
            if (zMax < z - ERRTOL['vertical']):
                removeFacetIDs.append(facetID)
            else:
                pt2F = self.pt2Facet(pt, z, speed, facetID)
                if (pt2F['reachable'] == "NotReachable"):
                    removeFacetIDs.append(facetID)

        for facetID in removeFacetIDs:
            tri = self.triFacets[facetID]
            if (facetID in self.triFacets):
                del self.triFacets[facetID]
            if (facetID in self.triCenters):
                del self.triCenters[facetID]
            if (self.surfaceGraph.has_node(facetID)):
                self.surfaceGraph.remove_node(facetID)
            self.tris = [i for i in self.tris if i != tri]

        filteredTris = []
        for tri in self.tris:
            horizontalFlag = all([abs(tri[k][2] - tri[0][2]) <= ERRTOL['vertical'] for k in range(3)])
            boundaryFlag = horizontalFlag and (abs(tri[0][2] - self.startTime) <= ERRTOL['vertical'] or abs(tri[0][2] - self.endTime) <= ERRTOL['vertical'])
            if (not boundaryFlag):
                filteredTris.append(tri)
            else:
                tau = tri[0][2]
                reachRadius = (tau - z) * speed
                keepFlag = reachRadius >= 0
                if (keepFlag):
                    for vertex in tri:
                        if (distEuclideanXY(pt, [vertex[0], vertex[1]]) > reachRadius + ERRTOL['distPt2Pt']):
                            keepFlag = False
                            break
                if (keepFlag):
                    filteredTris.append(tri)
        self.tris = filteredTris
        return

    # @tellRuntime('gridSurface.py.removeUnreachableToPt', indentLevel = 1)
    def removeUnreachableToPt(self, pt, z, speed):
        if (speed <= 0):
            raise UnsupportedInputError("ERROR: speed must be positive")

        removeFacetIDs = []
        for facetID in self.triFacets:
            tri = self.triFacets[facetID]
            zMin = min([tri[k][2] for k in range(3)])
            zMax = max([tri[k][2] for k in range(3)])
            if (zMin > z + ERRTOL['vertical']):
                removeFacetIDs.append(facetID)
                continue

            keepFacetFlag = False
            zLow = zMin
            zHigh = min(zMax, z)
            if (zLow <= zHigh + ERRTOL['vertical']):
                for s in range(81):
                    tau = zLow + (zHigh - zLow) * s / 80
                    crossPts = []
                    for i in range(3):
                        p0 = tri[i]
                        p1 = tri[(i + 1) % 3]
                        if (abs(p0[2] - tau) <= ERRTOL['vertical']):
                            crossPts.append([p0[0], p0[1]])
                        if ((p0[2] - tau) * (p1[2] - tau) < -ERRTOL['vertical'] ** 2):
                            ratio = (tau - p0[2]) / (p1[2] - p0[2])
                            crossPts.append([p0[0] + (p1[0] - p0[0]) * ratio, p0[1] + (p1[1] - p0[1]) * ratio])
                    uniqPts = []
                    for p in crossPts:
                        if (not any(distEuclideanXY(p, q) <= ERRTOL['distPt2Pt'] for q in uniqPts)):
                            uniqPts.append(p)
                    curDist = float('inf')
                    if (len(uniqPts) == 1):
                        curDist = distEuclideanXY(pt, uniqPts[0])
                    elif (len(uniqPts) >= 2):
                        seg = [uniqPts[0], uniqPts[1]]
                        maxDist = distEuclideanXY(uniqPts[0], uniqPts[1])
                        for i in range(len(uniqPts)):
                            for j in range(i + 1, len(uniqPts)):
                                d = distEuclideanXY(uniqPts[i], uniqPts[j])
                                if (d > maxDist):
                                    maxDist = d
                                    seg = [uniqPts[i], uniqPts[j]]
                        curDist = distPt2Seg(pt, seg)
                    if (curDist <= (z - tau) * speed + ERRTOL['distPt2Pt']):
                        keepFacetFlag = True
                        break
            if (not keepFacetFlag):
                removeFacetIDs.append(facetID)

        for facetID in removeFacetIDs:
            tri = self.triFacets[facetID]
            if (facetID in self.triFacets):
                del self.triFacets[facetID]
            if (facetID in self.triCenters):
                del self.triCenters[facetID]
            if (self.surfaceGraph.has_node(facetID)):
                self.surfaceGraph.remove_node(facetID)
            self.tris = [i for i in self.tris if i != tri]

        filteredTris = []
        for tri in self.tris:
            horizontalFlag = all([abs(tri[k][2] - tri[0][2]) <= ERRTOL['vertical'] for k in range(3)])
            boundaryFlag = horizontalFlag and (abs(tri[0][2] - self.startTime) <= ERRTOL['vertical'] or abs(tri[0][2] - self.endTime) <= ERRTOL['vertical'])
            if (not boundaryFlag):
                filteredTris.append(tri)
            else:
                tau = tri[0][2]
                reachRadius = (z - tau) * speed
                keepFlag = reachRadius >= 0
                if (keepFlag):
                    for vertex in tri:
                        if (distEuclideanXY([vertex[0], vertex[1]], pt) > reachRadius + ERRTOL['distPt2Pt']):
                            keepFlag = False
                            break
                if (keepFlag):
                    filteredTris.append(tri)
        self.tris = filteredTris
        return
    
    # @tellRuntime('gridSurface.py.extendNeighbor', indentLevel = 1)
    def extendNeighbor(self):
        # 先记录每个facetID当前的neighbor集合
        neiIDs = {}
        for facetID in self.triFacets:
            neiIDs[facetID] = list(self.surfaceGraph.neighbors(facetID))

        # 每个facetID拓展一圈出去
        for facetID in self.triFacets:
            for neiID in neiIDs[facetID]:
                for secNeiID in neiIDs[neiID]:
                    if (not self.surfaceGraph.has_edge(facetID, secNeiID) and facetID != secNeiID):
                        self.surfaceGraph.add_edge(facetID, secNeiID)

        return

    # @tellRuntime('gridSurface.py.buildZProfile', indentLevel = 1)
    def buildZProfile(self, z):
        t0 = None
        t1 = None
        for i in range(len(self.timedPoly) - 1):
            t0 = self.timedPoly[i][1]
            t1 = self.timedPoly[i + 1][1]
            if (abs(t0 - z) <= ERRTOL['vertical']):
                return self.timedPoly[i][0]
            elif (t0 <= z < t1):
                lowerPoly = [list(pt) for pt in self.timedPoly[i][0]]
                upperPoly = [list(pt) for pt in self.timedPoly[i + 1][0]]
                if (len(lowerPoly) < 3 or len(upperPoly) < 3):
                    return []

                lowerArea = 0
                for k in range(len(lowerPoly)):
                    lowerArea += lowerPoly[k][0] * lowerPoly[(k + 1) % len(lowerPoly)][1] - lowerPoly[(k + 1) % len(lowerPoly)][0] * lowerPoly[k][1]
                upperArea = 0
                for k in range(len(upperPoly)):
                    upperArea += upperPoly[k][0] * upperPoly[(k + 1) % len(upperPoly)][1] - upperPoly[(k + 1) % len(upperPoly)][0] * upperPoly[k][1]
                if (lowerArea * upperArea < 0):
                    upperPoly.reverse()

                nearestID = 0
                nearestDist = float('inf')
                for k in range(len(upperPoly)):
                    d = distEuclideanXY(lowerPoly[0], upperPoly[k])
                    if (d < nearestDist):
                        nearestDist = d
                        nearestID = k
                upperPoly = [upperPoly[(nearestID + k) % len(upperPoly)] for k in range(len(upperPoly))]

                lowerParams = [0]
                lowerPerim = 0
                for k in range(len(lowerPoly)):
                    lowerPerim += distEuclideanXY(lowerPoly[k], lowerPoly[(k + 1) % len(lowerPoly)])
                upperParams = [0]
                upperPerim = 0
                for k in range(len(upperPoly)):
                    upperPerim += distEuclideanXY(upperPoly[k], upperPoly[(k + 1) % len(upperPoly)])
                if (lowerPerim <= ERRTOL['distPt2Pt'] or upperPerim <= ERRTOL['distPt2Pt']):
                    return []

                accDist = 0
                for k in range(1, len(lowerPoly)):
                    accDist += distEuclideanXY(lowerPoly[k - 1], lowerPoly[k])
                    lowerParams.append(accDist / lowerPerim)
                accDist = 0
                for k in range(1, len(upperPoly)):
                    accDist += distEuclideanXY(upperPoly[k - 1], upperPoly[k])
                    upperParams.append(accDist / upperPerim)

                params = []
                for tau in lowerParams + upperParams:
                    addFlag = True
                    for existTau in params:
                        if (abs(tau - existTau) <= ERRTOL['vertical']):
                            addFlag = False
                            break
                    if (addFlag and tau < 1 - ERRTOL['vertical']):
                        params.append(tau)
                params = sorted(params)

                lowerSync = []
                upperSync = []
                for tau in params:
                    for poly, polyParams, sync in [(lowerPoly, lowerParams, lowerSync), (upperPoly, upperParams, upperSync)]:
                        for k in range(len(poly)):
                            tau0 = polyParams[k]
                            tau1 = polyParams[k + 1] if k < len(poly) - 1 else 1
                            if (tau0 - ERRTOL['vertical'] <= tau <= tau1 + ERRTOL['vertical']):
                                ratio = 0 if abs(tau1 - tau0) <= ERRTOL['vertical'] else (tau - tau0) / (tau1 - tau0)
                                sync.append([
                                    poly[k][0] + (poly[(k + 1) % len(poly)][0] - poly[k][0]) * ratio,
                                    poly[k][1] + (poly[(k + 1) % len(poly)][1] - poly[k][1]) * ratio])
                                break

                sc = 0 if abs(t1 - t0) <= ERRTOL['vertical'] else (z - t0) / (t1 - t0)
                poly = []
                for k in range(len(params)):
                    poly.append([
                        lowerSync[k][0] + (upperSync[k][0] - lowerSync[k][0]) * sc,
                        lowerSync[k][1] + (upperSync[k][1] - lowerSync[k][1]) * sc])
                return poly

        if (t0 == None or t1 == None):
            raise OutOfRangeError("ERROR: z is out of range")
        return self.timedPoly[-1][0]
    
    # @tellRuntime('gridSurface.py.buildUnionProfile', indentLevel = 1)
    def buildUnionProfile(self):
        poly = polysUnion(polys = [self.timedPoly[i][0] for i in range(len(self.timedPoly))])[0]
        return poly

    # @tellRuntime('gridSurface.py.buildCoreProfile', indentLevel = 1)
    def buildCoreProfile(self):
        try:
            poly = polysIntersect(polys = [self.timedPoly[i][0] for i in range(len(self.timedPoly))])[0]
            return poly
        except:
            return None

    # @tellRuntime('gridSurface.py.buildBtwCoreProfile', indentLevel = 1)
    def buildBtwCoreProfile(self, t1, t2):
        z1 = None
        z2 = None
        for i in range(len(self.timedPoly) - 1):
            tau0 = self.timedPoly[i][1]
            tau1 = self.timedPoly[i + 1][1]
            if (abs(tau0 - t1) <= ERRTOL['vertical'] or tau0 <= t1 < tau1):
                z1 = i
            if (abs(tau0 - t2) <= ERRTOL['vertical'] or tau0 <= t2 < tau1):
                z2 = i
                break
        return polysIntersect(polys = [timedPoly[i][0] for i in range(z1, z2)])[0]        

    # @tellRuntime('gridSurface.py.pt2Facet', indentLevel = 1)
    def pt2Facet(self, pt, z, vehSpeed, facetID):
        tri = self.triFacets[facetID]
        zMin = min([tri[k][2] for k in range(3)])
        zMax = max([tri[k][2] for k in range(3)])
        if (vehSpeed <= 0):
            raise UnsupportedInputError("ERROR: vehSpeed must be positive")

        zLow = max(z, zMin)

        # @tellRuntime('gridSurface.py.uniquePts', indentLevel = 2)
        def uniquePts(pts):
            uniq = []
            for p in pts:
                if (not any(distEuclideanXY(p, q) <= ERRTOL['distPt2Pt'] for q in uniq)):
                    uniq.append(p)
            return uniq

        # @tellRuntime('gridSurface.py.sliceFacet', indentLevel = 2)
        def sliceFacet(tau):
            crossPts = []
            for i in range(3):
                p0 = tri[i]
                p1 = tri[(i + 1) % 3]
                if (abs(p0[2] - tau) <= ERRTOL['vertical']):
                    crossPts.append([p0[0], p0[1]])
                if ((p0[2] - tau) * (p1[2] - tau) < -ERRTOL['vertical'] ** 2):
                    ratio = (tau - p0[2]) / (p1[2] - p0[2])
                    crossPts.append([p0[0] + (p1[0] - p0[0]) * ratio, p0[1] + (p1[1] - p0[1]) * ratio])

            uniq = uniquePts(crossPts)
            if (len(uniq) == 0):
                return None
            if (len(uniq) == 1):
                return [uniq[0], uniq[0]]

            seg = [uniq[0], uniq[1]]
            maxDist = distEuclideanXY(uniq[0], uniq[1])
            for i in range(len(uniq)):
                for j in range(i + 1, len(uniq)):
                    d = distEuclideanXY(uniq[i], uniq[j])
                    if (d > maxDist):
                        maxDist = d
                        seg = [uniq[i], uniq[j]]
            return seg

        # @tellRuntime('gridSurface.py.closestPtOnSlice', indentLevel = 2)
        def closestPtOnSlice(tau):
            seg = sliceFacet(tau)
            if (seg == None):
                return None
            if (distEuclideanXY(seg[0], seg[1]) <= ERRTOL['distPt2Pt']):
                return {
                    'pt': seg[0],
                    'dist': distEuclideanXY(pt, seg[0])
                }
            res = distPt2Seg(pt, seg, detailFlag = True)
            return {
                'pt': res['proj'],
                'dist': res['dist']
            }

        # @tellRuntime('gridSurface.py.evalTau', indentLevel = 2)
        def evalTau(tau):
            close = closestPtOnSlice(tau)
            if (close == None):
                return None
            reachable = close['dist'] <= (tau - z) * vehSpeed + ERRTOL['distPt2Pt']
            return {
                'pt': close['pt'],
                'dist': close['dist'],
                'reachable': reachable
            }

        fallback = evalTau(zMax)
        if (zMax < z - ERRTOL['vertical'] or fallback == None or fallback['reachable'] == False):
            bestPt = self.triCenters[facetID][0] if fallback == None else fallback['pt']
            bestDist = distEuclideanXY(pt, bestPt) if fallback == None else fallback['dist']
            speed = bestDist / (zMax - z) if zMax > z else float('inf')
            return {
                'dist': bestDist,
                'time': float('inf'),
                'pt': bestPt,
                'speed': speed,
                'facetID': facetID,
                'zVeh': zMax,
                'reachable': "NotReachable"
            }

        low = zLow
        high = zMax
        lowEval = evalTau(low)
        if (lowEval != None and lowEval['reachable'] == True):
            high = low
            finalEval = lowEval
        else:
            finalEval = fallback
            iterNum = 0
            while (high - low > ERRTOL['vertical'] and iterNum < 50):
                tau = (low + high) / 2
                cur = evalTau(tau)
                if (cur != None and cur['reachable'] == True):
                    high = tau
                    finalEval = cur
                else:
                    low = tau
                iterNum += 1

            finalEval = evalTau(high)
            if (finalEval == None):
                finalEval = fallback

        zVeh = high
        dist = finalEval['dist']
        bestPt = finalEval['pt']
        time = zVeh - z
        if (time <= ERRTOL['vertical']):
            speed = 0 if (dist <= ERRTOL['distPt2Pt']) else float('inf')
        else:
            speed = dist / time
        reachable = "CanGoFaster" if (speed < vehSpeed - ERRTOL['distPt2Pt']) else "ArrMaxSpeed"
        return {
            'dist': dist,
            'time': time,
            'pt': bestPt,
            'speed': speed,
            'facetID': facetID,
            'zVeh': zVeh,
            'reachable': reachable
        }

    # @tellRuntime('gridSurface.py.pt2Facet2Pt', indentLevel = 1)
    def pt2Facet2Pt(self, pt1, z1, pt2, vehSpeed, facetID):
        if (vehSpeed <= 0):
            raise UnsupportedInputError("ERROR: vehSpeed must be positive")

        tri = self.triFacets[facetID]
        zMin = min([tri[k][2] for k in range(3)])
        zMax = max([tri[k][2] for k in range(3)])

        zLow = max(z1, zMin)
        best = None

        # @tellRuntime('gridSurface.py.updateBest', indentLevel = 2)
        def updateBest(cur):
            nonlocal best
            if (cur != None and (best == None or cur['time'] < best['time'])):
                best = cur
            return

        # @tellRuntime('gridSurface.py.uniquePts', indentLevel = 2)
        def uniquePts(pts):
            uniq = []
            for p in pts:
                if (not any(distEuclideanXY(p, q) <= ERRTOL['distPt2Pt'] for q in uniq)):
                    uniq.append(p)
            return uniq

        # @tellRuntime('gridSurface.py.sliceFacet', indentLevel = 2)
        def sliceFacet(tau):
            crossPts = []
            for i in range(3):
                p0 = tri[i]
                p1 = tri[(i + 1) % 3]
                if (abs(p0[2] - tau) <= ERRTOL['vertical']):
                    crossPts.append([p0[0], p0[1]])
                if ((p0[2] - tau) * (p1[2] - tau) < -ERRTOL['vertical'] ** 2):
                    ratio = (tau - p0[2]) / (p1[2] - p0[2])
                    crossPts.append([p0[0] + (p1[0] - p0[0]) * ratio, p0[1] + (p1[1] - p0[1]) * ratio])

            uniq = uniquePts(crossPts)
            if (len(uniq) == 0):
                return None
            if (len(uniq) == 1):
                return [uniq[0], uniq[0]]

            seg = [uniq[0], uniq[1]]
            maxDist = distEuclideanXY(uniq[0], uniq[1])
            for i in range(len(uniq)):
                for j in range(i + 1, len(uniq)):
                    d = distEuclideanXY(uniq[i], uniq[j])
                    if (d > maxDist):
                        maxDist = d
                        seg = [uniq[i], uniq[j]]
            return seg

        # @tellRuntime('gridSurface.py.closestReachablePtOnSlice', indentLevel = 2)
        def closestReachablePtOnSlice(seg, tau):
            radius = max(0, (tau - z1) * vehSpeed)
            dx = seg[1][0] - seg[0][0]
            dy = seg[1][1] - seg[0][1]
            a = dx ** 2 + dy ** 2

            if (a <= ERRTOL['distPt2Pt'] ** 2):
                if (distEuclideanXY(pt1, seg[0]) <= radius + ERRTOL['distPt2Pt']):
                    return seg[0]
                return None

            fx = seg[0][0] - pt1[0]
            fy = seg[0][1] - pt1[1]
            b = 2 * (fx * dx + fy * dy)
            c = fx ** 2 + fy ** 2 - radius ** 2
            disc = b ** 2 - 4 * a * c

            if (disc < -ERRTOL['distPt2Pt']):
                if (c <= ERRTOL['distPt2Pt']):
                    tLow = 0
                    tHigh = 1
                else:
                    return None
            else:
                disc = max(0, disc)
                root1 = (-b - math.sqrt(disc)) / (2 * a)
                root2 = (-b + math.sqrt(disc)) / (2 * a)
                tLow = max(0, min(root1, root2))
                tHigh = min(1, max(root1, root2))
                if (tLow > tHigh + ERRTOL['vertical']):
                    return None

            tProj = ((pt2[0] - seg[0][0]) * dx + (pt2[1] - seg[0][1]) * dy) / a
            t = min(tHigh, max(tLow, tProj))
            return [seg[0][0] + dx * t, seg[0][1] + dy * t]

        # @tellRuntime('gridSurface.py.evalTau', indentLevel = 2)
        def evalTau(tau):
            if (tau < zLow - ERRTOL['vertical'] or tau > zMax + ERRTOL['vertical']):
                return None

            seg = sliceFacet(tau)
            if (seg == None):
                return None

            cand = closestReachablePtOnSlice(seg, tau)
            if (cand == None):
                return None

            dist1 = distEuclideanXY(pt1, cand)
            dist2 = distEuclideanXY(pt2, cand)
            time1 = tau - z1
            time2 = dist2 / vehSpeed
            totalTime = time1 + time2
            if (time1 <= ERRTOL['vertical']):
                speed1 = 0 if (dist1 <= ERRTOL['distPt2Pt']) else float('inf')
            else:
                speed1 = dist1 / time1
            return {
                'dist': dist1 + dist2,
                'time': totalTime,
                'pt': cand,
                'speed1': speed1,
                'facetID': facetID,
                'zVeh1': tau,
                'zVeh2': tau + time2,
                'reachable': "CanGoFaster" if (speed1 < vehSpeed - ERRTOL['distPt2Pt']) else "ArrMaxSpeed"
            }

        if (zLow <= zMax + ERRTOL['vertical']):
            coarseNum = 11
            if (abs(zMax - zLow) <= ERRTOL['vertical']):
                updateBest(evalTau(zLow))
            else:
                samples = []
                for s in range(coarseNum):
                    tau = zLow + (zMax - zLow) * s / (coarseNum - 1)
                    cur = evalTau(tau)
                    updateBest(cur)
                    samples.append({
                        'tau': tau,
                        'time': cur['time'] if cur != None else float('inf')
                    })

                phi = (1 + math.sqrt(5)) / 2
                refineIntervals = []
                for i in range(len(samples)):
                    preTime = samples[i - 1]['time'] if i > 0 else float('inf')
                    curTime = samples[i]['time']
                    sucTime = samples[i + 1]['time'] if i < len(samples) - 1 else float('inf')
                    if (curTime < float('inf') and curTime <= preTime and curTime <= sucTime):
                        lo = samples[max(0, i - 1)]['tau']
                        hi = samples[min(len(samples) - 1, i + 1)]['tau']
                        if (hi > lo + ERRTOL['vertical']):
                            refineIntervals.append([lo, hi])

                for interval in refineIntervals:
                    lo = interval[0]
                    hi = interval[1]
                    m1 = hi - (hi - lo) / phi
                    m2 = lo + (hi - lo) / phi
                    f1 = evalTau(m1)
                    f2 = evalTau(m2)
                    updateBest(f1)
                    updateBest(f2)
                    iterNum = 0
                    while (hi - lo > ERRTOL['vertical'] and iterNum < 50):
                        c1 = f1['time'] if f1 != None else float('inf')
                        c2 = f2['time'] if f2 != None else float('inf')
                        if (c1 <= c2):
                            hi = m2
                            m2 = m1
                            f2 = f1
                            m1 = hi - (hi - lo) / phi
                            f1 = evalTau(m1)
                            updateBest(f1)
                        else:
                            lo = m1
                            m1 = m2
                            f1 = f2
                            m2 = lo + (hi - lo) / phi
                            f2 = evalTau(m2)
                            updateBest(f2)
                        iterNum += 1

        if (best == None):
            bestPt = self.triCenters[facetID][0]
            dist1 = distEuclideanXY(pt1, bestPt)
            dist2 = distEuclideanXY(pt2, bestPt)
            speed1 = dist1 / (zMax - z1) if zMax > z1 + ERRTOL['vertical'] else float('inf')
            return {
                'dist': dist1 + dist2,
                'time': float('inf'),
                'pt': bestPt,
                'speed1': speed1,
                'facetID': facetID,
                'zVeh1': zMax,
                'zVeh2': zMax + dist2 / vehSpeed,
                'reachable': "NotReachable"
            }

        return best

    # @tellRuntime('gridSurface.py.fastestPt2Facet', indentLevel = 1)
    def fastestPt2Facet(self, pt, z, vehSpeed):
        if (vehSpeed <= 0):
            raise UnsupportedInputError("ERROR: vehSpeed must be positive")

        trace = []
        visitedFacetIDs = set()
        bestPt2F = None
        bestTime = float('inf')

        # @tellRuntime('gridSurface.py.facetLowerBound', indentLevel = 2)
        def facetLowerBound(facetID):
            tri = self.triFacets[facetID]
            zMin = min([tri[k][2] for k in range(3)])
            zMax = max([tri[k][2] for k in range(3)])
            if (zMax < z - ERRTOL['vertical']):
                return float('inf')
            poly = [[tri[k][0], tri[k][1]] for k in range(3)]
            spaceLB = distPt2Poly(pt = pt, poly = poly) / vehSpeed
            timeLB = max(0, zMin - z)
            return max(spaceLB, timeLB)

        seedLimit = 16
        seedFacetIDs = heapq.nsmallest(
            min(seedLimit, len(self.triFacets)),
            [facetID for facetID in self.triFacets],
            key = lambda facetID: (
                facetLowerBound(facetID),
                abs(self.triCenters[facetID][1] - z),
                distEuclideanXY(pt, self.triCenters[facetID][0])))

        openFacetIDs = []
        openSet = set()
        for facetID in seedFacetIDs:
            lb = facetLowerBound(facetID)
            if (lb < float('inf')):
                heapq.heappush(openFacetIDs, (lb, facetID))
                openSet.add(facetID)

        while (len(openFacetIDs) > 0):
            lb, curFacetID = heapq.heappop(openFacetIDs)
            openSet.discard(curFacetID)
            if (curFacetID in visitedFacetIDs or curFacetID not in self.triFacets):
                continue
            if (bestPt2F != None and lb >= bestTime - ERRTOL['vertical']):
                break

            visitedFacetIDs.add(curFacetID)
            cur2F = self.pt2Facet(pt, z, vehSpeed, curFacetID)
            trace.append(cur2F)
            if (cur2F['reachable'] != "NotReachable" and cur2F['time'] < bestTime):
                bestTime = cur2F['time']
                bestPt2F = cur2F

            if (self.surfaceGraph.has_node(curFacetID)):
                for facetID in self.surfaceGraph.neighbors(curFacetID):
                    if (facetID in visitedFacetIDs or facetID in openSet or facetID not in self.triFacets):
                        continue
                    lb = facetLowerBound(facetID)
                    if (lb < float('inf') and (bestPt2F == None or lb < bestTime - ERRTOL['vertical'])):
                        heapq.heappush(openFacetIDs, (lb, facetID))
                        openSet.add(facetID)

        if (bestPt2F == None):
            return {
                'reachable': False,
                'facetID': None,
                'pt': None,
                'zVeh': None,
                'speed': None,
                'time': None,
                'trace': trace
            }

        return {
            'reachable': True,
            'facetID': bestPt2F['facetID'],
            'pt': bestPt2F['pt'],
            'zVeh': bestPt2F['zVeh'],
            'speed': bestPt2F['speed'],
            'time': bestPt2F['time'],
            'trace': trace
        }

    # @tellRuntime('gridSurface.py.fastestPt2Facet2Pt', indentLevel = 1)
    def fastestPt2Facet2Pt(self, pt1, z1, pt2, vehSpeed):
        if (vehSpeed <= 0):
            raise UnsupportedInputError("ERROR: vehSpeed must be positive")

        trace = []
        visitedFacetIDs = set()
        bestPt2F = None
        bestTime = float('inf')

        # @tellRuntime('gridSurface.py.facetLowerBound', indentLevel = 2)
        def facetLowerBound(facetID):
            tri = self.triFacets[facetID]
            zMin = min([tri[k][2] for k in range(3)])
            zMax = max([tri[k][2] for k in range(3)])
            if (zMax < z1 - ERRTOL['vertical']):
                return float('inf')
            poly = [[tri[k][0], tri[k][1]] for k in range(3)]
            space1LB = distPt2Poly(pt = pt1, poly = poly) / vehSpeed
            space2LB = distPt2Poly(pt = pt2, poly = poly) / vehSpeed
            timeLB = max(0, zMin - z1)
            return max(space1LB, timeLB) + space2LB

        seedLimit = 16
        seedFacetIDs = heapq.nsmallest(
            min(seedLimit, len(self.triFacets)),
            [facetID for facetID in self.triFacets],
            key = lambda facetID: (
                facetLowerBound(facetID),
                abs(self.triCenters[facetID][1] - z1),
                distEuclideanXY(pt1, self.triCenters[facetID][0]) + distEuclideanXY(pt2, self.triCenters[facetID][0])))

        openFacetIDs = []
        openSet = set()
        for facetID in seedFacetIDs:
            lb = facetLowerBound(facetID)
            if (lb < float('inf')):
                heapq.heappush(openFacetIDs, (lb, facetID))
                openSet.add(facetID)

        while (len(openFacetIDs) > 0):
            lb, curFacetID = heapq.heappop(openFacetIDs)
            openSet.discard(curFacetID)
            if (curFacetID in visitedFacetIDs or curFacetID not in self.triFacets):
                continue
            if (bestPt2F != None and lb >= bestTime - ERRTOL['vertical']):
                break

            visitedFacetIDs.add(curFacetID)
            cur2F = self.pt2Facet2Pt(pt1, z1, pt2, vehSpeed, curFacetID)
            trace.append(cur2F)
            if (cur2F['reachable'] != "NotReachable" and cur2F['time'] < bestTime):
                bestTime = cur2F['time']
                bestPt2F = cur2F

            if (self.surfaceGraph.has_node(curFacetID)):
                for facetID in self.surfaceGraph.neighbors(curFacetID):
                    if (facetID in visitedFacetIDs or facetID in openSet or facetID not in self.triFacets):
                        continue
                    lb = facetLowerBound(facetID)
                    if (lb < float('inf') and (bestPt2F == None or lb < bestTime - ERRTOL['vertical'])):
                        heapq.heappush(openFacetIDs, (lb, facetID))
                        openSet.add(facetID)

        if (bestPt2F == None):
            return {
                'reachable': False,
                'facetID': None,
                'pt': None,
                'zVeh1': None,
                'zVeh2': None,
                'speed1': None,
                'time': None,
                'trace': None
            }

        return {
            'reachable': True,
            'facetID': bestPt2F['facetID'],
            'pt': bestPt2F['pt'],
            'zVeh1': bestPt2F['zVeh1'],
            'zVeh2': bestPt2F['zVeh2'],
            'speed1': bestPt2F['speed1'],
            'time': bestPt2F['time'],
            'trace': trace
        }

    # @tellRuntime('gridSurface.py.isPtInside', indentLevel = 1)
    def isPtInside(self, pt, z):
        zProj = self.buildZProfile(z)
        return isPtInPoly(pt, zProj)

    # @tellRuntime('gridSurface.py.dist2Seg', indentLevel = 1)
    def dist2Seg(self, pt1, z1, pt2, z2):
        overlapStart = max(min(z1, z2), self.startTime)
        overlapEnd = min(max(z1, z2), self.endTime)
        if (overlapStart > overlapEnd + ERRTOL['vertical']):
            return {
                'trespass': False,
                'trespassSemi': False,
                'dist': distPoly2Seq(seq = [pt1, pt2], poly = self.unionProj)
            }

        if (abs(z2 - z1) <= ERRTOL['vertical']):
            overlapSeg = [pt1, pt2]
        else:
            startRatio = (overlapStart - z1) / (z2 - z1)
            endRatio = (overlapEnd - z1) / (z2 - z1)
            overlapSeg = [
                [
                    pt1[0] + (pt2[0] - pt1[0]) * startRatio,
                    pt1[1] + (pt2[1] - pt1[1]) * startRatio],
                [
                    pt1[0] + (pt2[0] - pt1[0]) * endRatio,
                    pt1[1] + (pt2[1] - pt1[1]) * endRatio]]

        # Case 1: coreProfile存在，且有效时间范围内的路径穿过coreProfile，一定相交
        if (self.coreProj != None and isSegIntPoly(seg = overlapSeg, poly = self.coreProj)):
            return {
                'trespass': True,
                'trespassSemi': True,
                'dist': 0
            }

        # Case 2: [pt1, pt2]的投影没穿过unionProfile，一定不相交，这个时候距离的计算按照poly到seg的距离
        intSeg = intSeg2Poly(seg = [pt1, pt2], poly = self.unionProj)
        if (type(intSeg) != list and intSeg['status'] == 'NoCross'):
            dist = distPoly2Seq(seq = [pt1, pt2], poly = self.unionProj)
            return {
                'trespass': False,
                'trespassSemi': False,
                'dist': dist
            }

        # 把可能相交的时间段列出来
        possOverlap = []
        if (type(intSeg) == list):
            for inte in intSeg:
                if (inte['intersectType'] == 'Point'):
                    possOverlap.append([inte['intersect'], inte['intersect']])
                elif (inte['intersectType'] == 'Segment'):
                    possOverlap.append([inte['intersect'][0], inte['intersect'][1]])
        else:
            if (type(intSeg) == dict):
                if (intSeg['intersectType'] == 'Point'):
                    possOverlap.append([intSeg['intersect'], intSeg['intersect']])
                elif (intSeg['intersectType'] == 'Segment'):
                    possOverlap.append([intSeg['intersect'][0], intSeg['intersect'][1]])

        possTWs = []
        for s in possOverlap:
            dx = pt2[0] - pt1[0]
            dy = pt2[1] - pt1[1]
            segLen2 = dx ** 2 + dy ** 2
            if (segLen2 <= ERRTOL['distPt2Pt'] ** 2):
                ts = z1
                te = z1
            elif (abs(dx) >= abs(dy) and abs(dx) > ERRTOL['distPt2Pt']):
                ts = z1 + (z2 - z1) * ((s[0][0] - pt1[0]) / dx)
                te = z1 + (z2 - z1) * ((s[1][0] - pt1[0]) / dx)
            elif (abs(dy) > ERRTOL['distPt2Pt']):
                ts = z1 + (z2 - z1) * ((s[0][1] - pt1[1]) / dy)
                te = z1 + (z2 - z1) * ((s[1][1] - pt1[1]) / dy)
            else:
                ts = z1
                te = z1
            possTWs.append([ts, te])

        # 如果可能相交，相交只可能发生在投影与unionProj相交的区域，计算与时间切面的相交点
        # @tellRuntime('gridSurface.py.getPt', indentLevel = 2)
        def getPt(z):
            if (abs(z2 - z1) <= ERRTOL['vertical']):
                return (pt1[0], pt1[1])
            ptX = pt1[0] + (pt2[0] - pt1[0]) * ((z - z1) / (z2 - z1))
            ptY = pt1[1] + (pt2[1] - pt1[1]) * ((z - z1) / (z2 - z1))
            return (ptX, ptY)

        closestDist = float('inf')
        # Case 3: 简单处理，直接按切片
        # FIXME: 如果没有一个切片相交，就认为不相交
        for tpoly in self.timedPoly:
            # 先确定下在不在possTWs内，不在的话就没必要计算了
            for tw in possTWs:
                if (tw[0] <= tpoly[1] <= tw[1]):
                    pt = getPt(tpoly[1])
                    poly = tpoly[0]
                    if (isPtInPoly(pt, poly)):
                        return {
                            'trespass': True,
                            'trespassSemi': True,
                            'dist': 0
                        }
                    else:
                        dist = distPt2Poly(pt, poly)
                        if (dist < closestDist):
                            closestDist = dist
        return {
            'trespass': False,
            'trespassSemi': True,
            'dist': closestDist
        }
