import heapq
import math
import warnings
import networkx as nx

from .common import *
from .geometry import *
from .msg import *
from .travel import *
from .tsp import *

def solveDynamicTSP(
	endTime: float,
    nodes: dict, 
    locFieldName: str = 'loc',
    appearFieldName: str = 'appear',
    depotID: int|str = 0,
    nodeIDs: list[int|str]|str = 'All',
    vehicles: dict = {0: {'speed': 1}},
    vehicleID: int|str = 0,
    serviceTime: float = 0,
    reopt: str = 'FixedTime',
    edges: str = 'Euclidean',
    algo: str = 'Exact',
    detailFlag: bool = False,
    metaFlag: bool = False,
    **kwargs
    ) -> dict:

	clock = 0
	curNodes = {}

	while (clock <= endTime):

		# Check current -------------------------------------------------------
		# 更新当前时刻的位置/待访问的目标集合/travel matrix