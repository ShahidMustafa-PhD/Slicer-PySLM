from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np

@dataclass(frozen=True)
class HatchPath:
    """Represents a set of scan vectors for a single hatch region."""
    points: np.ndarray  # Shape (N, 2, 2) or similar for scan lines
    laser_power: float
    scan_speed: float

@dataclass
class Layer:
    """A single discrete slice of the 3D part."""
    z_height: float
    contours: List[np.ndarray] = field(default_factory=list)
    hatches: List[HatchPath] = field(default_factory=list)

@dataclass
class BuildStyle:
    """Domain entity representing the process parameters for SLM."""
    name: str
    layer_thickness: float  # mm
    laser_power: float      # Watts
    scan_speed: float       # mm/s
    hatch_spacing: float    # mm
    hatch_angle_increment: float # degrees

class SLMPart:
    """Root aggregate for a part being sliced."""
    def __init__(self, name: str, mesh_data):
        self.name = name
        self.mesh_data = mesh_data
        self.layers: List[Layer] = []
        self.metadata: dict = {}

    def add_layer(self, layer: Layer):
        self.layers.append(layer)
