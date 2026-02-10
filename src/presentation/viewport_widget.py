"""
viewport_widget.py  --  PySide6 + PyVistaQt 3D Viewport
Embeds VTK rendering inside a Qt widget for the SLM slicer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtCore import Signal

if TYPE_CHECKING:
    from src.application.scene_manager import SceneManager, SceneObject


class SLMViewport(QtInteractor):
    """
    3D viewport for the SLM slicer with embedded VTK rendering.
    
    Features:
    - Displays cylindrical build plate
    - Renders STL meshes with transforms
    - Click-to-select with ray tracing
    - Visual selection highlighting
    
    Signals:
    - object_selected: Emitted when user clicks on a mesh (uid: str)
    """
    
    object_selected = Signal(str)  # uid of selected object
    
    def __init__(self, scene: SceneManager, parent=None):
        """
        Initialize the viewport.
        
        Parameters
        ----------
        scene : SceneManager
            Reference to the scene manager (application layer)
        parent : QWidget, optional
            Parent Qt widget
        """
        super().__init__(parent)
        
        self.scene = scene
        self._mesh_actors = {}  # uid -> vtkActor mapping
        self._plate_actor = None
        
        # Setup the plotter
        self.enable_trackball_style()
        self.set_background("lightgray")
        
        # Create build plate geometry
        self._create_build_plate()
        
        # Setup camera
        self._reset_camera()
        
        # Enable picking (callback receives picked actor)
        self.enable_block_picking(callback=self._on_surface_picked)
    
    def _create_build_plate(self) -> None:
        """Create and add the cylindrical build plate to the scene."""
        plate = self.scene.build_plate
        
        # Create cylinder mesh
        cylinder = pv.Cylinder(
            center=(0, 0, 0),
            direction=(0, 0, 1),
            radius=plate.radius,
            height=plate.height_mm,
        )
        
        # Add to plotter
        self._plate_actor = self.add_mesh(
            cylinder,
            color="gray",
            opacity=0.3,
            show_edges=True,
            edge_color="darkgray",
            pickable=False,  # Don't allow picking the build plate
        )
    
    def _reset_camera(self) -> None:
        """Set default camera position (isometric view)."""
        plate = self.scene.build_plate
        radius = plate.radius
        
        # Position camera at 45° angle
        distance = radius * 2.5
        self.camera_position = [
            (distance * 0.7, -distance * 0.7, distance * 0.6),  # position
            (0, 0, radius * 0.15),  # focal point
            (0, 0, 1),  # view up
        ]
        self.reset_camera_clipping_range()
    
    def rebuild_scene(self) -> None:
        """
        Rebuild the entire 3D scene from the scene manager state.
        Call this whenever objects are added/removed/transformed.
        """
        # Remove all mesh actors
        for uid, actor in list(self._mesh_actors.items()):
            self.remove_actor(actor)
        self._mesh_actors.clear()
        
        # Re-add all objects from scene manager
        for obj in self.scene.objects:
            if obj.visible:
                self._add_mesh_to_scene(obj)
        
        self.render()
    
    def _add_mesh_to_scene(self, obj: SceneObject) -> None:
        """
        Add a single scene object to the VTK renderer.
        
        Parameters
        ----------
        obj : SceneObject
            The object to add
        """
        # Get transformed mesh
        mesh_trimesh = obj.transformed_mesh
        
        # Convert trimesh to PyVista
        vertices = mesh_trimesh.vertices
        faces = np.hstack([[3, *face] for face in mesh_trimesh.faces])
        
        pv_mesh = pv.PolyData(vertices, faces)
        
        # Determine color based on selection state
        color = "orange" if obj.selected else "lightblue"
        
        # Add to plotter
        actor = self.add_mesh(
            pv_mesh,
            color=color,
            show_edges=True,
            edge_color="black",
            opacity=1.0,
            pickable=True,
        )
        
        # Store actor reference
        self._mesh_actors[obj.uid] = actor
        
        # Store uid in actor for picking
        actor.GetProperty().SetInformation(pv.ID_TYPE_KEY, obj.uid)
    
    def _on_surface_picked(self, picked_point) -> None:
        """
        Callback when user clicks on a surface.
        
        Parameters
        ----------
        picked_point : tuple
            The 3D coordinates of the picked point
        """
        # Get the picked actor
        picker = self.picker
        if picker is None or picker.GetActor() is None:
            return
        
        picked_actor = picker.GetActor()
        
        # Find which object was picked
        for uid, actor in self._mesh_actors.items():
            if actor == picked_actor:
                # Emit signal to notify GUI
                self.object_selected.emit(uid)
                break
    
    def highlight_selected(self, uid: Optional[str]) -> None:
        """
        Update visual highlighting for the selected object.
        
        Parameters
        ----------
        uid : str or None
            UID of the object to highlight, or None to clear selection
        """
        # Update colors for all objects
        for obj_uid, actor in self._mesh_actors.items():
            if obj_uid == uid:
                actor.GetProperty().SetColor(1.0, 0.5, 0.0)  # Orange
            else:
                actor.GetProperty().SetColor(0.7, 0.8, 1.0)  # Light blue
        
        self.render()
    
    def reset_view(self) -> None:
        """Reset camera to default isometric view."""
        self._reset_camera()
        self.render()
    
    def fit_to_scene(self) -> None:
        """Zoom camera to fit all objects in view."""
        self.reset_camera()
        self.render()
    
    def set_view(self, direction: str) -> None:
        """
        Set camera to a specific orthogonal view.
        
        Parameters
        ----------
        direction : str
            One of: 'front', 'top', 'left', 'right', 'iso'
        """
        plate = self.scene.build_plate
        r = plate.radius
        dist = r * 2.5
        fp = (0, 0, r * 0.15)  # focal point
        
        views = {
            "front": [(0, -dist, fp[2]), fp, (0, 0, 1)],
            "top": [(0, 0, dist), fp, (0, -1, 0)],
            "left": [(-dist, 0, fp[2]), fp, (0, 0, 1)],
            "right": [(dist, 0, fp[2]), fp, (0, 0, 1)],
            "iso": [(dist * 0.7, -dist * 0.7, dist * 0.6), fp, (0, 0, 1)],
        }
        
        if direction.lower() in views:
            self.camera_position = views[direction.lower()]
            self.reset_camera_clipping_range()
            self.render()
