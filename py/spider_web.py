import math
import maya.cmds as cmds
import maya.api.OpenMaya as om


class SpiderWeb:
    _instance_count = 0

    def __init__(self, radius: float = 3.0, height: float = 0.5,
                 spoke_count: int = 8, rib_count: int = 3, web_thickness: float = 0.05,
                 web_curvature: float = 1.0, mesh_detail: int = 8):
        # Data
        self.radius = radius
        self.height = height
        self.spoke_count = spoke_count
        self.rib_count = rib_count
        self.web_thickness = web_thickness
        self.web_curvature = web_curvature
        self.mesh_detail = mesh_detail

        SpiderWeb._instance_count += 1
        self.instance_id = SpiderWeb._instance_count

        # Objects
        self.spoke_curves = []
        self.rib_curves = []
        self.root_locator = None
        self.curve_group = None
        self.mesh_group = None

        # Lattice
        self.lattice = None
        self.lattice_base = None
        self.lattice_deformer = None

    def spoke_offset(self, i: int):
        return self.radius * math.cos(((2 * math.pi) / self.spoke_count) * i), \
               0, \
               self.radius * math.sin(((2 * math.pi) / self.spoke_count) * i)

    def spoke_curve_offset(self, i: int):
        spoke_offset = list(self.spoke_offset(i))
        spoke_offset[0] *= 0.5
        spoke_offset[2] *= 0.5
        spoke_offset[1] = self.web_curvature
        return tuple(spoke_offset)

    def spoke_point_at(self, i: int, t: float):
        p0 = (0, self.height, 0)
        p1 = self.spoke_curve_offset(i)
        p2 = self.spoke_offset(i)
        return (
            (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1],
            (1 - t) ** 2 * p0[2] + 2 * (1 - t) * t * p1[2] + t ** 2 * p2[2],
        )

    def rib_offset(self, i: int, j: int):
        t = (j - 1) / self.rib_count
        return self.spoke_point_at(i, t)

    def create_mesh(self):
        cmds.select(cmds.listRelatives(self.curve_group, children=True))
        cmds.sweepMeshFromCurve()

        creator = cmds.ls(type="sweepMeshCreator")[0]
        cmds.setAttr(f"{creator}.capsEnable", True)
        cmds.setAttr(f"{creator}.profilePolySides", self.mesh_detail)
        cmds.setAttr(f"{creator}.scaleProfileX", self.web_thickness)
        cmds.setAttr(f"{creator}.scaleProfileY", self.web_thickness)
        cmds.setAttr(f"{creator}.interpolationPrecision", 90)
        cmds.setAttr(f"{creator}.interpolationOptimize", 1)

        sweep_meshes = cmds.ls("sweep*")
        self.mesh_group = cmds.group(sweep_meshes, name=f"spiderWeb_{self.instance_id}_meshes_grp")

    def create_lattice(self):
        lattice_size = self.radius * 2.2

        cmds.select(cmds.listRelatives(self.mesh_group, children=True))

        ffd = cmds.lattice(divisions=(self.spoke_count*2, self.height*2, self.spoke_count*2),
                           objectCentered=True,
                           ldivisions=(self.spoke_count*2, self.height*2, self.spoke_count*2))

        self.lattice_deformer = ffd[0]
        self.lattice = ffd[1]
        self.lattice_base = ffd[2]

        self.lattice = cmds.rename(self.lattice, f"spiderWeb_{self.instance_id}_lattice")
        self.lattice_base = cmds.rename(self.lattice_base, f"spiderWeb_{self.instance_id}_latticeBase")

        cmds.setAttr(f"{self.lattice_deformer}.localInfluenceS", 2)
        cmds.setAttr(f"{self.lattice_deformer}.localInfluenceT", 2)
        cmds.setAttr(f"{self.lattice_deformer}.localInfluenceU", 12)

        cmds.parent(self.lattice, self.root_locator)
        cmds.parent(self.lattice_base, self.root_locator)

    def create_clusters(self):
        s_div, t_div, u_div = cmds.lattice(self.lattice_deformer, q=True, divisions=True)

        for i, spoke_curve in enumerate(self.spoke_curves):
            close_points = []

            # Create temporary nearestPointOnCurve node
            npoc = cmds.createNode('nearestPointOnCurve')
            curve_shape = cmds.listRelatives(spoke_curve, shapes=True)[0]
            cmds.connectAttr(f"{curve_shape}.worldSpace[0]", f"{npoc}.inputCurve")

            for s in range(s_div):
                for t in range(t_div):
                    for u in range(u_div):
                        pt_name = f"{self.lattice}.pt[{s}][{t}][{u}]"
                        pt_pos = cmds.xform(pt_name, q=True, ws=True, t=True)

                        cmds.setAttr(f"{npoc}.inPosition", pt_pos[0], pt_pos[1], pt_pos[2])
                        closest_pos = cmds.getAttr(f"{npoc}.position")[0]

                        pt_vector = om.MVector(pt_pos[0], pt_pos[1], pt_pos[2])
                        curve_vector = om.MVector(closest_pos[0], closest_pos[1], closest_pos[2])
                        distance = (pt_vector - curve_vector).length()

                        if distance < self.radius * 0.15:
                            close_points.append(pt_name)

            cmds.delete(npoc)

            if close_points:
                cluster = cmds.cluster(close_points,
                                       name=f"spiderWeb_{self.instance_id}_cluster_{i}")
                cluster_handle = cmds.rename(cluster[1], f"spiderWeb_{self.instance_id}_clusterHandle_{i}")
                cmds.parent(cluster_handle, self.root_locator)

    def create_web(self):
        self.root_locator = cmds.spaceLocator(name=f"spiderWeb_{self.instance_id}_loc")[0]

        cmds.addAttr(self.root_locator, longName="webRadius", attributeType="double", defaultValue=self.radius)
        cmds.setAttr(f"{self.root_locator}.webRadius", self.radius)
        cmds.addAttr(self.root_locator, longName="webHeight", attributeType="double", defaultValue=self.height)
        cmds.setAttr(f"{self.root_locator}.webHeight", self.height)
        cmds.addAttr(self.root_locator, longName="webSpokeCount", attributeType="long", defaultValue=self.spoke_count)
        cmds.setAttr(f"{self.root_locator}.webSpokeCount", self.spoke_count)
        cmds.addAttr(self.root_locator, longName="webRibCount", attributeType="long", defaultValue=self.rib_count)
        cmds.setAttr(f"{self.root_locator}.webRibCount", self.rib_count)

        self.curve_group = cmds.group(empty=True, name=f"spiderWeb_{self.instance_id}_curves_grp")
        cmds.parent(self.curve_group, self.root_locator)

        for i in range(1, self.spoke_count + 1):
            curve = cmds.curve(d=2, p=[[0, self.height, 0], self.spoke_curve_offset(i), self.spoke_offset(i)],
                               name=f"spoke_{self.instance_id}_{i}")
            self.spoke_curves.append(curve)
            cmds.parent(curve, self.curve_group)

        for j in range(1, self.rib_count + 1):
            for i in range(1, self.spoke_count + 1):
                start_point = self.rib_offset(i, j)
                end_point = self.rib_offset(i + 1 if i < self.spoke_count else 1, j)

                center = (0, self.height, 0)
                straight_mid = (
                    (start_point[0] + end_point[0]) / 2,
                    (start_point[1] + end_point[1]) / 2,
                    (start_point[2] + end_point[2]) / 2
                )

                mid_point = (
                    straight_mid[0] * (1 - self.web_curvature) + center[0] * self.web_curvature,
                    straight_mid[1] * (1 - self.web_curvature) + center[1] * self.web_curvature,
                    straight_mid[2] * (1 - self.web_curvature) + center[2] * self.web_curvature
                )

                curve = cmds.curve(d=2, p=[start_point, mid_point, end_point],
                                   name=f"rib_{self.instance_id}_{j}_seg_{i}")
                self.rib_curves.append(curve)
                cmds.parent(curve, self.curve_group)

        self.create_mesh()
        self.create_lattice()
        self.create_clusters()

    def remove_web(self):
        if self.mesh_group and cmds.objExists(self.mesh_group):
            cmds.delete(self.mesh_group)
        if self.root_locator and cmds.objExists(self.root_locator):
            cmds.delete(self.root_locator)


