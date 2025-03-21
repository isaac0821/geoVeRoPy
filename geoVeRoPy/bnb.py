import math
from .common import *
from .ds import *

class BnBTreeNode(object):
    def __init__(self, key:int, value, parent:'BSTreeNode'=None, treeNodes: list['TreeNode'] = None, relaxed: bool, pruned:bool, **kwargs):
        self.key = key
        self.value = value
        self.parent = parent if parent != None else BnBTreeNilNode()
        self.treeNodes = treeNodes if treeNodes != None else [BnBTreeNilNode()]
        self.relaxed = relaxed
        self.pruned = pruned
        self.upperBound = None
        self.lowerBound = None
        self.__dict__.update(kwargs)

    @property
    def isNil(self):
        return False

class BnBTreeNilNode(BnBTreeNode):
    def __init__(self):
        return

    @property
    def isNil(self):
        return True

class BnBTree(Tree):

