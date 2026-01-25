import requests
import time
import random

from .common import *
from .geometry import *

def matrixDist(nodes: dict, ptFieldName: str = 'pt', nodeIDs: list|str = 'All', edges: str = 'Euclidean', detailFlag: bool = False, **kwargs) -> dict:
    """
    Given a `nodes` dictionary, returns the traveling matrix between nodes

    Parameters
    ----------

    nodes: dict, required
        A `nodes`dictionary with location information
    ptFieldName: str, optional, default as 'pt'
        The key in nodes dictionary to indicate the locations
    nodeIDs: list of int|str, or 'All', optional, default as 'All'
        A list of nodes in `nodes` that needs to be considered, other nodes will be ignored
    edges: str, optional, default as 'Euclidean'
        The methods for the calculation of distances between nodes. Options and required additional information are as follows:

        1) (default) 'Euclidean', using Euclidean distance, no additional information needed
        2) 'EuclideanBarrier', using Euclidean distance, if `polys` is provided, the path between nodes will consider them as barriers and by pass those areas.
            - polys: list of poly, the polygons to be considered as barriers
        3) 'LatLon', calculate distances by lat/lon, no additional information needed
            - distUnit: str, the unit of distance, default as 'meter'
        4) 'ManhattenXY', calculate distance by Manhatten distance            
        5) 'Dictionary', directly provide the travel matrix
            - tau: the traveling matrix
        6) 'Grid', traveling on a grid with barriers, usually used in warehouses
            - column: number of columns
            - row: number of rows
            - barrier: a list of coordinates on the grid indicating no-entrance
    **kwargs: optional
        Provide additional inputs for different `edges` options

    Returns
    -------

    tuple
        Two dictionaries, the first one is the travel matrix, index by (nodeID1, nodeID2), the second one is the dictionary for path between start and end locations (useful for 'EuclideanBarrier').

    """

    # Define tau
    tau = {}
    pathPt = {}

    if (type(nodeIDs) is not list):
        if (nodeIDs == 'All'):
            nodeIDs = []
            for i in nodes:
                nodeIDs.append(i)

    if (edges == 'Euclidean'):
        res = _matrixDistEuclideanXY(
            nodes = nodes, 
            nodeIDs = nodeIDs, 
            ptFieldName = ptFieldName,
            detailFlag = detailFlag)
    elif (edges == 'EuclideanBarrier'):
        if ('polys' not in kwargs or kwargs['polys'] == None):
            warnings.warning("WARNING: No barrier provided.")
            res = _matrixDistEuclideanXY(
                nodes = nodes, 
                nodeIDs = nodeIDs, 
                ptFieldName = ptFieldName,
                detailFlag = detailFlag)
        else:
            res = _matrixDistBtwPolysXY(
                nodes = nodes, 
                nodeIDs = nodeIDs, 
                polys = kwargs['polys'], 
                ptFieldName = ptFieldName,
                detailFlag = detailFlag)
    elif (edges == 'LatLon'):
        distUnit = 'meter' if 'distUnit' not in kwargs else kwargs['distUnit']
        res = _matrixDistLatLon(
            nodes = nodes, 
            nodeIDs = nodeIDs, 
            distUnit = distUnit,
            ptFieldName = ptFieldName,
            detailFlag = detailFlag)
    elif (edges == 'Manhatten'):
        res = _matrixDistManhattenXY(
            nodes = nodes, 
            nodeIDs = nodeIDs, 
            ptFieldName = ptFieldName,
            detailFlag = detailFlag)
    elif (edges == 'Dictionary'):
        if ('tau' not in kwargs or kwargs['tau'] == None):
            raise MissingParameterError("ERROR: 'tau' is not specified")
        for p in kwargs['tau']:
            tau[p] = kwargs['tau'][p]
            pathPt[p] = kwargs['path'][p] if 'path' in kwargs else [nodes[p[0]][ptFieldName], nodes[p[1]][ptFieldName]]
        if (detailFlag):
            res = {
                'tau': tau,
                'pathPt': pathPt
            }
        else:
            res = tau
    elif (edges == 'Grid'):
        if ('grid' not in kwargs or kwargs['grid'] == None):
            raise MissingParameterError("ERROR: 'grid' is not specified")
        if ('column' not in kwargs['grid'] or 'row' not in kwargs['grid']):
            raise MissingParameterError("'column' and 'row' need to be specified in 'grid'")
        res = _matrixDistGrid(
            nodes = nodes, 
            nodeIDs = nodeIDs, 
            grids = kwargs['grid'], 
            ptFieldName = ptFieldName,
            detailFlag = detailFlag)
    elif (edges == 'RoadNetwork'):
        if ('source' not in kwargs or kwargs['source'] == None):
            raise MissingParameterError("ERROR: 'source' is not specified")
        if ('APIKey' not in kwargs or kwargs['APIKey'] == None):
            raise MissingParameterError("ERROR: 'APIkey' is not specified")
        if (kwargs['source'] == 'Baidu'):
            if (detailFlag):
                raise UnsupportedInputError("ERROR: Stay tune")
            else:
                try:
                    res = _matrixBaidu(nodes, nodeIDs, kwargs['APIKey'], ptFieldName)
                except:
                    raise UnsupportedInputError("ERROR: Failed to fetch data, check network connection and API key")
        else:
            raise UnsupportedInputError("ERROR: Right now we support 'Baidu'")
    else:
        raise UnsupportedInputError(ERROR_MISSING_EDGES)        

    return res

