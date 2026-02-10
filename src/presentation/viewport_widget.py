"""
viewport_widget.py  --  PySide6 + PyVistaQt 3D Viewport
=========================================================
Cura-inspired 3D viewport for the SLM slicer application.
Embeds VTK rendering inside a Qt widget with click-to-select
picking, cylindrical build-plate visualisation, and interactive
object manipulation (Move/Rotate).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtCore import Signal, Qt, QPoint, QTimer

if TYPE_CHECKING:
    from src.application.scene_manager import SceneManager, SceneObject


class SLMViewport(QtInteractor):
    """
    Industrial 3D viewport for the SLM Slicer.

    Features
    --------
    - Cylindrical build plate  (120 mm diameter x 10 mm height)  <-- User Req #1
    - Reference grid on build surface (Z = 0)
    - Click-to-select via VTK prop picking
    - Interactive Move/Rotate tools (User Req #2, #3)
    - Visual selection highlighting
    - Camera presets

    Signals
    -------
    object_selected(str)
        Emitted with the UID of the mesh the user clicked.
    """

    object_selected = Signal(str)

    # Tool Constants
    TOOL_MOVE = 0
    TOOL_SCALE = 1
    TOOL_ROTATE = 2
    TOOL_MIRROR = 3

    def __init__(self, scene: "SceneManager", parent=None):
        super().__init__(parent)
        self.scene = scene
        self._mesh_actors: Dict[str, object] = {}
        self._plate_actors: List[object] = []
        self._ready = False

        # Interaction state
        self._current_tool: Optional[int] = None
        self._drag_active = False
        self._drag_start_pos = QPoint()
        self._drag_obj_uid: Optional[str] = None
        self._drag_initial_transform = None  # (translation, rotation, scale)
        self._drag_plane_point: Optional[np.ndarray] = None  # for Move tool

        # Renderer defaults
        try:
            self.enable_trackball_style()
        except AttributeError:
            pass
        self.set_background("#EAEAEA", top="#CFCFCF")

        # Post-construction init (avoids VTK race conditions with Qt)
        QTimer.singleShot(0, self._deferred_init)

    def _deferred_init(self) -> None:
        if self._ready:
            return
        self._ready = True
        self._create_build_plate()
        self._create_floor_grid()
        self._setup_default_camera()
        try:
            self.add_axes(interactive=False)
        except Exception:
            pass

    # ------------------------------------------------------------------
    #  Tool Mode
    # ------------------------------------------------------------------

    def set_tool(self, tool_id: int) -> None:
        """Set the active interaction tool (Move, Rotate, etc.)."""
        self._current_tool = tool_id
        # We could add visual cursors here later

    # ------------------------------------------------------------------
    #  Build Plate  (120 mm dia, 10 mm tall, top at Z = 0)
    # ------------------------------------------------------------------

    def _create_build_plate(self) -> None:
        """Render the cylindrical SLM build plate."""
        for a in self._plate_actors:
            try:
                self.remove_actor(a)
            except Exception:
                pass
        self._plate_actors.clear()

        plate = self.scene.build_plate
        r = plate.radius           # 60 mm
        h = plate.height_mm        # 10 mm

        # --- Top disc (build surface) at Z = 0 --------------------------
        try:
            disc = pv.Disc(center=(0, 0, 0), inner=0, outer=r,
                           normal=(0, 0, 1), r_res=1, c_res=72)
        except Exception:
            # Fallback
            n = 72
            theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
            pts = np.column_stack([r * np.cos(theta), r * np.sin(theta),
                                   np.zeros(n)])
            pts = np.vstack([[0, 0, 0], pts])
            cells = []
            for i in range(n):
                cells.extend([3, 0, i + 1, ((i + 1) % n) + 1])
            disc = pv.PolyData(pts, faces=np.array(cells, dtype=np.int_))

        a1 = self.add_mesh(disc, color="#A8A8A8", opacity=0.55,
                           show_edges=False, pickable=False,
                           reset_camera=False)
        self._plate_actors.append(a1)

        # --- Cylinder body (below build surface) -------------------------
        # Center at -h/2 so top is at Z=0
        cyl = pv.Cylinder(center=(0, 0, -h / 2), direction=(0, 0, 1),
                          radius=r, height=h, resolution=72, capping=True)
        a2 = self.add_mesh(cyl, color="#8A8A8A", opacity=0.22,
                           show_edges=False, pickable=False,
                           reset_camera=False)
        self._plate_actors.append(a2)

        # --- Top-edge ring -----------------------------------------------
        n_ring = 128
        theta = np.linspace(0, 2 * np.pi, n_ring + 1)
        ring_pts = np.column_stack(
            [r * np.cos(theta), r * np.sin(theta), np.zeros(n_ring + 1)]
        )
        segs = np.column_stack(
            [np.full(n_ring, 2), np.arange(n_ring), np.arange(1, n_ring + 1)]
        )
        ring = pv.PolyData(ring_pts, lines=segs.ravel())
        a3 = self.add_mesh(ring, color="#555555", line_width=2,
                           pickable=False, reset_camera=False)
        self._plate_actors.append(a3)

    def _create_floor_grid(self) -> None:
        plate = self.scene.build_plate
        r = plate.radius
        spacing = 10.0
        pts: list = []
        segs: list = []
        idx = 0

        for coord in np.arange(-r + spacing, r, spacing):
            half = np.sqrt(max(0.0, r ** 2 - coord ** 2))
            pts += [[coord, -half, 0.02], [coord, half, 0.02]]
            segs.append([2, idx, idx + 1]); idx += 2
            pts += [[-half, coord, 0.02], [half, coord, 0.02]]
            segs.append([2, idx, idx + 1]); idx += 2

        if pts:
            grid = pv.PolyData(
                np.array(pts, dtype=np.float64),
                lines=np.array(segs, dtype=np.int_).ravel(),
            )
            a = self.add_mesh(grid, color="#B8B8B8", line_width=1,
                              opacity=0.35, pickable=False,
                              reset_camera=False)
            self._plate_actors.append(a)

    # ------------------------------------------------------------------
    #  Scene & Camera
    # ------------------------------------------------------------------

    def _setup_default_camera(self) -> None:
        r = self.scene.build_plate.radius
        d = r * 3.0
        self.camera_position = [
            (d * 0.75, -d * 0.85, d * 0.55),
            (0, 0, r * 0.05),
            (0, 0, 1),
        ]
        self.reset_camera_clipping_range()

    def reset_view(self) -> None:
        self._setup_default_camera()
        self.render()

    def fit_to_scene(self) -> None:
        self.reset_camera()
        self.render()

    def set_view(self, direction: str) -> None:
        r = self.scene.build_plate.radius
        d = r * 3.0
        fp = (0, 0, r * 0.05)
        presets = {
            "front": [(0, -d, fp[2]), fp, (0, 0, 1)],
            "back":  [(0,  d, fp[2]), fp, (0, 0, 1)],
            "top":   [(0,  0,  d),    fp, (0, -1, 0)],
            "left":  [(-d, 0, fp[2]), fp, (0, 0, 1)],
            "right": [(d,  0, fp[2]), fp, (0, 0, 1)],
            "iso":   [(d * 0.75, -d * 0.85, d * 0.55), fp, (0, 0, 1)],
        }
        if direction.lower() in presets:
            self.camera_position = presets[direction.lower()]
            self.reset_camera_clipping_range()
            self.render()

    def rebuild_scene(self) -> None:
        """Rebuild all mesh actors from the SceneManager state."""
        for actor in self._mesh_actors.values():
            try:
                self.remove_actor(actor)
            except Exception:
                pass
        self._mesh_actors.clear()

        for obj in self.scene.objects:
            if obj.visible:
                self._add_mesh_actor(obj)

        self.render()

    def _add_mesh_actor(self, obj: "SceneObject") -> None:
        tm = obj.transformed_mesh
        verts = np.asarray(tm.vertices, dtype=np.float64)
        faces_raw = np.asarray(tm.faces, dtype=np.int_)
        cells = np.column_stack(
            [np.full(len(faces_raw), 3), faces_raw]
        ).ravel()
        pv_mesh = pv.PolyData(verts, cells)

        colour = "#FF8C1A" if obj.selected else "#6EC6FF"
        actor = self.add_mesh(
            pv_mesh, color=colour, show_edges=True,
            edge_color="#3A3A3A", opacity=1.0, pickable=True,
            reset_camera=False,
        )
        self._mesh_actors[obj.uid] = actor

    def highlight_selected(self, uid: Optional[str]) -> None:
        for obj_uid, actor in self._mesh_actors.items():
            prop = actor.GetProperty()
            if obj_uid == uid:
                prop.SetColor(1.0, 0.55, 0.1)
                prop.SetEdgeColor(0.8, 0.30, 0.0)
            else:
                prop.SetColor(0.43, 0.78, 1.0)
                prop.SetEdgeColor(0.23, 0.23, 0.23)
        self.render()

    # ------------------------------------------------------------------
    #  Interactive Manipulation (Analysis Requirement #2 & #3)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):          # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            
            # Use pick to find object
            picked_uid = self._pick_uid_at(event.pos())
            
            # If clicked on an object and a tool is active, start dragging
            if picked_uid and self._current_tool is not None:
                # Select it if not already
                if picked_uid != self.scene.selected_object:
                    self.object_selected.emit(picked_uid)
                    
                obj = self.scene.get_object(picked_uid)
                if obj and obj.selected:
                    self._start_drag(obj, event.pos())
                    # Do NOT call super() to prevent camera orbit
                    return

            # If clicked on an object (even without tool), emit selection
            if picked_uid:
                self.object_selected.emit(picked_uid)
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):           # noqa: N802
        if self._drag_active and self._current_tool is not None:
            obj = self.scene.get_object(self._drag_obj_uid)
            if obj:
                self._update_drag(obj, event.pos())
                self.render()
                return  # Consume event

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):        # noqa: N802
        if self._drag_active:
            self._end_drag()
            super().mouseReleaseEvent(event)
            return

        # Regular click logic (if not dragged)
        super().mouseReleaseEvent(event)

    def _start_drag(self, obj: "SceneObject", qt_pos: QPoint) -> None:
        self._drag_active = True
        self._drag_obj_uid = obj.uid
        # Clone transform for undo/initial state
        self._drag_initial_transform = obj.transform.clone()
        
        if self._current_tool == self.TOOL_MOVE:
            # Raycast to Z=0 plane to get anchor point
            self._drag_plane_point = self._intersect_z_plane(qt_pos)

    def _update_drag(self, obj: "SceneObject", qt_pos: QPoint) -> None:
        if self._current_tool == self.TOOL_MOVE:
            if self._drag_plane_point is None:
                return
            new_pt = self._intersect_z_plane(qt_pos)
            if new_pt is not None:
                delta = new_pt - self._drag_plane_point
                # Apply delta to initial position
                new_trans = self._drag_initial_transform.translation + delta
                # Update SceneManager directly (no undo per frame)
                self.scene.set_transform(
                    obj.uid, translation=new_trans, record_undo=False
                )
                # Re-render actor geometry is tricky slightly efficiently
                # But here we just rebuild the whole scene or just that actor?
                # Rebuilding is safest for visual sync.
                self.rebuild_scene()

        elif self._current_tool == self.TOOL_ROTATE:
            # Horizontal drag rotates around Z
            dx = qt_pos.x() - self._drag_start_pos.x()
            angle_delta = dx * 0.5  # sensitivity
            
            init_rot = self._drag_initial_transform.rotation_deg
            new_z = init_rot[2] - angle_delta  # Minus to match intuitive drag
            
            new_rot = init_rot.copy()
            new_rot[2] = new_z
            
            self.scene.set_transform(
                obj.uid, rotation_deg=new_rot, record_undo=False
            )
            self.rebuild_scene()

        elif self._current_tool == self.TOOL_SCALE:
            # Vertical drag scales
            dy = qt_pos.y() - self._drag_start_pos.y()
            scale_factor = 1.0 - (dy * 0.01)
            new_scale = self._drag_initial_transform.scale * scale_factor
            
            self.scene.set_transform(
                obj.uid, scale=new_scale, record_undo=False
            )
            self.rebuild_scene()

    def _end_drag(self) -> None:
        """Commit the final transform to Undo stack."""
        if not self._drag_obj_uid:
            self._drag_active = False
            return

        obj = self.scene.get_object(self._drag_obj_uid)
        if obj:
            # Push Undo entry representing the whole move
            from src.application.scene_manager import _UndoEntry
            entry = _UndoEntry(
                obj.uid,
                self._get_tool_name(),
                self._drag_initial_transform,
                obj.transform.clone()
            )
            self.scene.undo_redo.push(entry)

        self._drag_active = False
        self._drag_obj_uid = None
        self._drag_plane_point = None

    def _get_tool_name(self) -> str:
        if self._current_tool == self.TOOL_MOVE: return "Move"
        if self._current_tool == self.TOOL_ROTATE: return "Rotate"
        if self._current_tool == self.TOOL_SCALE: return "Scale"
        return "Transform"

    # ------------------------------------------------------------------
    #  Ray Casting Helpers
    # ------------------------------------------------------------------

    def _pick_uid_at(self, qt_pos: QPoint) -> Optional[str]:
        """Find object UID under mouse cursor."""
        try:
            import vtk
            picker = vtk.vtkPropPicker()
            vtk_y = self.height() - qt_pos.y() - 1
            picker.Pick(qt_pos.x(), vtk_y, 0, self.renderer)
            actor = picker.GetActor()
            if actor:
                for uid, stored in self._mesh_actors.items():
                    if stored is actor:
                        return uid
        except Exception:
            pass
        return None

    def _intersect_z_plane(self, qt_pos: QPoint) -> Optional[np.ndarray]:
        """Intersect camera ray with Z=0 plane."""
        # Get start (near) and end (far) points of ray in world space
        try:
            vtk_y = self.height() - qt_pos.y() - 1
            self.renderer.SetDisplayPoint(qt_pos.x(), vtk_y, 0.0)
            self.renderer.DisplayToWorld()
            near = np.array(self.renderer.GetWorldPoint()[:3])
            
            self.renderer.SetDisplayPoint(qt_pos.x(), vtk_y, 1.0)
            self.renderer.DisplayToWorld()
            far = np.array(self.renderer.GetWorldPoint()[:3])
            
            direction = far - near
            if np.isclose(direction[2], 0):
                return None  # Ray parallel to plane
            
            # t for Ray = near + t * direction, intersecting Z=0
            # near.z + t * direction.z = 0  => t = -near.z / direction.z
            t = -near[2] / direction[2]
            return near + t * direction
        except Exception:
            return None
