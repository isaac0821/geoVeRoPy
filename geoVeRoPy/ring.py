from .common import *

# Basic ring objects
class RingNode(object):
    def __init__(self, key, value=None, prev: 'RingNode' = None, next: 'RingNode' = None, **kwargs):
        self.key = key
        self.value = value if value != None else key
        self.prev = prev if prev != None else RingNilNode()
        self.next = next if next != None else RingNilNode()
        self.__dict__.update(kwargs)

    def clone(self):
        newObj = RingNode(self.key, self.value)
        newObj.prev = self.prev
        newObj.next = self.next
        return newObj

    @property
    def isNil(self):
        return False

    def __repr__(self):
        s =("{key: " + str(self.key) + ", "
            + "value: " + str(self.value) + ", "
            + "prev: " + (str(self.prev.key) if (not self.prev.isNil) else "None") + ", "
            + "next: " + (str(self.next.key) if (not self.next.isNil) else "None") + "} ")
        return s

class RingNilNode(RingNode):
    def __init__(self):
        return

    @property
    def isNil(self):
        return True

class Ring(object):
    def __init__(self):
        self.head = RingNilNode()
        self._count = 0

    @property
    def isEmpty(self):
        if (self.head.isNil):
            return True
        else:
            return False

    @property
    def count(self):
        return self._count

    def __repr__(self):
        return self.traverse().__repr__()

    def rehead(self, key):
        self.head = self.query(key)

    def query(self, key) -> "RingNode":
        if (self.head.isNil):
            raise EmptyError("ERROR: The ring is empty.")
        cur = self.head
        trvFlag = False
        queried = 0
        while (not trvFlag):
            if (cur.key == key):
                return cur
            else:
                cur = cur.next
                queried += 1
                if (queried > self._count):
                    raise OutOfRangeError("ERROR: Unexpected loop")
                if (cur.key == self.head.key):
                    trvFlag = True
        if (trvFlag):
            return RingNilNode()

    def traverse(self, closeFlag=False) -> list:
        route = []
        cur = self.head
        while (not cur.isNil):
            if (len(route) > self._count):
                raise OutOfRangeError("ERROR: Unexpected loop")
            route.append(cur)
            cur = cur.next
            if (cur.key == self.head.key):
                break
        if (closeFlag):
            route.append(self.head)
        return route

    def insert(self, m, n):
        if (n.isNil):
            raise EmptyError("ERROR: Cannot insert an empty node.")
        if (self.head.isNil):
            self.head = n
            n.next = n
            n.prev = n
            self._count += 1
        else:
            m.next.prev = n
            n.prev = m
            n.next = m.next
            m.next = n
            self._count += 1

    def append(self, n):
        if (n.isNil):
            raise EmptyError("ERROR: Cannot insert an empty node.")
        if (self.head.isNil):
            self.head = n
            n.next = n
            n.prev = n
            self._count += 1
        else:
            return self.insert(self.head.prev, n)

    def remove(self, n):
        n.prev.next = n.next
        n.next.prev = n.prev
        self._count -= 1

# Route objects
class RouteNode(RingNode):
    def __init__(self, key, value=None, prev: 'RouteNode'=None, next: 'RouteNode'=None):
        self.key = key
        self.value = value if value != None else key
        self.prev = prev if prev != None else RouteNilNode()
        self.next = next if next != None else RouteNilNode()

    def clone(self):
        newObj = RouteNode(self.key, self.value)
        newObj.prev = self.prev
        newObj.next = self.next
        return newObj

class RouteNilNode(RouteNode):
    def __init__(self):
        return

    @property
    def isNil(self):
        return True