def _matrixBaidu(nodes, nodeIDs, API, ptFieldName = 'pt'):
    # 分解成block
    subList = None
    if (len(nodeIDs) > 5):
        numBin = math.ceil(len(nodeIDs) / 5)
        subList = splitList(nodeIDs, numBin)
    else:
        return _matrixBaiduBlock(nodes, nodeIDs, nodeIDs, API, ptFieldName)

    m = {}
    for i in range(len(subList)):
        for j in range(len(subList)):
            # print(subList[i], subList[j])
            rnd = random.random() * 4
            print(5 + rnd)
            time.sleep(5 + rnd)
            print(subList[i], subList[j])
            block = _matrixBaiduBlock(nodes, subList[i], subList[j], API, ptFieldName)
            for key in block:
                m[key] = block[key]

    return m

def _matrixBaiduBlock(nodes: dict, oriIDs: list, desIDs: list, API, ptFieldName = 'pt'):
    oriStr = ""
    for i in range(len(oriIDs)):
        oriStr += str(nodes[oriIDs[i]][ptFieldName][0]) + "," + str(nodes[oriIDs[i]][ptFieldName][1]) + "|"
    oriStr = oriStr[:-1]

    desStr = ""
    for i in range(len(desIDs)):
        desStr += str(nodes[desIDs[i]][ptFieldName][0]) + "," + str(nodes[desIDs[i]][ptFieldName][1]) + "|"
    desStr = desStr[:-1]

    url = "https://api.map.baidu.com/routematrix/v2/driving"
    params = {
        "origins": oriStr,
        "destinations": desStr,
        "ak": API,
    }
    response = requests.get(url=url, params=params)
    
    tau = {}
    try:
        if (response):
            k = 0
            for i in range(len(oriIDs)):
                for j in range(len(desIDs)):
                    tau[oriIDs[i], desIDs[j]] = response.json()['result'][k]['distance']['value']
                    k += 1
    except:
        print(response)
        raise

    return tau

def _shapepointBaidu(startPt, endPt, API, waypoints):
    seq = [startPt]
    seq.extend(waypoints)
    seq.append(endPt)
    subSeqs = None
    if (len(seq) > 18):
        numBin = math.ceil((len(seq) + 2) / 20)
        subSeqs = splitList(seq, numBin)
    else:
        return _shapepointBaiduSeq(startPt, endPt, API, waypoints)

    path = []
    for sub in subSeqs:
        rnd = random.random() * 4
        time.sleep(5 + rnd)
        waypoints = None
        if (len(sub) > 2):
            waypoints = [sub[i] for i in range(1, len(sub) - 1)]
        sp = _shapepointBaiduSeq(sub[0], sub[-1], API, waypoints)
        path.extend(sp)

    return path

