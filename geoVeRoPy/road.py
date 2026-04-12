import geojson
import math
import shapely
import networkx as nx

from .geometry import *
from .plot import *

def createRoadNetworkFromGeoJSON(
    geoJSONPath: str,
    boundaryLatLon: poly|None = None,
    projType: str = 'LatLon',
    buildingIncludedFlag: bool = False
    ) -> dict:

    """Given a path to geoJSON file, returns a road network dictionary with roads (and buildings)


    Parameters
    ----------
    
    geoJSONPath: string, required
        The path to a geoJSON file (".geojson")
    boundaryLatLon: list[pt], optionan, default as None
        Filter out the area that are not within the boundary, if given
    projType: string, optional, default as 'LatLon'
        Determine the axises of exported data, options are ['LatLon', 'Mercator']
    buildingIncludedFlag: bool, optional, default as False
        True if buildings are included

    Returns
    -------

    dict
        A road network dictionary, in the following formatt:
            >>> road = {
            ...     'boundary': boundary,
            ...     'road': road,
            ...     'building': building
            ... }
    """

    # Open the geojson file ===================================================
    with open(geoJSONPath, encoding = 'utf-8') as f:
        gj = geojson.load(f)

    # Create roads from geoJSON ===============================================
    road = {}
    roadID = 0

    # Create buildings from geoJSON ===========================================
    building = {}
    buildingID = 0

    # Loop through data
    # FIXME: Need to truncate the roads on the edge of polygon
    for i in range(len(gj["features"])):
        if (gj["features"][i]["geometry"]["type"] == "LineString" 
            and "properties" in gj["features"][i] 
            and "highway" in gj["features"][i]["properties"]):

            roadEntireIncludedFlag = False   # All nodes should be included
            roadPartialIncludedFlag = False  # Some (but not all) nodes should be included

            # The shape of the road is projected using Mercator projection
            # FIXME: truncate the roads that partially inside polygon
            line = []
            for p in gj["features"][i]["geometry"]["coordinates"]:
                if (boundaryLatLon == None or isPtOnPoly([p[1], p[0]], boundaryLatLon)):
                    roadEntireIncludedFlag = True
                if (projType == 'Mercator'):
                    line.append(list(ptLatLon2XYMercator([p[1], p[0]])))
                elif (projType == 'LatLon'):
                    line.append([p[1], p[0]])

            if (roadEntireIncludedFlag):
                road[roadID] = {}
                road[roadID]['shape'] = line

                # Name of road
                if ("name" in gj["features"][i]["properties"]):
                    road[roadID]['name'] = gj["features"][i]["properties"]["name"]

                # Speed of road
                if ("maxspeed" in gj["features"][i]["properties"]):
                    road[roadID]['maxspeed'] = gj["features"][i]["properties"]["maxspeed"]
                else:
                    road[roadID]['maxspeed'] = 30 # [mph]

                # Is it one-way
                if ("oneway" in gj["features"][i]["properties"]):
                    road[roadID]['oneway'] = gj["features"][i]["properties"]["oneway"]    
                else:
                    road[roadID]['oneway'] = False

                # Road class
                road[roadID]['class'] = gj["features"][i]["properties"]["highway"]
                
                roadID += 1

        if (buildingIncludedFlag):
            if (gj["features"][i]["geometry"]["type"] in ["MultiPolygon"]
                and "properties" in gj["features"][i]
                and "building" in gj["features"][i]["properties"]):

                # The shape of the road is projected using Mercator projection
                poly = []
                if (projType == 'Mercator'):
                    for p in gj["features"][i]["geometry"]["coordinates"][0][0]:
                        poly.append(list(ptLatLon2XYMercator([p[1], p[0]])))
                elif (projType == 'LatLon'):
                    for p in gj["features"][i]["geometry"]["coordinates"][0][0]:
                        poly.append([p[1], p[0]])
                building[buildingID] = {}
                building[buildingID]['shape'] = poly

                # Building type
                if (gj["features"][i]["properties"]["building"] == 'yes'):
                    building[buildingID]['type'] = "building"
                else:
                    building[buildingID]['type'] = gj["features"][i]["properties"]["building"]

                buildingID += 1

    # Fix the position ========================================================
    minX = None
    maxX = None
    minY = None
    maxY = None
    for r in road:
        for p in road[r]['shape']:
            if (minX == None or p[0] < minX):
                minX = p[0]
            if (maxX == None or p[0] > maxX):
                maxX = p[0]
            if (minY == None or p[1] < minY):
                minY = p[1]
            if (maxY == None or p[1] > maxY):
                maxY = p[1]
    if (projType == 'Mercator'):
        for r in road:
            for p in road[r]['shape']:
                p[0] -= minX
                p[1] -= minY

    # Define boundary =========================================================
    boundary = []
    if (projType == 'Mercator'):
        boundary = [(0, 0), (maxX - minX, 0), (maxX - minX, maxY - minY), (0, maxY - minY)]
    elif (projType == 'LatLon'):
        boundary = [(minX, minY), (maxX, minY), (maxX, maxY), (minX, maxY)]

    return {
        'boundary': boundary,
        'projType': projType,
        'road': road,
        'building': building
    }

def clipRoadsByPoly(roads: dict, poly: poly) -> dict:

    # FIXME: Currently using a stupid method, since it is a one-time function    
    # Roads ===================================================================
    clip = {}
    maxRoadID = max(roads.keys()) + 1
    for r in roads:
        # 最笨的办法，一条一条路处理
        seqInt = intSeq2Poly(roads[r]['shape'], poly)

        # 如果是完整的路径
        if (type(seqInt) != list):
            if (seqInt['status'] == 'Cross' and seqInt['intersectType'] == 'Segment'):
                clip[r] = {}
                for k in roads[r]:
                    clip[r][k] = roads[r][k]
                clip[r]['shape'] = seqInt['intersect']

        # 如果路径被切割开
        else:
            for parti in seqInt:
                if (parti['status'] == 'Cross' and parti['intersectType'] == 'Segment'):
                    clip[maxRoadID] = {}
                    for k in roads[r]:
                        clip[maxRoadID][k] = roads[r][k]
                    clip[maxRoadID]['shape'] = parti['intersect']
                    maxRoadID += 1

    return clip

def clipRoadsByMultiPoly(roads: dict, multiPoly: polys) -> dict:
    # FIXME: Currently using a stupid method, since it is a one-time function    
    # Roads ===================================================================
    clip = {}
    roadID = 0
    for poly in multiPoly:
        for r in roads:
            # 最笨的办法，一条一条路处理
            seqInt = intSeq2Poly(roads[r]['shape'], poly)

            # 如果是完整的路径
            if (type(seqInt) != list):
                if (seqInt['status'] == 'Cross' and seqInt['intersectType'] == 'Segment'):
                    clip[roadID] = {}
                    for k in roads[r]:
                        clip[roadID][k] = roads[r][k]
                    clip[roadID]['shape'] = seqInt['intersect']
                    roadID += 1

            # 如果路径被切割开
            else:
                for parti in seqInt:
                    if (parti['status'] == 'Cross' and parti['intersectType'] == 'Segment'):
                        clip[roadID] = {}
                        for k in roads[r]:
                            clip[roadID][k] = roads[r][k]
                        clip[roadID]['shape'] = parti['intersect']
                        roadID += 1

    return clip

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
