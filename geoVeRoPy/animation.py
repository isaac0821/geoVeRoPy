import matplotlib.pyplot as plt

from matplotlib import rcParams
# rcParams['font.family'] = 'SimSun'
from matplotlib.animation import FuncAnimation
from matplotlib.animation import PillowWriter
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm

from .common import *
from .color import *
from .geometry import *
from .gridSurface import *

def aniRouting(timeRange: tuple[int, int], nodes: dict|None = None, vehicles: dict|None = None, polygons: dict|None = None):
    """Given nodes, vehicles, static polygons, and dynamic polygons, create animation

    Parameters
    ----------

    nodes: dictionary, optional, default None
        A dictionary of nodes.
            >>> nodes[nID] = {
            ...     'pt': [x, y],
            ...     'neighbor': poly, # A polygon indicating neighborhood
            ...     'direction': direction, # Moving direction
            ...     'speed': speed, # Moving speed
            ...     'marker': 'r',    # Optional, default as 'o'
            ...     'markerSize': 2,  # Optional, default as None
            ...     'color': 'red',   # Optional, default as 'Random'
            ...     'size': 3,        # Optional, default as 3
            ...     'fontsize': 3,    # Optional, default as 3
            ... }
    vehicles: dictionary, optional, default None
        A dictionary of vehicle. 
            >>> vehicles[vID] = {
            ...     'vehicle': vehicleName,
            ...     'seq': [], # A sequence of visiting locations
            ...     'timeStamp': [], # A sequence of time stamps when visiting each location
            ...     'note': [], # Note to show during each leg of sequence
            ...     'color': vehColor,
            ...     'pathColor': pathColor,
            ...     'traceColor': traceColor,
            ...     'traceShadowTime': traceShadowTime
            ... }
    polygons: dictionary, optional, default None
        A dictionary indicating polygons that are dynamic/static in the animation
            >>> polygons[pID] = {
            ...     'anchor': [x, y], # The anchor of the polygon
            ...     'poly': [pt1, pt2], # A sequence of extreme points, coordinates are relative to 'anchor'
            ...     'direction': direction, # Moving direction
            ...     'speed': speed, # Moving speed,
            ...     'timeRange': [ts, te], # Time range of the movement
            ...     'edgeColor': color, # Edge color
            ...     'fillColor': color, # Fill color
            ...     'fillStyle': "///", # Fill style
            ...     'opacity': 0.5, # opacity
            ... }

    """

    # Styling characters ======================================================
    # Nodes -------------------------------------------------------------------
    ptFieldName = 'pt' if 'ptFieldName' not in kwargs else kwargs['ptFieldName']
    nodeTimedSeqFieldName = 'timedSeq' if 'nodeTimedSeqFieldName' not in kwargs else kwargs['nodeTimedSeqFieldName']
    nodeTimeWindowFieldName = 'timeWindow' if 'nodeTimeWindowFieldName' not in kwargs else kwargs['nodeTimeWindowFieldName']
    nodeColor = 'black' if 'nodeColor' not in kwargs else kwargs['nodeColor']
    nodeMarker = 'o' if 'nodeMarker' not in kwargs else kwargs['nodeMarker']
    nodeMarkerSize = 2 if 'nodeMarkerSize' not in kwargs else kwargs['nodeMarkerSize']

    # Vehicles ----------------------------------------------------------------
    vehTimedSeqFieldName = 'timedSeq' if 'vehTimedSeqFieldName' not in kwargs else kwargs['vehTimedSeqFieldName']
    vehLabelFieldName = 'label' if 'vehLabelFieldName' not in kwargs else kwargs['vehLabelFieldName']
    vehNoteFieldName = 'note' if 'vehNoteFieldName' not in kwargs else kwargs['vehNoteFieldName']
    vehColor = 'blue' if 'vehColor' not in kwargs else kwargs['vehColor']
    vehMarker = '^' if 'vehMarker' not in kwargs else kwargs['vehMarker']
    vehMarkerSize = 5 if 'vehMarkerSize' not in kwargs else kwargs['vehMarkerSize']
    vehPathColor = 'gray' if 'vehPathColor' not in kwargs else kwargs['vehPathColor']
    vehPathWidth = 3 if 'vehPathWidth' not in kwargs else kwargs['vehPathWidth']
    vehTraceColor = 'orange' if 'vehTraceColor' not in kwargs else kwargs['vehTraceColor']
    vehTraceWidth = 3 if 'vehTraceWidth' not in kwargs else kwargs['vehTraceWidth']
    vehTraceShadowTime = None if 'vehTraceShadowTime' not in kwargs else kwargs['vehTraceShadowTime']
    vehSpdShowLabelFlag = True if 'vehSpdShowLabelFlag' not in kwargs else kwargs['vehSpdShowLabelFlag']
    vehSpdShowArrowFlag = True if 'vehSpdShowArrowFlag' not in kwargs else kwargs['vehSpdShowArrowFlag']
    vehSpdArrowLength = 5 if 'vehSpdArrowLength' not in kwargs else kwargs['vehSpdArrowLength']
    vehShowNoteFlag = True if 'vehShowNoteFlag' not in kwargs else kwargs['vehShowNoteFlag']

    # Polygons ----------------------------------------------------------------
    polyAnchorFieldName = None if 'polyAnchorFieldName' not in kwargs else kwargs['polyAnchorFieldName']
    polyTimedSeqFieldName = None if 'polyTimedSeqFieldName' not in kwargs else kwargs['polyTimedSeqFieldName']
    polyTimeWindowFieldName = None if 'polyTimeWindowFieldName' not in kwargs else kwargs['polyTimeWindowFieldName']
    polyFieldName = 'poly' if 'polyFieldName' not in kwargs else kwargs['polyFieldName']
    polyEdgeColor = 'black' if 'polyEdgeColor' not in kwargs else kwargs['polyEdgeColor']
    polyEdgeWidth = 1 if 'polyEdgeWidth' not in kwargs else kwargs['polyEdgeWidth']
    polyFillColor = 'gray' if 'polyFillColor' not in kwargs else kwargs['polyFillColor']
    polyFillStyle = '///' if 'polyFillStyle' not in kwargs else kwargs['polyFillStyle']
    polyOpacity = 0.5 if 'polyOpacity' not in kwargs else kwargs['polyOpacity']

    # Settings ----------------------------------------------------------------
    speed = 1 if 'speed' not in kwargs else kwargs['speed']
    fps = 12 if 'fps' not in kwargs else kwargs['fps']
    repeatFlag = True if 'repeatFlag' not in kwargs else kwargs['repeatFlag']
    xyReverseFlag = False if 'xyReverseFlag' not in kwargs else kwargs['xyReverseFlag']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showProgressFlag = True if 'showProgressFlag' not in kwargs else kwargs['showProgressFlag']
    aniSavePath = None if 'aniSavePath' not in kwargs else kwargs['aniSavePath']
    aniSaveDPI = 30 if 'aniSaveDPI' not in kwargs else kwargs['aniSaveDPI']

    # Check for required fields ===============================================
    if (nodes == None and vehicles == None and polygons == None):
        raise MissingParameterError("ERROR: Need to provide entities for animation.")

    # If no based matplotlib figure provided, define boundary =================
    fig, ax = plt.subplots()
    allX = []
    allY = []
    if (nodes != None):
        for i in nodes:
            if (not xyReverseFlag):
                allX.append(nodes[i][ptFieldName][0])
                allY.append(nodes[i][ptFieldName][1])
            else:
                allX.append(nodes[i][ptFieldName][1])
                allY.append(nodes[i][ptFieldName][0])
    (xMin, xMax, yMin, yMax) = boundingBox
    if (xMin == None):
        xMin = min(allX) - 0.1 * abs(max(allX) - min(allX))
    if (xMax == None):
        xMax = max(allX) + 0.1 * abs(max(allX) - min(allX))
    if (yMin == None):
        yMin = min(allY) - 0.1 * abs(max(allY) - min(allY))
    if (yMax == None):
        yMax = max(allY) + 0.1 * abs(max(allY) - min(allY))
    width = 0
    height = 0
    if (figSize == None or (figSize[0] == None and figSize[1] == None)):
        if (xMax - xMin > yMax - yMin):
            width = 5
            height = 5 * ((yMax - yMin) / (xMax - xMin))
        else:
            width = 5 * ((xMax - xMin) / (yMax - yMin))
            height = 5
    elif (figSize != None and figSize[0] != None and figSize[1] == None):
        width = figSize[0]
        height = figSize[0] * ((yMax - yMin) / (xMax - xMin))
    elif (figSize != None and figSize[0] == None and figSize[1] != None):
        width = figSize[1] * ((xMax - xMin) / (yMax - yMin))
        height = figSize[1]
    else:
        (width, height) = figSize

    fig.set_figwidth(width) 
    fig.set_figheight(height)

    # Styling =================================================================
    nodeStyle = {}
    if (nodes != None):
        for nID in nodes:
            nodeStyle[nID] = {}
            if (nodeColor == None or nodeColor == 'Random'):
                nodeStyle[nID]['nodeColor'] = rndColor()
            elif (nodeColor != None):
                nodeStyle[nID]['nodeColor'] = nodeColor
            elif ('nodeColor' in nodes[nID]):
                nodeStyle[nID]['nodeColor'] = nodes[nID]['nodeColor']
            
            if (nodeMarker != None):
                nodeStyle[nID]['nodeMarker'] = nodeMarker
            elif ('nodeMarker' in nodes[nID]):
                nodeStyle[nID]['nodeMarker'] = nodes[nID]['nodeMarker']

            if (nodeMarkerSize != None):
                nodeStyle[nID]['nodeMarkerSize'] = nodeMarkerSize
            elif ('nodeMarkerSize' in nodes[nID]):
                nodeStyle[nID]['nodeMarkerSize'] = nodes[nID]['nodeMarkerSize']

    polyStyle = {}
    if (polygons != None):
        for pID in polygons:
            polyStyle[pID] = {}
            if (polyEdgeColor == None or polyEdgeColor == 'Random'):
                polyStyle[pID]['edgeColor'] = rndColor()
            elif (polyEdgeColor != None):
                polyStyle[pID]['edgeColor'] = polyEdgeColor
            elif ('edgeColor' in polygons[pID]):
                polyStyle[pID]['edgeColor'] = polygons[pID]['edgeColor']

            if (polyEdgeWidth != None):
                polyStyle[pID]['edgeWidth'] = polyEdgeWidth
            elif ('edgeWidth' in polygons[pID]):
                polyStyle[pID]['edgeWidth'] = polygons[pID]['edgeWidth']

            if (polyFillColor == 'Random'):
                polyStyle[pID]['fillColor'] = rndColor()
            elif (polyFillColor != None):
                polyStyle[pID]['fillColor'] = polyFillColor
            elif ('fillColor' in polygons[pID]):
                polyStyle[pID]['fillColor'] = polygons[pID]['fillColor']

            if (polyFillStyle != None):
                polyStyle[pID]['fillStyle'] = polyFillStyle
            elif ('fillStyle' in polygons[pID]):
                polyStyle[pID]['fillStyle'] = polygons[pID]['fillStyle']

            if (polyOpacity != None):
                polyStyle[pID]['opacity'] = polyOpacity
            elif ('opacity' in polygons[pID]):
                polyStyle[pID]['opacity'] = polygons[pID]['opacity']

    vehicleStyle = {}
    if (vehicles != None):
        for vID in vehicles:
            vehicleStyle[vID] = {}
            if (vehColor == 'Random'):
                vehicleStyle[vID]['vehColor'] = rndColor()
            elif (vehColor != None):
                vehicleStyle[vID]['vehColor'] = vehColor
            elif ('color' in vehicles[vID]):
                vehicleStyle[vID]['vehColor'] = vehicles[vID]['color']

            if (vehMarker != None):
                vehicleStyle[vID]['vehMarker'] = vehMarker
            elif ('marker' in vehicles[vID]):
                vehicleStyle[vID]['vehMarker'] = vehicles[vID]['marker']

            if (vehMarkerSize != None):
                vehicleStyle[vID]['vehMarkerSize'] = vehMarkerSize
            elif ('markerSize' in vehicles[vID]):
                vehicleStyle[vID]['vehMarkerSize'] = vehicles[vID]['markerSize']

            if (vehPathColor == 'Random'):
                vehicleStyle[vID]['pathColor'] = rndColor()
            elif (vehPathColor != None):
                vehicleStyle[vID]['pathColor'] = vehPathColor
            elif ('pathColor' in vehicles[vID]):
                vehicleStyle[vID]['pathColor'] = vehicles[vID]['pathColor']

            if (vehPathWidth != None):
                vehicleStyle[vID]['pathWidth'] = vehPathWidth
            elif ('pathWidth' in polygons[pID]):
                vehicleStyle[vID]['pathWidth'] = vehicles[vID]['pathWidth']

            if (vehTraceColor == 'Random'):
                vehicleStyle[vID]['traceColor'] = rndColor()
            elif (vehTraceColor != None):
                vehicleStyle[vID]['traceColor'] = vehTraceColor
            elif ('traceColor' in vehicles[vID]):
                vehicleStyle[vID]['traceColor'] = vehicles[vID]['traceColor']

            if (vehTraceWidth != None):
                vehicleStyle[vID]['traceWidth'] = vehTraceWidth
            elif ('traceWidth' in polygons[pID]):
                vehicleStyle[vID]['traceWidth'] = vehicles[vID]['traceWidth']

            if (vehTraceShadowTime != None):
                vehicleStyle[vID]['traceShadowTime'] = vehTraceShadowTime
            elif ('traceShadowTime' in vehicles[vID]):
                vehicleStyle[vID]['traceShadowTime'] = vehicles[vID]['traceShadowTime']
            else:
                vehicleStyle[vID]['traceShadowTime'] = None

    def animate(t):
        ax.clear()
        ax.set_xlim(xMin, xMax)
        ax.set_ylim(yMin, yMax)

        # Clock
        clock = timeRange[0] + t * speed / (fps * 1.0)
        ax.set_title("Clock: %s[s]" % round(clock, 2))

        if (showProgressFlag):
            print("Clock: %s[s]" % round(clock, 2))

        # Plot static/dynamic polygons
        if (polygons != None):
            # Plot each polygon -----------------------------------------------
            for pID in polygons:
                # 判定此时刻是否需要绘制poly
                plotPolyFlag = False
                if (polyTimeWindowFieldName not in polygons[pID] or polygons[pID][polyTimeWindowFieldName][0] <= clock <= polygons[pID][polyTimeWindowFieldName][1]):
                    plotPolyFlag = True

                # 每个Poly的坐标轮廓
                pX = []
                pY = []
                if (plotPolyFlag):
                    if (type(polygons[pID][polyFieldName]) == TriGridSurface):
                        poly = polygons[pID][polyFieldName].buildZProfile(clock)
                        for pt in poly:
                            if (not xyReverseFlag):
                                pX.append(pt[0])
                                pY.append(pt[1])
                            else:
                                pX.append(pt[1])
                                pY.append(pt[0])
                    else:
                        for p in polygons[pID][polyFieldName]:
                            pt = None
                            if (polyAnchorFieldName in polygons[pID] and polyTimedSeqFieldName in polygons[pID]):
                                # 如果还没开始动，在原点不动
                                if (clock < polygons[pID][polyTimedSeqFieldName][0][1]):
                                    pt = p
                                # 如果到达终点了，在终点不动
                                elif (clock > polygons[pID][polyTimedSeqFieldName][-1][1]):
                                    dx = (polygons[pID][polyTimedSeqFieldName][-1][0][0] - polygons[pID][polyAnchorFieldName][0])
                                    dy = (polygons[pID][polyTimedSeqFieldName][-1][0][1] - polygons[pID][polyAnchorFieldName][1])
                                    pt = (p[0] + dx, p[1] + dy)
                                else: 
                                    curSnap = snapInTimedSeq(
                                        timedSeq = polygons[pID][polyTimedSeqFieldName],
                                        t = clock)
                                    dx = (curSnap['pt'][0] - polygons[pID][polyAnchorFieldName][0])
                                    dy = (curSnap['pt'][1] - polygons[pID][polyAnchorFieldName][1])
                                    pt = (p[0] + dx, p[1] + dy)
                            elif ('direction' in polygons[pID] and 'speed' in polygons[pID]):
                                if (clock < polygons[pID][polyTimeWindowFieldName][0]):
                                    pt = p
                                elif (clock < polygons[pID][polyTimeWindowFieldName][1]):
                                    pt = ptInDistXY(p, polygons[pID]['direction'], polygons[pID]['speed'] * clock)
                                else:
                                    pt = ptInDistXY(p, polygons[pID]['direction'], polygons[pID]['speed'] * (polygons[pID]['timeRange'][1] - polygons[pID]['timeRange'][0]))
                            else:
                                pt = p

                            if (not xyReverseFlag):
                                pX.append(pt[0])
                                pY.append(pt[1])
                            else:
                                pX.append(pt[1])
                                pY.append(pt[0])

                # Plot polygons with styling
                if (plotPolyFlag):
                    if ('fillColor' not in polyStyle[pID]):
                        ax.plot(pX, pY, 
                            color=polyStyle[pID]['edgeColor'], 
                            linewidth=polyStyle[pID]['edgeWidth'])
                    elif ('fillStyle' not in polyStyle[pID]):
                        ax.fill(pX, pY, 
                            facecolor=polyStyle[pID]['fillColor'], 
                            edgecolor=polyStyle[pID]['edgeColor'], 
                            linewidth=polyStyle[pID]['edgeWidth'], 
                            alpha=polyStyle[pID]['opacity'])
                    else:
                        ax.fill(pX, pY, 
                            facecolor=polyStyle[pID]['fillColor'], 
                            edgecolor=polyStyle[pID]['edgeColor'], 
                            hatch=polyStyle[pID]['fillStyle'], 
                            linewidth=polyStyle[pID]['edgeWidth'], 
                            alpha=polyStyle[pID]['opacity'])

        # Plot nodes
        if (nodes != None):
            # Plot the location of nodes --------------------------------------
            for nID in nodes:
                plotNodeFlag = False
                if (nodeTimeWindowFieldName not in nodes[nID] or nodes[nID][nodeTimeWindowFieldName][0] <= clock <= nodes[nID][nodeTimeWindowFieldName][1]):
                    plotNodeFlag = True

                x = None
                y = None       
                curPt = None         
                if (plotNodeFlag):
                    if (nodeTimedSeqFieldName not in nodes[nID]):
                        curPt = nodes[nID][ptFieldName]
                    else:
                        curSnap = snapInTimedSeq(
                            timedSeq = nodes[nID][nodeTimedSeqFieldName],
                            t = clock)
                        curPt = curSnap['pt']

                if (not xyReverseFlag):
                    x = curPt[0]
                    y = curPt[1]
                else:
                    x = curPt[1]
                    y = curPt[0]
                # Styling of each node
                if (plotNodeFlag):
                    ax.plot(x, y, 
                        color = nodeStyle[nID]['nodeColor'], 
                        marker = nodeStyle[nID]['nodeMarker'], 
                        markersize = nodeStyle[nID]['nodeMarkerSize'])
                    if ('label' not in nodes[nID]):
                        lbl = nID
                    else:
                        lbl = nodes[nID]['label']
                    ax.annotate(lbl, (x, y))

        # Plot vehicle
        if (vehicles != None):
            # Plot each vehicle -----------------------------------------------
            for vID in vehicles:
                # Plot path
                if ('pathColor' in vehicleStyle[vID]):
                    pathX = []
                    pathY = []
                    if (not xyReverseFlag):
                        pathX = [vehicles[vID][vehTimedSeqFieldName][i][0][0] for i in range(len(vehicles[vID][vehTimedSeqFieldName]))]
                        pathY = [vehicles[vID][vehTimedSeqFieldName][i][0][1] for i in range(len(vehicles[vID][vehTimedSeqFieldName]))]
                    else:
                        pathX = [vehicles[vID][vehTimedSeqFieldName][i][0][1] for i in range(len(vehicles[vID][vehTimedSeqFieldName]))]
                        pathY = [vehicles[vID][vehTimedSeqFieldName][i][0][0] for i in range(len(vehicles[vID][vehTimedSeqFieldName]))]
                    ax.plot(pathX, pathY, color=vehicleStyle[vID]['pathColor'], linewidth = 1)

                # Plot trace
                if ('traceColor' in vehicleStyle[vID]):
                    ts = timeRange[0]
                    te = clock
                    if (vehicleStyle[vID]['traceShadowTime'] != None):
                        ts = max(te - vehicleStyle[vID]['traceShadowTime'], timeRange[0])

                    if (ts < te):
                        trace = traceInTimedSeq(
                            timedSeq = vehicles[vID][vehTimedSeqFieldName],
                            ts = ts,
                            te = te)
                        if (len(trace) > 0 and 'traceColor' in vehicleStyle[vID]):
                            traceX = []
                            traceY = []
                            if (not xyReverseFlag):
                                traceX = [i[0] for i in trace]
                                traceY = [i[1] for i in trace]
                            else:
                                traceX = [i[1] for i in trace]
                                traceY = [i[0] for i in trace]
                            ax.plot(traceX, traceY, color=vehicleStyle[vID]['traceColor'], linewidth = 1)

                # Plot vehicle
                curSnap = snapInTimedSeq(
                    timedSeq = vehicles[vID][vehTimedSeqFieldName],
                    t = clock)
                curPt = curSnap['pt']
                ax.plot(curPt[0], curPt[1], 
                    color = vehicleStyle[vID]['vehColor'], 
                    marker = vehicleStyle[vID]['vehMarker'], 
                    markersize = vehicleStyle[vID]['vehMarkerSize'])

                if (vehLabelFieldName not in vehicles[vID]):
                    lbl = str(vID)
                else:
                    lbl = vehicles[vID][vehLabelFieldName]

                if (vehSpdShowLabelFlag):
                    curSpd = curSnap['speed']
                    lbl += " %s[m/s]" % (round(curSpd, 2))
                
                if (vehShowNoteFlag and vehNoteFieldName in vehicles[vID]):
                    note = ""
                    if (clock <= vehicles[vID]['timedSeq'][0][1]):
                        note = vehicles[vID][vehNoteFieldName][0]
                    elif (clock >= vehicles[vID]['timedSeq'][-1][1]):
                        note = vehicles[vID][vehNoteFieldName][-1]
                    else:
                        for i in range(len(vehicles[vID]['timedSeq']) - 1):
                            if (vehicles[vID]['timedSeq'][i][1] <= clock < vehicles[vID]['timedSeq'][i + 1][1]):
                                note = vehicles[vID][vehNoteFieldName][i]
                                break
                    ax.annotate(lbl + "\n" + note, (curPt[0], curPt[1]))
                else:
                    ax.annotate(lbl, (curPt[0], curPt[1]))

    ani = FuncAnimation(
        fig, animate, 
        frames=int((timeRange[1] / (speed * 1.0) - timeRange[0] / (speed * 1.0)) * fps), 
        interval= int(1000 / fps), 
        repeat = repeatFlag)

    if (aniSavePath):
        ani.save("%s.gif" % aniSavePath, dpi=aniSaveDPI, writer=PillowWriter(fps=fps))

    return ani