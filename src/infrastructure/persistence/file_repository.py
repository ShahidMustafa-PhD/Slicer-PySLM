import trimesh

class FileRepository:
    """Infrastructure implementation for file handling."""
    
    def load_stl(self, path: str):
        """Loads an STL file using Trimesh."""
        return trimesh.load(path)

    def save_binary_build_file(self, part, path: str):
        """Exports to machine-specific binary formats (CLI, etc.)."""
        # Placeholder for complex binary serialization logic
        pass