def _shapepointBaiduSeq(startPt, endPt, API, waypoints=None):
    url = "https://api.map.baidu.com/direction/v2/driving"

    params = {
        "origin": f"{startPt[0]},{startPt[1]}",
        "destination": f"{endPt[0]},{endPt[1]}",
        "ak": API
    }

    wp = []
    if (waypoints != None):
        for p in waypoints:
            wp.append(f"{p[0]},{p[1]}|")

    response = requests.get(url=url, params=params)

    path = []
    try:
        if response:
            path = []
            for route in j['result']['routes']:
                for step in route['steps']:
                    coords = step['path'].split(";")
                    for c in range(len(coords) - 1):
                        xy = coords[c].split(',')
                        path.append((xy[0], xy[1]))
    except:
        print(response)
        raise

    return path

def _matrixDistEuclideanXY(nodes: dict, nodeIDs: list, ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    pathPt = {}
    for i in nodeIDs:
        for j in nodeIDs:
            if (i != j):
                d = distEuclideanXY(nodes[i][ptFieldName], nodes[j][ptFieldName])
                if (detailFlag):
                    tau[i, j] = d['dist']
                    tau[j, i] = d['dist']
                    pathPt[i, j] = [nodes[i][ptFieldName], nodes[j][ptFieldName]]
                    pathPt[j, i] = [nodes[j][ptFieldName], nodes[i][ptFieldName]]
                else:
                    tau[i, j] = d
                    tau[j, i] = d
            else:
                tau[i, j] = 0
                tau[j, i] = 0
                pathPt[i, j] = []
                pathPt[j, i] = []

    if (detailFlag):
        return {
            'tau': tau,
            'pathPt': pathPt
        }
    else:
        return tau

def _matrixDistManhattenXY(nodes: dict, nodeIDs: list, ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    pathPt = {}
    for i in nodeIDs:
        for j in nodeIDs:
            if (i != j):
                d = distManhattenXY(nodes[i][ptFieldName], nodes[j][ptFieldName])                
                if (detailFlag):
                    tau[i, j] = d['dist']
                    tau[j, i] = d['dist']
                    pathPt[i, j] = d['path']
                    pathPt[j, i] = [d['path'][len(d['path']) - 1 - i] for i in range(len(d['path']))]
                else:
                    tau[i, j] = d
                    tau[j, i] = d
            else:
                tau[i, j] = 0
                tau[j, i] = 0
                if (detailFlag):
                    pathPt[i, j] = []
                    pathPt[j, i] = []

    if (detailFlag):
        return {
            'tau': tau,
            'pathPt': pathPt
        }
    else:
        return tau

def _matrixDistLatLon(nodes: dict, nodeIDs: list, distUnit = 'meter', ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    pathPt = {}
    for i in nodeIDs:
        for j in nodeIDs:
            if (i != j):
                d = distLatLon(nodes[i][ptFieldName], nodes[j][ptFieldName], distUnit)
                if (detailFlag):
                    tau[i, j] = d['dist']
                    tau[j, i] = d['dist']
                    pathPt[i, j] = [nodes[i][ptFieldName], nodes[j][ptFieldName]]
                    pathPt[j, i] = [nodes[j][ptFieldName], nodes[i][ptFieldName]]
                else:
                    tau[i, j] = d
                    tau[j, i] = d
            else:
                tau[i, j] = 0
                tau[j, i] = 0
                pathPt[i, j] = []
                pathPt[j, i] = []

    if (detailFlag):
        return {
            'tau': tau,
            'pathPt': pathPt
        }
    else:
        return tau

def _matrixDistGrid(nodes: dict, nodeIDs: list, grid: dict, ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    pathPt = {}
    for i in nodeIDs:
        for j in nodeIDs:
            if (i != j):
                d = distOnGrid(pt1 = nodes[i][ptFieldName], pt2 = nodes[j][ptFieldName], grid = grid, detailFlag = detailFlag)
                if (detailFlag):
                    tau[i, j] = d['dist']
                    tau[j, i] = d['dist']
                    pathPt[i, j] = d['path']
                    pathPt[j, i] = [d['path'][len(d['path']) - 1 - i] for i in range(len(d['path']))]
                else:
                    tau[i, j] = d
                    tau[j, i] = d
            else:
                tau[i, j] = 0
                tau[j, i] = 0
                pathPt[i, j] = []
                pathPt[j, i] = []

    if (detailFlag):
        return {
            'tau': tau,
            'pathPt': pathPt
        }
    else:
        return tau

def _matrixDistBtwPolysXY(nodes: dict, nodeIDs: list, polys: polys, polyVG = None, ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    pathPt = {}
    
    if (polyVG == None):
        polyVG = polysVisibleGraph(polys)

    for i in nodeIDs:
        for j in nodeIDs:
            if (i != j):
                d = distBtwPolysXY(pt1 = nodes[i][ptFieldName], pt2 = nodes[j][ptFieldName], polys = polys, polyVG = polyVG, detailFlag = detailFlag)
                if (detailFlag):
                    tau[i, j] = d['dist']
                    tau[j, i] = d['dist']
                    pathPt[i, j] = d['path']
                    pathPt[j, i] = [d['path'][len(d['path']) - 1 - i] for i in range(len(d['path']))]
                else:
                    tau[i, j] = d
                    tau[j, i] = d
            else:
                tau[i, j] = 0
                tau[j, i] = 0
                pathPt[i, j] = []
                pathPt[j, i] = []

    if (detailFlag):
        return {
            'tau': tau,
            'pathPt': pathPt
        }
    else:
        return tau

def vectorDist(pt: pt, nodes: dict, ptFieldName: str = 'pt', nodeIDs: list|str = 'All', edges: str = 'Euclidean', detailFlag: bool = False, **kwargs) -> dict:
    """
    Given a location and a `nodes` dictionary, returns the traveling distance and path between the location to each node.

    Parameters
    ----------

    pt: pt, required
        Origin/destination location.
    nodes: dict, required
        A `nodes`dictionary with location information. See :ref:`nodes` for reference.
    ptFieldName: str, optional, default as 'pt'
        The key in nodes dictionary to indicate the locations
    nodeIDs: list of int|str, or 'All', optional, default as 'All'
        A list of nodes in `nodes` that needs to be considered, other nodes will be ignored
    edges: str, optional, default as 'Euclidean'
        The methods for the calculation of distances between nodes. Options and required additional information are referred to :func:`~vrpSolver.geometry.matrixDist()`.
    **kwargs: optional
        Provide additional inputs for different `edges` options

    Returns
    -------

    tuple
        tau, revTau, pathPt, revPathPt. Four dictionaries, the first one is the travel distance from pt to each node index by nodeID, the second the travel distance from each node back to pt. The third and fourth dictionaries are the corresponded path.

    """

    # Define tau
    tau = {}
    revTau = {}
    pathPt = {}
    revPathPt = {}

    if (type(nodeIDs) is not list):
        if (nodeIDs == 'All'):
            nodeIDs = []
            for i in nodes:
                nodeIDs.append(i)

    if (edges == 'Euclidean'):
        res = _vectorDistEuclideanXY(
            pt = pt,
            nodes = nodes, 
            nodeIDs = nodeIDs, 
            ptFieldName = ptFieldName,
            detailFlag = detailFlag)
    elif (edges == 'EuclideanBarrier'):
        if ('polys' not in kwargs or kwargs['polys'] == None):
            warnings.warning("WARNING: No barrier provided.")
            res = _vectorDistEuclideanXY(
                pt = pt,
                nodes = nodes, 
                nodeIDs = nodeIDs, 
                ptFieldName = ptFieldName,
                detailFlag = detailFlag)
        else:
            res = _vectorDistBtwPolysXY(
                pt = pt,
                nodes = nodes, 
                nodeIDs = nodeIDs, 
                polys = kwargs['polys'], 
                ptFieldName = ptFieldName,
                detailFlag = detailFlag)
    elif (edges == 'LatLon'):
        res = _vectorDistLatLon(
            pt = pt,
            nodes = nodes, 
            nodeIDs = nodeIDs, 
            ptFieldName = ptFieldName,
            detailFlag = detailFlag)
    elif (edges == 'Manhatten'):
        res = _vectorDistManhattenXY(
            pt = pt,
            nodes = nodes, 
            nodeIDs = nodeIDs, 
            ptFieldName = ptFieldName,
            detailFlag = detailFlag)
    elif (edges == 'Grid'):
        if ('grid' not in kwargs or kwargs['grid'] == None):
            raise MissingParameterError("'grid' is not specified")
        if ('column' not in kwargs['grid'] or 'row' not in kwargs['grid']):
            raise MissingParameterError("'column' and 'row' need to be specified in 'grid'")
        res = _vectorDistGrid(
            pt = pt,
            nodes = nodes, 
            nodeIDs = nodeIDs, 
            grids = kwargs['grid'], 
            ptFieldName = ptFieldName,
            detailFlag = detailFlag)
    else:
        raise UnsupportedInputError(ERROR_MISSING_EDGES)        

    return res

def _vectorDistEuclideanXY(pt: pt, nodes: dict, nodeIDs: list, ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    revTau = {}
    pathPt = {}
    revPathPt = {}
    for i in nodeIDs:
        d = distEuclideanXY(pt, nodes[i][ptFieldName])
        tau[i] = d
        if (detailFlag):
            revTau[i] = d
            pathPt[i] = [pt, nodes[i][ptFieldName]]
            revPathPt[i] = [nodes[i][ptFieldName], pt]

    if (detailFlag):
        return {
            'tau': tau,
            'revTau': revTau,
            'pathPt': pathPt,
            'revPathPt': revPathPt
        }
    else:
        return tau

def _vectorDistManhattenXY(pt: pt, nodes: dict, nodeIDs: list, ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    revTau = {}
    pathPt = {}
    revPathPt = {}
    for i in nodeIDs:
        d = distManhattenXY(pt, nodes[i][ptFieldName], detailFlag)
        if (detailFlag):
            tau[i] = d['dist']
            revTau[i] = d['dist']
            pathPt[i] = d['path']
            revPathPt[i] = [d['path'][len(d['path']) - 1 - i] for i in range(len(d['path']))]
        else:
            tau[i] = d

    if (detailFlag):
        return {
            'tau': tau,
            'revTau': revTau,
            'pathPt': pathPt,
            'revPathPt': revPathPt
        }
    else:
        return tau

def _vectorDistLatLon(pt: pt, nodes: dict, nodeIDs: list, distUnit = 'meter', ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    revTau = {}
    pathPt = {}
    revPathPt = {}
    for i in nodeIDs:
        d = distLatLon(pt, nodes[i][ptFieldName], distUnit)
        tau[i] = d
        if (detailFlag):
            revTau[i] = d
            pathPt[i] = [pt, nodes[i][ptFieldName]]
            revPathPt[i] = [nodes[i][ptFieldName], pt]

    if (detailFlag):
        return {
            'tau': tau,
            'revTau': revTau,
            'pathPt': pathPt,
            'revPathPt': revPathPt
        }
    else:
        return tau

def _vectorDistGrid(pt: pt, nodes: dict, nodeIDs: list, grid: dict, ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    revTau = {}
    pathPt = {}
    revPathPt = {}
    for i in nodeIDs:
        d = distOnGrid(pt1 = pt, pt2 = nodes[i][ptFieldName], grid = grid, detailFlag = detailFlag)
        if (detailFlag):
            tau[i] = d['dist']
            revTau[i] = d['dist']
            pathPt[i] = d['path']
            revPathPt[i] = [d['path'][len(d['path']) - 1 - i] for i in range(len(d['path']))]
        else:
            tau[i] = d
    
    if (detailFlag):
        return {
            'tau': tau,
            'revTau': revTau,
            'pathPt': pathPt,
            'revPathPt': revPathPt
        }
    else:
        return tau

def _vectorDistBtwPolysXY(pt: pt, nodes: dict, nodeIDs: list, polys: polys, polyVG = None, ptFieldName = 'pt', detailFlag: bool = False):
    tau = {}
    revTau = {}
    pathPt = {}
    revPathPt = {}

    if (polyVG == None):
        polyVG = polysVisibleGraph(polys)

    for i in nodeIDs:
        d = distBtwPolysXY(pt1 = pt, pt2 = nodes[i][ptFieldName], polys = polys, polyVG = polyVG, detailFlag = detailFlag)
        if (detailFlag):
            tau[i] = d['dist']
            revTau[i] = d['dist']
            pathPt[i] = d['path']
            revPathPt[i] = [d['path'][len(d['path']) - 1 - i] for i in range(len(d['path']))]
        else:
            tau[i] = d

    if (detailFlag):
        return {
            'tau': tau,
            'revTau': revTau,
            'pathPt': pathPt,
            'revPathPt': revPathPt
        }
    else:
        return tau

def scaleDist(pt1: pt, pt2: pt, edges: str = 'Euclidean', detailFlag: bool = False, **kwargs) -> dict:
    """
    Given a two locations, returns the traveling distance and path between locations.

    Parameters
    ----------

    pt1: pt, required
        The first location.
    pt2: pt, required
        The second location.
    edges: str, optional, default as 'Euclidean'
        The methods for the calculation of distances between nodes. Options and required additional information are referred to :func:`~vrpSolver.geometry.matrixDist()`.
    **kwargs: optional
        Provide additional inputs for different `edges` options

    Returns
    -------

    dict
        tau, revTau, pathPt, revPathPt. Four keys, the first one is the travel distance from pt to each node index by nodeID, the second the travel distance from each node back to pt. The third and fourth dictionaries are the corresponded path.

    """

    # Define tau
    dist = None
    revDist = None
    pathPt = []
    revPathPt = []

    if (edges == 'Euclidean'):
        dist = distEuclideanXY(pt1, pt2)
        if (detailFlag):
            revDist = dist
            pathPt = [pt1, pt2]
            revPathPt = [pt2, pt1]
    elif (edges == 'EuclideanBarrier'):
        if ('polys' not in kwargs or kwargs['polys'] == None):
            warnings.warning("WARNING: No barrier provided.")
            dist = distEuclideanXY(pt1, pt2)
            if (detailFlag):
                revDist = dist
                pathPt = [pt1, pt2]
                revPathPt = [pt2, pt1]
        else:
            res = distBtwPolysXY(pt1, pt2, kwargs['polys'], detailFlag)
            if (detailFlag):
                dist = res['dist']
                revDist = dist
                pathPt = [i for i in res['path']]
                revPathPt = [pathPt[len(pathPt) - i - 1] for i in range(len(pathPt))]
            else:
                dist = res
    elif (edges == 'LatLon'):
        dist = distLatLon(pt1, pt2)
        if (detailFlag):
            revDist = dist
            pathPt = [pt1, pt2]
            revPathPt = [pt2, pt1]
    elif (edges == 'Manhatten'):
        dist = distManhattenXY(pt1, pt2)
        if (detailFlag):
            revDist = dist
            pathPt = [pt1, (pt1[0], pt2[1]), pt2]
            revPathPt = [pt2, (pt1[0], pt2[1]), pt1]
    elif (edges == 'Grid'):
        if ('grid' not in kwargs or kwargs['grid'] == None):
            raise MissingParameterError("'grid' is not specified")
        if ('column' not in kwargs['grid'] or 'row' not in kwargs['grid']):
            raise MissingParameterError("'column' and 'row' need to be specified in 'grid'")
        res = distOnGrid(pt1, pt2, kwargs['grid'])
        dist = res['dist']
        if (detailFlag):
            revDist = dist
            pathPt = [i for i in res['path']]
            revPathPt = [pathPt[len(pathPt) - i - 1] for i in range(len(pathPt))]
    else:
        raise UnsupportedInputError(ERROR_MISSING_EDGES)        

    if (detailFlag):
        return {
            'dist': dist,
            'revDist': revDist,
            'pathPt': pathPt,
            'revPathPt': revPathPt
        }
    else:
        return dist
