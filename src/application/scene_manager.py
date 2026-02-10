"""
scene_manager.py  --  Application Layer
Manages all 3D objects on the virtual build plate, their transforms, and copies.
Pure Python logic -- no GUI or rendering imports.
"""
from __future__ import annotations

import uuid
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import trimesh


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------
@dataclass
class Transform:
    """Affine transform applied to a scene object (mm / degrees)."""
    translation: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    rotation_deg: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    scale: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float64))

    # ---- helpers -----------------------------------------------------------
    def to_matrix(self) -> np.ndarray:
        """Return a 4x4 homogeneous transform matrix."""
        rx, ry, rz = np.radians(self.rotation_deg)
        Rx = trimesh.transformations.rotation_matrix(rx, [1, 0, 0])
        Ry = trimesh.transformations.rotation_matrix(ry, [0, 1, 0])
        Rz = trimesh.transformations.rotation_matrix(rz, [0, 0, 1])
        R = Rz @ Ry @ Rx

        S = np.eye(4)
        S[0, 0], S[1, 1], S[2, 2] = self.scale

        T = np.eye(4)
        T[:3, 3] = self.translation

        return T @ R @ S


# ---------------------------------------------------------------------------
# Scene Object  (one loaded model instance)
# ---------------------------------------------------------------------------
@dataclass
class SceneObject:
    uid: str
    name: str
    mesh: trimesh.Trimesh
    transform: Transform = field(default_factory=Transform)
    visible: bool = True
    selected: bool = False

    @property
    def transformed_mesh(self) -> trimesh.Trimesh:
        """Return a *copy* of the mesh with the transform baked in."""
        m = self.mesh.copy()
        m.apply_transform(self.transform.to_matrix())
        return m

    @property
    def bounds_mm(self) -> np.ndarray:
        """Axis-aligned bounding box after transform: [[min_x,y,z],[max_x,y,z]]."""
        return self.transformed_mesh.bounds


# ---------------------------------------------------------------------------
# Build Plate definition
# ---------------------------------------------------------------------------
@dataclass
class BuildPlate:
    """Cylindrical SLM build plate (default: EOS M290-style 120 mm dia)."""
    diameter_mm: float = 120.0
    height_mm: float = 20.0
    origin: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))

    @property
    def radius(self) -> float:
        return self.diameter_mm / 2.0


# ---------------------------------------------------------------------------
# SceneManager  --  single source of truth for the build layout
# ---------------------------------------------------------------------------
class SceneManager:
    """
    Owns every model currently on the build plate.

    Responsibilities
    ----------------
    * Add / remove / duplicate objects
    * Track selection state (for the GUI)
    * Provide the complete transformed mesh list for slicing
    """

    def __init__(self, build_plate: Optional[BuildPlate] = None) -> None:
        self.build_plate = build_plate or BuildPlate()
        self._objects: Dict[str, SceneObject] = {}
        self._selection_uid: Optional[str] = None

    # ---- queries -----------------------------------------------------------
    @property
    def objects(self) -> List[SceneObject]:
        return list(self._objects.values())

    @property
    def selected_object(self) -> Optional[SceneObject]:
        if self._selection_uid and self._selection_uid in self._objects:
            return self._objects[self._selection_uid]
        return None

    @property
    def object_count(self) -> int:
        return len(self._objects)

    def get_object(self, uid: str) -> Optional[SceneObject]:
        return self._objects.get(uid)

    # ---- commands ----------------------------------------------------------
    def add_mesh(self, name: str, mesh: trimesh.Trimesh) -> SceneObject:
        """Place a new mesh on the build plate (centred at origin)."""
        uid = uuid.uuid4().hex[:8]

        # Auto-centre on XY, place on plate surface (Z=0)
        centroid = mesh.centroid.copy()
        mesh.apply_translation(-centroid)
        z_min = mesh.bounds[0][2]
        mesh.apply_translation([0, 0, -z_min])  # sit on Z=0

        obj = SceneObject(uid=uid, name=name, mesh=mesh)
        self._objects[uid] = obj
        self.select(uid)
        return obj

    def remove(self, uid: str) -> bool:
        if uid in self._objects:
            del self._objects[uid]
            if self._selection_uid == uid:
                self._selection_uid = None
            return True
        return False

    def remove_selected(self) -> bool:
        if self._selection_uid:
            return self.remove(self._selection_uid)
        return False

    def duplicate(self, uid: str, offset: Optional[np.ndarray] = None) -> Optional[SceneObject]:
        """Deep-copy an existing object and place it with an optional offset."""
        source = self._objects.get(uid)
        if source is None:
            return None
        new_uid = uuid.uuid4().hex[:8]
        new_mesh = source.mesh.copy()
        new_transform = copy.deepcopy(source.transform)

        if offset is None:
            offset = np.array([source.mesh.extents[0] * 1.2, 0.0, 0.0])
        new_transform.translation = source.transform.translation + offset

        obj = SceneObject(
            uid=new_uid,
            name=f"{source.name}_copy",
            mesh=new_mesh,
            transform=new_transform,
        )
        self._objects[new_uid] = obj
        self.select(new_uid)
        return obj

    def duplicate_selected(self, offset: Optional[np.ndarray] = None) -> Optional[SceneObject]:
        if self._selection_uid:
            return self.duplicate(self._selection_uid, offset)
        return None

    def select(self, uid: Optional[str]) -> None:
        # deselect previous
        if self._selection_uid and self._selection_uid in self._objects:
            self._objects[self._selection_uid].selected = False
        self._selection_uid = uid
        if uid and uid in self._objects:
            self._objects[uid].selected = True

    def deselect_all(self) -> None:
        self.select(None)

    def set_transform(self, uid: str, **kwargs) -> None:
        """Update transform fields for an object.
        Accepts keyword args: translation, rotation_deg, scale (numpy arrays).
        """
        obj = self._objects.get(uid)
        if obj is None:
            return
        if "translation" in kwargs:
            obj.transform.translation = np.asarray(kwargs["translation"], dtype=np.float64)
        if "rotation_deg" in kwargs:
            obj.transform.rotation_deg = np.asarray(kwargs["rotation_deg"], dtype=np.float64)
        if "scale" in kwargs:
            obj.transform.scale = np.asarray(kwargs["scale"], dtype=np.float64)

    # ---- slicing facade ----------------------------------------------------
    def collect_transformed_meshes(self) -> List[trimesh.Trimesh]:
        """Return every visible object's transformed mesh (ready for slicing)."""
        return [obj.transformed_mesh for obj in self._objects.values() if obj.visible]

    def collect_for_slicing(self) -> List[dict]:
        """Return a lightweight description list suitable for passing to SlicerService."""
        result = []
        for obj in self._objects.values():
            if not obj.visible:
                continue
            result.append({
                "uid": obj.uid,
                "name": obj.name,
                "mesh": obj.transformed_mesh,
            })
        return result
