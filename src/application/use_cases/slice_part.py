from src.app.dtos.slice_request import SliceRequestDTO
from src.domain.models import SLMPart, BuildStyle

class SlicePartUseCase:
    """Application service to orchestrate the slicing process."""
    
    def __init__(self, geometry_engine, file_repository):
        self.geometry_engine = geometry_engine
        self.file_repository = file_repository

    def execute(self, request: SliceRequestDTO):
        # 1. Load Geometry via Infrastructure
        mesh = self.file_repository.load_stl(request.stl_path)
        
        # 2. Create Domain Entity
        part = SLMPart(name=request.stl_path, mesh_data=mesh)
        style = BuildStyle(
            name="Default",
            layer_thickness=request.layer_thickness,
            laser_power=request.laser_power,
            scan_speed=request.scan_speed,
            hatch_spacing=0.1,
            hatch_angle_increment=67.5
        )

        # 3. Perform Heavy Math (Slicing) via Domain Logic
        # This is where PySLM calls would be orchestrated
        print(f"Slicing {part.name} with layer thickness {style.layer_thickness}mm...")
        
        # 4. Persistence
        # self.file_repository.save_slices(part, request.output_path)
        
        return {"status": "success", "layers_generated": len(part.layers)}
