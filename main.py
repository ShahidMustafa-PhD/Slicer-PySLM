"""
main.py  --  Application Entry Point
Wires all layers together using manual Dependency Injection, then launches the GUI.

Usage
-----
    python main.py
"""
import sys
import os

# Ensure the project root is on sys.path so `src.*` imports work
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.application.scene_manager import SceneManager
from src.application.slicer_service import SlicerService
from src.infrastructure.repositories.asset_loader import AssetLoader
from src.presentation.main_window import SlicerGUI


def main() -> None:
    # ------------------------------------------------------------------
    # 1.  Infrastructure layer  (adapters, repositories)
    # ------------------------------------------------------------------
    asset_loader = AssetLoader()

    # Optional: if PySLM is installed, plug in the real adapter
    slicer_adapter = None
    try:
        from src.infrastructure.adapters.pyslm_adapter import PySLMAdapter
        slicer_adapter = PySLMAdapter()
        print("[DI] PySLMAdapter injected.")
    except Exception:
        print("[DI] PySLM not available -- using built-in slicer.")

    # ------------------------------------------------------------------
    # 2.  Application layer  (services, scene)
    # ------------------------------------------------------------------
    scene = SceneManager()                          # empty build plate
    slicer_service = SlicerService(slicer_adapter)  # inject adapter

    # ------------------------------------------------------------------
    # 3.  Presentation layer  (GUI)
    # ------------------------------------------------------------------
    gui = SlicerGUI(
        scene=scene,
        slicer_service=slicer_service,
        asset_loader=asset_loader,
    )

    print(f"[Startup] Launching {gui.__class__.__name__}...")
    gui.run()


if __name__ == "__main__":
    main()
