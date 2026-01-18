import numpy as np

from scipy.interpolate import splprep, splev

import matplotlib.pyplot as plt

from matplotlib import rcParams
from matplotlib import patches
from matplotlib.animation import FuncAnimation
from matplotlib.animation import PillowWriter
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import cm

from .tree import *
from .common import *
from .color import *
from .msg import *
from .province import *
from .geometry import *
from .travel import *
from .curveArc import *
from .gridSurface import *

def plotLocs(locs: list[pt], **kwargs):

    """
    Plot locations on a figure

    Parameters
    ----------
    locs: list of pt, required
        A list of locations to be plotted
    **kwargs: optional
        Additional matplotlib information

    Returns
    -------
    fig, ax
        matplotlib.pyplot object
    """

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # styling characters ======================================================
    locColor = 'Random' if 'locColor' not in kwargs else kwargs['locColor']
    locMarker = 'o' if 'locMarker' not in kwargs else kwargs['locMarker']
    locMarkerSize = 1 if 'locMarkerSize' not in kwargs else kwargs['locMarkerSize']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    # Check for required fields ===============================================
    if (locs == None):
        raise MissingParameterError("ERROR: Missing required field `locs`.")

    # If no based matplotlib figure provided, define boundary =================
    if (fig == None or ax == None):
        fig, ax = plt.subplots()
        boundingBox = defaultBoundingBox(
            boundingBox = boundingBox, 
            pts = locs,
            latLonFlag = latLonFlag)
        (xMin, xMax, yMin, yMax) = boundingBox
        (width, height) = defaultFigSize(boundingBox, figSize[0], figSize[1], latLonFlag)

        if (not latLonFlag):
            fig.set_figwidth(width)
            fig.set_figheight(height)
            ax.set_xlim(xMin, xMax)
            ax.set_ylim(yMin, yMax)
        else:
            fig.set_figwidth(height)
            fig.set_figheight(width)
            ax.set_xlim(yMin, yMax)
            ax.set_ylim(xMin, xMax)

    # Draw locs ==============================================================
    # 逐个点绘制
    for i in locs:
        # Define color --------------------------------------------------------
        color = None
        if (locColor == 'Random'):
            color = rndColor()
        else:
            color = locColor
        # plot nodes ----------------------------------------------------------
        x = None
        y = None
        if (not latLonFlag):
            x = i[0]
            y = i[1]
        else:
            x = i[1]
            y = i[0]
        ax.plot(x, y, color = color, marker = locMarker, markersize = locMarkerSize)

    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None and isinstance(fig, plt.Figure)):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotLocs3D(locs3D: list[pt3D], **kwargs):
    """
    Plot 3D locations on a figure

    Parameters
    ----------
    locs3D: list of pt3D, required
        A list of locations to be plotted
    **kwargs: optional
        Additional matplotlib information

    Returns
    -------
    fig, ax
        matplotlib.pyplot object
    """

    # Check for required fields ===============================================
    if (locs3D == None):
        raise MissingParameterError("ERROR: Missing required field `locs3D`.")

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox3D = (None, None, None, None, None, None) if 'boundingBox3D' not in kwargs else kwargs['boundingBox3D']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # styling characters ======================================================
    locColor = 'Random' if 'locColor' not in kwargs else kwargs['locColor']
    locMarker = 'o' if 'locMarker' not in kwargs else kwargs['locMarker']
    locMarkerSize = 1 if 'locMarkerSize' not in kwargs else kwargs['locMarkerSize']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    # If no based matplotlib figure provided, define boundary =================
    if (fig == None or ax == None):
        fig = plt.figure()
        ax = plt.axes(projection = '3d')
        (xMin, xMax, yMin, yMax, zMin, zMax) = boundingBox3D
        ax.set_xlim(xMin, xMax)
        ax.set_ylim(yMin, yMax)
        ax.set_zlim(zMin, zMax)

    # Draw locs ==============================================================
    for i in locs3D:
        # Define color --------------------------------------------------------
        color = None
        if (locColor == 'Random'):
            color = rndColor()
        else:
            color = locColor

        # plot nodes ----------------------------------------------------------        
        x = None
        y = None
        z = i[2]
        if (not latLonFlag):
            x = i[0]
            y = i[1]
        else:
            x = i[1]
            y = i[0]

        ax.scatter3D(x, y, z, c = color, marker = locMarker, s = locMarkerSize)

    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None and isinstance(fig, plt.Figure)):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotNodes(nodes: dict, **kwargs):

    """
    Draw nodes

    Parameters
    ----------
    nodes: dictionary, required
        A `nodes` dictionary. See :ref:`nodes` for reference.
    **kwargs: optional
        Additional matplotlib information

    Returns
    -------
    fig, ax
        matplotlib.pyplot object
    """

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # styling characters ======================================================
    nodeColor = 'Random' if 'nodeColor' not in kwargs else kwargs['nodeColor']
    nodeMarker = 'o' if 'nodeMarker' not in kwargs else kwargs['nodeMarker']
    nodeMarkerSize = 1 if 'nodeMarkerSize' not in kwargs else kwargs['nodeMarkerSize']
    neighborColor = 'gray' if 'neighborColor' not in kwargs else kwargs['neighborColor']
    neighborOpacity = 0.5 if 'neighborOpacity' not in kwargs else kwargs['neighborOpacity']
    neighborFillStyle = '///' if 'neighborFillStyle' not in kwargs else kwargs['neighborFillStyle']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    # Field names =============================================================
    locFieldName = 'loc' if 'locFieldName' not in kwargs else kwargs['locFieldName']
    neighborFieldName = 'neighbor' if 'neighborFieldName' not in kwargs else kwargs['neighborFieldName']

    # Check for required fields ===============================================
    if (nodes == None):
        raise MissingParameterError(ERROR_MISSING_NODES)

    # If no based matplotlib figure provided, define boundary =================
    if (fig == None or ax == None):
        fig, ax = plt.subplots()
        boundingBox = defaultBoundingBox(
            boundingBox = boundingBox, 
            nodes = nodes, 
            locFieldName = locFieldName, 
            latLonFlag = latLonFlag)
        (xMin, xMax, yMin, yMax) = boundingBox
        (width, height) = defaultFigSize(boundingBox, figSize[0], figSize[1], latLonFlag)
        if (isinstance(fig, plt.Figure)):
            fig.set_figwidth(width)
            fig.set_figheight(height)
            ax.set_xlim(xMin, xMax)
            ax.set_ylim(yMin, yMax)

    # Create node styles ======================================================
    nodeStyle = {}
    for n in nodes:
        nodeStyle[n] = {}

        # x,y -----------------------------------------------------------------
        nodeStyle[n]['x'] = None
        nodeStyle[n]['y'] = None
        if (not latLonFlag):
            nodeStyle[n]['x'] = nodes[n][locFieldName][0]
            nodeStyle[n]['y'] = nodes[n][locFieldName][1]
        else:
            nodeStyle[n]['x'] = nodes[n][locFieldName][1]
            nodeStyle[n]['y'] = nodes[n][locFieldName][0]

        # Color ---------------------------------------------------------------
        if ('color' in nodes[n]):
            nodeStyle[n]['color'] = nodes[n]['color']
        elif (nodeColor == 'Random'):
            nodeStyle[n]['color'] = rndColor()
        else:
            nodeStyle[n]['color'] = nodeColor

        # Marker --------------------------------------------------------------
        if ('marker' in nodes[n]):
            nodeStyle[n]['marker'] = nodes[n]['marker']
        else:
            nodeStyle[n]['marker'] = nodeMarker

        if ('markerSize' in nodes[n]):
            nodeStyle[n]['markerSize'] = nodes[n]['markerSize']
        else:
            nodeStyle[n]['markerSize'] = nodeMarkerSize

        # Label ---------------------------------------------------------------
        if ('label' in nodes[n]):
            nodeStyle[n]['label'] = nodes[n]['label']
        else:
            nodeStyle[n]['label'] = n

        if ('ha' in nodes[n]):
            nodeStyle[n]['ha'] = nodes[n]['ha']
        else:
            nodeStyle[n]['ha'] = 'left'
        
        if ('va' in nodes[n]):
            nodeStyle[n]['va'] = nodes[n]['va']
        else:
            nodeStyle[n]['va'] = 'top'

        if ('fontsize' in nodes[n]):
            nodeStyle[n]['fontsize'] = nodes[n]['fontsize']
        else:
            nodeStyle[n]['fontsize'] = 10

    # Draw nodes ==============================================================
    for n in nodes:
        ax.plot(
            nodeStyle[n]['x'], 
            nodeStyle[n]['y'], 
            color = nodeStyle[n]['color'], 
            marker = nodeStyle[n]['marker'], 
            markersize = nodeStyle[n]['markerSize'])
        ax.annotate(
            nodeStyle[n]['label'], 
            (nodeStyle[n]['x'], nodeStyle[n]['y']), 
            ha=nodeStyle[n]['ha'], 
            va=nodeStyle[n]['va'],
            fontsize=nodeStyle[n]['fontsize'])

    # Neighborhood style ======================================================
    nodeNeiStyle = {}
    for n in nodes:
        if ('neiShape' in nodes[n]):
            # Neighborhood color --------------------------------------------------
            if ('neighborColor' in nodes[n]):
                nodeNeiStyle['neighborColor'] = nodes[n]['neighborColor']
            else:
                nodeNeiStyle['neighborColor'] = neighborColor

            # Neighborhood opacity ------------------------------------------------
            if ('neighborOpacity' in nodes[n]):
                nodeNeiStyle['neighborOpacity'] = nodes[n]['neighborOpacity']
            else:
                nodeNeiStyle['neighborOpacity'] = neighborOpacity

            # Neighborhood fill style ---------------------------------------------
            if ('neighborFillStyle' in nodes[n]):
                nodeNeiStyle['neighborFillStyle'] = nodes[n]['neighborFillStyle']
            else:
                nodeNeiStyle['neighborFillStyle'] = neighborFillStyle

    # Draw node neighborhoods =================================================
    for n in nodes:
        if ('neiShape' in nodes[n] and nodes[n]['neiShape'] == 'Poly'):
            fig, ax = plotPoly(
                fig = fig,
                ax = ax,
                poly = nodes[n][neighborFieldName],
                edgeWidth = 1,
                edgeColor = 'black',
                fillColor = nodeNeiStyle['neighborColor'],
                fillStyle = nodeNeiStyle['neighborFillStyle'],
                opacity = nodeNeiStyle['neighborOpacity'],
                latLonFlag = latLonFlag,
                showAxis = showAxis)
        
        elif ('neiShape' in nodes[n] and nodes[n]['neiShape'] == 'Circle'):
            if ('radius' not in nodes[n]):
                raise MissingParameterError(f"ERROR: Missing radius for node {n}, specify with 'radius' in nodes[{n}].")
            neiPoly = circleByCenterXY(
                center = nodes[n][locFieldName],
                radius = nodes[n]['radius'])
            fig, ax = plotPoly(
                fig = fig,
                ax = ax,
                poly = neiPoly,
                edgeWidth = 1,
                edgeColor = 'black',
                fillColor = nodeNeiStyle['neighborColor'],
                fillStyle = nodeNeiStyle['neighborFillStyle'],
                opacity = nodeNeiStyle['neighborOpacity'],
                latLonFlag = latLonFlag,
                showAxis = showAxis)

        elif ('neiShape' in nodes[n] and nodes[n]['neiShape'] == 'Isochrone'):
            for p in range(len(nodes[n][neighborFieldName])):
                fig, ax = plotPoly(
                    fig = fig,
                    ax = ax,
                    poly = nodes[n][neighborFieldName][p],
                    edgeWidth = 1,
                    edgeColor = 'black',
                    fillColor = nodeNeiStyle['neighborColor'],
                    fillStyle = nodeNeiStyle['neighborFillStyle'],
                    opacity = nodeNeiStyle['neighborOpacity'] / len(nodes[n][neighborFieldName]),
                    latLonFlag = latLonFlag,
                    showAxis = showAxis)

    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None and isinstance(fig, plt.Figure)):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotArcs(arcs: dict, **kwargs):
    
    """
    Draw arcs

    Parameters
    ----------
    arcs: dict, required
        An `arcs` dictionary, each arc is defined by two points. See :ref:`arcs` for reference.

    Returns
    -------
    fig, ax
        matplotlib.pyplot object
    """

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    arcColor = 'Random' if 'arcColor' not in kwargs else kwargs['arcColor']
    arcWidth = 1.0 if 'arcWidth' not in kwargs else kwargs['arcWidth']
    arcLabel = None if 'arcLabel' not in kwargs else kwargs['arcLabel']
    arcLineStyle = 'solid' if 'arcLineStyle' not in kwargs else kwargs['arcLineStyle']
    arcDashes = (None, None) if 'arcDashes' not in kwargs else kwargs['arcDashes']
    arcStartColor = 'black' if 'arcStartColor' not in kwargs else kwargs['arcStartColor']
    arcEndColor = 'black' if 'arcEndColor' not in kwargs else kwargs['arcEndColor']
    arcMarkerSize = 2.0 if 'arcMarkerSize' not in kwargs else kwargs['arcMarkerSize']
    arrowFlag = True if 'arrowFlag' not in kwargs else kwargs['arrowFlag']
    arrowPosition = 0.5 if 'arrowPosition' not in kwargs else kwargs['arrowPosition']
    arrowHeadWidth = 2.0 if 'arrowHeadWidth' not in kwargs else kwargs['arrowHeadWidth']
    arrowHeadLength = 3.0 if 'arrowHeadLength' not in kwargs else kwargs['arrowHeadLength']
    arrowShowLimit = None if 'arrowShowLimit' not in kwargs else kwargs['arrowShowLimit']
    neighborOpacity = 0.5 if 'neighborOpacity' not in kwargs else kwargs['neighborOpacity']
    neighborEntWidth = 1.2 if 'neighborEntWidth' not in kwargs else kwargs['neighborEntWidth']
    neighborEntColor = 'black' if 'neighborEntColor' not in kwargs else kwargs['neighborEntColor']
    neighborBtwWidth = 1 if 'neighborBtwWidth' not in kwargs else kwargs['neighborBtwWidth']
    neighborBtwColor = 'black' if 'neighborBtwColor' not in kwargs else kwargs['neighborBtwColor']
    neighborFillStyle = '///' if 'neighborFillStyle' not in kwargs else kwargs['neighborFillStyle']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    # Field names =============================================================
    arcFieldName = 'arc' if 'arcFieldName' not in kwargs else kwargs['arcFieldName']
    arcStartLocFieldName = 'startLoc' if 'arcStartLocFieldName' not in kwargs else kwargs['arcStartLocFieldName']
    arcEndLocFieldName = 'endLoc' if 'arcEndLocFieldName' not in kwargs else kwargs['arcEndLocFieldName']
    neiAFieldName = 'neiA' if 'neiAFieldName' not in kwargs else kwargs['neiAFieldName']
    neiBFieldName = 'neiB' if 'neiBFieldName' not in kwargs else kwargs['neiBFieldName']
    neiBtwFieldName = 'neiBtw' if 'neiBtwFieldName' not in kwargs else kwargs['neiBtwFieldName']

    # Check for required fields ===============================================
    if (arcs == None):
        raise MissingParameterError("ERROR: Missing required field `arcs`.")
    for i in arcs:
        if (arcFieldName not in arcs[i] and arcStartLocFieldName not in arcs[i] and arcEndLocFieldName not in arcs[i]):
            raise MissingParameterError("ERROR: Cannot find arc field in given `arcs` - %s" % i)

    # If no based matplotlib figure provided, define boundary =================
    if (fig == None or ax == None):
        fig, ax = plt.subplots()
        boundingBox = defaultBoundingBox(
            boundingBox = boundingBox, 
            arcs = arcs, 
            arcFieldName = arcFieldName,
            arcStartLocFieldName = arcStartLocFieldName,
            arcEndLocFieldName = arcEndLocFieldName, 
            latLonFlag = latLonFlag)
        (xMin, xMax, yMin, yMax) = boundingBox
        (width, height) = defaultFigSize(boundingBox, figSize[0], figSize[1], latLonFlag)
        if (isinstance(fig, plt.Figure)):
            fig.set_figwidth(width)
            fig.set_figheight(height)
            ax.set_xlim(xMin, xMax)
            ax.set_ylim(yMin, yMax)

    # Create arc styles =======================================================
    arcStyle = {}
    for n in arcs:
        arcStyle[n] = {}

        # x,y -----------------------------------------------------------------
        if (arcFieldName in arcs[n]):        
            if (not latLonFlag):
                arcStyle[n]['x1'] = arcs[n][arcFieldName][0][0]
                arcStyle[n]['x2'] = arcs[n][arcFieldName][1][0]
                arcStyle[n]['y1'] = arcs[n][arcFieldName][0][1]
                arcStyle[n]['y2'] = arcs[n][arcFieldName][1][1]
            else:
                arcStyle[n]['x1'] = arcs[n][arcFieldName][0][1]
                arcStyle[n]['x2'] = arcs[n][arcFieldName][1][1]
                arcStyle[n]['y1'] = arcs[n][arcFieldName][0][0]
                arcStyle[n]['y2'] = arcs[n][arcFieldName][1][0]
        elif (arcStartLocFieldName in arcs[n] and arcEndLocFieldName in arcs[n]):
            if (not latLonFlag):
                arcStyle[n]['x1'] = arcs[n][arcStartLocFieldName][0]
                arcStyle[n]['y1'] = arcs[n][arcStartLocFieldName][1]
                arcStyle[n]['x2'] = arcs[n][arcEndLocFieldName][0]
                arcStyle[n]['y2'] = arcs[n][arcEndLocFieldName][1]
            else:
                arcStyle[n]['x1'] = arcs[n][arcStartLocFieldName][1]
                arcStyle[n]['y1'] = arcs[n][arcStartLocFieldName][0]
                arcStyle[n]['x2'] = arcs[n][arcEndLocFieldName][1]
                arcStyle[n]['y2'] = arcs[n][arcEndLocFieldName][0]
        else:
            raise MissingParameterError("ERROR: Cannot find corresponded `arcFieldName` or (`arcStartLocFieldName` and `arcEndLocFieldName`) in given `arcs` structure.")

        # Color ---------------------------------------------------------------
        if ('color' in arcs[n]):
            arcStyle[n]['color'] = arcs[n]['color']
        elif (arcColor == 'Random'):
            arcStyle[n]['color'] = rndColor()
        else:
            arcStyle[n]['color'] = arcColor

        if ('startColor' in arcs[n]):
            arcStyle[n]['startColor'] = arcs[n]['startColor']
        elif (arcStartColor == 'Random'):
            arcStyle[n]['startColor'] = rndColor()
        else:
            arcStyle[n]['startColor'] = arcStartColor

        if ('endColor' in arcs[n]):
            arcStyle[n]['endColor'] = arcs[n]['endColor']
        elif (arcEndColor == 'Random'):
            arcStyle[n]['endColor'] = rndColor()
        else:
            arcStyle[n]['endColor'] = arcEndColor

        if ('markerSize' in arcs[n]):
            arcStyle[n]['markerSize'] = arcs[n]['markerSize']
        elif (arcEndColor == 'Random'):
            arcStyle[n]['markerSize'] = rndColor()
        else:
            arcStyle[n]['markerSize'] = arcMarkerSize

        # Dashes --------------------------------------------------------------
        if ('dashes' in arcs[n]):
            arcStyle[n]['dashes'] = arcs[n]['dashes']
        elif (arcDashes == None):
            arcStyle[n]['dashes'] = (None, None)
        else:
            arcStyle[n]['dashes'] = arcDashes

        # Width ---------------------------------------------------------------
        if ('width' in arcs[n]):
            arcStyle[n]['width'] = arcs[n]['width']
        else:
            arcStyle[n]['width'] = arcWidth

        # Style ---------------------------------------------------------------
        if ('style' in arcs[n]):
            arcStyle[n]['style'] = arcs[n]['style']
        else:
            arcStyle[n]['style'] = arcLineStyle

        # Label ---------------------------------------------------------------
        if ('label' in arcs[n]):
            arcStyle[n]['label'] = arcs[n]['label']
        else:
            arcStyle[n]['label'] = None

        if ('ha' in arcs[n]):
            arcStyle[n]['ha'] = arcs[n]['ha']
        else:
            arcStyle[n]['ha'] = 'left'
        
        if ('va' in arcs[n]):
            arcStyle[n]['va'] = arcs[n]['va']
        else:
            arcStyle[n]['va'] = 'top'

    # Draw arcs ===============================================================
    for n in arcs:
        # Plot arcs
        ax.plot(
            [arcStyle[n]['x1'], arcStyle[n]['x2']], 
            [arcStyle[n]['y1'], arcStyle[n]['y2']], 
            color = arcStyle[n]['color'], 
            linewidth=arcStyle[n]['width'], 
            linestyle = arcStyle[n]['style'], 
            dashes = arcStyle[n]['dashes'])
        # Plot arrows
        if (arrowFlag):
            length = distEuclideanXY((arcStyle[n]['x1'], arcStyle[n]['y1']), (arcStyle[n]['x2'], arcStyle[n]['y2']))
            if (arrowShowLimit == None or length >= arrowShowLimit):
                deg = headingXY([arcStyle[n]['x1'], arcStyle[n]['y1']], [arcStyle[n]['x2'], arcStyle[n]['y2']])
                ptC = [arcStyle[n]['x1'] + (arcStyle[n]['x2'] - arcStyle[n]['x1']) * arrowPosition, arcStyle[n]['y1'] + (arcStyle[n]['y2'] - arcStyle[n]['y1']) * arrowPosition]
                ptM = ptInDistXY(ptC, direction = deg + 180, dist = arrowHeadLength / 2)
                ptH = ptInDistXY(ptC, direction = deg, dist = arrowHeadLength / 2)
                pt1 = ptInDistXY(ptM, direction = deg + 90, dist = arrowHeadWidth / 2)
                pt2 = ptInDistXY(ptM, direction = deg - 90, dist = arrowHeadWidth / 2)
                ax.fill([ptH[0], pt1[0], pt2[0]], [ptH[1], pt1[1], pt2[1]], facecolor=arcStyle[n]['color'], edgecolor=arcStyle[n]['color'], linewidth=0)

        # Plot both ends
        ax.plot(arcStyle[n]['x1'], arcStyle[n]['y1'], 
            color = arcStyle[n]['startColor'], 
            marker = 'o', 
            markersize = arcStyle[n]['markerSize'])
        ax.plot(arcStyle[n]['x2'], arcStyle[n]['y2'], 
            color = arcStyle[n]['endColor'], 
            marker = 'o', 
            markersize = arcStyle[n]['markerSize'])

        # Plot label
        dx = arcStyle[n]['x2'] - arcStyle[n]['x1']
        dy = arcStyle[n]['y2'] - arcStyle[n]['y1']
        ax.annotate(arcStyle[n]['label'], 
            (arcStyle[n]['x1'] + dx / 2, arcStyle[n]['y1'] + dy / 2), 
            ha=arcStyle[n]['ha'], 
            va=arcStyle[n]['va'])

    # Draw arcs neighborhoods =================================================
    for n in arcs:
        if (neiAFieldName in arcs[n]):
            fig, ax = plotPoly(
                fig = fig,
                ax = ax,
                poly = arcs[n][neiAFieldName],
                edgeWidth = neighborEntWidth,
                edgeColor = 'black',
                fillColor = neighborEntColor,
                opacity = neighborOpacity,
                latLonFlag = latLonFlag,
                showAxis = showAxis,
                fillStyle = neighborFillStyle)
        if (neiBFieldName in arcs[n]):
            fig, ax = plotPoly(
                fig = fig,
                ax = ax,
                poly = arcs[n][neiBFieldName],
                edgeWidth = neighborEntWidth,
                edgeColor = 'black',
                fillColor = neighborEntColor,
                opacity = neighborOpacity,
                latLonFlag = latLonFlag,
                showAxis = showAxis,
                fillStyle = neighborFillStyle)
        if (neiBtwFieldName in arcs[n]):
            fig, ax = plotPoly(
                fig = fig,
                ax = ax,
                poly = arcs[n][neiBtwFieldName],
                edgeWidth = neighborBtwWidth,
                edgeColor = 'black',
                fillColor = neighborBtwColor,
                opacity = neighborOpacity,
                latLonFlag = latLonFlag,
                showAxis = showAxis,
                fillStyle = neighborFillStyle)

    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None and isinstance(fig, plt.Figure)):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotCurveArc(curveArc: CurveArc, lod: int = 30, **kwargs):

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Style characters ========================================================
    lineColor = 'Random' if 'lineColor' in kwargs else kwargs['lineColor']
    lineWidth = 1.0 if 'lineWidth' in kwargs else kwargs['lineWidth']
    lineStyle = 'solid' if 'lineStyle' in kwargs else kwargs['lineStyle']
    lineDashes = (5, 2) if 'lineDashes' in kwargs else kwargs['lineDashes']
    arrowFlag = True if 'arrowFlag' in kwargs else kwargs['arrowFlag']

    # Plot curve ==============================================================
    # 计算夹角和拆分出来的边数
    deltaDeg = curveArc.endDeg - curveArc.startDeg
    numInsert = max(2, int(lod * deltaDeg / 360))
    dg = deltaDeg / (numInsert)

    if (lineColor == 'Random'):
        lineColor = rndColor()

    # 生成曲线
    curve = []
    curve.append(ptInDistXY(
        pt = curveArc.center, 
        direction = curveArc.startDeg, 
        dist = curveArc.radius))
    for i in range(numInsert):
        curve.append(ptInDistXY(
            pt = curveArc.center, 
            direction = curveArc.startDeg + dg * i, 
            dist = curveArc.radius))
    curve.append(ptInDistXY(
        pt = curveArc.center, 
        direction = curveArc.endDeg, 
        dist = curveArc.radius))    

    fig, ax = plotLocSeq(
        fig = fig,
        ax = ax,
        locSeq = curve,
        lineColor = lineColor,
        lineWidth = lineWidth,
        lineStyle = lineStyle,
        lineDashes = lineDashes,
        nodeMarkerSize = 0,
        arrowFlag = False,
        figSize = figSize, 
        boundingBox = boundingBox,
        showAxis = showAxis,
        showFig = False
        )

    # Plot nodes ==============================================================
    nodes = {}
    for i in curveArc.traverse():
        nodes[i.key] = {'loc': i.loc, 'label': ""}
    fig, ax = plotNodes(
        fig = fig,
        ax = ax,
        nodes = nodes,
        nodeColor = lineColor,
        nodeMarkerSize = 4)

    # Save figure =============================================================
    if (saveFigPath != None and isinstance(fig, plt.Figure)):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotPathCover(locSeq: list[pt], radius: float, lod: int = 30, **kwargs):

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    edgeColor = 'Random' if 'edgeColor' not in kwargs else kwargs['edgeColor']
    edgeWidth = 1.0 if 'edgeWidth' not in kwargs else kwargs['edgeWidth']
    edgeStyle = 'solid' if 'edgeStyle' not in kwargs else kwargs['edgeStyle']
    edgeDashes = (5, 2) if 'edgeDashes' not in kwargs else kwargs['edgeDashes']
    fillColor = None if 'fillColor' not in kwargs else kwargs['fillColor']
    fillStyle = "///" if 'fillStyle' not in kwargs else kwargs['fillStyle']
    opacity = 0.5 if 'opacity' not in kwargs else kwargs['opacity']

    # curveArcs = {}
    # # NOTE: 先记录每个segment的角度
    # for i in range(1, len(locSeq) - 2):
    #     dir2Next = headingXY(locSeq[i], locSeq[i + 1])
    #     dir2Prev = headingXY(locSeq[i], locSeq[i - 1])
    fig, ax = plotCircle(
        fig = fig,
        ax = ax,
        lod = lod,
        center = locSeq[0],
        radius = radius,
        edgeWidth = 0.1,
        edgeColor = 'gray',
        fillColor = 'gray',
        fillStyle = '///',
        boundingBox = boundingBox,
        opacity = 0.3)

    for i in range(1, len(locSeq) - 1):
        # 分别看看和上一个点、下一个点的距离，会不会让圆相交
        # dist2Prev = distEuclideanXY(locSeq[i], locSeq[i - 1])
        dist2Next = distEuclideanXY(locSeq[i], locSeq[i + 1])

        # 如果分别到上一个和下一个都大于R，完整圆
        if (dist2Next > 2 * radius):
            fig, ax = plotCircle(
                fig = fig,
                ax = ax,
                lod = lod,
                center = locSeq[i],
                radius = radius,
                edgeWidth = 0.1,
                edgeColor = 'gray',
                fillColor = 'gray',
                fillStyle = '///',
                boundingBox = boundingBox,
                opacity = 0.3)
        # 如果没有大于L
        else:
            cir = circleByCenterXY(locSeq[i], radius, lod)
            cirNext = circleByCenterXY(locSeq[i + 1], radius, lod)
            subCir = polysSubtract(polys = [cir], subPolys = [cirNext])[0]
            fig, ax = plotPoly(
                fig = fig,
                ax = ax,
                poly = subCir,
                edgeWidth = 0.1,
                edgeColor = 'gray',
                fillColor = 'gray',
                fillStyle = '///',
                boundingBox = boundingBox,
                opacity = 0.3)

    for i in range(len(locSeq) - 1):
        deg = headingXY(locSeq[i], locSeq[i + 1])
        pt1 = ptInDistXY(locSeq[i], deg + 90, radius)
        pt2 = ptInDistXY(locSeq[i + 1], deg + 90, radius)
        pt3 = ptInDistXY(locSeq[i + 1], deg - 90, radius)
        pt4 = ptInDistXY(locSeq[i], deg - 90, radius)

        # Case 1: L > 2R
        L = distEuclideanXY(locSeq[i], locSeq[i + 1])
        if (L > 2 * radius):
            poly = [pt1, pt2, pt3, pt4]
            c1 = circleByCenterXY(locSeq[i], radius, lod)
            c2 = circleByCenterXY(locSeq[i + 1], radius, lod)
            poly = polysSubtract(polys = [poly], subPolys = [c1])[0]
            poly = polysSubtract(polys = [poly], subPolys = [c2])[0]
            fig, ax = plotPoly(
                fig = fig,
                ax = ax,
                poly = poly,
                edgeWidth = 0.1,
                edgeColor = 'gray',
                fillColor = 'gray',
                fillStyle = '///',
                boundingBox = boundingBox,
                opacity = 0.3)
        # Case 2: L <= 2R
        elif (L > radius):
            poly = [pt1, pt2, pt3, pt4]
            c1 = circleByCenterXY(locSeq[i], radius, lod)
            c2 = circleByCenterXY(locSeq[i + 1], radius, lod)
            poly = polysSubtract(polys = [poly], subPolys = [c1])[0]
            polys = polysSubtract(polys = [poly], subPolys = [c2])

            poly1 = polys[0]
            fig, ax = plotPoly(
                fig = fig,
                ax = ax,
                poly = poly1,
                edgeWidth = 0.1,
                edgeColor = 'gray',
                fillColor = 'gray',
                fillStyle = '///',
                boundingBox = boundingBox,
                opacity = 0.3)

            try:
                poly2 = polys[1]
                fig, ax = plotPoly(
                    fig = fig,
                    ax = ax,
                    poly = poly2,
                    edgeWidth = 0.1,
                    edgeColor = 'gray',
                    fillColor = 'gray',
                    fillStyle = '///',
                    boundingBox = boundingBox,
                    opacity = 0.3)
            except:
                pass
                
        # Case 3: L < R
        elif (L < radius):
            try:
                poly = [pt1, pt2, pt3, pt4]
                c1 = circleByCenterXY(locSeq[i], radius, lod)
                c2 = circleByCenterXY(locSeq[i + 1], radius, lod)
                polys = polysSubtract(polys = [poly], subPolys = [c1])
                poly1 = polys[0]
                poly2 = polys[1]
                poly1 = polysSubtract(polys = [poly1], subPolys = [c2])[0]
                poly2 = polysSubtract(polys = [poly2], subPolys = [c2])[0]

                fig, ax = plotPoly(
                    fig = fig,
                    ax = ax,
                    poly = poly1,
                    edgeWidth = 0.1,
                    edgeColor = 'gray',
                    fillColor = 'gray',
                    fillStyle = '///',
                    boundingBox = boundingBox,
                    opacity = 0.3)
                fig, ax = plotPoly(
                    fig = fig,
                    ax = ax,
                    poly = poly2,
                    edgeWidth = 0.1,
                    edgeColor = 'gray',
                    fillColor = 'gray',
                    fillStyle = '///',
                    boundingBox = boundingBox,
                    opacity = 0.3)
            except:
                pass

    return fig, ax

