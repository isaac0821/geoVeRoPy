import networkx as nx

from .geometry import *
from .polyTour import *
from .curveArc import *

def ptSetSeq2Circle(seq: list, circles: dict, seqDegenedFlag: bool = True):

    if (not seqDegenedFlag):
        seq = seqRemoveDegen(seq)['newSeq']

    actions = []
    accMileage = 0

    for i in range(len(seq) - 1):
        # seg[0]的mileage更小
        seg = [seq[i], seq[i + 1]]

        for p in circles:
            # 根据Seg和circle的相交情况做判断
            segIntCircle = intSeg2Circle(seg = seg, circle = circles[p], detailFlag = True)

            # 没有相交，不管
            if (segIntCircle['status'] == 'NoCross'):
                pass

            # 相切，很可能是线段一段触碰到圆的边界
            elif (segIntCircle['status'] == 'Cross' and segIntCircle['intersectType'] == 'Point'):
                # 同时一进一出
                actions.append({
                    'loc': segIntCircle['intersect'],
                    'action': 'touch',
                    'circleID': p,
                    'mileage': accMileage + segIntCircle['mileage'],
                    'segID': i
                })

            # 相交
            elif (segIntCircle['status'] == 'Cross' and segIntCircle['intersectType'] == 'Segment'):
                actions.append({
                    'loc': segIntCircle['intersect'][0],
                    'action': 'enter',
                    'circleID': p,
                    'mileage': accMileage + segIntCircle['mileage'][0],
                    'segID': i
                })
                actions.append({
                    'loc': segIntCircle['intersect'][1],
                    'action': 'leave',
                    'circleID': p,
                    'mileage': accMileage + segIntCircle['mileage'][1],
                    'segID': i
                })

        accMileage += distEuclideanXY(seg[0], seg[1])

    actions = sorted(actions, key = lambda d: d['mileage'])

    # 后处理，把同一个点上的进进出出消去
    # Step 1: 先按是否重合对点进行聚合  
    curActionList = [actions[0]['mileage']]
    curActAggList = [actions[0]]
    aggActionList = []
    # 挤香肠算法
    for i in range(1, len(actions)):
        # 如果当前点和任意一个挤出来的点足够近，则计入
        samePtFlag = False

        for m in curActionList:
            if (abs(m - actions[i]['mileage']) <= ERRTOL['distPt2Pt']):
                curActAggList.append(actions[i])
                curActionList.append(actions[i]['mileage'])
                samePtFlag = True
                break

        # 若不重复，了结
        if (not samePtFlag):
            aggActionList.append([k for k in curActAggList])
            curActAggList = [actions[i]]
            curActionList = [actions[i]['mileage']]

    aggActionList.append([k for k in curActAggList])

    # 先过滤掉touch类的
    filteredActionList = []

    for i in range(len(aggActionList)):
        # 如果
        if (len(aggActionList[i]) == 1):
            filteredActionList.append(aggActionList[i][0])

    return aggActionList
