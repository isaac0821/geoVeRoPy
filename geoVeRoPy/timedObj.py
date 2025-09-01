import networkx as nx

from .geometry import *
from .common import *
from .msg import *

# Vector 
def pt2Vec(pt: pt, vec: dict, vehSpeed: float, z: float=0):
	"""
	Given a vector that starts from z=0, and a pt appears at z, finds the fastest path for pt to engage vec

	Parameters
	----------
	pt: pt, required
		Coordinate of the chaser
	vec: dict, required
		The target that are moving
	vehSpeed: float, required
		Maximum speed of the chaser

	"""

	# pt appears at z
	# vec appears at 0

	x0, y0 = pt

	return {
		'meet': meet,
		'chaseVec': chaseVec
	}