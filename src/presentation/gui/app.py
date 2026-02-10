import dearpygui.dearpygui as dpg
from src.app.use_cases.slice_part import SlicePartUseCase
from src.app.dtos.slice_request import SliceRequestDTO

class SlicerGUI:
    """Presentation layer using Dear PyGui."""
    
    def __init__(self, slice_use_case: SlicePartUseCase):
        self.slice_use_case = slice_use_case

    def run(self):
        dpg.create_context()
        
        with dpg.window(label="SLM Slicer Engine"):
            dpg.add_input_text(label="STL Path", tag="stl_path")
            dpg.add_input_float(label="Layer Thickness (mm)", default_value=0.03, tag="thickness")
            dpg.add_button(label="Start Slicing", callback=self._on_slice_click)
            dpg.add_text("", tag="status_text")

        dpg.create_viewport(title='PySLM Industrial Slicer', width=600, height=400)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

    def _on_slice_click(self):
        # Translate GUI state to DTO
        request = SliceRequestDTO(
            stl_path=dpg.get_value("stl_path"),
            layer_thickness=dpg.get_value("thickness"),
            output_path="output.cli"
        )
        
        # Call Application Layer
        result = self.slice_use_case.execute(request)
        dpg.set_value("status_text", f"Success! {result['layers_generated']} layers created.")

if __name__ == "__main__":
    # In a real app, DI would happen here or in a main.py
    # from src.infra.persistence.file_repository import FileRepository
    # repo = FileRepository()
    # use_case = SlicePartUseCase(geometry_engine=None, file_repository=repo)
    # gui = SlicerGUI(use_case)
    # gui.run()
    pass
