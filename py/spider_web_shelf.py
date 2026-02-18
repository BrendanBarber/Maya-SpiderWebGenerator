"""
Spider Web Generator Installer

Usage: Run this script in Maya's Script Editor to add a 'SpiderWeb'
button to the Custom shelf.
"""
import maya.cmds as cmds
import maya.mel as mel


SHELF_NAME = "Custom"
BUTTON_LABEL = "SpiderWeb"

# The full embedded command gets baked into the shelf button.
SHELF_COMMAND = r'''
import math
import types
import sys
import maya.cmds as cmds

# ------------------------------------------------------------------ #
#  Persistent namespace -- survives after exec() by living as a module
# ------------------------------------------------------------------ #
_MODULE_NAME = "_spiderWebShelf"
if _MODULE_NAME not in sys.modules:
    sys.modules[_MODULE_NAME] = types.ModuleType(_MODULE_NAME)
_mod = sys.modules[_MODULE_NAME]


# ------------------------------------------------------------------ #
#  SpiderWeb class
# ------------------------------------------------------------------ #
class SpiderWeb:
    _instance_count = 0

    def __init__(self, radius=3.0, height=0.5, spoke_count=8, rib_count=3,
                 web_thickness=0.05, web_curvature=1.0):
        self.radius = radius
        self.height = height
        self.spoke_count = spoke_count
        self.rib_count = rib_count
        self.web_thickness = web_thickness
        self.web_curvature = web_curvature

        SpiderWeb._instance_count += 1
        self.instance_id = SpiderWeb._instance_count

        self.spoke_curves = []
        self.rib_curves = []
        self.root_locator = None
        self.curve_group = None
        self.circle_controller = None
        self.wire_deformer = None

    def spoke_offset(self, i):
        return (self.radius * math.cos(((2 * math.pi) / self.spoke_count) * i),
                0,
                self.radius * math.sin(((2 * math.pi) / self.spoke_count) * i))

    def spoke_curve_offset(self, i):
        so = list(self.spoke_offset(i))
        so[0] *= 0.5
        so[2] *= 0.5
        so[1] = self.web_curvature
        return tuple(so)

    def spoke_point_at(self, i, t):
        p0 = (0, self.height, 0)
        p1 = self.spoke_curve_offset(i)
        p2 = self.spoke_offset(i)
        return (
            (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1],
            (1 - t) ** 2 * p0[2] + 2 * (1 - t) * t * p1[2] + t ** 2 * p2[2],
        )

    def rib_offset(self, i, j):
        t = (j - 1) / self.rib_count
        return self.spoke_point_at(i, t)

    def create_wire_deformer(self):
        self.circle_controller = cmds.circle(
            name=f"spiderWeb_{self.instance_id}_controller",
            center=(0, 0, 0), normal=(0, 1, 0),
            radius=self.radius, sections=self.spoke_count, degree=1
        )[0]
        cmds.parent(self.circle_controller, self.root_locator)
        cmds.select(self.spoke_curves)
        cmds.select(self.circle_controller, add=True)
        wire_result = cmds.wire(
            self.spoke_curves, wire=self.circle_controller,
            dropoffDistance=(0, 1),
            name=f"spiderWeb_{self.instance_id}_wire"
        )
        self.wire_deformer = wire_result[0]
        cmds.setAttr(f"{self.wire_deformer}.localInfluence", 0)

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

        center_loc = cmds.spaceLocator(name=f"spiderWeb_{self.instance_id}_center_loc")[0]
        cmds.parent(center_loc, self.root_locator)
        cmds.setAttr(f"{center_loc}.translateY", self.height)
        cmds.setAttr(f"{center_loc}.visibility", 0)
        cmds.setAttr(f"{center_loc}.overrideEnabled", 1)
        cmds.setAttr(f"{center_loc}.overrideDisplayType", 2)

        for i in range(1, self.spoke_count + 1):
            curve = cmds.curve(d=2, p=[[0, self.height, 0], self.spoke_curve_offset(i), self.spoke_offset(i)],
                               name=f"spoke_{self.instance_id}_{i}")
            self.spoke_curves.append(curve)
            cmds.parent(curve, self.curve_group)

        for j in range(1, self.rib_count + 1):
            rib_parameter = j / self.rib_count
            for i in range(1, self.spoke_count + 1):
                next_spoke = (i % self.spoke_count) + 1
                spoke_curve_1 = self.spoke_curves[i - 1]
                spoke_curve_2 = self.spoke_curves[next_spoke - 1]

                start_point = self.rib_offset(i, j)
                end_point = self.rib_offset(next_spoke, j)
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

                rib_curve = cmds.curve(d=2, p=[start_point, mid_point, end_point],
                                       name=f"rib_{self.instance_id}_{j}_seg_{i}")
                self.rib_curves.append(rib_curve)
                cmds.parent(rib_curve, self.curve_group)
                cmds.setAttr(f"{rib_curve}.inheritsTransform", 0)

                poci_start = cmds.createNode('pointOnCurveInfo', name=f"poci_rib_{self.instance_id}_{j}_{i}_start")
                cmds.connectAttr(f"{spoke_curve_1}.worldSpace[0]", f"{poci_start}.inputCurve")
                cmds.setAttr(f"{poci_start}.parameter", rib_parameter)
                cmds.connectAttr(f"{poci_start}.position", f"{rib_curve}.controlPoints[0]")

                poci_end = cmds.createNode('pointOnCurveInfo', name=f"poci_rib_{self.instance_id}_{j}_{i}_end")
                cmds.connectAttr(f"{spoke_curve_2}.worldSpace[0]", f"{poci_end}.inputCurve")
                cmds.setAttr(f"{poci_end}.parameter", rib_parameter)
                cmds.connectAttr(f"{poci_end}.position", f"{rib_curve}.controlPoints[2]")

                blend = cmds.createNode('blendColors', name=f"blend_rib_{self.instance_id}_{j}_{i}_mid")
                cmds.setAttr(f"{blend}.blender", self.web_curvature)

                avg = cmds.createNode('plusMinusAverage', name=f"avg_rib_{self.instance_id}_{j}_{i}")
                cmds.setAttr(f"{avg}.operation", 3)
                cmds.connectAttr(f"{poci_start}.position", f"{avg}.input3D[0]")
                cmds.connectAttr(f"{poci_end}.position", f"{avg}.input3D[1]")

                cmds.connectAttr(f"{avg}.output3D", f"{blend}.color2")
                cmds.connectAttr(f"{center_loc}.worldPosition[0]", f"{blend}.color1")
                cmds.connectAttr(f"{blend}.output", f"{rib_curve}.controlPoints[1]")

        self.create_wire_deformer()

_mod.SpiderWeb = SpiderWeb


# ------------------------------------------------------------------ #
#  Option Box UI
# ------------------------------------------------------------------ #
WINDOW_NAME = "spiderWebOptionBox"
_mod.WINDOW_NAME = WINDOW_NAME


def _toggle_transform_fields(*args):
    enabled = cmds.checkBoxGrp("swOB_moveEnabled", query=True, value1=True)
    cmds.floatFieldGrp("swOB_translate", edit=True, enable=enabled)
    cmds.floatFieldGrp("swOB_rotate", edit=True, enable=enabled)
    cmds.button("swOB_getFromSel", edit=True, enable=enabled)

_mod.toggle_transform_fields = _toggle_transform_fields


def _get_from_selection(*args):
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("Nothing selected. Select an object to get its transform.")
        return
    obj = sel[0]
    t = cmds.xform(obj, query=True, worldSpace=True, translation=True)
    r = cmds.xform(obj, query=True, worldSpace=True, rotation=True)
    cmds.floatFieldGrp("swOB_translate", edit=True,
                        value1=t[0], value2=t[1], value3=t[2])
    cmds.floatFieldGrp("swOB_rotate", edit=True,
                        value1=r[0], value2=r[1], value3=r[2])
    cmds.checkBoxGrp("swOB_moveEnabled", edit=True, value1=True)
    _mod.toggle_transform_fields()

_mod.get_from_selection = _get_from_selection


def _create_web(*args):
    SW = _mod.SpiderWeb
    radius = cmds.floatSliderGrp("swOB_radius", query=True, value=True)
    height = cmds.floatSliderGrp("swOB_height", query=True, value=True)
    spokes = cmds.intSliderGrp("swOB_spokes", query=True, value=True)
    ribs = cmds.intSliderGrp("swOB_ribs", query=True, value=True)
    thickness = cmds.floatSliderGrp("swOB_thickness", query=True, value=True)
    curvature = cmds.floatSliderGrp("swOB_curvature", query=True, value=True)

    web = SW(
        radius=radius, height=height,
        spoke_count=spokes, rib_count=ribs,
        web_thickness=thickness, web_curvature=curvature,
    )
    web.create_web()

    move_enabled = cmds.checkBoxGrp("swOB_moveEnabled", query=True, value1=True)
    if move_enabled:
        tx = cmds.floatFieldGrp("swOB_translate", query=True, value1=True)
        ty = cmds.floatFieldGrp("swOB_translate", query=True, value2=True)
        tz = cmds.floatFieldGrp("swOB_translate", query=True, value3=True)
        rx = cmds.floatFieldGrp("swOB_rotate", query=True, value1=True)
        ry = cmds.floatFieldGrp("swOB_rotate", query=True, value2=True)
        rz = cmds.floatFieldGrp("swOB_rotate", query=True, value3=True)
        cmds.xform(web.root_locator, worldSpace=True, translation=(tx, ty, tz))
        cmds.xform(web.root_locator, worldSpace=True, rotation=(rx, ry, rz))

    cmds.select(web.root_locator)
    print("Created spider web: {}".format(web.root_locator))

_mod.create_web = _create_web


def _close_window(*args):
    if cmds.window(_mod.WINDOW_NAME, exists=True):
        cmds.deleteUI(_mod.WINDOW_NAME)

_mod.close_window = _close_window


# ------------------------------------------------------------------ #
#  Create and show the option box
# ------------------------------------------------------------------ #
if cmds.window(WINDOW_NAME, exists=True):
    cmds.deleteUI(WINDOW_NAME)

cmds.window(WINDOW_NAME, title="Spider Web Options",
            widthHeight=(380, 420), sizeable=True)

cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

# Web Parameters
cmds.frameLayout(label="Web Parameters", collapsable=True,
                 borderStyle="etchedIn", marginWidth=8, marginHeight=8)
cmds.columnLayout(adjustableColumn=True, rowSpacing=2)

cmds.floatSliderGrp("swOB_radius", label="Radius", field=True,
                     minValue=0.1, maxValue=20.0, value=3.0,
                     columnWidth3=(80, 60, 200))
cmds.floatSliderGrp("swOB_height", label="Height", field=True,
                     minValue=0.0, maxValue=10.0, value=0.5,
                     columnWidth3=(80, 60, 200))
cmds.intSliderGrp("swOB_spokes", label="Spokes", field=True,
                   minValue=3, maxValue=32, value=8,
                   columnWidth3=(80, 60, 200))
cmds.intSliderGrp("swOB_ribs", label="Ribs", field=True,
                   minValue=1, maxValue=20, value=3,
                   columnWidth3=(80, 60, 200))
cmds.floatSliderGrp("swOB_thickness", label="Thickness", field=True,
                     minValue=0.005, maxValue=0.5, value=0.05,
                     columnWidth3=(80, 60, 200))
cmds.floatSliderGrp("swOB_curvature", label="Curvature", field=True,
                     minValue=0.0, maxValue=1.0, value=1.0,
                     columnWidth3=(80, 60, 200))

cmds.setParent("..")
cmds.setParent("..")

cmds.separator(style="in", height=8)

# Transform
cmds.frameLayout(label="Transform", collapsable=True,
                 borderStyle="etchedIn", marginWidth=8, marginHeight=8)
cmds.columnLayout(adjustableColumn=True, rowSpacing=4)

cmds.checkBoxGrp("swOB_moveEnabled", label="",
                  label1="Move After Creation", value1=False,
                  changeCommand="import sys; sys.modules['_spiderWebShelf'].toggle_transform_fields()")

cmds.floatFieldGrp("swOB_translate", label="Translate",
                    numberOfFields=3,
                    value1=0.0, value2=0.0, value3=0.0,
                    enable=False, columnWidth4=(80, 80, 80, 80))
cmds.floatFieldGrp("swOB_rotate", label="Rotate",
                    numberOfFields=3,
                    value1=0.0, value2=0.0, value3=0.0,
                    enable=False, columnWidth4=(80, 80, 80, 80))

cmds.button("swOB_getFromSel", label="Get from Selection",
            command="import sys; sys.modules['_spiderWebShelf'].get_from_selection()",
            enable=False)

cmds.setParent("..")
cmds.setParent("..")

cmds.separator(style="in", height=8)

# Action Buttons
cmds.rowLayout(numberOfColumns=2, columnWidth2=(185, 185),
               columnAlign2=("center", "center"))
cmds.button(label="Create",
            command="import sys; sys.modules['_spiderWebShelf'].create_web()",
            width=180, backgroundColor=(0.3, 0.5, 0.3))
cmds.button(label="Close",
            command="import sys; sys.modules['_spiderWebShelf'].close_window()",
            width=180)
cmds.setParent("..")

cmds.showWindow(WINDOW_NAME)
'''


def install_shelf_button():
    """Add a SpiderWeb button to Maya's Custom shelf"""
    shelf_top = mel.eval('$tmpVar=$gShelfTopLevel')

    if not cmds.shelfLayout(SHELF_NAME, exists=True):
        cmds.shelfLayout(SHELF_NAME, parent=shelf_top)

    # Remove existing button to allow re-install
    existing = cmds.shelfLayout(SHELF_NAME, query=True, childArray=True) or []
    for child in existing:
        if cmds.shelfButton(child, exists=True):
            if cmds.shelfButton(child, query=True, label=True) == BUTTON_LABEL:
                cmds.deleteUI(child)

    cmds.shelfButton(
        label=BUTTON_LABEL,
        annotation="Open Spider Web option box",
        image1="meshVarGroup.png",
        command=SHELF_COMMAND,
        sourceType="python",
        parent=SHELF_NAME,
    )
    print("SpiderWeb shelf button installed on '{}' shelf.".format(SHELF_NAME))


install_shelf_button()