class Route(Ring):
    def __init__(self, tau, asymFlag=False):
        self.head = RouteNilNode()
        self.tau = tau
        self.dist = 0
        self._revDist = 0
        self.asymFlag = asymFlag
        self._count = 0

    def clone(self):
        newRoute = Route(self.tau, self.asymFlag)
        cur = self.head
        l = 0
        while (not cur.isNil):
            if (l > self._count):
                raise OutOfRangeError("ERROR: Unexpected loop")
            clone = cur.clone()
            newRoute.append(clone)
            cur = cur.next
            l += 1
            if (cur.key == self.head.key):
                break
        return newRoute

    @property
    def revDist(self):
        if (self.asymFlag):
            return self._revDist
        else:
            return self.dist

    def reverse(self):
        tra = self.traverse()
        for n in tra:
            n.prev, n.next = n.next, n.prev
        if (self.asymFlag):
            self.dist, self._revDist = self._revDist, self.dist

    def rotate(self, s, e):
        # = = s.prev s s.next = = = e.prev e e.next = = 
        # = = s.prev e e.prev = = = s.next s e.next = = 

        sPrev = s.prev
        eNext = e.next

        s.prev.next = e
        e.next.prev = s

        # 如果是asymmetric
        distS2E = 0
        distE2S = 0
        # 计算 s => e之间累计的距离
        if (self.asymFlag):
            k = s
            while (k.key != e.key):
                distS2E += self.tau[k.key, k.next.key]
                distE2S += self.tau[k.next.key, k.key]
                k = k.next

        tra = []
        k = s
        while (k.key != e.key):
            tra.append(k)
            k = k.next
        tra.append(e)

        for n in tra:
            n.prev, n.next = n.next, n.prev

        e.prev = sPrev
        s.next = eNext

        self.dist = self.dist - self.tau[sPrev.key, s.key] - self.tau[e.key, eNext.key] + self.tau[sPrev.key, e.key] + self.tau[s.key, eNext.key] - distS2E + distE2S
        self._revDist = self._revDist - self.tau[eNext.key, e.key] - self.tau[s.key, sPrev.key] + self.tau[eNext.key, s.key] + self.tau[e.key, sPrev.key] - distE2S + distS2E

    def query(self, key) -> "RouteNode":
        if (self.head.isNil):
            raise EmptyError("ERROR: The route is empty.")
        cur = self.head
        trvFlag = False
        while (not trvFlag):
            if (cur.key == key):
                return cur
            else:
                cur = cur.next
                if (cur.key == self.head.key):
                    trvFlag = True
        if (trvFlag):
            return RouteNilNode()

    def insert(self, m, n):
        if (n.isNil):
            raise EmptyError("ERROR: Cannot insert an empty node.")
        if (self.head.isNil):
            self.head = n
            n.next = n
            n.prev = n
            self.dist = 0
            if (self.asymFlag):
                self._revDist = 0
            self._count = 1
        else:
            self.dist += self.tau[m.key, n.key] + self.tau[n.key, m.next.key] - self.tau[m.key, m.next.key]
            if (self.asymFlag):
                self._revDist += self.tau[m.next.key, n.key] + self.tau[n.key, m.key] - self.tau[m.next.key, m.key]
            m.next.prev = n
            n.prev = m
            n.next = m.next
            m.next = n            
            self._count += 1
        return

    def append(self, n):
        if (self.head.isNil):
            self.head = n
            n.next = n
            n.prev = n
            self.dist = 0
            if (self.asymFlag):
                self._revDist = 0
            self._count = 1
        else:
            return self.insert(self.head.prev, n)

    def remove(self, n):
        self.dist += self.tau[n.prev.key, n.next.key] - self.tau[n.prev.key, n.key] - self.tau[n.key, n.next.key]
        if (self.asymFlag):
            self._revDist += self.tau[n.next.key, n.prev.key] - self.tau[n.key, n.prev.key] - self.tau[n.next.key, n.key]
        n.prev.next = n.next
        n.next.prev = n.prev
        if (self.head.key == n.key):
            self.head = n.next
        self._count -= 1

    def swap(self, n):
        nPrev = n.prev
        nNext = n.next
        nNNext = n.next.next
        # Pointers
        nPrev.next = nNext
        n.prev = nNext
        n.next = nNNext
        nNext.prev = nPrev
        nNext.next = n
        nNNext.prev = n
        # Calculate dist
        self.dist += (self.tau[nPrev.key, nNext.key] + self.tau[nNext.key, n.key] + self.tau[n.key, nNNext.key]
                    - self.tau[nPrev.key, n.key] - self.tau[n.key, nNext.key] - self.tau[nNext.key, nNNext.key])
        if (self.asymFlag):
            self._revDist += (self.tau[nNNext.key, n.key] + self.tau[n.key, nNext.key] + self.tau[nNext.key, nPrev.key]
                            - self.tau[nNNext.key, nNext.key] + self.tau[nNext.key, n.key] - self.tau[n.key, nPrev.key])

    def exchange(self, nI, nJ):
        if (nI == nJ):
            raise KeyExistError("ERROR: Cannot swap itself")
        # Old: = = = i j k l m n = = = | -> exchange(j, m)
        # New: = = = i m k l j n = = =
        if (nI.next.key == nJ.key):
            self.swap(nI)
        if (nI.next.next.key == nJ.key):
            # Old: = = pI nI nX nJ sJ = =
            # New: = = pI nJ nX nI sJ = =
            pI = nI.prev
            nX = nI.next
            sJ = nJ.next
            pI.next = nJ
            nJ.prev = pI
            nJ.next = nX
            nX.prev = nJ
            nX.next = nI
            nI.prev = nX
            nI.next = sJ
            sJ.prev = nI
            self.dist += (self.tau[pI.key, nJ.key] + self.tau[nJ.key, nX.key] + self.tau[nX.key, nI.key] + self.tau[nI.key, sJ.key]
                - self.tau[pI.key, nI.key] - self.tau[nI.key, nX.key] - self.tau[nX.key, nJ.key] - self.tau[nJ.key, sJ.key])
            if (self.asymFlag):
                self._revDist += (self.tau[sJ.key, nI.key] + self.tau[nI.key, nX.key] + self.tau[nX.key, nJ.key] + self.tau[nJ.key, pI.key]
                    - self.tau[sJ.key, nJ.key] - self.tau[nJ.key, nX.key] - self.tau[nX.key, nI.key] - self.tau[nI.key, pI.key])

        else:
            # Old: = = pI nI sI x x x pJ nJ sJ = =
            # New: = = pI nJ sI x x x pJ nI sJ = =
            pI = nI.prev
            sI = nI.next
            pJ = nJ.prev
            sJ = nJ.next            
            pI.next = nJ
            nJ.prev = pI
            nJ.next = sI
            sI.prev = nJ
            pJ.next = nI
            nI.prev = pJ
            nI.next = sJ
            sJ.prev = nI
            self.dist += (self.tau[pI.key, nJ.key] + self.tau[nJ.key, sI.key] + self.tau[pJ.key, nI.key] + self.tau[nI.key, sJ.key]
                - self.tau[pI.key, nI.key] - self.tau[nI.key, sI.key] - self.tau[pJ.key, nJ.key] - self.tau[nJ.key, sJ.key])
            if (self.asymFlag):
                self._revDist += (self.tau[sJ.key, nI.key] + self.tau[nI.key, pJ.key] + self.tau[sI.key, nJ.key] + self.tau[nJ.key, pI.key]
                    - self.tau[sJ.key, nJ.key] - self.tau[nJ.key, pJ.key] - self.tau[sI.key, nI.key] - self.tau[nI.key, pI.key])

    def cheapestInsert(self, n):
        # First, insert it after self.head
        # Before: ... --> head -> xxx -> head.next --> ...
        # After:  ... --> head ->  n  -> head.next --> ...
        self.insert(self.head, n)
        sofarCheapestCost = self.dist if not self.asymFlag else min(self.dist, self._revDist)
        sofarCheapestKey = self.head
        if (self._count <= 2):
            return
        cur = self.head
        trvFlag = True
        while (trvFlag):
            self.swap(n)
            cur = cur.next
            newCost = self.dist if not self.asymFlag else min(self.dist, self._revDist)
            if (newCost < sofarCheapestCost):
                sofarCheapestCost = newCost
                sofarCheapestKey = cur
            if (cur.key == self.head.key):
                trvFlag = False
        self.remove(n)
        self.insert(sofarCheapestKey, n)
        if (self.asymFlag and self.dist > self._revDist):
            self.reverse()

    def findLargestRemoval(self, noRemoval=None) -> int:
        if (noRemoval == None):
            noRemoval = [self.head.key]
        bestRemovalCost = self.dist if not self.asymFlag else max(self.dist, self._revDist)
        bestRemovalKey = None
        cur = self.head
        trvFlag = True
        while (trvFlag):
            cur = cur.next
            if (cur.key not in noRemoval):
                newDist = (self.dist + self.tau[cur.prev.key, cur.next.key] 
                    - self.tau[cur.prev.key, cur.key] - self.tau[cur.key, cur.next.key])
                if (self.asymFlag):
                    newRevDist = (self._revDist + self.tau[cur.next.key, cur.prev.key]
                        - self.tau[cur.next.key, cur.key] - self.tau[cur.key, cur.prev.key])
                    newDist = min(newDist, newRevDist)
                if (newDist < bestRemovalCost):
                    bestRemovalCost = newDist
                    bestRemovalKey = cur.key
            if (cur.key == self.head.key):
                trvFlag = False
        return {
            'bestRemovalKey': bestRemovalKey,
            'bestRemovalCost': bestRemovalCost
        }

    def impv2Opt(self):
        # NOTE: Now its better.
        oriHeadKey = self.head.key
        nI = self.head.next
        sofarBestDist = self.dist if not self.asymFlag else min(self.dist, self._revDist)
        improvedFlag = False
        canImpvFlag = True
        while (canImpvFlag):
            canImpvFlag = False

            endKey = nI.prev.key
            while (nI.key != endKey):
                # 1. First attempt
                # Old: = = = nI nINext nJ nJNext nJ2Next nJ3Next nJ4Next = = = | -> exchange(nINext, nJ)        | -> exchange(nINext, nJ)
                # 2. Follow-up attempts
                # New: = = = nI nJ nINext nJNext nJ2Next nJ3Next nJ4Next = = = | -> exchange(nINext, nJNext)    | -> remove(nJNext)
                #                                                                -> exchange(nJ, nJNext)          -> insert(nI, nJNext)
                # New: = = = nI nJNext nJ nINext nJ2Next nJ3Next nJ4Next = = = | -> exchange(nINext, n2JNext)   | -> remove(nJ2Next)
                #                                                                -> exchange(nJ, nJ2Next)         -> insert(nI, nJ2Next)
                #                                                                -> exchange(nJNext, nJ2Next)
                # New: = = = nI nJ2Next nJNext nJ nINext nJ3Next nJ4Next = = = | -> exchange(nINext, n3JNext)   | -> remove(nJ3Next)
                #                                                                -> exchange(nJ, nJ3Next)         -> insert(nI, nJ3Next)
                #                                                                -> exchange(nJNext, nJ3Next) 
                #                                                                -> exchange(nJ2Next, nJ3Next)
                # New: = = = nI nJ3Next nJ2Next nJNext nJ nINext nJ4Next = = =
                # ...
                # 3. Recover to initial status (Until: nJXNext == nIPrev)
                # Old: nI nJ = = = nINext nJNext (nIPrev) | -> exchange(nJNext, nI)
                # New: nI nJNext nJ = = = nINext
                # self.reverse()

                # 1. First attempt
                nJ = nI.next.next
                nINext = nI.next
                self.swap(nINext)
                newDist = self.dist if not self.asymFlag else min(self.dist, self._revDist)
                if (newDist < sofarBestDist):
                    sofarBestDist = newDist
                    self.rehead(oriHeadKey)
                    canImpvFlag = True
                    improvedFlag = True
                    break

                # 2. Follow-up attempts
                for _ in range(self._count - 4):
                    nJXNext = nINext.next
                    self.remove(nJXNext)
                    self.insert(nI, nJXNext)
                    newDist = self.dist if not self.asymFlag else min(self.dist, self._revDist)
                    if (newDist < sofarBestDist):
                        sofarBestDist = newDist
                        self.rehead(oriHeadKey)
                        canImpvFlag = True
                        improvedFlag = True
                        break
                if (canImpvFlag):
                    break

                # 3. Recover to initial status
                nJXNext = nINext.next
                self.swap(nJXNext)
                self.reverse()
                self.rehead(oriHeadKey)
                
                nI = nI.next
        return improvedFlag
