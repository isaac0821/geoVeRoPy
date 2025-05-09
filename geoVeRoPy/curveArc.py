import math

from .ring import *
from .geometry import *
from .common import *

class CurveArcNode(object):
    def __init__(self, key, loc, deg, center, prev=None, next=None):
        self.key = key # key的值具体是多少不重要，只要可以通过prev和next检索到就行
        self.loc = loc
        self.deg = deg
        self.center = center
        self.prev = prev if prev != None else CurveArcNilNode()
        self.next = next if next != None else CurveArcNilNode()

    @property
    def isNil(self):
        return False

class CurveArcNilNode(CurveArcNode):
    def __init__(self):
        return

    @property
    def isNil(self):
        return True

class CurveArc(object):
    def __init__(self, center, radius, startDeg, endDeg, lod = 12):
        # 这里是顺时针， startDeg一定要小于endDeg，如果endDeg跨过了0°，就加上360°
        self.center = center
        self.radius = radius
        self.startDeg = startDeg
        self.endDeg = endDeg

        # 初始化生成一系列的curveArcNode，至少3个，按照lod生成
        if (lod < 2):
            lod = 2

        # 先生成一个列表的CurveArcNode
        cvNodeList = []
        for i in range(lod + 1):
            d = startDeg + i * (endDeg - startDeg) / lod
            cvNodeList.append(CurveArcNode(
                key = i,
                loc = ptInDistXY(self.center, d, self.radius),
                deg = d,
                center = self.center,
                prev = None,
                next = None
            ))        

        for i in range(len(cvNodeList) - 1):
            cvNodeList[i].next = cvNodeList[i + 1]
        for i in range(1, len(cvNodeList)):
            cvNodeList[i].prev = cvNodeList[i - 1]

        self._count = len(cvNodeList)

        self.head = cvNodeList[0]
        self.tail = cvNodeList[-1]

    def getLineString(self, lod = 60):
        locs = []
        for i in range(lod + 1):
            d = self.startDeg + i * (self.endDeg - self.startDeg) / lod
            locs.append(ptInDistXY(self.center, d, self.radius))
        return shapely.LineString(locs)

    def query(self, key) -> "CurveArcNode":
        if (self.head.isNil):
            raise EmptyError("ERROR: The CurveArc is empty.")
        cur = self.head
        queried = 0
        while (not cur.isNil):
            if (cur.key == key):
                return cur
            else:
                cur = cur.next
                queried += 1
                if (queried > self._count):
                    raise OutOfRangeError("ERROR: Unexpected loop")
        return CurveArcNilNode()

    @property
    def count(self):
        return self._count

    def traverse(self) -> list:
        cvNodes = []
        cur = self.head
        while (not cur.isNil):
            if (len(cvNodes) > self._count):
                raise OutOfRangeError("ERROR: Unexpected loop")
            cvNodes.append(cur)
            cur = cur.next

        return cvNodes

    def insertAround(self, n):
        # 给定一个CurveArcNode，在前方和后方分别插入一个CurveArcNode

        if (not n.prev.isNil):
            newDeg = n.prev.deg + (n.deg - n.prev.deg) / 2

            newCurveArcPrev = CurveArcNode(
                key = self._count + 1,
                loc = ptInDistXY(self.center, newDeg, self.radius),
                deg = newDeg,
                center = self.center)

            nPrev = n.prev
            nPrev.next = newCurveArcPrev
            newCurveArcPrev.prev = nPrev
            newCurveArcPrev.next = n
            n.prev = newCurveArcPrev

            self._count += 1

        if (not n.next.isNil):
            newDeg = n.deg + (n.next.deg - n.deg) / 2

            newCurveArcNext = CurveArcNode(
                key = self._count + 1,
                loc = ptInDistXY(self.center, newDeg, self.radius),
                deg = newDeg,
                center = self.center)

            nNext = n.next
            n.next = newCurveArcNext
            newCurveArcNext.prev = n
            newCurveArcNext.next = nNext
            nNext.prev = newCurveArcNext

            self._count += 1

        return

def intCurveArc2Circle(curveArc: CurveArc, circle: dict) -> CurveArc:

    # 先转出LineString，再去和circle相交，得到新的LineString
    # NOTE: 交到的LineString可能有两部分，要连起来
    ls = curveArc.getLineString()
    cc = shapely.Polygon(circleByCenterXY(center = circle['center'], radius = circle['radius']))
    intLine = shapely.intersection(ls, cc)

    if (intLine.is_empty):
        return None

    nl = []
    # 如果0°包括在里头，则为两段，否则只会有一段
    if (intLine.geom_type == 'MultiLineString'):
        nl1 = [i for i in mapping(intLine)['coordinates'][0]]
        nl2 = [i for i in mapping(intLine)['coordinates'][1]]

        # 把nl1和nl2拼接起来
        if (is2PtsSame(nl1[0], nl2[0])):
            # nl1.reverse -> nl2
            nl1.reverse()
            nl = nl1
            nl.extend(nl2)

        elif (is2PtsSame(nl1[-1], nl2[0])):
            # nl1 -> nl2
            nl = nl1
            nl.extend(nl2)

        elif (is2PtsSame(nl1[0], nl2[-1])):
            # nl1.reverse() -> nl2.reverse()
            nl1.reverse()
            nl = nl1
            nl2.reverse()
            nl.extend(nl2)

        elif (is2PtsSame(nl1[-1], nl2[-1])):
            # nl1 -> nl2.reverse()
            nl = nl1
            nl2.reverse()
            nl.extend(nl2)

    else:
        nl = [i for i in mapping(intLine)['coordinates']]

    # 求出LineString的开始和结束圆心角
    # 技巧，三等分，确定序列是顺时针还是逆时针
    nlFirstDeg = headingXY(curveArc.center, nl[0])
    nlLastDeg = headingXY(curveArc.center, nl[-1])

    pt1Third = ptMid([nl[int(len(nl) / 3)], nl[int(len(nl) / 3 - 1)]])
    pt2Third = ptMid([nl[int(len(nl) * 2 / 3)], nl[int(len(nl) * 2 / 3 - 1)]])
    
    nl1ThirdDeg = headingXY(curveArc.center, pt1Third)
    nl2ThirdDeg = headingXY(curveArc.center, pt2Third)

    # 确定是顺时针还是逆时针
    dir1 = nl1ThirdDeg > nlFirstDeg
    dir2 = nl2ThirdDeg > nl1ThirdDeg
    dir3 = nlLastDeg > nl2ThirdDeg

    # 如果三个区间段内至少两个是顺时针，就是顺时针
    clockWiseFlag = None
    if (dir1 + dir2 + dir3 >= 2):
        clockWiseFlag = True
    else:
        clockWiseFlag = False

    # 如果是顺时针，第一个应该比第二个小，否则第二个加360
    startDeg = None
    endDeg = None
    if (clockWiseFlag):
        if (nlFirstDeg < nlLastDeg):
            startDeg = nlFirstDeg
            endDeg = nlLastDeg
        else:
            startDeg = nlFirstDeg
            endDeg = nlLastDeg + 360
    else:
        if (nlFirstDeg > nlLastDeg):
            startDeg = nlLastDeg
            endDeg = nlFirstDeg
        else:
            startDeg = nlLastDeg
            endDeg = nlFirstDeg + 360

    return CurveArc(
        center = curveArc.center, 
        radius = curveArc.radius, 
        startDeg = startDeg, 
        endDeg = endDeg)
