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
        self.extendNeighbor()

        # Total projection
        self.unionProj = self.buildUnionProfile()
        self.coreProj = self.buildCoreProfile()

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

    def buildUnionProfile(self):
        poly = polysUnion(polys = [self.timedPoly[i][0] for i in range(len(self.timedPoly))])[0]
        return poly

    def buildCoreProfile(self):
        poly = polysIntersect(polys = [self.timedPoly[i][0] for i in range(len(self.timedPoly))])[0]
        return poly

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

    def pt2Facet(self, pt, z, vehSpeed, facetID):
        # Step 1: 计算水平方向距离
        dist = distEuclideanXY(pt, self.triCenters[facetID][0])
        
        # Step 2: 计算按照最快速度需要的时间
        time = dist / vehSpeed
        speed = vehSpeed

        # Step 3: 计算facet对应的最早和最晚的z
        zMin = min([self.triFacets[facetID][k][2] for k in range(3)])
        zMax = max([self.triFacets[facetID][k][2] for k in range(3)])
        
        # Step 4: 计算近似在facet上的点
        zVeh = z + time
        
        # Step 5: 判断到达需要的速度
        reachable = None        
        if (zVeh < zMin):
            # Case 1: zVeh < zMin，说明到达facet不需要按照最快速度
            reachable = "CanGoFaster"
            zVeh = zMin
            speed = dist / (zMin - z)
            time = dist / speed

        elif (zMin <= zVeh <= zMax):
            # Case 2: zMin <= zVeh <= zMax，说明到达facet正好需要按照最快速度到达
            reachable = "ArrMaxSpeed"

        elif (zMax < zVeh):
            # Case 3: zMax < zVeh，说明最大速度也到达不了
            reachable = "NotReachable"
            zVeh = zMax
            if (zMax > z):
                speed = dist / (zMax - z)
                time = dist / speed
            else:
                speed = float('inf')
                time = float('inf')

        return {
            'dist': dist,
            'time': time,
            'pt': self.triCenters[facetID][0],
            'speed': speed,
            'facetID': facetID,
            'zVeh': zVeh,
            'reachable': reachable
        }

    def pt2Facet2Pt(self, pt1, z1, pt2, vehSpeed, facetID):
        # NOTE: 其实和pt2Facet一样，只是多了一段

        # Step 1: 计算水平方向距离，这两段距离都不会变化
        dist1 = distEuclideanXY(pt1, self.triCenters[facetID][0])
        dist2 = distEuclideanXY(pt2, self.triCenters[facetID][0])
        dist = dist1 + dist2
        
        # Step 2: 计算按照最快速度需要的时间
        time1 = dist1 / vehSpeed
        time2 = dist2 / vehSpeed
        time = time1 + time2

        speed1 = vehSpeed
        speed2 = vehSpeed # 注意，speed2 永远不需要改变，但zVeh2可能会变

        # Step 3: 计算facet对应的最早和最晚的z
        zMin = min([self.triFacets[facetID][k][2] for k in range(3)])
        zMax = max([self.triFacets[facetID][k][2] for k in range(3)])
        
        # Step 4: 计算近似在facet上的点是zVeh1
        zVeh1 = z1 + time1
        zVeh2 = zVeh1 + time2
        
        # Step 5: 判断到达需要的速度
        reachable = None

        if (zVeh1 < zMin):
            # Case 1: zVeh < zMin，说明到达facet不需要按照最快速度，第一段变慢了，第二段还是最快速度
            reachable = "CanGoFaster"
            
            speed1 = dist1 / (zMin - z1)
            time1 = dist1 / speed1
            time = time1 + time2

            zVeh1 = zMin
            zVeh2 = zVeh1 + time2

        elif (zMin <= zVeh1 <= zMax):
            # Case 2: zMin <= zVeh <= zMax，说明到达facet正好需要按照最快速度到达
            reachable = "ArrMaxSpeed"

        elif (zMax < zVeh1):
            # Case 3: zMax < zVeh，说明最大速度也到达不了
            reachable = "NotReachable"
            zVeh1 = zMax
            zVeh2 = zVeh1 + time2
            if (zMax > z1):
                speed1 = dist1 / (zMax - z1)
                time1 = dist1 / speed1
                time = time1 + time2
            else:
                speed1 = float('inf')
                time = float('inf')

        return {
            'dist': dist,
            'time': time,
            'pt': self.triCenters[facetID][0],
            'speed1': speed1,
            'facetID': facetID,
            'zVeh1': zVeh1,
            'zVeh2': zVeh2,
            'reachable': reachable
        }

    def fastestPt2Facet(self, pt, z, vehSpeed):
        tabuFacetIDs = []

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

        trace = []
        
        # Start greedy search =================================================
        curFacetID = (idx, 0)
        cur2F = self.pt2Facet(pt, z, vehSpeed, curFacetID)
        tabuFacetIDs.append(curFacetID)
        trace.append(cur2F)

        # Initialize search tree ==============================================
        searchTree = Tree()
        searchTree.insert(TreeNode(key = curFacetID, value = cur2F, openFlag = True))
        curTreeNode = searchTree.root

        bestFacetID = None
        bestTime = float('inf')

        # Rough search ========================================================
        # 然后在表面上进行搜索，粗搜索，按照facet的中间点确定距离
        # FIXME: 找第一个局部最优解...
        canImproveFlag = True
        while (canImproveFlag):
            canImproveFlag = False

            # 找到curFacetID所有相邻的facetID
            adjFacetIDs = [i for i in self.surfaceGraph.neighbors(curTreeNode.value['facetID'])]
            lstNei2F = []
            # 对于每个adjFacet，得比当前好且没有被覆盖到过才有必要写入，对于有必要写入的，加入子节点
            for k in adjFacetIDs:
                # 首先得是没搜索过的，搜索过的在searchTree上以及有了
                if (k not in tabuFacetIDs and self.triCenters[k][1] >= z):
                    pt2F = self.pt2Facet(pt, z, vehSpeed, k)

                    # 接下来判断是不是比当前的好
                    keepFlag = True
                    
                    # # Case 1: 当前的不可行，邻居也不可行，保存距离短的，距离一样的，保存z更大的
                    # if (cur2F['reachable'] == "NotReachable" and pt2F["reachable"] == "NotReachable"):
                    #     if (cur2F['dist'] > pt2F['dist']):
                    #         keepFlag = True
                    #     elif (cur2F['zVeh'] < pt2F['zVeh']):
                    #         keepFlag = True

                    # # Case 2: 当前的不可行，邻居可行，保存
                    # elif (cur2F['reachable'] == "NotReachable" and pt2F["reachable"] != "NotReachable"):
                    #     keepFlag = True
                    
                    # # Case 3: 当前的速度慢但可达，邻居也可达，保存速度快的
                    # elif (cur2F['reachable'] == "CanGoFaster" and pt2F["reachable"] == "ArrMaxSpeed"):
                    #     keepFlag = True
                    # elif (cur2F['reachable'] == "CanGoFaster" and pt2F["reachable"] == "CanGoFaster"):
                    #     if (cur2F['speed'] < pt2F['speed']):
                    #         keepFlag = True
                    # elif (cur2F['reachable'] == "ArrMaxSpeed" and pt2F["reachable"] == "ArrMaxSpeed"):
                    #     if (cur2F['dist'] > pt2F['dist']):
                    #         keepFlag = True

                    # 如果比当前这个好，那么加入，在searchTree上作为当前的子节点
                    if (keepFlag):
                        tabuFacetIDs.append(k)
                        lstNei2F.append(pt2F)                                               

            # 把所有的可能的邻居排序，按照时间
            if (len(lstNei2F) > 0):
                # 排序的顺序：先按照ArrMaxSpeed => CanGoFast => NotReachable排
                arr = [i for i in lstNei2F if i['reachable'] == 'ArrMaxSpeed']
                cgf = [i for i in lstNei2F if i['reachable'] == 'CanGoFaster']
                nrb = [i for i in lstNei2F if i['reachable'] == 'NotReachable']

                arr = sorted(arr, key = lambda d: d['time'])                   # ArrMaxSpeed按照时间排列，因为都已经是最快速度了
                cgf = sorted(cgf, key = lambda d: d['speed'], reverse = True)  # CanGoFaster按照速度排列，速度快的更好
                nrb = sorted(nrb, key = lambda d: d['zVeh'], reverse = True)                   # NotReachable按照dist排列，离得越近越好

                lstNei2F = [i for i in arr]
                lstNei2F.extend([i for i in cgf])
                lstNei2F.extend([i for i in nrb])

                for n in lstNei2F:
                    # print("New Child: ", n)
                    neiTreeNode = TreeNode(key = n['facetID'], value = n, openFlag = True)
                    searchTree.insert(neiTreeNode, curTreeNode)
                    if (n['reachable'] != "NotReachable" and n['time'] <= bestTime):
                        bestTime = n['time']
                        bestFacetID = n['facetID']

            # 如果curTreeNode有open的子节点，按深度优先尝试第一个open的子节点
            hasOpenChildFlag = False
            if (len(curTreeNode.treeNodes) > 0):
                for child in curTreeNode.treeNodes:
                    if (not child.isNil and child.openFlag == True):
                        trace.append(child.value.copy())
                        curTreeNode = child
                        # print(curTreeNode.value['time'], curTreeNode.value['speed'], curTreeNode.value['dist'])
                        # print("Go Deeper: ", curTreeNode.value['facetID'])
                        cur2F = curTreeNode.value
                        hasOpenChildFlag = True
                        canImproveFlag = True
                        break

            if (not hasOpenChildFlag):
                curTreeNode.openFlag = False
                if (curTreeNode.parent.isNil):
                    canImproveFlag = False
                else:
                    curTreeNode = curTreeNode.parent
                    # print(curTreeNode.value['time'], curTreeNode.value['speed'], curTreeNode.value['dist'])
                    # print("Backtrack: ", curTreeNode.value['facetID'])
                    cur2F = curTreeNode.value

        bestNode = searchTree.query(bestFacetID)
        
        return {
            'facetID': bestNode.value['facetID'],
            'pt': bestNode.value['pt'],
            'zVeh': bestNode.value['zVeh'],
            'speed': bestNode.value['speed'],
            'time': bestNode.value['time'],
            'trace': trace
        }

    def fastestPt2Facet2Pt(self, pt1, z1, pt2, vehSpeed):
        tabuFacetIDs = []

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
            if (abs(t0 - z1) <= ERRTOL['vertical'] or t0 <= z1 < t1):
                idx = i
                break

        trace = []
        
        # Start greedy search =================================================
        curFacetID = (idx, 0)
        cur2F = self.pt2Facet2Pt(pt1, z1, pt2, vehSpeed, curFacetID)
        tabuFacetIDs.append(curFacetID)
        trace.append(cur2F)

        # Initialize search tree ==============================================
        searchTree = Tree()
        searchTree.insert(TreeNode(key = curFacetID, value = cur2F, openFlag = True))
        curTreeNode = searchTree.root

        bestFacetID = None
        bestTime = float('inf')

        # Rough search ========================================================
        # 然后在表面上进行搜索，粗搜索，按照facet的中间点确定距离
        # FIXME: 找第一个局部最优解...
        canImproveFlag = True
        while (canImproveFlag):
            canImproveFlag = False

            # 找到curFacetID所有相邻的facetID
            adjFacetIDs = [i for i in self.surfaceGraph.neighbors(curTreeNode.value['facetID'])]
            lstNei2F = []
            # 对于每个adjFacet，得比当前好且没有被覆盖到过才有必要写入，对于有必要写入的，加入子节点
            for k in adjFacetIDs:
                # 首先得是没搜索过的，搜索过的在searchTree上以及有了
                if (k not in tabuFacetIDs and self.triCenters[k][1] >= z1):
                    pt2F = self.pt2Facet2Pt(pt1, z1, pt2, vehSpeed, k)

                    # 接下来判断是不是比当前的好
                    keepFlag = True
                    
                    # # Case 1: 当前的不可行，邻居也不可行，保存距离短的，距离一样的，保存z更大的
                    # if (cur2F['reachable'] == "NotReachable" and pt2F["reachable"] == "NotReachable"):
                    #     if (cur2F['dist'] > pt2F['dist']):
                    #         keepFlag = True
                    #     elif (cur2F['zVeh2'] < pt2F['zVeh2']):
                    #         keepFlag = True

                    # # Case 2: 当前的不可行，邻居可行，保存
                    # elif (cur2F['reachable'] == "NotReachable" and pt2F["reachable"] != "NotReachable"):
                    #     keepFlag = True
                    
                    # # Case 3: 当前的速度慢但可达，邻居也可达，保存速度快的
                    # elif (cur2F['reachable'] == "CanGoFaster" and pt2F["reachable"] == "ArrMaxSpeed"):
                    #     keepFlag = True
                    # elif (cur2F['reachable'] == "CanGoFaster" and pt2F["reachable"] == "CanGoFaster"):
                    #     if (cur2F['speed1'] < pt2F['speed1']):
                    #         keepFlag = True
                    # elif (cur2F['reachable'] == "ArrMaxSpeed" and pt2F["reachable"] == "ArrMaxSpeed"):
                    #     if (cur2F['dist'] > pt2F['dist']):
                    #         keepFlag = True

                    # 如果比当前这个好，那么加入，在searchTree上作为当前的子节点
                    if (keepFlag):
                        tabuFacetIDs.append(k)
                        lstNei2F.append(pt2F)                                               

            # 把所有的可能的邻居排序，按照时间
            if (len(lstNei2F) > 0):
                # 排序的顺序：先按照ArrMaxSpeed => CanGoFast => NotReachable排
                arr = [i for i in lstNei2F if i['reachable'] == 'ArrMaxSpeed']
                cgf = [i for i in lstNei2F if i['reachable'] == 'CanGoFaster']
                nrb = [i for i in lstNei2F if i['reachable'] == 'NotReachable']

                arr = sorted(arr, key = lambda d: d['time'])                   # ArrMaxSpeed按照时间排列，因为都已经是最快速度了
                cgf = sorted(cgf, key = lambda d: d['speed1'], reverse = True)  # CanGoFaster按照速度排列，速度快的更好
                nrb = sorted(nrb, key = lambda d: d['zVeh1'], reverse = True)                   # NotReachable按照dist排列，离得越近越好

                lstNei2F = [i for i in arr]
                lstNei2F.extend([i for i in cgf])
                lstNei2F.extend([i for i in nrb])

                for n in lstNei2F:
                    neiTreeNode = TreeNode(key = n['facetID'], value = n, openFlag = True)
                    searchTree.insert(neiTreeNode, curTreeNode)
                    if (n['reachable'] != "NotReachable" and n['time'] <= bestTime):
                        bestTime = n['time']
                        bestFacetID = n['facetID']

            # 如果curTreeNode有open的子节点，按深度优先尝试第一个open的子节点
            hasOpenChildFlag = False
            if (len(curTreeNode.treeNodes) > 0):
                for child in curTreeNode.treeNodes:
                    if (not child.isNil and child.openFlag == True):
                        trace.append(child.value.copy())
                        curTreeNode = child
                        # print(curTreeNode.value['time'], curTreeNode.value['speed1'], curTreeNode.value['dist'])
                        # print("Go Deeper: ", curTreeNode.value['facetID'])
                        cur2F = curTreeNode.value
                        hasOpenChildFlag = True
                        canImproveFlag = True
                        break

            if (not hasOpenChildFlag):
                curTreeNode.openFlag = False
                if (curTreeNode.parent.isNil):
                    canImproveFlag = False
                else:
                    curTreeNode = curTreeNode.parent
                    # print(curTreeNode.value['time'], curTreeNode.value['speed1'], curTreeNode.value['dist'])
                    # print("Backtrack: ", curTreeNode.value['facetID'])
                    cur2F = curTreeNode.value

        bestNode = searchTree.query(bestFacetID)
        
        return {
            'facetID': bestNode.value['facetID'],
            'pt': bestNode.value['pt'],
            'zVeh1': bestNode.value['zVeh1'],
            'zVeh2': bestNode.value['zVeh2'],
            'speed1': bestNode.value['speed1'],
            'time': bestNode.value['time'],
            'trace': trace
        }

    def isPtInside(self, pt, z):
        zProj = self.buildZProfile(z)
        return isPtInPoly(pt, zProj)

    def dist2Seg(self, pt1, z1, pt2, z2):
        # Case 1: [pt1, pt2]的投影穿过了coreProfile，一定相交
        if (isSegIntPoly(seg = [pt1, pt2], poly = self.coreProj)):
            return {
                'trespass': True,
                'trespassSemi': True,
                'dist': 0
            }

        # Case 2: [pt1, pt2]的投影没穿过unionProfile，一定不相交，这个时候距离的计算按照poly到seg的距离
        intSeg = intSeg2Poly(seg = [pt1, pt2], poly = self.unionProj)
        if (intSeg['status'] == 'NoCross'):
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
            ts = z1 + (z2 - z1) * ((s[0][0] - pt1[0]) / (pt2[0] - pt1[0]))
            te = z1 + (z2 - z1) * ((s[1][0] - pt1[0]) / (pt2[0] - pt1[0]))
            possTWs.append([ts, te])

        # 如果可能相交，相交只可能发生在投影与unionProj相交的区域，计算与时间切面的相交点
        def getPt(z):
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
                        if (dist <= ERRTOL['distPt2Poly']):
                            return {
                            'trespass': True,
                            'trespassSemi': True,
                            'dist': 0
                        }
                        if (dist < closestDist):
                            closestDist = dist
        return {
            'trespass': False,
            'trespassSemi': True,
            'dist': closestDist
        }
