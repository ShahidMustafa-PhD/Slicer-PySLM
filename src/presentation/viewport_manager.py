"""
viewport_manager.py  --  Presentation Layer  (Cura 5.x exact viewport)
======================================================================

Bridges PyVista (off-screen VTK renderer) with Dear PyGui
(dynamic texture).  Provides:

* Light gray background (Cura viewport_background #FAFAFA)
* Build plate with Cura buildplate color (#F4F4F4)
* Reference grid (Cura buildplate_grid #B4B4B4 / minor #E4E4E4)
* Axis orientation arrows (Cura x_axis/y_axis/z_axis colors)
* Ambient + key + fill three-point lighting
* Orbit / Pan / Zoom via mouse
* Tool-specific object interaction: Move / Scale / Rotate / Mirror
* Object XY-plane dragging
* Layer preview mode for PREVIEW stage
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np
import pyvista as pv

# Force off-screen BEFORE any plotter is created
pv.OFF_SCREEN = True

import dearpygui.dearpygui as dpg

from src.application.scene_manager import SceneManager, SceneObject


# =========================================================================
#  Visual constants  (Cura cura-light/theme.json exact values)
# =========================================================================
_BG_COLOR     = (0.980, 0.980, 0.980)   # viewport_background [250,250,250]

_PLATE_COLOR  = "#F4F4F4"               # buildplate [244,244,244]
_PLATE_EDGE   = "#B4B4B4"               # buildplate_grid
_GRID_COLOR   = "#E4E4E4"               # buildplate_grid_minor

_MESH_COLOR   = "#A0D8EF"               # Cura-style light blue (default object)
_SELECTED_CLR = "#3282FF"               # model_selection_outline [50,130,255]
_GHOST_CLR    = "#C0C0C0"               # unselected hint
_WARN_CLR     = "#DA1E28"               # out-of-bounds warning colour


class ViewportManager:
    """
    Owns the PyVista off-screen plotter and renders each frame into
    a Dear PyGui dynamic texture.
    """

    def __init__(
        self,
        scene: SceneManager,
        width: int = 1024,
        height: int = 740,
        texture_tag: str = "viewport_texture",
    ) -> None:
        self.scene = scene
        self.width = width
        self.height = height
        self.texture_tag = texture_tag

        # --- PyVista plotter ---
        self.plotter = pv.Plotter(
            off_screen=True,
            window_size=[self.width, self.height],
            lighting="three lights",
        )
        self.plotter.set_background(
            color=_BG_COLOR, top=_BG_COLOR,
        )

        # Camera defaults (isometric-ish, looking at origin)
        self.plotter.camera_position = [
            (120, -120, 100),   # position
            (0, 0, 15),         # focal point
            (0, 0, 1),          # view-up
        ]

        # --- Interaction state ---
        self._lmb = False
        self._rmb = False
        self._mmb = False
        self._last: Optional[Tuple[float, float]] = None
        self._drag_uid: Optional[str] = None

        # Active tool  (set by the GUI)
        self._active_tool: str = "move"

        # Sensitivity
        self._orbit_speed = 0.35
        self._pan_speed   = 0.30
        self._zoom_speed  = 0.08

        # Layer preview state
        self._preview_mode: bool = False
        self._preview_layers: List = []
        self._preview_layer_idx: int = 0

    # ---- Tool property ----------------------------------------------------
    @property
    def active_tool(self) -> str:
        return self._active_tool

    @active_tool.setter
    def active_tool(self, tool: str) -> None:
        self._active_tool = tool

    # =====================================================================
    #  Setup
    # =====================================================================
    def register_texture(self) -> None:
        """Create the DPG dynamic texture (call after dpg.create_context)."""
        blank = [0.0] * (self.width * self.height * 4)
        with dpg.texture_registry(show=False):
            dpg.add_dynamic_texture(
                width=self.width, height=self.height,
                default_value=blank, tag=self.texture_tag,
            )

    # =====================================================================
    #  Scene rebuild  (objects added / removed / selection changed)
    # =====================================================================
    def rebuild_scene(self) -> None:
        """Full re-render: plate + grid + axes + all meshes."""
        self.plotter.clear()
        self._add_build_plate()
        self._add_grid()
        self._add_axes()
        self._add_scene_objects()
        self.plotter.reset_camera_clipping_range()
        self._push_frame()

    def refresh(self) -> None:
        """Lightweight re-render (camera change only)."""
        self._push_frame()

    # =====================================================================
    #  Build plate
    # =====================================================================
    def _add_build_plate(self) -> None:
        plate = self.scene.build_plate
        cyl = pv.Cylinder(
            center=(0, 0, -plate.height_mm / 2.0),
            direction=(0, 0, 1),
            radius=plate.radius,
            height=plate.height_mm,
            resolution=80,
            capping=True,
        )
        self.plotter.add_mesh(
            cyl, color=_PLATE_COLOR,
            show_edges=False, opacity=0.55,
            smooth_shading=True,
            name="__plate__",
        )

        # Top-face ring highlight
        ring = pv.Disc(
            center=(0, 0, 0.01), inner=plate.radius - 0.3,
            outer=plate.radius, normal=(0, 0, 1), c_res=80,
        )
        self.plotter.add_mesh(
            ring, color=_PLATE_EDGE, opacity=0.7,
            name="__plate_ring__",
        )

    # =====================================================================
    #  Grid & Axes
    # =====================================================================
    def _add_grid(self) -> None:
        r = self.scene.build_plate.radius
        sz = int(r * 2.6)
        res = max(12, sz // 10)
        grid = pv.Plane(
            center=(0, 0, -0.02), direction=(0, 0, 1),
            i_size=sz, j_size=sz,
            i_resolution=res, j_resolution=res,
        )
        self.plotter.add_mesh(
            grid, color=_GRID_COLOR, style="wireframe",
            opacity=0.25, name="__grid__",
        )

    def _add_axes(self) -> None:
        """Small XYZ arrows near origin (Cura axis colours)."""
        length = self.scene.build_plate.radius * 0.25
        origin = np.array([-self.scene.build_plate.radius * 0.85,
                           -self.scene.build_plate.radius * 0.85, 0.5])
        # Cura axis colours: x_axis=[218,30,40], y_axis=[25,110,240], z_axis=[36,162,73]
        for axis, color in zip(
            [np.array([1, 0, 0]), np.array([0, 1, 0]), np.array([0, 0, 1])],
            ["#DA1E28", "#196EF0", "#24A249"],
        ):
            arrow = pv.Arrow(
                start=origin, direction=axis,
                scale=length, tip_length=0.3,
                tip_radius=0.12, shaft_radius=0.04,
            )
            self.plotter.add_mesh(
                arrow, color=color, opacity=0.85,
                name=f"__axis_{color}__",
            )

    # =====================================================================
    #  Meshes
    # =====================================================================
    def _add_scene_objects(self) -> None:
        for obj in self.scene.objects:
            if not obj.visible:
                continue
            tmesh = obj.transformed_mesh
            pv_mesh = pv.wrap(tmesh)

            if obj.selected:
                self.plotter.add_mesh(
                    pv_mesh, color=_SELECTED_CLR,
                    show_edges=True, edge_color="#196EF0",
                    opacity=1.0, smooth_shading=True,
                    name=obj.uid,
                )
            else:
                self.plotter.add_mesh(
                    pv_mesh, color=_MESH_COLOR,
                    show_edges=False,
                    opacity=0.92, smooth_shading=True,
                    name=obj.uid,
                )

    # =====================================================================
    #  Framebuffer -> DPG texture
    # =====================================================================
    def _push_frame(self) -> None:
        try:
            img = self.plotter.screenshot(None, return_img=True)
        except Exception:
            return

        h, w = img.shape[:2]
        if h != self.height or w != self.width:
            try:
                from PIL import Image as PILImage
                pil = PILImage.fromarray(img).resize(
                    (self.width, self.height), PILImage.LANCZOS,
                )
                img = np.asarray(pil)
            except ImportError:
                return

        rgba = np.ones((self.height, self.width, 4), dtype=np.float32)
        rgba[:, :, :3] = img.astype(np.float32) / 255.0
        dpg.set_value(self.texture_tag, rgba.flatten().tolist())

    # =====================================================================
    #  Mouse handlers
    # =====================================================================
    def on_mouse_down(self, button: int, pos: Tuple[float, float]) -> None:
        if button == 0:
            self._lmb = True
        elif button == 1:
            self._rmb = True
        elif button == 2:
            self._mmb = True
        self._last = pos

    def on_mouse_up(self, button: int) -> None:
        if button == 0:
            self._lmb = False
            self._drag_uid = None
        elif button == 1:
            self._rmb = False
        elif button == 2:
            self._mmb = False
        self._last = None

    def on_mouse_move(self, pos: Tuple[float, float],
                      on_transform_cb=None) -> None:
        """Handle mouse movement.
        on_transform_cb: optional callback invoked after a tool transform
        so the GUI can sync the sidebar.
        """
        if self._last is None:
            self._last = pos
            return

        dx = pos[0] - self._last[0]
        dy = pos[1] - self._last[1]
        self._last = pos

        if dx == 0 and dy == 0:
            return

        cam = self.plotter.camera

        if self._rmb:
            # ORBIT
            cam.Azimuth(-dx * self._orbit_speed)
            cam.Elevation(-dy * self._orbit_speed)
            self.plotter.reset_camera_clipping_range()
            self._push_frame()

        elif self._mmb:
            # PAN
            fp  = np.array(cam.focal_point)
            pos_cam = np.array(cam.position)
            up  = np.array(cam.up)
            fwd = fp - pos_cam
            fwd /= (np.linalg.norm(fwd) + 1e-12)
            right = np.cross(fwd, up)
            right /= (np.linalg.norm(right) + 1e-12)
            up_n = np.cross(right, fwd)
            shift = (-dx * right + dy * up_n) * self._pan_speed
            cam.focal_point = tuple(fp + shift)
            cam.position    = tuple(pos_cam + shift)
            self.plotter.reset_camera_clipping_range()
            self._push_frame()

        elif self._lmb and self._drag_uid:
            obj = self.scene.get_object(self._drag_uid)
            if not obj:
                return

            tool = self._active_tool

            if tool == "move":
                # OBJECT DRAG on XY plane
                obj.transform.translation[0] += dx * 0.15
                obj.transform.translation[1] -= dy * 0.15
                self.rebuild_scene()
                if on_transform_cb:
                    on_transform_cb()

            elif tool == "scale":
                # Uniform scale by drag distance
                factor = 1.0 + (dx - dy) * 0.005
                factor = max(0.01, factor)
                obj.transform.scale *= factor
                self.rebuild_scene()
                if on_transform_cb:
                    on_transform_cb()

            elif tool == "rotate":
                # Rotate around Z axis
                angle_deg = dx * 0.5
                obj.transform.rotation_deg[2] += angle_deg
                self.rebuild_scene()
                if on_transform_cb:
                    on_transform_cb()

            elif tool == "mirror":
                # Mirror is click-based (handled by GUI), not drag
                pass

    def on_mouse_wheel(self, delta: float) -> None:
        factor = 1.0 - delta * self._zoom_speed
        self.plotter.camera.Zoom(factor)
        self.plotter.reset_camera_clipping_range()
        self._push_frame()

    # =====================================================================
    #  Object picking (improved: distance to projected centroid)
    # =====================================================================
    def try_pick_object(self, mouse_pos: Tuple[float, float]) -> Optional[str]:
        """Pick the object whose projected centroid is closest to mouse_pos.
        Uses camera projection for better accuracy than pure 3D distance."""
        best_uid = None
        best_dist = float("inf")

        # Attempt projection-based picking
        try:
            cam = self.plotter.camera
            renderer = self.plotter.renderer
            w, h = self.width, self.height

            for obj in self.scene.objects:
                if not obj.visible:
                    continue
                centre = obj.transformed_mesh.centroid

                # Use VTK coordinate conversion
                coord = renderer.world_to_display(centre)
                if coord is not None:
                    sx, sy = coord[0], h - coord[1]  # flip Y
                    d = math.sqrt((sx - mouse_pos[0]) ** 2 + (sy - mouse_pos[1]) ** 2)
                    if d < best_dist and d < 150:  # 150px threshold
                        best_dist = d
                        best_uid = obj.uid
        except Exception:
            # Fallback: simple 3D centroid proximity
            cam_pos = np.array(self.plotter.camera.position)
            for obj in self.scene.objects:
                if not obj.visible:
                    continue
                centre = obj.transformed_mesh.centroid
                dist = np.linalg.norm(centre - cam_pos)
                if dist < best_dist:
                    best_dist = dist
                    best_uid = obj.uid

        return best_uid

    def start_drag(self, uid: str) -> None:
        self._drag_uid = uid

    # =====================================================================
    #  Layer Preview mode  (for PREVIEW stage)
    # =====================================================================
    def set_preview_mode(self, enabled: bool) -> None:
        self._preview_mode = enabled
        if not enabled:
            self._preview_layers = []
            self._preview_layer_idx = 0

    def set_preview_data(self, parts: list) -> None:
        """Load SLMPart list for preview. Combines all layer contours."""
        self._preview_layers = []
        # Merge layers across parts by z-height
        z_map: dict[float, list] = {}
        for part in parts:
            for layer in part.layers:
                z_key = round(layer.z_height, 4)
                if z_key not in z_map:
                    z_map[z_key] = []
                z_map[z_key].extend(layer.contours)
        for z in sorted(z_map.keys()):
            self._preview_layers.append((z, z_map[z]))
        self._preview_layer_idx = min(
            self._preview_layer_idx, max(0, len(self._preview_layers) - 1)
        )

    @property
    def preview_layer_count(self) -> int:
        return len(self._preview_layers)

    @property
    def preview_layer_index(self) -> int:
        return self._preview_layer_idx

    @preview_layer_index.setter
    def preview_layer_index(self, idx: int) -> None:
        self._preview_layer_idx = max(0, min(idx, len(self._preview_layers) - 1))

    def rebuild_preview(self) -> None:
        """Render the current preview layer as 3D lines on the build plate."""
        self.plotter.clear()
        self._add_build_plate()
        self._add_grid()
        self._add_axes()

        if self._preview_layers and 0 <= self._preview_layer_idx < len(self._preview_layers):
            z, contours = self._preview_layers[self._preview_layer_idx]
            for ci, contour in enumerate(contours):
                if contour is None or len(contour) < 2:
                    continue
                pts_2d = np.array(contour)
                if pts_2d.ndim != 2 or pts_2d.shape[1] < 2:
                    continue
                n = pts_2d.shape[0]
                pts_3d = np.zeros((n, 3))
                pts_3d[:, :2] = pts_2d[:, :2]
                pts_3d[:, 2] = z
                try:
                    line = pv.lines_from_points(pts_3d)
                    self.plotter.add_mesh(
                        line, color="#196EF0", line_width=2,
                        name=f"__contour_{ci}__",
                    )
                except Exception:
                    pass

            # Add a transparent disc at current Z to show layer plane
            disc = pv.Disc(
                center=(0, 0, z), inner=0,
                outer=self.scene.build_plate.radius,
                normal=(0, 0, 1), c_res=80,
            )
            self.plotter.add_mesh(
                disc, color="#196EF0", opacity=0.08, name="__layer_plane__",
            )

        self.plotter.reset_camera_clipping_range()
        self._push_frame()

    # =====================================================================
    #  Cleanup
    # =====================================================================
    def shutdown(self) -> None:
        try:
            self.plotter.close()
        except Exception:
            pass
