"""
slicer_service.py  --  Application Layer
Orchestrates the slicing pipeline.  Receives domain-level interfaces
via constructor injection so it never depends on PySLM directly.

Supports:
* Progress callback for real-time UI updates
* Build-time estimation
* CLI file export (Common Layer Interface)
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import trimesh

from src.domain.models import BuildStyle, Layer, SLMPart


# -----------------------------------------------------------------------
#  Material presets  (params dictionaries keyed by material name)
# -----------------------------------------------------------------------
MATERIAL_PRESETS: Dict[str, Dict[str, float]] = {
    "Ti-6Al-4V": {
        "laser_power": 200.0,
        "scan_speed": 1000.0,
        "hatch_spacing": 0.10,
        "hatch_angle_increment": 67.0,
    },
    "316L Stainless": {
        "laser_power": 175.0,
        "scan_speed": 800.0,
        "hatch_spacing": 0.12,
        "hatch_angle_increment": 67.0,
    },
    "AlSi10Mg": {
        "laser_power": 350.0,
        "scan_speed": 1300.0,
        "hatch_spacing": 0.15,
        "hatch_angle_increment": 67.0,
    },
    "IN718": {
        "laser_power": 285.0,
        "scan_speed": 960.0,
        "hatch_spacing": 0.11,
        "hatch_angle_increment": 67.0,
    },
}

PROFILE_PRESETS: Dict[str, float] = {
    "Fine (20 \u00b5m)": 0.020,
    "Normal (30 \u00b5m)": 0.030,
    "Draft (50 \u00b5m)": 0.050,
}


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
        self.last_result: Optional[Dict[str, Any]] = None
        self.last_parts: List[SLMPart] = []

    # ------------------------------------------------------------------
    #  Main entry point called by the GUI
    # ------------------------------------------------------------------
    def slice(
        self,
        mesh_items: List[dict],
        params: dict,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Slice every mesh on the build plate.

        Parameters
        ----------
        mesh_items : list of {"uid", "name", "mesh" (trimesh.Trimesh)}
        params     : dict with keys layer_thickness, laser_power, scan_speed,
                     hatch_spacing, hatch_angle_increment
        progress_cb : callable(progress_0_1, message), optional
            GUI progress callback.

        Returns
        -------
        dict   summary with total_layers, per-part info, elapsed time, etc.
        """
        def _progress(val: float, msg: str = "") -> None:
            if progress_cb:
                try:
                    progress_cb(val, msg)
                except Exception:
                    pass

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
        total_z_expected = 0
        part_summaries: List[dict] = []
        all_parts: List[SLMPart] = []

        # Pre-calculate total expected layers for progress
        for item in mesh_items:
            mesh: trimesh.Trimesh = item["mesh"]
            z_min, z_max = mesh.bounds[0][2], mesh.bounds[1][2]
            total_z_expected += max(1, int((z_max - z_min) / style.layer_thickness))

        processed_layers = 0
        _progress(0.0, "Starting slice...")

        for mi, item in enumerate(mesh_items):
            mesh: trimesh.Trimesh = item["mesh"]
            name: str = item["name"]

            part = SLMPart(name=name, mesh_data=mesh)

            # Compute Z range
            z_min, z_max = mesh.bounds[0][2], mesh.bounds[1][2]
            heights = np.arange(z_min, z_max, style.layer_thickness)

            _progress(
                processed_layers / max(1, total_z_expected),
                f"Slicing {name}... ({mi + 1}/{len(mesh_items)})",
            )

            for zi, z in enumerate(heights):
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

                processed_layers += 1
                if zi % 20 == 0:
                    _progress(
                        processed_layers / max(1, total_z_expected),
                        f"Slicing {name}: layer {zi + 1}/{len(heights)}",
                    )

            total_layers += len(part.layers)
            all_parts.append(part)
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
        est_time = self.estimate_build_time(params, total_layers, mesh_items)
        _progress(1.0, f"Complete — {total_layers} layers in {elapsed:.1f}s")

        self.last_parts = all_parts
        self.last_result = {
            "total_layers": total_layers,
            "parts": part_summaries,
            "elapsed_s": round(elapsed, 3),
            "est_build_time_h": round(est_time, 2),
            "layer_thickness": style.layer_thickness,
            "params": params,
        }
        return self.last_result

    # =====================================================================
    #  Build time estimation  (simplified model)
    # =====================================================================
    @staticmethod
    def estimate_build_time(
        params: dict,
        total_layers: int,
        meshes: Optional[List[dict]] = None,
    ) -> float:
        """Return estimated build time in **hours**.

        Uses a simplified model:
            time ≈ (total_area * num_layers * hatch_spacing) / scan_speed
                  + recoat_time_per_layer * num_layers

        Falls back to a rough heuristic if mesh data isn't provided.
        """
        scan_speed = params.get("scan_speed", 1000.0)     # mm/s
        hatch_spacing = params.get("hatch_spacing", 0.10)  # mm
        recoat_s = 8.0  # typical recoater time per layer

        total_area_mm2 = 0.0
        if meshes:
            for item in meshes:
                mesh = item.get("mesh")
                if mesh is not None:
                    ext = mesh.extents
                    total_area_mm2 += ext[0] * ext[1]
        else:
            total_area_mm2 = 2500.0

        lines_per_layer = total_area_mm2 / max(hatch_spacing, 0.01)
        avg_line_len = max(total_area_mm2 ** 0.5, 1.0)
        scan_time_per_layer = (lines_per_layer * avg_line_len) / max(scan_speed, 1.0)

        total_s = (scan_time_per_layer + recoat_s) * total_layers
        return total_s / 3600.0

    # =====================================================================
    #  Export  (Common Layer Interface — simplified ASCII CLI)
    # =====================================================================
    def export_cli(self, filepath: str) -> int:
        """
        Write the last slice result as a simplified ASCII CLI file.
        Returns the number of layers written.
        """
        if not self.last_parts:
            raise RuntimeError("No slice data — run slice() first.")

        written = 0
        with open(filepath, "w") as f:
            f.write("$$HEADERSTART\n")
            f.write("$$ASCII\n")
            f.write("$$UNITS/1.0  ;; mm\n")
            if self.last_result:
                lt = self.last_result.get("layer_thickness", 0.030)
                f.write(f"$$LAYER_THICKNESS/{lt:.4f}\n")
            f.write("$$HEADEREND\n\n")

            for part in self.last_parts:
                f.write(f";; Part: {part.name}\n")
                for layer in part.layers:
                    f.write(f"$$LAYER/{layer.z_height:.4f}\n")
                    for contour in layer.contours:
                        if contour is not None and len(contour) > 0:
                            pts = contour.flatten()
                            coord_str = ",".join(f"{v:.4f}" for v in pts)
                            f.write(f"$$POLYLINE/1,1,{len(contour)},{coord_str}\n")
                    written += 1
            f.write("$$END\n")

        print(f"[SlicerService] Exported {written} layers to {filepath}")
        return written

    # =====================================================================
    #  Export  (SVG layer preview — single layer)
    # =====================================================================
    def export_layer_svg(self, filepath: str, layer_index: int = 0) -> bool:
        """Export a single layer's contours as SVG for visual verification."""
        if not self.last_parts:
            return False

        contours = []
        for part in self.last_parts:
            if layer_index < len(part.layers):
                contours.extend(part.layers[layer_index].contours)

        if not contours:
            return False

        all_pts_list = [c for c in contours if c is not None and len(c) > 0]
        if not all_pts_list:
            return False
        all_pts = np.vstack(all_pts_list)
        x_min, y_min = all_pts.min(axis=0)[:2]
        x_max, y_max = all_pts.max(axis=0)[:2]
        margin = 2.0
        w = x_max - x_min + 2 * margin
        h = y_max - y_min + 2 * margin

        with open(filepath, "w") as f:
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" '
                    f'viewBox="{x_min - margin} {y_min - margin} {w} {h}" '
                    f'width="{w * 3}" height="{h * 3}">\n')
            f.write(f'  <rect x="{x_min - margin}" y="{y_min - margin}" '
                    f'width="{w}" height="{h}" fill="#f8f8f8"/>\n')
            for contour in contours:
                if contour is None or len(contour) < 2:
                    continue
                pts = " ".join(f"{p[0]:.3f},{p[1]:.3f}" for p in contour)
                f.write(f'  <polyline points="{pts}" '
                        f'fill="none" stroke="#196EF0" stroke-width="0.15"/>\n')
            f.write("</svg>\n")
        return True
