import dearpygui.dearpygui as dpg
import pyvista as pv
import numpy as np
from src.application.slicer_service import SlicerService

class SlicerGUI:
    def __init__(self, service: SlicerService):
        self.service = service
        self.file_path = ""
        
        # PyVista Off-screen Plotter setup
        self.plotter = pv.Plotter(off_screen=True, window_size=[600, 400])
        self.plotter.set_background("black")
        
        # Texture Data (RGBA float32 for DPG)
        self.width, self.height = 600, 400
        self.texture_data = np.zeros((self.height, self.width, 4), dtype=np.float32)

    def _load_mesh_to_viewport(self):
        """Read STL and update the off-screen renderer"""
        if not self.file_path: return
        
        try:
            mesh = pv.read(self.file_path)
            self.plotter.clear()
            self.plotter.add_mesh(mesh, color="lightblue", show_edges=True)
            self.plotter.reset_camera()
            self._update_texture()
        except Exception as e:
            print(f"Error loading mesh: {e}")

    def _update_texture(self):
        """Capture PyVista buffer and push to DPG texture"""
        # 1. Take a 'screenshot' into a numpy array
        img = self.plotter.screenshot(None, return_img=True) 
        
        # 2. Convert RGB to RGBA and normalize to 0.0-1.0 for DPG
        rgba = np.ones((self.height, self.width, 4), dtype=np.float32)
        rgba[:, :, :3] = img.astype(np.float32) / 255.0
        
        # 3. Update the DPG texture value
        dpg.set_value("viewport_texture", rgba.flatten())

    def render(self):
        dpg.create_context()
        
        # Setup Texture Registry
        with dpg.texture_registry(show=False):
            dpg.add_dynamic_texture(
                width=self.width, height=self.height, 
                default_value=self.texture_data.flatten(), 
                tag="viewport_texture"
            )

        with dpg.window(label="SLM Slicer Engine", width=1000, height=700):
            with dpg.group(horizontal=True):
                # LEFT: Control Panel
                with dpg.child_window(width=300):
                    dpg.add_text("Build Settings")
                    dpg.add_input_text(label="STL", callback=lambda s, a: setattr(self, 'file_path', a))
                    dpg.add_button(label="Preview STL", callback=self._load_mesh_to_viewport)
                    dpg.add_separator()
                    dpg.add_button(label="Start Slicing", callback=lambda: self.service.run_full_process(self.file_path))

                # RIGHT: 3D Viewport
                with dpg.child_window(label="3D Preview"):
                    dpg.add_image("viewport_texture")

        dpg.create_viewport(title='Slicer GUI', width=1050, height=750)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

# --- Entry Point ---
if __name__ == "__main__":
    from src.infrastructure.adapters.pyslm_adapter import PySLMAdapter
    
    # Wire the layers together (Dependency Injection)
    adapter = PySLMAdapter()
    slicer_logic = SlicerService(slicer=adapter)
    
    # Launch the GUI
    gui = SlicerGUI(service=slicer_logic)
    gui.render()