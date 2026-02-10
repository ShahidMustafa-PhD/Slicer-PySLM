from pydantic import BaseModel
from typing import Optional

class SliceRequestDTO(BaseModel):
    """Data transfer object for starting a slicing operation."""
    stl_path: str
    layer_thickness: float
    output_path: str
    laser_power: Optional[float] = 200.0
    scan_speed: Optional[float] = 1000.0