def plotLocSeq(locSeq: list[pt], splFlag = False, **kwargs):
    
    """Given a list of coordinates, plot a open polyline by sequences.

    Parameters
    ----------

    locSeq: list[pt], required
        A list of coordinates to form a sequence
    splFlag: bool, required
        True if draw a spline curve instead of line segments

    Returns
    -------
    fig, ax: matplotlib.pyplot object
    """

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    lineColor = 'Random' if 'lineColor' not in kwargs else kwargs['lineColor']
    lineWidth = 1.0 if 'lineWidth' not in kwargs else kwargs['lineWidth']
    lineStyle = 'solid' if 'lineStyle' not in kwargs else kwargs['lineStyle']
    lineDashes = (5, 2) if 'lineDashes' not in kwargs else kwargs['lineDashes']
    nodeColor = 'black' if 'nodeColor' not in kwargs else kwargs['nodeColor']
    nodeMarkerSize = 1 if 'nodeMarkerSize' not in kwargs else kwargs['nodeMarkerSize']
    arrowFlag = True if 'arrowFlag' not in kwargs else kwargs['arrowFlag']
    arrowPosition = 0.5 if 'arrowPosition' not in kwargs else kwargs['arrowPosition']
    arrowHeadWidth = 0.1 if 'arrowHeadWidth' not in kwargs else kwargs['arrowHeadWidth']
    arrowHeadLength = 0.2 if 'arrowHeadLength' not in kwargs else kwargs['arrowHeadLength']
    arrowShowLimit = None if 'arrowShowLimit' not in kwargs else kwargs['arrowShowLimit']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    # Check for required fields ===============================================
    if (fig == None or ax == None):
        fig, ax = plt.subplots()
        boundingBox = defaultBoundingBox(
            boundingBox = boundingBox, 
            pts = locSeq,
            latLonFlag = latLonFlag)
        (xMin, xMax, yMin, yMax) = boundingBox
        (width, height) = defaultFigSize(boundingBox, figSize[0], figSize[1], latLonFlag)

        if (not latLonFlag):
            fig.set_figwidth(width)
            fig.set_figheight(height)
            ax.set_xlim(xMin, xMax)
            ax.set_ylim(yMin, yMax)
        else:
            fig.set_figwidth(height)
            fig.set_figheight(width)
            ax.set_xlim(yMin, yMax)
            ax.set_ylim(xMin, xMax)

    if (locSeq == None):
        raise MissingParameterError("ERROR: Missing required field `locSeq`.")
    if (lineStyle == 'solid'):
        lineDashes = (None, None)

    if (arrowFlag):
        if (splFlag):
            raise UnsupportedInputError("ERROR: splFlag not supported for arrows yet.")
        arcs = {}
        for i in range(len(locSeq) - 1):
            if (not is2PtsSame(locSeq[i], locSeq[i + 1])):
                arcs[i] = {'arc': [locSeq[i], locSeq[i + 1]]}

        # Color ===================================================================
        if (lineColor == 'Random'):
            lineColor = rndColor()

        fig, ax = plotArcs(
            fig = fig,
            ax = ax,
            arcs = arcs,
            arcFieldName = 'arc',
            arcColor = lineColor,
            arcWidth = lineWidth,
            arcLineStyle = lineStyle,
            arcDashes = lineDashes if lineStyle == 'dashed' else (None, None),
            arcLabel = "",
            arrowFlag = arrowFlag,
            arrowPosition = arrowPosition,
            arrowHeadWidth = arrowHeadWidth,
            arrowHeadLength = arrowHeadLength,
            arrowShowLimit = arrowShowLimit,
            arcStartColor = nodeColor,
            arcEndColor = nodeColor ,
            arcMarkerSize = nodeMarkerSize,
            latLonFlag = latLonFlag,
            figSize = figSize,
            boundingBox = boundingBox,
            showAxis = showAxis,
            saveFigPath = saveFigPath,
            showFig = showFig)
    else:
        x = []
        y = []

        if (not splFlag):
            for pt in locSeq:
                if (latLonFlag):
                    x.append(pt[1])
                    y.append(pt[0])
                else:
                    x.append(pt[0])
                    y.append(pt[1])
        else:
            lc = None
            if (latLonFlag):
                lc = [(i[1], i[0]) for i in locSeq]
            else:
                lc = locSeq

            points = np.array(locSeq)
            tck, u = splprep(points.T, u=None, s=0.0, per=False)
            u_new = np.linspace(0, 1, lod)
            x_smooth, y_smooth = splev(u_new, tck, der=0)

            for i in range(len(x_smooth)):
                x.append(x_smooth[i])
                y.append(y_smooth[i])

        color = None
        if (lineColor == 'Random'):
            color = rndColor()
        elif (type(lineColor) == str):
            color = lineColor
        ax.plot(x, y, color = color, linewidth = lineWidth, linestyle = lineStyle, dashes = lineDashes)

    return fig, ax

