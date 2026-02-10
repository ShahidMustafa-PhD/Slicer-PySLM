"""
viewport_widget.py  --  PySide6 + PyVistaQt 3D Viewport
=========================================================
Cura-inspired 3D viewport for the SLM slicer application.
Embeds VTK rendering inside a Qt widget with click-to-select
picking and cylindrical build-plate visualisation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

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
    - Cylindrical build plate  (120 mm diameter x 10 mm height)
    - Reference grid on build surface (Z = 0)
    - Click-to-select via VTK prop picking
    - Visual selection highlighting  (orange = selected, blue = default)
    - Camera presets  (front / top / left / right / iso)

    Signals
    -------
    object_selected(str)
        Emitted with the UID of the mesh the user clicked.
    """

    object_selected = Signal(str)

    # ------------------------------------------------------------------
    #  Construction
    # ------------------------------------------------------------------

    def __init__(self, scene: "SceneManager", parent=None):
        super().__init__(parent)
        self.scene = scene
        self._mesh_actors: Dict[str, object] = {}
        self._plate_actors: List[object] = []
        self._press_pos: Optional[QPoint] = None
        self._ready = False

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
            # Fallback if pv.Disc unavailable
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
        cyl = pv.Cylinder(center=(0, 0, -h / 2), direction=(0, 0, 1),
                          radius=r, height=h, resolution=72, capping=True)
        a2 = self.add_mesh(cyl, color="#8A8A8A", opacity=0.22,
                           show_edges=False, pickable=False,
                           reset_camera=False)
        self._plate_actors.append(a2)

        # --- Top-edge ring at Z = 0 for visual delineation ---------------
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

    # ------------------------------------------------------------------
    #  Floor Grid  (10 mm spacing, clipped to circular plate)
    # ------------------------------------------------------------------

    def _create_floor_grid(self) -> None:
        plate = self.scene.build_plate
        r = plate.radius
        spacing = 10.0
        pts: list = []
        segs: list = []
        idx = 0

        for coord in np.arange(-r + spacing, r, spacing):
            half = np.sqrt(max(0.0, r ** 2 - coord ** 2))
            # Y-parallel line at X = coord
            pts += [[coord, -half, 0.02], [coord, half, 0.02]]
            segs.append([2, idx, idx + 1]); idx += 2
            # X-parallel line at Y = coord
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
    #  Camera
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

    # ------------------------------------------------------------------
    #  Scene Rebuild
    # ------------------------------------------------------------------

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
        """Convert one SceneObject (trimesh) to a PyVista actor."""
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

    # ------------------------------------------------------------------
    #  Click-to-Select  (Qt mouse events  →  VTK prop picker)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):          # noqa: N802
        if event.button() == Qt.LeftButton:
            self._press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):        # noqa: N802
        if event.button() == Qt.LeftButton and self._press_pos is not None:
            delta = event.pos() - self._press_pos
            if abs(delta.x()) + abs(delta.y()) < 8:   # click, not drag
                self._perform_pick(event.pos())
            self._press_pos = None
        super().mouseReleaseEvent(event)

    def _perform_pick(self, qt_pos: QPoint) -> None:
        """Use VTK vtkPropPicker to find the actor under the cursor."""
        try:
            import vtk
            picker = vtk.vtkPropPicker()
            vtk_y = self.height() - qt_pos.y() - 1   # Qt → VTK y-flip
            picker.Pick(qt_pos.x(), vtk_y, 0, self.renderer)
            actor = picker.GetActor()
            if actor is not None:
                for uid, stored in self._mesh_actors.items():
                    if stored is actor:
                        self.object_selected.emit(uid)
                        return
        except Exception:
            pass

    # ------------------------------------------------------------------
    #  Selection Highlighting
    # ------------------------------------------------------------------

    def highlight_selected(self, uid: Optional[str]) -> None:
        """Set colour of selected object to orange, rest to light-blue."""
        for obj_uid, actor in self._mesh_actors.items():
            prop = actor.GetProperty()
            if obj_uid == uid:
                prop.SetColor(1.0, 0.55, 0.1)       # orange
                prop.SetEdgeColor(0.8, 0.30, 0.0)
            else:
                prop.SetColor(0.43, 0.78, 1.0)       # light-blue
                prop.SetEdgeColor(0.23, 0.23, 0.23)
        self.render()
