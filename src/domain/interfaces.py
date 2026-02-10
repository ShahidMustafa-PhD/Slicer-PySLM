# src/domain/interfaces.py
from abc import ABC, abstractmethod

class SlicerInterface(ABC):
    @abstractmethod
    def slice_mesh(self, stl_path: str, layer_height: float):
        """Standard method to slice an STL file."""
        pass

    @abstractmethod
    def generate_hatches(self, settings: dict):
        """Standard method to generate laser toolpaths."""
        pass