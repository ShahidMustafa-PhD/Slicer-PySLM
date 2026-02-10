"""
asset_loader.py  --  Infrastructure Layer
Handles loading mesh files (STL, 3MF, OBJ, AMF) using trimesh.
Returns a plain trimesh.Trimesh so that the Application layer never depends
on file-format details.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

import trimesh

# Supported extensions (lower-case, with dot)
SUPPORTED_EXTENSIONS = {".stl", ".3mf", ".obj", ".amf"}


class AssetLoadError(Exception):
    """Raised when an asset cannot be loaded or parsed."""


class AssetLoader:
    """
    Infrastructure repository responsible for reading 3D mesh files
    from disk and returning normalised trimesh.Trimesh objects.
    """

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def load(self, file_path: str) -> Tuple[str, trimesh.Trimesh]:
        """
        Load a mesh file and return (display_name, trimesh.Trimesh).

        Raises
        ------
        AssetLoadError  if the file is missing, unsupported, or corrupt.
        """
        path = Path(file_path)
        self._validate(path)

        try:
            loaded = trimesh.load(str(path), force="mesh")
        except Exception as exc:
            raise AssetLoadError(f"trimesh could not parse '{path.name}': {exc}") from exc

        # trimesh.load may return a Scene for multi-body files (3MF, AMF).
        mesh = self._ensure_single_mesh(loaded, path.name)

        # Repair: merge close vertices, fix normals
        mesh.merge_vertices()
        mesh.fix_normals()

        display_name = path.stem  # e.g. "bracket" from bracket.stl
        return display_name, mesh

    def load_many(self, file_paths: List[str]) -> List[Tuple[str, trimesh.Trimesh]]:
        """Convenience: load several files at once."""
        return [self.load(fp) for fp in file_paths]

    @staticmethod
    def supported_extensions() -> List[str]:
        """Return the list of supported file extensions."""
        return sorted(SUPPORTED_EXTENSIONS)

    @staticmethod
    def file_dialog_filter() -> str:
        """
        Return a filter string suitable for Dear PyGui's file dialog.
        Example: "*.stl *.3mf *.obj *.amf"
        """
        return " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _validate(self, path: Path) -> None:
        if not path.exists():
            raise AssetLoadError(f"File not found: {path}")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise AssetLoadError(
                f"Unsupported format '{path.suffix}'. "
                f"Accepted: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

    @staticmethod
    def _ensure_single_mesh(loaded, filename: str) -> trimesh.Trimesh:
        """
        trimesh.load can return either a Trimesh or a Scene.
        Collapse multi-body scenes into a single mesh.
        """
        if isinstance(loaded, trimesh.Trimesh):
            return loaded

        if isinstance(loaded, trimesh.Scene):
            meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if not meshes:
                raise AssetLoadError(f"No triangulated geometry found in '{filename}'.")
            combined = trimesh.util.concatenate(meshes)
            return combined

        raise AssetLoadError(f"Unexpected object type from trimesh: {type(loaded)}")