def plotLocSeq3D(locSeq3D: list[pt3D], **kwargs):

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox3D = (None, None, None, None, None, None) if 'boundingBox3D' not in kwargs else kwargs['boundingBox3D']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    lineColor = 'Random' if 'lineColor' not in kwargs else kwargs['lineColor']
    lineWidth = 1.0 if 'lineWidth' not in kwargs else kwargs['lineWidth']
    lineStyle = 'solid' if 'lineStyle' not in kwargs else kwargs['lineStyle']
    lineDashes = (5, 2) if 'lineDashes' not in kwargs else kwargs['lineDashes']
    nodeColor = 'black' if 'nodeColor' not in kwargs else kwargs['nodeColor']
    nodeMarkerSize = 1 if 'nodeMarkerSize' not in kwargs else kwargs['nodeMarkerSize']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    # Check for required fields ===============================================
    if (locSeq3D == None):
        raise MissingParameterError("ERROR: Missing required field `locSeq3D`.")

    # If no based matplotlib figure provided, define boundary =================
    if (fig == None or ax == None):
        fig = plt.figure()
        ax = plt.axes(projection = '3d')
        (xMin, xMax, yMin, yMax, zMin, zMax) = defaultBoundingBox(
            boundingBox3D = boundingBox3D,
            locs3D = locSeq3D)
        ax.set_xlim(xMin, xMax)
        ax.set_ylim(yMin, yMax)
        ax.set_zlim(zMin, zMax)

    x = []
    y = []
    z = []
    for loc in locSeq3D:
        if (not latLonFlag):
            x.append(loc[0])
            y.append(loc[1])
        else:
            x.append(loc[1])
            y.append(loc[0])
        z.append(loc[2])

    color = None
    if (lineColor == 'Random'):
        color = rndColor()
    else:
        color = lineColor

    if (lineStyle == 'dashed'):
        ax.plot(x, y, z, c = color, linewidth=lineWidth, linestyle = 'dashed', dashes = lineDashes)
    else:
        ax.plot(x, y, z, c = color, linewidth=lineWidth, linestyle = lineStyle)
            
    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None and isinstance(fig, plt.Figure)):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotNodeSeq(nodes: dict, nodeSeq: list[int|str], **kwargs):

    """Given a `nodes` dictionary and a sequence of node IDs, plot a route that visits each node by IDs.

    Parameters
    ----------
    nodes: dict, required
        A `node` dictionary. See :ref:`nodes` for reference.
    nodeSeq: list[int|str], required
        A list of nodeIDs which will form a visiting sequence

    Returns
    -------
    fig, ax: matplotlib.pyplot object
    """

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    lineColor = 'Random' if 'lineColor' not in kwargs else kwargs['lineColor']
    lineWidth = 1 if 'lineWidth' not in kwargs else kwargs['lineWidth']
    lineStyle = 'solid' if 'lineStyle' not in kwargs else kwargs['lineStyle']
    lineDashes = (5, 2) if 'lineDashes' not in kwargs else kwargs['lineDashes']
    nodeColor = 'black' if 'nodeColor' not in kwargs else kwargs['nodeColor']
    nodeMarkerSize = 1 if 'nodeMarkerSize' not in kwargs else kwargs['nodeMarkerSize']
    arrowFlag = True if 'arrowFlag' not in kwargs else kwargs['arrowFlag']
    arrowPosition = 0.5 if 'arrowPosition' not in kwargs else kwargs['arrowPosition']
    arrowHeadWidth = 0.1 if 'arrowHeadWidth' not in kwargs else kwargs['arrowHeadWidth']
    arrowHeadLength = 0.2 if 'arrowHeadLength' not in kwargs else kwargs['arrowHeadLength']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    # Field names =============================================================
    locFieldName = 'loc' if 'locFieldName' not in kwargs else kwargs['locFieldName']

    # Create arcs =============================================================
    if (nodeSeq == None):
        raise MissingParameterError("ERROR: Missing required field `nodeSeq`.")
    # Call plotArcs ===========================================================
    for n in nodeSeq:
        if (n not in nodes):
            raise UnsupportedInputError("ERROR: Cannot find %s in nodes" % n)

    arcs = {}
    for i in range(len(nodeSeq) - 1):
        arcs[i] = {'arc': [nodes[nodeSeq[i]][locFieldName], nodes[nodeSeq[i + 1]][locFieldName]]}

    # Color ===================================================================
    if (lineColor == 'Random'):
        lineColor = rndColor()

    fig, ax = plotArcs(
        fig = fig,
        ax = ax,
        arcs = arcs,
        arcFieldName = 'arc',
        arcColor = lineColor,
        arcWidth = lineWidth,
        arcStyle = lineStyle,
        arcDashes = lineDashes if lineStyle == 'dashed' else (None, None),
        arcLabel = "",
        arcStartColor = nodeColor,
        arcEndColor = nodeColor,
        arcMarkerSize = nodeMarkerSize,
        arrowFlag = arrowFlag,
        arrowPosition = arrowPosition,
        arrowHeadWidth = arrowHeadWidth,
        arrowHeadLength = arrowHeadLength,        
        latLonFlag = latLonFlag,
        figSize = figSize,
        boundingBox = boundingBox,
        showAxis = showAxis,
        saveFigPath = saveFigPath,
        showFig = showFig)

    return fig, ax

