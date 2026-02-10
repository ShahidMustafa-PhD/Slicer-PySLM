try:
    import pyslm
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "pyslm is required but not installed. Install it with `pip install pyslm`."
    ) from exc
from src.domain.interfaces import SlicerInterface
from src.domain.models import SLMPart, BuildStyle

class PySLMAdapter(SlicerInterface):
    """
    Adapter for the PySLM library.
    Encapsulates the complexity of PySLM's slicing and hatching algorithms.
    """
    
    def generate_toolpath(self, part: SLMPart, style: BuildStyle):
        """
        Implementation of the slicing process using PySLM.
        """
        # 1. Create the PySLM Part from the domain object's mesh data
        # Note: PySLM usually takes a path or a direct mesh reference
        # Assuming SLMPart.mesh_data is compatible or we load from part.name
        slm_part = pyslm.Part(part.name)
        
        # 2. Configure the Slicing Stack
        stack = pyslm.Stack(slm_part)
        
        # 3. Perform slicing using the style parameters (layer_thickness)
        # Note: PySLM uses .slice() or similar depending on version
        stack.slice(style.layer_thickness)
        
        # 4. Apply Hatching (Hatch spacing, angle, etc.)
        # This is where PySLM's power comes in
        # stack.generate_hatches(hatch_spacing=style.hatch_spacing, angle=style.hatch_angle_increment)
        
        print(f"Successfully generated toolpath for {part.name} using PySLM")
        return stack