def fetch_selected_web():
    sel = cmds.ls(selection=True)
    if not sel:
        return None
    loc = sel[0]

    if not cmds.objExists(f"{loc}.webRadius"):
        return None

    web = SpiderWeb(
        radius=cmds.getAttr(f"{loc}.webRadius"),
        height=cmds.getAttr(f"{loc}.webHeight"),
        spoke_count=int(cmds.getAttr(f"{loc}.webSpokeCount")),
        rib_count=int(cmds.getAttr(f"{loc}.webRibCount"))
    )

    web.root_locator = loc
    web.curve_group = [c for c in cmds.listRelatives(loc, children=True) if "grp" in c][0]
    web.spoke_curves = [c for c in cmds.listRelatives(web.curve_group, children=True) if "spoke" in c]
    web.rib_curves = [c for c in cmds.listRelatives(web.curve_group, children=True) if "rib" in c]

    # Find the mesh group
    loc_name = loc.split("_loc")[0]
    potential_mesh_group = f"{loc_name}_meshes_grp"
    if cmds.objExists(potential_mesh_group):
        web.mesh_group = potential_mesh_group

    return web


if (sel_web := fetch_selected_web()) is None:
    sel_web = SpiderWeb(radius=5.0, height=1.0,
                        spoke_count=12, rib_count=5, web_thickness=0.05,
                        web_curvature=0.75, mesh_detail=16)
    sel_web.create_web()
else:
    sel_web.remove_web()