def plotPoly(poly: poly, **kwargs):

    """Draw a polygon

    Parameters
    ----------

    poly: poly, required, default None
        A polygon to be plotted

    Returns
    -------
    fig, ax: matplotlib.pyplot object
    """

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    edgeWidth = 0.5 if 'edgeWidth' not in kwargs else kwargs['edgeWidth']
    edgeColor = 'Random' if 'edgeColor' not in kwargs else kwargs['edgeColor']
    fillColor = None if 'fillColor' not in kwargs else kwargs['fillColor']
    fillStyle = "///" if 'fillStyle' not in kwargs else kwargs['fillStyle']
    opacity = 0.5 if 'opacity' not in kwargs else kwargs['opacity']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    # Check for required fields ===============================================
    if (poly == None):
        raise MissingParameterError("ERROR: Missing required field `poly`.")

    # If no based matplotlib figure provided, define boundary =================
    if (fig == None or ax == None):
        fig, ax = plt.subplots()
        boundingBox = defaultBoundingBox(
            boundingBox = boundingBox, 
            poly = poly,
            latLonFlag = latLonFlag)

        (xMin, xMax, yMin, yMax) = boundingBox
        width = None
        height = None
        if (figSize == None or figSize[0] == None or figSize[1] == None):
            (width, height) = defaultFigSize(boundingBox, figSize[0], figSize[1], latLonFlag)
        else:
            (width, height) = figSize

        fig.set_figwidth(width)
        fig.set_figheight(height)
        ax.set_xlim(xMin, xMax)
        ax.set_ylim(yMin, yMax)

    # Get the x, y list =======================================================
    x = []
    y = []
    for pt in poly:
        if (not latLonFlag):
            x.append(pt[0])
            y.append(pt[1])
        else:
            x.append(pt[1])
            y.append(pt[0])
    if (not latLonFlag):
        x.append(poly[0][0])
        y.append(poly[0][1])
    else:
        x.append(poly[0][1])
        y.append(poly[0][0])

    if (abs(x[-1] - x[0]) > ERRTOL['distPt2Pt']):
        x.append(x[0])
        y.append(y[0])

    # Plot ====================================================================
    if (edgeColor == 'Random'):
        edgeColor = rndColor()
    if (fillColor == None):
        ax.plot(x, y, color = edgeColor, linewidth = edgeWidth)
    else:
        if (fillColor == 'Random'):
            ax.fill(x, y, facecolor=rndColor(), edgecolor=edgeColor, hatch=fillStyle, linewidth=edgeWidth, alpha=opacity)
        else:
            ax.fill(x, y, facecolor=fillColor, edgecolor=edgeColor, hatch=fillStyle, linewidth=edgeWidth, alpha=opacity)

    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None and isinstance(fig, plt.Figure)):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotCircle(center: pt, radius: float, lod: int = 30, **kwargs):

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    edgeWidth = 0.5 if 'edgeWidth' not in kwargs else kwargs['edgeWidth']
    edgeColor = 'Random' if 'edgeColor' not in kwargs else kwargs['edgeColor']
    fillColor = None if 'fillColor' not in kwargs else kwargs['fillColor']
    fillStyle = "///" if 'fillStyle' not in kwargs else kwargs['fillStyle']
    opacity = 0.5 if 'opacity' not in kwargs else kwargs['opacity']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    # Create polygon ==========================================================
    polyCircle = [[
        center[0] + radius * math.sin(2 * d * math.pi / lod),
        center[1] + radius * math.cos(2 * d * math.pi / lod),
    ] for d in range(lod + 1)]

    # Plot polygon ============================================================
    fig, ax = plotPoly(
        poly = polyCircle,
        edgeWidth = edgeWidth,
        edgeColor = edgeColor,
        fillColor = fillColor,
        fillStyle = fillStyle,
        opacity = opacity,
        latLonFlag = latLonFlag,
        fig = fig,
        ax = ax,
        figSize = figSize,
        boundingBox = boundingBox,
        showAxis = showAxis,
        saveFigPath = saveFigPath,
        showFig = showFig,
    )
    return fig, ax

