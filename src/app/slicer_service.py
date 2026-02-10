class SlicerService:
    def __init__(self, slicer: SlicerInterface):
        # The service doesn't know it's PySLM; it just knows it's a 'Slicer'
        self.slicer = slicer

    def run_full_process(self, file_path):
        self.slicer.slice_mesh(file_path, 0.03)
        self.slicer.generate_hatches({"dist": 0.1, "angle": 67.0})