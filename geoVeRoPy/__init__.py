__version__ = "0.0.17"
__author__ = "Lan Peng"

# A few SE tips/notes =========================================================
# 1. Avoid nested if/for for more than three levels
# 2. A function should not be more than one page in length
# 3. Variables start with lower-case, classes names start with upper-case
# 4. NEVER use variable start with `my-` or `tmp-`, it is lame
# =============================================================================

# Constants, messages, and basic modules
from .msg import *
from .common import *
from .color import *

# Data
from .province import *
from .road import *

# Data structures
from .ring import *
from .tree import *
from .gridSurface import *
from .curveArc import *

# Visualize modules
from .plot import *
from .animation import *
from .instance import *

# Geometry
from .geometry import *
from .obj2Obj import *
from .polyTour import *
from .grid import *

# TSP/VRP
from .tsp import *
from .tsptw import *
from .vrptw import *
from .op import *

# Close enough TSP
from .cetsp import *
# from .ceop import *
# from .gceop import *
from .serviceTime import *

# Moving target TSP
# from .mttsp import *