def plotTimedPoly(timedPoly, triGridSurface = None, plotPolyFlag = True, plotSurfaceFlag = True, **kwargs):

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox3D = (None, None, None, None, None, None) if 'boundingBox3D' not in kwargs else kwargs['boundingBox3D']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    lineColor = 'Random' if 'lineColor' not in kwargs else kwargs['lineColor']
    lineWidth = 1.0 if 'lineWidth' not in kwargs else kwargs['lineWidth']
    lineStyle = 'solid' if 'lineStyle' not in kwargs else kwargs['lineStyle']
    lineDashes = (5, 2) if 'lineDashes' not in kwargs else kwargs['lineDashes']
    surfaceColor = 'Random' if 'surfaceColor' not in kwargs else kwargs['surfaceColor']
    surfaceOpacity = 0.2 if 'surfaceOpacity' not in kwargs else kwargs['surfaceOpacity']

    if (lineColor == 'Random'):
        lineColor = rndColor()
    if (surfaceColor == 'Random'):
        surfaceColor = rndColor()

    # If no based matplotlib figure provided, define boundary =================
    if (fig == None or ax == None):
        fig = plt.figure()
        ax = plt.axes(projection = '3d')
        (xMin, xMax, yMin, yMax, zMin, zMax) = defaultBoundingBox3D(
            boundingBox3D = boundingBox3D,
            timedPoly = timedPoly)
        ax.set_xlim(xMin, xMax)
        ax.set_ylim(yMin, yMax)
        ax.set_zlim(zMin, zMax)

    # Plot polys in time ======================================================
    if (plotPolyFlag):
        for k in timedPoly:
            locSeq3D = []
            for pt in k[0]:
                locSeq3D.append((pt[0], pt[1], k[1]))
            locSeq3D.append((k[0][0][0], k[0][0][1], k[1]))
            fig, ax = plotLocSeq3D(
                fig = fig,
                ax = ax,
                locSeq3D = locSeq3D,
                lineColor = lineColor,
                lineWidth = lineWidth,
                lineStyle = lineStyle,
                lineDashes = lineDashes)

    # Plot surface ============================================================
    if (plotSurfaceFlag):
        if (triGridSurface == None):
            triGridSurface = TriGridSurface(timedPoly)
        ax.add_collection3d(Poly3DCollection(triGridSurface.tris, alpha = surfaceOpacity, edgecolor = surfaceColor))
    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None and isinstance(fig, plt.Figure)):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotPolygons(polygons: dict, **kwargs):

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    showAnchorFlag = True if 'showAnchorFlag' not in kwargs else kwargs['showAnchorFlag']
    anchorFieldName = 'anchor' if 'anchorFieldName' not in kwargs else kwargs['anchorFieldName']
    edgeWidth = 0.5 if 'edgeWidth' not in kwargs else kwargs['edgeWidth']
    edgeColor = 'Random' if 'edgeColor' not in kwargs else kwargs['edgeColor']
    fillColor = None if 'fillColor' not in kwargs else kwargs['fillColor']
    fillStyle = "///" if 'fillStyle' not in kwargs else kwargs['fillStyle']
    opacity = 0.5 if 'opacity' not in kwargs else kwargs['opacity']
    latLonFlag = False if 'latLonFlag' not in kwargs else kwargs['latLonFlag']

    polyFieldName = 'poly' if 'polyFieldName' not in kwargs else kwargs['polyFieldName']

    # Sanity check ============================================================
    if (type(polygons) != dict):
        raise UnsupportedInputError("ERROR: `polygons` is a dictionary, to plot an individual polygon, please use plotPoly() instead.")

    # If no based matplotlib figure provided, define boundary =================
    if (fig == None or ax == None):
        fig, ax = plt.subplots()
        boundingBox = defaultBoundingBox(
            boundingBox = boundingBox, 
            polygons = polygons,
            anchorFieldName = anchorFieldName,
            polyFieldName = polyFieldName,
            latLonFlag = latLonFlag)
        (xMin, xMax, yMin, yMax) = boundingBox
        (width, height) = defaultFigSize(boundingBox, figSize[0], figSize[1], latLonFlag)
        if (isinstance(fig, plt.Figure)):
            fig.set_figwidth(width)
            fig.set_figheight(height)
            ax.set_xlim(xMin, xMax)
            ax.set_ylim(yMin, yMax)

    # First, plot polygons ====================================================
    for p in polygons:
        fig, ax = plotPoly(
            fig = fig,
            ax = ax,
            poly = polygons[p][polyFieldName],
            edgeWidth = edgeWidth,
            edgeColor = edgeColor,
            fillColor = fillColor,
            fillStyle = fillStyle,
            opacity = opacity,
            latLonFlag = latLonFlag,
            figSize = figSize)

    # Next, plot anchors ======================================================
    if (showAnchorFlag):
        for p in polygons:
            if ('label' not in polygons[p]):
                lbl = p
            else:
                lbl = polygons[p]['label']
            ha = 'center'
            va = 'center'
            ct = polygons[p]['anchor']
            if (latLonFlag):
                ct = [ct[1], ct[0]]
            ax.annotate(lbl, ct, ha=ha, va=va)

    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None and isinstance(fig, plt.Figure)):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotMapChina(
    regionList: list,
    readFromLocalFlag: bool = True,
    localDirectory: str = "D:/Zoo/gull/geoVeRoPy/data/map",
    saveToLocalFlag: bool = True,
    edgeWidth: float = 0.5,
    edgeColor: str = 'Random',
    fillColor: str|None = None,
    fillStyle: str = "///",
    opacity: float = 0.5,   
    **kwargs
    ):

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    multiPoly = []

    # 一会儿要绘制的边界线们
    for region in regionList:
        multiPoly.extend(findPolysChina(
            province = region[0],
            city = region[1],
            district = region[2],
            readFromLocalFlag = readFromLocalFlag,
            localDirectory = localDirectory,
            saveToLocalFlag = saveToLocalFlag))

    # 计算范围大小
    x = []
    y = []
    for polys in multiPoly:
        for poly in polys:
            for pt in poly:
                x.append(pt[0])
                y.append(pt[1])
    boundingBox = (min(x), max(x), min(y), max(y))
    figSize = defaultFigSize(boundingBox, figSize[0], figSize[1], True)

    # 读取本地的
    for polys in multiPoly:
        for poly in polys:
            fig, ax = plotPoly(
                fig = fig,
                ax = ax,
                poly = poly,
                edgeWidth = edgeWidth,
                edgeColor = edgeColor,
                fillColor = fillColor,
                fillStyle = fillStyle,
                opacity = opacity,
                latLonFlag = True,
                boundingBox = boundingBox,
                figSize = figSize,
                saveFigPath = saveFigPath,
                showAxis = showAxis,
                showFig = showFig)

    return fig, ax

