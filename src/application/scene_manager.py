"""
scene_manager.py  --  Application Layer
Manages all 3D objects on the virtual build plate, their transforms, and copies.
Pure Python logic -- no GUI or rendering imports.
"""
from __future__ import annotations

import json
import math
import uuid
import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

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

    def to_dict(self) -> dict:
        """Serialise for save/load."""
        return {
            "translation": self.translation.tolist(),
            "rotation_deg": self.rotation_deg.tolist(),
            "scale": self.scale.tolist(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transform":
        return cls(
            translation=np.array(d["translation"], dtype=np.float64),
            rotation_deg=np.array(d["rotation_deg"], dtype=np.float64),
            scale=np.array(d["scale"], dtype=np.float64),
        )

    def clone(self) -> "Transform":
        return Transform(
            translation=self.translation.copy(),
            rotation_deg=self.rotation_deg.copy(),
            scale=self.scale.copy(),
        )


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
    source_path: str = ""  # file the mesh was loaded from

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
# Undo / Redo  (simple memento pattern)
# ---------------------------------------------------------------------------
class _UndoEntry:
    """Snapshot of one object transform for undo/redo."""
    __slots__ = ("uid", "label", "transform_before", "transform_after")

    def __init__(self, uid: str, label: str,
                 before: Transform, after: Transform) -> None:
        self.uid = uid
        self.label = label
        self.transform_before = before
        self.transform_after = after


class UndoRedoManager:
    """Linear undo/redo stack with a configurable depth limit."""

    def __init__(self, max_depth: int = 50) -> None:
        self._stack: List[_UndoEntry] = []
        self._index: int = -1
        self.max_depth = max_depth

    # ---- public API -------------------------------------------------------
    def push(self, entry: _UndoEntry) -> None:
        # discard any redo entries beyond current position
        self._stack = self._stack[: self._index + 1]
        self._stack.append(entry)
        if len(self._stack) > self.max_depth:
            self._stack.pop(0)
        self._index = len(self._stack) - 1

    def can_undo(self) -> bool:
        return self._index >= 0

    def can_redo(self) -> bool:
        return self._index < len(self._stack) - 1

    @property
    def undo_label(self) -> str:
        if self.can_undo():
            return self._stack[self._index].label
        return ""

    @property
    def redo_label(self) -> str:
        if self.can_redo():
            return self._stack[self._index + 1].label
        return ""

    def undo(self) -> Optional[_UndoEntry]:
        if not self.can_undo():
            return None
        entry = self._stack[self._index]
        self._index -= 1
        return entry

    def redo(self) -> Optional[_UndoEntry]:
        if not self.can_redo():
            return None
        self._index += 1
        return self._stack[self._index]

    def clear(self) -> None:
        self._stack.clear()
        self._index = -1


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
    * Undo / redo
    * Build-volume validation
    * Mirror / arrange helpers
    """

    def __init__(self, build_plate: Optional[BuildPlate] = None) -> None:
        self.build_plate = build_plate or BuildPlate()
        self._objects: Dict[str, SceneObject] = {}
        self._selection_uid: Optional[str] = None
        self.undo_redo = UndoRedoManager()
        self._recent_files: List[str] = []

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

    @property
    def recent_files(self) -> List[str]:
        return list(self._recent_files)

    # ---- commands ----------------------------------------------------------
    def add_mesh(self, name: str, mesh: trimesh.Trimesh,
                 source_path: str = "") -> SceneObject:
        """Place a new mesh on the build plate (centred at origin)."""
        uid = uuid.uuid4().hex[:8]

        # Auto-centre on XY, place on plate surface (Z=0)
        centroid = mesh.centroid.copy()
        mesh.apply_translation(-centroid)
        z_min = mesh.bounds[0][2]
        mesh.apply_translation([0, 0, -z_min])  # sit on Z=0

        obj = SceneObject(uid=uid, name=name, mesh=mesh, source_path=source_path)
        self._objects[uid] = obj
        self.select(uid)

        if source_path:
            self._add_recent(source_path)
        return obj

    def _add_recent(self, path: str) -> None:
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:10]

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
            source_path=source.source_path,
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

    def set_transform(self, uid: str, *,
                      record_undo: bool = False,
                      label: str = "Transform",
                      **kwargs) -> None:
        """Update transform fields for an object.
        Accepts keyword args: translation, rotation_deg, scale (numpy arrays).
        """
        obj = self._objects.get(uid)
        if obj is None:
            return

        if record_undo:
            before = obj.transform.clone()

        if "translation" in kwargs:
            obj.transform.translation = np.asarray(kwargs["translation"], dtype=np.float64)
        if "rotation_deg" in kwargs:
            obj.transform.rotation_deg = np.asarray(kwargs["rotation_deg"], dtype=np.float64)
        if "scale" in kwargs:
            obj.transform.scale = np.asarray(kwargs["scale"], dtype=np.float64)

        if record_undo:
            after = obj.transform.clone()
            self.undo_redo.push(_UndoEntry(uid, label, before, after))

    # ---- mirror ------------------------------------------------------------
    def mirror_selected(self, axis: str = "x") -> bool:
        """Mirror the selected object along the given axis (x / y / z).
        Returns True on success."""
        obj = self.selected_object
        if obj is None:
            return False

        before = obj.transform.clone()
        idx = {"x": 0, "y": 1, "z": 2}.get(axis.lower(), 0)
        obj.transform.scale[idx] *= -1.0

        after = obj.transform.clone()
        self.undo_redo.push(_UndoEntry(obj.uid, f"Mirror {axis.upper()}", before, after))
        return True

    # ---- visibility --------------------------------------------------------
    def toggle_visibility(self, uid: str) -> bool:
        obj = self._objects.get(uid)
        if obj is None:
            return False
        obj.visible = not obj.visible
        return True

    # ---- build-volume validation -------------------------------------------
    def check_build_volume(self) -> List[Tuple[str, str]]:
        """Return list of (uid, reason) for objects that violate the build volume."""
        issues: List[Tuple[str, str]] = []
        r = self.build_plate.radius
        for obj in self._objects.values():
            if not obj.visible:
                continue
            bounds = obj.bounds_mm
            min_pt, max_pt = bounds[0], bounds[1]

            # Check XY radial extent
            corners_xy = [
                (min_pt[0], min_pt[1]),
                (min_pt[0], max_pt[1]),
                (max_pt[0], min_pt[1]),
                (max_pt[0], max_pt[1]),
            ]
            for cx, cy in corners_xy:
                if math.sqrt(cx ** 2 + cy ** 2) > r:
                    issues.append((obj.uid, f"{obj.name}: extends outside build plate radius"))
                    break

            # Check Z below plate
            if min_pt[2] < -0.01:
                issues.append((obj.uid, f"{obj.name}: extends below build plate (Z={min_pt[2]:.2f})"))
        return issues

    # ---- auto arrange (simple grid) ----------------------------------------
    def auto_arrange(self) -> None:
        """Arrange all objects in a grid centred on the build plate."""
        objs = [o for o in self._objects.values() if o.visible]
        if not objs:
            return
        n = len(objs)
        cols = max(1, int(math.ceil(math.sqrt(n))))
        spacing = self.build_plate.radius * 0.6

        for i, obj in enumerate(objs):
            col = i % cols
            row = i // cols
            cx = (col - (cols - 1) / 2.0) * spacing
            cy = (row - (n // cols - 1) / 2.0) * spacing
            before = obj.transform.clone()
            obj.transform.translation[0] = cx
            obj.transform.translation[1] = cy
            after = obj.transform.clone()
            self.undo_redo.push(_UndoEntry(obj.uid, "Auto-arrange", before, after))

    # ---- undo / redo execution ---------------------------------------------
    def perform_undo(self) -> Optional[str]:
        entry = self.undo_redo.undo()
        if entry is None:
            return None
        obj = self._objects.get(entry.uid)
        if obj:
            obj.transform.translation = entry.transform_before.translation.copy()
            obj.transform.rotation_deg = entry.transform_before.rotation_deg.copy()
            obj.transform.scale = entry.transform_before.scale.copy()
        return entry.label

    def perform_redo(self) -> Optional[str]:
        entry = self.undo_redo.redo()
        if entry is None:
            return None
        obj = self._objects.get(entry.uid)
        if obj:
            obj.transform.translation = entry.transform_after.translation.copy()
            obj.transform.rotation_deg = entry.transform_after.rotation_deg.copy()
            obj.transform.scale = entry.transform_after.scale.copy()
        return entry.label

    # ---- serialisation (save / load project) --------------------------------
    def serialize(self) -> dict:
        """Serialise the scene to a JSON-compatible dict."""
        data: dict[str, Any] = {
            "version": "1.0",
            "build_plate": {
                "diameter_mm": self.build_plate.diameter_mm,
                "height_mm": self.build_plate.height_mm,
            },
            "objects": [],
        }
        for obj in self._objects.values():
            data["objects"].append({
                "uid": obj.uid,
                "name": obj.name,
                "source_path": obj.source_path,
                "transform": obj.transform.to_dict(),
                "visible": obj.visible,
            })
        return data

    def serialize_json(self) -> str:
        return json.dumps(self.serialize(), indent=2)

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
