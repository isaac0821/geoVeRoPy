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
        self.triCenters[key] = ((x[0] + y[0] + z[0]) / 3, (x[1] + y[1] + z[1]) / 3, (x[2] + y[2] + z[2]) / 3)
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
    def fastestPt2Facet(self, pt, z):
        # 先找到一个可行的点，假如存在的话
        # NOTE: 先找到位于这个平面上的最近的facet，此时需要的速度是无限大
        # NOTE: 从(0, z对应的layer)搜起
        
        idx = None
        t0 = None
        t1 = None
        for i in range(len(self.timedPoly) - 1):
            t0 = self.timedPoly[i][1]
            t1 = self.timedPoly[i + 1][1]
            if (abs(t0 - z) <= ERRTOL['vertical'] or t0 <= z < t1):
                idx = i
                break

        # greedy search for the best facet
        curFacetID = (0, idx)
        curSpeed = None
        curDist = None

        # 然后在表面上进行搜索，粗搜索，按照facet的中间点确定距离
        # NOTE: 找局部最优解...


        # 细搜索，在找到的facet上找确定的点
        
        return ptOnFacet

    # 对于给定的时空上的一个点，作为起点，再给定空间中的一个点，作为终点，找到按照最快速度下最短时间内可以到达的最近facet
    def fastestPt2Facet2Pt(self, startPt, z, endPt):

        return {
            'facetID': facetID,
            'ptOnFacet': ptOnFacet
        }

    def isPtInside(self, pt, z):
        zProj = self.buildZProfile(z)
        return isPtInPoly(pt, zProj)

    def isPtReachable(self, pt, z, vehSpeed):
        # 粗略的做法，二分查找是否剖面相交
        t = z        

        return

def distTimedPt2timedPt(timedPt1, timedPt2, detailFlag = True):
    dist = distEuclidean(timedPt1[0], timedPt2[0])
    dt = timedPt2[1] - timedPt1[1]
    speed = None
    if (dt <= 0):
        speed = None
    else:
        speed = dist / dt
    return {
        'dist': dist,
        'speed': speed
    }

def shortestPt2TriGridSurface(pt, triGridSurface, vehSpeed, startZ = 0):
    

    

def pt2TriGridSurface2Pt(startPt, triGridSurface, endPt, vehSpeed, startZ = 0):
    return