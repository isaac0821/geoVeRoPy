import math
import networkx as nx
from .common import *
from .geometry import *

class TriGridSurface(object):
    def __init__(self, timedPoly):
        # 初始化
        self.triFacets = {}
        self.triCenters = {}
        self.timedPoly = timedPoly
        self.startTime = timedPoly[0][1]
        self.endTime = timedPoly[-1][1]
        self.surfaceGraph = nx.Graph()

        self.buildFacets(timedPoly)

        # Total projection
        self.z0Proj = polysUnion(polys = [timedPoly[i][0] for i in range(len(timedPoly))])[0]

    # 存入facets
    def buildFacets(self, timedPoly):
        poly3D = []
        for i in range(len(timedPoly)):
            poly3D.append([(pt[0], pt[1], timedPoly[i][1]) for pt in timedPoly[i][0]])

        # 先构造第一圈
        self.addFacet(
            key = (0, 0),
            adjTo = [],
            tri = [poly3D[0][0], poly3D[0][1], poly3D[1][0]])
        self.addFacet(
            key = (0, 1),
            adjTo = [(0, 0)],
            tri = [poly3D[1][0], poly3D[1][1], poly3D[0][1]])

        for k in range(1, len(poly3D[0]) - 1):
            self.addFacet(
                key = (0, 2 * k),
                adjTo = [(0, 2 * k - 1)],
                tri = [poly3D[0][k], poly3D[0][k + 1], poly3D[1][k]])
            self.addFacet(
                key = (0, 2 * k + 1),
                adjTo = [(0, 2 * k)],
                tri = [poly3D[1][k], poly3D[1][k + 1], poly3D[0][k + 1]])

        self.addFacet(
            key = (0, 2 * (len(poly3D[0]) - 1)),
            adjTo = [(0, 2 * (len(poly3D[0]) - 1) - 1)],
            tri = [poly3D[0][(len(poly3D[0]) - 1)], poly3D[0][0], poly3D[1][(len(poly3D[0]) - 1)]])
        self.addFacet(
            key = (0, 2 * len(poly3D[0]) - 1),
            adjTo = [(0, 2 * (len(poly3D[0]) - 1)), (0, 0)],
            tri = [poly3D[1][(len(poly3D[0]) - 1)], poly3D[1][0], poly3D[0][0]])

        # 从第二圈开始垒
        for m in range(1, len(poly3D) - 1):
            self.addFacet(
                key = (m, 0),
                adjTo = [(m - 1, 1)],
                tri = [poly3D[m][0], poly3D[m][1], poly3D[m + 1][0]])
            self.addFacet(
                key = (m, 1),
                adjTo = [(m, 0)],
                tri = [poly3D[m + 1][0], poly3D[m + 1][1], poly3D[m][1]])

            for k in range(1, len(poly3D[m]) - 1):
                self.addFacet(
                    key = (m, 2 * k),
                    adjTo = [(m, 2 * k - 1), (m - 1, 2 * k + 1)],
                    tri = [poly3D[m][k], poly3D[m][k + 1], poly3D[m + 1][k]])
                self.addFacet(
                    key = (m, 2 * k + 1),
                    adjTo = [(m, 2 * k)],
                    tri = [poly3D[m + 1][k], poly3D[m + 1][k + 1], poly3D[m][k + 1]])

            self.addFacet(
                key = (m, 2 * (len(poly3D[m]) - 1)),
                adjTo = [(m, 2 * (len(poly3D[m]) - 1) - 1), (m - 1, 2 * (len(poly3D[m]) - 1) + 1)],
                tri = [poly3D[m][(len(poly3D[m]) - 1)], poly3D[m][0], poly3D[m + 1][(len(poly3D[m]) - 1)]])
            self.addFacet(
                key = (m, 2 * len(poly3D[m]) - 1),
                adjTo = [(m, 2 * (len(poly3D[m]) - 1)), (m, 0)],
                tri = [poly3D[m + 1][(len(poly3D[m]) - 1)], poly3D[m + 1][0], poly3D[m][0]])

        return

    # 存入一个facet
    def addFacet(self, key, adjTo, tri):
        self.surfaceGraph.add_node(key)
        self.triFacets[key] = tri
        [x, y, z] = tri
        self.triCenters[key] = [[(x[0] + y[0] + z[0]) / 3, (x[1] + y[1] + z[1]) / 3], max(x[2], y[2], z[2])]

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

    # 给定截面高度，返回截面
    def buildZProfile(self, z):
        segs = []
        poly = []
        t0 = None
        t1 = None
        # 找到z的位置上下两层poly
        for i in range(len(self.timedPoly) - 1):
            t0 = self.timedPoly[i][1]
            t1 = self.timedPoly[i + 1][1]
            if (abs(t0 - z) <= ERRTOL['vertical']):
                return self.timedPoly[i][0]
            elif (t0 <= z < t1):
                segs.append([self.timedPoly[i][0][0], self.timedPoly[i + 1][0][0]])
                for k in range(1, len(self.timedPoly[i][0])):
                    segs.append([self.timedPoly[i][0][k], self.timedPoly[i + 1][0][k]])
                    segs.append([self.timedPoly[i][0][k], self.timedPoly[i + 1][0][k - 1]])
                segs.append([self.timedPoly[i][0][0], self.timedPoly[i + 1][0][-1]])
        
                sc = (z - t0) / (t1 - t0)
                for s in segs:
                    poly.append([s[0][0] + (s[1][0] - s[0][0]) * sc, s[0][1] + (s[1][1] - s[0][1]) * sc])
                break
        if (t0 == None or t1 == None):
            raise OutOfRangeError("ERROR: z is out of range")
        return poly

    # 对于给定的时空上的点，找到最快速度可以到达的最近的facet
    def fastestPt2Facet(self, pt, z, vehSpeed):
        knownFacetIDs = []

        # Find initial facet ==================================================
        # 先找到一个可行的点，假如存在的话，至少找到一个好的开始点
        # NOTE: 先找到位于这个平面上的最近的facet，此时需要的速度是无限大
        # NOTE: 从(0, z对应的layer)搜起
        # FIXME: 应该从更近的点开始搜索，这里图了个省事儿
        # FIXME: 接下来应该预估在哪里碰到
        idx = None
        for i in range(len(self.timedPoly) - 1):
            t0 = self.timedPoly[i][1]
            t1 = self.timedPoly[i + 1][1]
            if (abs(t0 - z) <= ERRTOL['vertical'] or t0 <= z < t1):
                idx = i
                break
        tptOri = [pt, z]

        trace = []
        
        # Start greedy search =================================================
        curFacetID = (idx, 0)
        tptCur = self.triCenters[curFacetID]
        curT2T = distTpt2Tpt(tptOri, tptCur)
        knownFacetIDs.append(curFacetID)

        trace.append(tptCur)

        # Rough search ========================================================
        # 然后在表面上进行搜索，粗搜索，按照facet的中间点确定距离
        # FIXME: 找第一个局部最优解...
        canImproveFlag = True
        while (canImproveFlag):
            canImproveFlag = False

            # 找到所有相邻的facetID
            adjFacetIDs = [i for i in self.surfaceGraph.neighbors(curFacetID)]
            lstNeiT2T = []

            # 对于每个adjFacet，得比当前好且没有被覆盖到过才有必要写入
            for k in adjFacetIDs:
                # 首先得是没搜索过的
                if (k not in knownFacetIDs and self.triCenters[k][1] >= tptOri[1]):
                    t2t = distTpt2Tpt(tptOri, self.triCenters[k])
                    t2t['facetID'] = k

                    # 接下来判断是不是比当前的好
                    keepFlag = False
                    # Case 1: 当前的不可行，邻居可行，保存
                    if (t2t['speed'] <= vehSpeed and curT2T['speed'] > vehSpeed):
                        keepFlag = True
                    # Case 2: 当前的可行，邻居可行，且时间更短，保存
                    elif (t2t['speed'] <= vehSpeed and t2t['time'] <= curT2T['time'] and t2t['dist'] < curT2T['dist']):
                        keepFlag = True
                    elif (t2t['speed'] <= vehSpeed and t2t['dist'] <= curT2T['dist'] and t2t['time'] <= curT2T['time']):
                        keepFlag = True
                    # Case 3: 都不可行，且距离更短，保存
                    elif (curT2T['speed'] > vehSpeed and t2t['speed'] > vehSpeed and t2t['dist'] < curT2T['dist']):
                        keepFlag = True

                    if (keepFlag):
                        lstNeiT2T.append(t2t)
                        knownFacetIDs.append(k)

            if (len(lstNeiT2T) > 0):
                hasFeasibleFlag = False
                # 如果其中有一个可行解，就移除所有不可行解，找到可行解中时间最短的，然后在时间最短的中找到距离最短的
                lstNeiT2T = sorted(lstNeiT2T, key = lambda d:d['time'])
                for i in range(len(lstNeiT2T)):
                    if (lstNeiT2T[i]['speed'] <= vehSpeed):
                        hasFeasibleFlag = True
                        curFacetID = lstNeiT2T[i]['facetID']
                        break
                # 如果其中每个解都不可行，那就找到所有不可行解中速度最慢的，然后找到速度最慢的中距离最短的，尽可能快的到达可行域
                if (not hasFeasibleFlag):
                    lstNeiT2T = sorted(lstNeiT2T, key = lambda d:d['speed'])
                    curFacetID = lstNeiT2T[0]['facetID']
                canImproveFlag = True

                tptCur = self.triCenters[curFacetID]
                curT2T = distTpt2Tpt(tptOri, tptCur)
                trace.append(tptCur)

        # Detail search =======================================================
        # 细搜索，在找到的facet上找确定的点
        # 第一步，确定可行域的边界
        pass
        
        return {
            'facetID': curFacetID,
            'tpt': tptCur,
            'speed': curT2T['speed'],
            'time': curT2T['time'],
            'trace': trace
        }

    # 对于给定的时空上的一个点，作为起点，再给定空间中的一个点，作为终点，找到按照最快速度下最短时间内可以到达的最近facet
    def fastestPt2Facet2Pt(self, startPt, endPt, startZ, vehSpeed):

        return {
            'facetID': facetID,
            'ptOnFacet': ptOnFacet
        }

    def isPtInside(self, pt, z):
        zProj = self.buildZProfile(z)
        return isPtInPoly(pt, zProj)

def distTpt2Tpt(timedPt1, timedPt2):
    dist = distEuclideanXY(timedPt1[0], timedPt2[0])
    dt = timedPt2[1] - timedPt1[1]
    speed = None
    if (dt > 0):
        speed = dist / dt
    else:
        speed = float('inf')
    return {
        'dist': dist,
        'time': dt,
        'speed': speed
    }
