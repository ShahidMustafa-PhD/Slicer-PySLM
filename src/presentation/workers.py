"""
workers.py  --  Threading for Background Tasks
QThread-based workers to prevent GUI blocking during slicing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any

from PySide6.QtCore import QObject, QThread, Signal

if TYPE_CHECKING:
    from src.application.slicer_service import SlicerService


class SlicerWorker(QObject):
    """
    Worker object for running the slicing operation in a background thread.
    
    Signals:
    - progress_updated(int, str): Progress percentage (0-100) and message
    - slicing_finished(dict): Emitted when slicing completes successfully
    - slicing_failed(str): Emitted on error with error message
    """
    
    progress_updated = Signal(int, str)  # percentage, message
    slicing_finished = Signal(dict)  # result dictionary
    slicing_failed = Signal(str)  # error message
    
    def __init__(
        self,
        slicer_service: SlicerService,
        mesh_items: list,
        params: dict,
    ):
        """
        Initialize the worker.
        
        Parameters
        ----------
        slicer_service : SlicerService
            Reference to the application-layer slicer service
        mesh_items : list
            List of meshes to slice (from scene.collect_for_slicing())
        params : dict
            Slicing parameters (layer_thickness, laser_power, etc.)
        """
        super().__init__()
        
        self.slicer_service = slicer_service
        self.mesh_items = mesh_items
        self.params = params
        self._is_cancelled = False
    
    def run(self) -> None:
        """
        Execute the slicing operation.
        This method is called by QThread when thread starts.
        """
        try:
            # Define progress callback
            def _progress_cb(progress_0_1: float, message: str) -> None:
                if self._is_cancelled:
                    raise RuntimeError("Slicing cancelled by user")
                
                # Convert to percentage
                percentage = int(progress_0_1 * 100)
                self.progress_updated.emit(percentage, message)
            
            # Run the slicing operation
            result = self.slicer_service.slice(
                mesh_items=self.mesh_items,
                params=self.params,
                progress_cb=_progress_cb,
            )
            
            # Emit success
            if not self._is_cancelled:
                self.slicing_finished.emit(result)
        
        except Exception as e:
            # Emit failure
            error_msg = f"Slicing failed: {str(e)}"
            self.slicing_failed.emit(error_msg)
    
    def cancel(self) -> None:
        """Request cancellation of the slicing operation."""
        self._is_cancelled = True


class SlicingThread(QThread):
    """
    Convenience QThread subclass for running SlicerWorker.
    
    Usage:
        thread = SlicingThread(slicer_service, mesh_items, params)
        thread.worker.progress_updated.connect(update_progress_bar)
        thread.worker.slicing_finished.connect(handle_completion)
        thread.worker.slicing_failed.connect(handle_error)
        thread.start()
    """
    
    def __init__(
        self,
        slicer_service: SlicerService,
        mesh_items: list,
        params: dict,
        parent=None,
    ):
        """
        Initialize the thread with a worker.
        
        Parameters
        ----------
        slicer_service : SlicerService
            Application-layer slicer service
        mesh_items : list
            Meshes to slice
        params : dict
            Slicing parameters
        parent : QObject, optional
            Parent Qt object
        """
        super().__init__(parent)
        
        # Create worker
        self.worker = SlicerWorker(slicer_service, mesh_items, params)
        
        # Move worker to this thread
        self.worker.moveToThread(self)
        
        # Connect thread start to worker run
        self.started.connect(self.worker.run)
    
    def cancel(self) -> None:
        """Cancel the slicing operation and quit the thread."""
        self.worker.cancel()
        self.quit()
        self.wait()


class ExportWorker(QObject):
    """
    Worker for exporting sliced data to CLI format in background.
    
    Signals:
    - export_finished(str): Emitted with output file path on success
    - export_failed(str): Emitted with error message on failure
    """
    
    export_finished = Signal(str)  # output file path
    export_failed = Signal(str)  # error message
    
    def __init__(self, slicer_service: SlicerService, output_path: str):
        super().__init__()
        self.slicer_service = slicer_service
        self.output_path = output_path
    
    def run(self) -> None:
        """Execute the export operation."""
        try:
            # Call the export method
            layer_count = self.slicer_service.export_cli(self.output_path)
            
            if layer_count > 0:
                self.export_finished.emit(self.output_path)
            else:
                self.export_failed.emit("No layers to export")
        
        except Exception as e:
            self.export_failed.emit(f"Export failed: {str(e)}")


class ExportThread(QThread):
    """Thread wrapper for ExportWorker."""
    
    def __init__(
        self,
        slicer_service: SlicerService,
        output_path: str,
        parent=None,
    ):
        super().__init__(parent)
        
        self.worker = ExportWorker(slicer_service, output_path)
        self.worker.moveToThread(self)
        self.started.connect(self.worker.run)