def plotMapUS(
    stateList: list[str]|str = [],
    edgeWidth: float = 0.5,
    edgeColor: str = 'Random',
    fillColor: str|None = None,
    fillStyle: str = "///",
    opacity: float = 0.5,   
    **kwargs
    ):

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    if (fig == None or ax == None):
        fig, ax = plt.subplots()
    
    prvPoly = {}
    if (type(stateList) == str):
        stateList = [stateList]
    for prv in stateList:
        if prv in prov:
            ct = ptPolyCenter(prov[prv]['shape'])
            prvPoly[prv] = {
                'anchor': ct,
                'label': prov[prv]['abbr'],
                'poly': prov[prv]['shape'],
            }
        else:
            for k in prov:
                if (prv == prov[k]['abbr']):
                    ct = ptPolyCenter(prov[k]['shape'])
                    prvPoly[prv] = {
                        'anchor': ct,
                        'label': prov[k]['abbr'],
                        'poly': prov[k]['shape'],
                    }

    fig, ax = plotPolygons(
        fig = fig,
        ax = ax,
        polygons = prvPoly,
        showAnchorFlag = False,
        edgeWidth = edgeWidth,
        edgeColor = edgeColor,
        fillColor = fillColor,
        fillStyle = fillStyle,
        opacity = opacity,
        latLonFlag = True,
        figSize = figSize,
        saveFigPath = saveFigPath,
        showAxis = showAxis,
        showFig=showFig)

    return fig, ax

