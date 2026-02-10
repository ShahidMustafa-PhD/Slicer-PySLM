# src/infrastructure/adapters/pyslm_adapter.py
import pyslm  # This pulls from /external/pyslm
from src.domain.interfaces import SlicerInterface

class PySLMAdapter(SlicerInterface):
    def __init__(self):
        self.stack = None

    def slice_mesh(self, stl_path: str, layer_height: float):
        # Translate the request into PySLM logic
        part = pyslm.Part(stl_path)
        self.stack = pyslm.Stack(part)
        self.stack.slice(layerHeight=layer_height)
        print(f"PySLM sliced {stl_path} at {layer_height}mm")

    def generate_hatches(self, settings: dict):
        if self.stack:
            self.stack.generateHatches(
                hatchDistance=settings.get("dist", 0.1),
                hatchAngle=settings.get("angle", 67.0)
            )