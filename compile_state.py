from cline import Line, Circle
from instruction import Compute, Parameterize
from util import *


class CompileState:
    def __init__(self, sample_bucket, solve_bucket):

        self.sample_bucket = sample_bucket
        self.solve_bucket = solve_bucket

        self.visited = sample_bucket.points
        self.solve_instructions = list()
        self.ps = solve_bucket.points
        self.cs = solve_bucket.assertions
        self.open_roots = dict()
        self.root_blacklist = list()

        self.compute_tricks = [
            self.computeCircumcenter
            , self.computeOrthocenter
            , self.computeMidp
            , self.computeIncenter
            , self.computeMixIncenter
            , self.computeInterLL
            , self.computeInter
        ]

        self.param_tricks = [
            self.paramOnSeg
            , self.paramOnLine
            , self.paramOnCirc
            , self.paramCoords
        ]

    def solve(self):
        while self.ps:
            p = self.ps.pop(0)
            self.process_point(p)
            self.visited.append(p)

        # Resolve roots
        if self.open_roots:
            for key, root in self.open_roots.items():
                self.root_blacklist.append(root)
            if self.root_blacklist:
                print(f"[WARNING] root blacklist: {self.root_blacklist}")

                self.visited = self.sample_bucket.points
                self.solve_instructions = list()
                self.ps = solve_bucket.points
                self.cs = solve_bucket.assertions
                self.open_roots = dict()
                return self.solve()
        else:
            for c in self.cs:
                self.solve_instructions.append(Assert(c))
                for ndg in c.ndgs:
                    self.solve_instructions.append(AssertNDG(ndg))
                for ordC in c.orders:
                    self.solve_instructions.append(Assert(ordC))

    def process_point(self, p):

        # Get all constraints to process for point p
        cs_for_p = list()
        for c in self.cs:
            if p in c.points and all(p1 == p or p1 in self.visited for p1 in c.points):
                cs_for_p.append(c)

        for trick in (self.compute_tricks + self.param_tricks):
            if trick(p, cs_for_p):
                return

    '''
    Compute Tricks
    '''
    def computeCircumcenter(self, p, cs):
        ccCs = [c for c in cs if c.pred == "circumcenter"]
        for c in ccCs:
            if c.points[0] == p:
                self.solve_instructions.append(Compute(p, ["circumcenter", c.points[1:]]))
                self.cs.remove(c)
                return True
        return False

    def computeOrthocenter(self, p, cs):
        orthocenterCs = [c for c in cs if c.pred == "orthocenter"]
        for c in orthocenterCs:
            if c.points[0] == p:
                self.solve_instructions.append(Compute(p, ["orthocenter", c.points[1:]]))
                self.cs.remove(c)
                return True
        return False


    def computeMidp(self, p, cs):
        midpCs = [c for c in cs if c.pred == "midp"]
        for c in midpCs:
            if c.points[0] == p:
                self.solve_instructions.append(Compute(p, ["midp", c.points[1:]]))
                self.cs.remove(c)
                return True
        return False


    def computeIncenter(self, p, cs):
        incenterCs = [c for c in cs if c.pred == "incenter"]
        for c in incenterCs:
            if c.points[0] == p:
                self.solve_instructions.append(Compute(p, ["incenter", c.points[1:]]))
                self.cs.remove(c)
                return True
        return False

    def computeMixIncenter(self, p, cs):
        mixIncenterCs = [c for c in cs if c.pred == "mixtilinearIncenter"]
        for c in mixIncenterCs:
            if c.points[0] == p:
                self.solve_instructions.append(Compute(p, ["mixtilinearIncenter", c.points[1:]]))
                self.cs.remove(c)
                return True
        return False

    def computeInterLL(self, p, cs):
        interllCs = [c for c in cs if c.pred == "interLL"]
        for c in interllCs:
            if c.points[0] == p:
                a, b, c, d = c.points[1:]
                l1 = Line("connecting", [a, b])
                l2 = Line("connecting", [c, d])
                self.solve_instructions.append(Compute(p, ["interLL", l1, l2]))
                self.cs.remove(c)
                return True
        return False

    def computeInter(self, p, cs):
        lines = self.linesFor(p, cs)
        circles = self.circlesFor(p, cs)

        if len(lines) >= 2:
            cs1, l1 = lines[0]
            cs2, l2 = lines[1]
            self.solve_instructions.append(Compute(p, ["interLL", l1, l2]))
            for c in cs1 + cs2:
                self.cs.remove(c)
            return True
        elif len(lines) == 1 and circles:
            cs1, l = lines[0]
            cs2, circ = circles[0]

            root, rcs = determine_root(p, l, circ, cs)
            if root is None:
                return False
            self.solve_instructions.append(Compute(p, ["interLC", l, circ, root]))
            for c in cs1 + cs2 + rcs:
                self.cs.remove(c)
            return True
        elif len(circles) >= 2:
            cs1, c1 = circles[0]
            cs2, c2 = circles[1]

            root, rcs = determine_root(p, c1, c2, cs)
            if root is None:
                return False
            self.solve_instructions.append(Compute(p, ["interCC", c1, c2, root]))
            for c in cs1 + cs2 + rcs:
                self.cs.remove(c)
            return True
        return False



    '''
    Parameterization Tricks
    '''
    def paramOnSeg(self, p, cs):
        onSegCs = [c for c in cs if c.pred == "onSeg"]
        for c in onSegCs:
            if c.points[0] == p:
                self.solve_instructions.append(Parameterize(p, ["onSeg", c.points[1:3], c.points[3:]]))
                self.cs.remove(c)
                return True
        return False

    def paramOnLine(self, p, cs):
        lines = self.linesFor(p, cs)
        if lines:
            lcs, l = lines[0]
            self.solve_instructions.append(Parameterize(p, ["onLine", l]))
            for c in lcs:
                self.cs.remove(c)
            return True
        return False

    def paramOnCirc(self, p, cs):
        circles = self.circlesFor(p, cs)
        if circles:
            ccs, circ = circles[0]
            self.solve_instructions.append(Parameterize(p, ["onCirc", circ]))
            for c in ccs:
                self.cs.remove(c)
            return True
        return False


    def paramCoords(self, p, cs):
        print(f"WARNING: point is parameterized by its coordinates: {p}")
        self.solve_instructions.append(Parameterize(p, ["coords"]))
        return True


    '''
    Utility Functions
    '''
    # Note: For each line, returns (constraint that determines line, line)
    def linesFor(self, p, cs):
        lines = list()

        for c in cs:
            pred = c.pred
            ps = c.points
            if pred == "coll":
                other_ps = [p1 for p1 in ps if p1 != p]
                lines.append((c, Line("connecting", other_ps)))
        return lines

    def circlesFor(self, p, cs):
        circles = list()

        for c in cs:
            pred = c.pred
            ps = c.points
            if pred == "cycl":
                other_ps = [p1 for p1 in ps if p1 != p]
                lines.append((c, Circle("c3", other_ps)))
        return circles

    # Returns (root, constraints to get root)
    # Responsible for updating blacklist and open roots
    def determine_root(self, p, cl1, cl2, cs):
        # FIXME: Should we try for all combos of lines and circles?
        # FIXME: Should key be sorted?

        k = (cl1, cl1) # key
        shared_points = list(set(cl1.pointsOn()).intersect(cl2.pointsOn()))
        oppCs = [c for c in cs if c.pred == "oppSides"]
        sameCs = [c for c in cs if c.pred == "sameSides"]

        if k in self.open_roots: # rsNotPrevious
            root = Root("neq", [self.open_roots[k]]) # FIXME: Check that self.open_roots[k] is a point, not a list
            del self.open_roots[k]
            return (root, list())
        elif shared_lc_points: # rsNeq
            root = Root("neq", [shared_lc_points[0]])
            return (root, list())
        elif oppCs and (oppCs[0].points[0] == p or oppCs[0].points[1] == p):
            a, b, c, d = oppCs[0].points[0], oppCs[0].points[1], oppCs[0].points[2], oppCs[0].points[3]
            if oppCs[0].points[0] == p:
                root = Root("oppSides", [b, Line("connecting", [c, d])])
            else: # oppCs[0].points[1] == p
                root = Root("oppSides", [a, Line("connecting", [c, d])])
            return (root, [oppCs[0]])
        elif sameCs and (sameCs[0].points[0] == p or sameCs[0].points[1] == p):
            a, b, c, d = sameCs[0].points[0], sameCs[0].points[1], sameCs[0].points[2], sameCs[0].points[3]
            if sameCs[0].points[0] == p:
                root = Root("sameSides", [b, Line("connecting", [c, d])])
            else: # sameCs[0].points[1] == p
                root = Root("sameSides", [a, Line("connecting", [c, d])])
            return (root, [sameCs[0]])
        else:
            # rsArbitrary
            if p not in self.root_blacklist:
                self.open_roots[key] = p
                root = Root("arbitrary", list())
                return (root, list())
            else:
                return (None, None)
