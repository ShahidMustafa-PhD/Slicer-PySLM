"""
slicer_service.py  --  Application Layer
Orchestrates the slicing pipeline.  Receives domain-level interfaces
via constructor injection so it never depends on PySLM directly.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np
import trimesh

from src.domain.models import BuildStyle, Layer, SLMPart


class SlicerService:
    """
    High-level service consumed by the Presentation layer.

    Parameters
    ----------
    slicer_adapter : optional
        An object implementing SlicerInterface (e.g. PySLMAdapter).
        If *None*, a built-in basic slicer is used that works without PySLM.
    """

    def __init__(self, slicer_adapter=None) -> None:
        self._adapter = slicer_adapter

    # ------------------------------------------------------------------
    #  Main entry point called by the GUI
    # ------------------------------------------------------------------
    def slice(
        self,
        mesh_items: List[dict],
        params: dict,
    ) -> Dict[str, Any]:
        """
        Slice every mesh on the build plate.

        Parameters
        ----------
        mesh_items : list of {"uid", "name", "mesh" (trimesh.Trimesh)}
        params     : dict with keys layer_thickness, laser_power, scan_speed,
                     hatch_spacing, hatch_angle_increment

        Returns
        -------
        dict   summary with total_layers, per-part info, elapsed time, etc.
        """
        t0 = time.perf_counter()

        style = BuildStyle(
            name="GUI_Style",
            layer_thickness=params.get("layer_thickness", 0.03),
            laser_power=params.get("laser_power", 200.0),
            scan_speed=params.get("scan_speed", 1000.0),
            hatch_spacing=params.get("hatch_spacing", 0.10),
            hatch_angle_increment=params.get("hatch_angle_increment", 67.0),
        )

        total_layers = 0
        part_summaries: List[dict] = []

        for item in mesh_items:
            mesh: trimesh.Trimesh = item["mesh"]
            name: str = item["name"]

            part = SLMPart(name=name, mesh_data=mesh)

            # Compute Z range
            z_min, z_max = mesh.bounds[0][2], mesh.bounds[1][2]
            heights = np.arange(z_min, z_max, style.layer_thickness)

            for z in heights:
                try:
                    section = mesh.section(
                        plane_origin=[0, 0, z],
                        plane_normal=[0, 0, 1],
                    )
                    contours = []
                    if section is not None:
                        path_2d, _ = section.to_planar()
                        for entity in path_2d.entities:
                            pts = path_2d.vertices[entity.points]
                            contours.append(pts)
                except Exception:
                    contours = []

                layer = Layer(z_height=float(z), contours=contours)
                part.add_layer(layer)

            total_layers += len(part.layers)
            part_summaries.append({
                "name": name,
                "layers": len(part.layers),
                "z_range": (float(z_min), float(z_max)),
            })

            print(
                f"[SlicerService] {name}: {len(part.layers)} layers  "
                f"(Z {z_min:.3f} -> {z_max:.3f} mm)"
            )

        elapsed = time.perf_counter() - t0
        return {
            "total_layers": total_layers,
            "parts": part_summaries,
            "elapsed_s": round(elapsed, 3),
        }