def plotRoads(
    roads: dict,
    roadBoundary: poly|polys = None,
    roadWidth: dict[str,float]|float = {
            'motorway': 2,
            'motorway_link': 2,
            'truck': 1.5,
            'truck_link': 1.5,
            'primary': 1.2,
            'primary_link': 1.2,
            'secondary': 1,
            'secondary_link': 1,
            'tertiary': 1,
            'tertiary_link': 1,
            'residential': 0.8,
            'others': 0.8
        },
    roadColors: dict[str,str]|str = {
            'motorway': 'red',
            'motorway_link': 'red',
            'truck': 'orange',
            'truck_link': 'orange',
            'primary': 'orange',
            'primary_link': 'orange',
            'secondary': 'orange',
            'secondary_link': 'orange',
            'tertiary': 'orange',
            'tertiary_link': 'orange',
            'residential': 'green',
            'others': 'gray'
        },
    roadShowFlags: list[str, bool]|str|bool = 'All',
    **kwargs
    ): 

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # FIXME: In future, we might want to distinguish roads by max speed or show the names of roads
    # If no based matplotlib figure, define boundary ==========================
    if (fig == None or ax == None):
        fig, ax = plt.subplots()
        allX = []
        allY = []
        if (roadBoundary != None):
            try:    
                for poly in roadBoundary:
                    for pt in poly:
                        allX.append(float(pt[0]))
                        allY.append(float(pt[1]))
            except:
                for pt in roadBoundary:
                    allX.append(float(pt[0]))
                    allY.append(float(pt[1]))
        else:
            for road in roads:
                for pt in roads[road]['shape']:
                    allX.append(pt[0])
                    allY.append(pt[1])

        (xMin, xMax, yMin, yMax) = boundingBox
        if (xMin == None):
            xMin = min(allX) - 0.05 * abs(max(allX) - min(allX))
        if (xMax == None):
            xMax = max(allX) + 0.05 * abs(max(allX) - min(allX))
        if (yMin == None):
            yMin = min(allY) - 0.05 * abs(max(allY) - min(allY))
        if (yMax == None):
            yMax = max(allY) + 0.05 * abs(max(allY) - min(allY))
        boundingBox = (xMin, xMax, yMin, yMax)
        figSize = defaultFigSize(boundingBox, figSize[0], figSize[1], True)
        (width, height) = figSize

        fig.set_figwidth(width)
        fig.set_figheight(height)
        ax.set_xlim(yMin, yMax)
        ax.set_ylim(xMin, xMax)

    # Plot roads ==============================================================
    for road in roads:
        if (roadShowFlags == 'All' or roadShowFlags == True 
            or (type(roadShowFlags) == list 
                and roads[road]['class'] in roadShowFlags)):
            x = []
            y = []
            for pt in roads[road]['shape']:
                x.append(pt[1])
                y.append(pt[0])
            color = None
            if (roadColors == 'Random'):
                color = rndColor()
            elif (type(roadColors) == str):
                color = roadColors
            elif (type(roadColors) == dict):
                if (roads[road]['class'] in roadColors):
                    color = roadColors[roads[road]['class']]
                else:
                    color = roadColors['others']
            rw = 1
            if (type(roadWidth) == dict):
                if (roads[road]['class'] in roadWidth):
                    rw = roadWidth[roads[road]['class']]
            else:
                rw = roadWidth
            ax.plot(x, y, color = color, linewidth = rw)

    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotBuildings(
    buildings: dict,
    buildingBoundary: poly|polys = None,
    buildingColors: dict[str,str]|str = {
            'building': 'yellow',
            'commercial': 'yellow',
            'residential': 'green',
            'house': 'green',
            'static_caravan': 'green',
            'industrial': 'orange',
            'manufacture': 'orange'
        },
    buildingShowFlags: list[str, bool]|str|bool = False,
    **kwargs
    ):

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox = (None, None, None, None) if 'boundingBox' not in kwargs else kwargs['boundingBox']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # FIXME: In future, we might want to distinguish roads by max speed or show the names of roads
    # If no based matplotlib figure, define boundary ==========================
    if (fig == None or ax == None):
        fig, ax = plt.subplots()
        allX = []
        allY = []
        if (buildingBoundary != None):
            try:    
                for poly in buildingBoundary:
                    for pt in poly:
                        allX.append(float(pt[1]))
                        allY.append(float(pt[0]))
            except:
                for pt in buildingBoundary:
                    allX.append(float(pt[1]))
                    allY.append(float(pt[0]))

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

        if (isinstance(fig, plt.Figure)):
            fig.set_figwidth(width)
            fig.set_figheight(height)
            ax.set_xlim(xMin, xMax)
            ax.set_ylim(yMin, yMax)

    # Plot buildings ==========================================================
    for building in buildings:
        if (buildingShowFlags == 'All' or buildingShowFlags == True
            or (type(buildingShowFlags) == list
                and buildings[building]['type'] in buildingShowFlags)):
            x = []
            y = []
            color = None
            for pt in buildings[building]['shape']:
                x.append(pt[1])
                y.append(pt[0])
            if (buildingColors == 'Random'):
                color = rndColor()
            elif (type(buildingColors) == str):
                color = buildingColors
            elif (type(buildingColors) == dict):
                if (buildings[building]['type'] in buildingColors):
                    color = buildingColors[buildings[building]['type']]
                else:
                    color = 'gray'
            ax.fill(x, y, facecolor=color)

    # Axis on and off =========================================================
    if (not showAxis):
        plt.axis('off')

    # Save figure =============================================================
    if (saveFigPath != None):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax

