import maya.cmds as cmds
import math


class SpiderWeb:
    def __init__(self, radius: float = 3.0, height: float = 0.5, spoke_count: int = 8, rib_count: int = 3):
        # Data
        self.radius = radius
        self.height = height
        self.spoke_count = spoke_count
        self.rib_count = rib_count
        # Objects
        self.spoke_curves = []
        self.rib_curves = []
        self.root_locator = None
        self.curve_group = None

    def spoke_offset(self, i: int):
        return self.radius * math.cos(((2 * math.pi) / self.spoke_count) * i), \
               0, \
               self.radius * math.sin(((2 * math.pi) / self.spoke_count) * i)

    def rib_offset(self, i: int, j: int):
        s = self.spoke_offset(i)
        return s[0] * ((j - 1) / self.rib_count), (self.height * (self.rib_count - j + 1)) / self.rib_count, s[2] * (
                (j - 1) / self.rib_count)

    def create_web(self):
        self.root_locator = cmds.spaceLocator(name="spiderWeb_loc")[0]
        self.curve_group = cmds.group(empty=True, name="spiderWeb_curves_grp")
        cmds.parent(self.curve_group, self.root_locator)

        for i in range(1, self.spoke_count + 1):
            curve = cmds.curve(d=1, p=[[0, self.height, 0], self.spoke_offset(i)], name=f"spoke_{i}")
            self.spoke_curves.append(curve)
            cmds.parent(curve, self.curve_group)

        for j in range(1, self.rib_count + 1):
            points = [self.rib_offset(i, j) for i in range(1, self.spoke_count + 1)]
            points.append(self.rib_offset(1, j))

            curve = cmds.curve(d=1, p=points, name=f"rib_{j}")
            self.rib_curves.append(curve)
            cmds.parent(curve, self.curve_group)


web = SpiderWeb(radius=5.0, height=1.0, spoke_count=12, rib_count=4)
web.create_web()