def plotGantt(
    gantt: list[dict],
    group: list[dict] | None = None, 
    phase: list[dict] | None = None,
    xlabel: str = "Time",
    ylabel: str = "",
    startTime: float = 0,
    endTime: float|None = None,
    **kwargs
    ) -> "Given a Gantt dictionary, plot Gantt":

    """Given a Gantt dictionary, plot a Gantt chart

    Parameters
    ----------
    gantt: list of dictionaries, required
        A list of dictionaries, each represents a gantt block, in the following format\
            >>> gantt = [{
            ...     'entityID': entityID, 
            ...     'timeWindow': [startTime, endTime], 
            ...     'desc': (optional) description of the window,
            ...     'color': (optional, default as 'random') color, 
            ...     'style': (optional, default as 'solid') 'solid' 
            ... }, ... ]
    group: list of dictionaries, optional, default []
        Groups of entityIDs, in the following format
            >>> group = [{
            ...     'title': groupTitle,
            ...     'entities': [entityID1, entityID2, ...],
            ...     'showFlag': True,
            ...     'backgroundColor': 'gray',
            ...     'backgroundOpacity': 0.5
            ... }, ... ]
    phase: list of dictionaries, optional, default []
        A list of phases, in the following format
            >>> phase = [{
            ...     'title': phaseTitle,
            ...     'timeWindow': [startTime, endTime],
            ...     'backgroundColor': 'gray',
            ...     'backgroundOpacity': 0.5
            ... }, ... ]
    xlabel: string, optional, default "Time"
        The label of x-axis
    ylabel: string, optional, default ""
        The label of y-axis
    """

    # Matplotlib characters ===================================================
    fig = None if 'fig' not in kwargs else kwargs['fig']
    ax = None if 'ax' not in kwargs else kwargs['ax']
    figSize = (None, 5) if 'figSize' not in kwargs else kwargs['figSize']
    boundingBox3D = (None, None, None, None, None, None) if 'boundingBox3D' not in kwargs else kwargs['boundingBox3D']
    showAxis = True if 'showAxis' not in kwargs else kwargs['showAxis']
    saveFigPath = None if 'saveFigPath' not in kwargs else kwargs['saveFigPath']
    showFig = True if 'showFig' not in kwargs else kwargs['showFig']

    # Styling characters ======================================================
    ganttHeight = 0.8 if 'ganttHeight' not in kwargs else kwargs['ganttHeight']
    ganttLinewidth = 1.0 if 'ganttLinewidth' not in kwargs else kwargs['ganttLinewidth']
    ganttBlockHeight = 1.0 if 'ganttBlockHeight' not in kwargs else kwargs['ganttBlockHeight']
    groupSeparatorHeight = 0.5 if 'groupSeparatorHeight' not in kwargs else kwargs['groupSeparatorHeight']
    groupSeparatorStyle = "-" if 'groupSeparatorStyle' not in kwargs else kwargs['groupSeparatorStyle']
    groupSeparatorLinewidth = 0.5 if 'groupSeparatorLinewidth' not in kwargs else kwargs['groupSeparatorLinewidth']
    groupSeparatorColor = 'gray' if 'groupSeparatorColor' not in kwargs else kwargs['groupSeparatorColor']
    phaseSeparatorStyle = "--" if 'phaseSeparatorStyle' not in kwargs else kwargs['phaseSeparatorStyle']
    phaseSeparatorLinewidth = 0.5 if 'phaseSeparatorLinewidth' not in kwargs else kwargs['phaseSeparatorLinewidth']
    phaseSeparatorColor = 'gray' if 'phaseSeparatorColor' not in kwargs else kwargs['phaseSeparatorColor']
    entitiesOffset = {} if 'entitiesOffset' not in kwargs else kwargs['entitiesOffset']

    # Check for required fields ===============================================
    if (gantt == None):
        raise MissingParameterError(ERROR_MISSING_GANTT)

    # Pre-calculate ===========================================================
    realStart = None
    realEnd = None
    for g in gantt:
        if ('entityID' not in g or 'timeWindow' not in g):
            raise MissingParameterError("ERROR: Missing 'entityID' and 'timeWindow' in gantt.")

        if (realStart == None or realStart > g['timeWindow'][0]):
            realStart = g['timeWindow'][0]
        if (realEnd == None or realEnd < g['timeWindow'][1]):
            realEnd = g['timeWindow'][1]
    if (startTime == None):
        startTime = realStart
    if (endTime == None):
        endTime = realEnd

    # Arrange entities ========================================================
    if (group == None or group == []):
        group = [{
            'title': "",
            'entities': [],
            'showFlag': True,
            'backgroundColor': None,
            'backgroundOpacity': 0
        }]
        for g in gantt:
            if (g['entityID'] not in group[0]['entities']):
                group[0]['entities'].append(g['entityID'])

    entities = []
    for g in group:
        if (g['showFlag']):
            entities.extend(g['entities'])
            entities.append(None)
    if (entities[-1] == None):
        entities = entities[:-1]
    entities.reverse()

    totalHeight = len([i for i in entities if i != None]) * ganttBlockHeight + len([i for i in entities if i == None]) * groupSeparatorHeight
    yAcc = 0.5 * ganttBlockHeight
    yticks = [0.5 * ganttBlockHeight]
    for i in range(1, len(entities)):        
        if (entities[i - 1] != None and entities[i] != None):
            yAcc += ganttBlockHeight
            yticks.append(yAcc)
        elif (entities[i - 1] == None or entities[i] == None):
            yAcc += 0.5 * groupSeparatorHeight + 0.5 * ganttBlockHeight
            yticks.append(yAcc)

    # If no based matplotlib figure, define fig size ==========================
    if (fig == None or ax == None):
        fig, ax = plt.subplots()
        width = 0
        height = 0
        if (figSize == None or (figSize[0] == None and figSize[1] == None)):
            width = 5 * ((endTime - startTime) / totalHeight)
            height = 5
        elif (figSize != None and figSize[0] != None and figSize[1] == None):
            width = figSize[0]
            height = figSize[0] * (totalHeight / (endTime - startTime))
        elif (figSize != None and figSize[0] == None and figSize[1] != None):
            width = figSize[1] * ((endTime - startTime) / totalHeight)
            height = figSize[1]
        else:
            (width, height) = figSize
        if (isinstance(fig, plt.Figure)):
            fig.set_figwidth(width)
            fig.set_figheight(height)
            ax.set_xlim(startTime, endTime + (endTime - startTime) * 0.05)
            ax.set_ylim(0, totalHeight)
    ax.set_yticks(yticks)   
    ax.set_yticklabels(entities)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)

    # Plot groups =============================================================
    groupColor = []
    groupOpacity = []
    groupTitle = []
    for i in range(len(group)):
        if (group[i]['showFlag']):
            if (group[i]['backgroundColor'] != 'Random'):
                groupColor.append(group[i]['backgroundColor'])
            else:
                groupColor.append(rndColor())
            groupOpacity.append(group[i]['backgroundOpacity'])
            groupTitle.append(group[i]['title'])
    groupStyle = []
    yS = 0
    yE = 0
    for i in range(len(entities)):
        if (entities[i] == None):
            yE = yticks[i]
            groupStyle.append([yS, yE])
            yS = yticks[i]
    groupStyle.append([yS, yticks[-1] + 0.5 * ganttBlockHeight])
    for g in range(len(groupStyle)):
        s = groupStyle[g][0]
        e = groupStyle[g][1]
        ax.fill([startTime, startTime, endTime + (endTime - startTime) * 0.05, endTime + (endTime - startTime) * 0.05, startTime], 
            [s, e, e, s, s], color=groupColor[g], alpha=groupOpacity[g])
        ax.annotate(groupTitle[g], (endTime + (endTime - startTime) * 0.05, e), ha='right', va='top')

    # Plot phases =============================================================
    phaseSep = []
    phaseAnchor = []
    phaseTitle = []
    if (phase != None and phase != []):
        if (phaseSeparatorStyle != None):
            for i in range(1, len(phase)):
                sep = phase[i - 1]['timeWindow'][1] + (phase[i]['timeWindow'][0] - phase[i - 1]['timeWindow'][1]) / 2
                ax.plot([sep, sep], [0, totalHeight], color = phaseSeparatorColor, linewidth = phaseSeparatorLinewidth, linestyle = phaseSeparatorStyle)
            ax.plot([phase[-1]['timeWindow'][1], phase[-1]['timeWindow'][1]], [0, totalHeight], color = phaseSeparatorColor, linewidth = phaseSeparatorLinewidth, linestyle = phaseSeparatorStyle)
        for i in range(len(phase)):
            if (phase[i]['backgroundColor'] != None):
                ax.fill([phase[i]['timeWindow'][0], phase[i]['timeWindow'][0], phase[i]['timeWindow'][1], phase[i]['timeWindow'][1], phase[i]['timeWindow'][0]], 
                    [0, totalHeight, totalHeight, 0, 0], 
                    color=phase[i]['backgroundColor'] if phase[i]['backgroundColor'] != 'Random' else rndColor(), 
                    alpha=phase[i]['backgroundOpacity'])
                ax.annotate(phase[i]['title'], (phase[i]['timeWindow'][0] + (phase[i]['timeWindow'][1] - phase[i]['timeWindow'][0]) / 2, totalHeight), ha='center', va='bottom')

    # Plot each gantt block ===================================================
    for i in range(len(entities)):
        if (entities[i] != None):
            entOffSet = 0
            if (entities[i] in entitiesOffset):
                entOffSet = entitiesOffset[entities[i]]

            center = yticks[i]
            lane = [0]
            ent = [g for g in gantt if g['entityID'] == entities[i]]
            ent.sort(key = lambda x:x['timeWindow'][0])
            for g in ent:
                ganttOffSet = 0
                needNewLaneFlag = True
                for k in range(len(lane)):
                    if (lane[k] <= g['timeWindow'][0]):
                        ganttOffSet = k
                        lane[k] = g['timeWindow'][1]
                        needNewLaneFlag = False
                        break
                if (needNewLaneFlag):
                    lane.append(g['timeWindow'][1])
                    ganttOffSet = len(lane) - 1

                # 形状位置
                s = g['timeWindow'][0]
                e = g['timeWindow'][1]
                x = [s, s, e, e, s]

                top = None
                if ('desc' not in g or ('descPosition' in g and g['descPosition'] == 'Inside')):
                    top = yticks[i] + ganttHeight / 2 - ganttOffSet * ganttHeight + entOffSet
                else:
                    top = yticks[i] + ganttHeight / 4 - ganttOffSet * ganttHeight + entOffSet
                bottom = yticks[i] - ganttHeight / 2 - ganttOffSet * ganttHeight + entOffSet

                y = [bottom, top, top, bottom, bottom]
                ax.plot(x, y, color = 'black', linewidth = ganttLinewidth)
                if ('color' in g and g['color'] != 'random'):
                    ax.fill(x, y, color = g['color'], linewidth = ganttLinewidth)
                else:
                    rndRGB = rndColor()
                    ax.fill(x, y, color = rndRGB, linewidth = ganttLinewidth)
                if ('desc' in g):
                    if ('descPosition' not in g or g['descPosition'] == 'Top'):
                        ax.annotate(g['desc'], (s + ganttHeight / 8, top + ganttHeight / 8))
                    elif ('descPosition' in g and g['descPosition'] == 'Inside'):
                        ax.annotate(g['desc'], (s + ganttHeight / 8, bottom + ganttHeight / 8))
                if (g['style'] != 'solid'):
                    ax.fill(x, y, hatch = g['style'], fill=False, linewidth = ganttLinewidth)
        elif (groupSeparatorStyle != None):
            center = yticks[i]
            ax.plot((startTime, endTime + (endTime - startTime) * 0.05), (center, center), linestyle = groupSeparatorStyle, linewidth = groupSeparatorLinewidth, color = groupSeparatorColor)

    # Show time span ==========================================================
    if (showTailFlag):
        xTicks = list(ax.get_xticks())
        xTicks.append(realEnd)
        ax.set_xticks(xTicks)  

    # Grids ===================================================================
    if (showGridFlag):
        ax.grid(b = True, linestyle=':')

    # Fix height if fig, ax are not provided ==================================
    if (fig == None or ax == None):
        fig.set_figheight(5 * max(pos))

    # Save figure =============================================================
    if (saveFigPath != None):
        fig.savefig(saveFigPath)
    if (not showFig):
        plt.close(fig)

    return fig, ax
