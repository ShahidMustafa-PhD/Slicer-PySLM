"""
main_window.py  --  PySide6 Main Window (QMainWindow)
Industrial-grade SLM Slicer GUI with docking panels and 3D viewport.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFormLayout,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QStatusBar,
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QKeySequence

from src.presentation.viewport_widget import SLMViewport
from src.presentation.workers import SlicingThread, ExportThread
from src.presentation.dialogs import (
    SettingsDialog,
    MaterialDialog,
    ProfileDialog,
    BuildPlateDialog,
    AboutDialog,
)

if TYPE_CHECKING:
    from src.application.scene_manager import SceneManager
    from src.application.slicer_service import SlicerService
    from src.infrastructure.repositories.asset_loader import AssetLoader


class SlicerGUI(QMainWindow):
    """
    Main application window for the PySLM Slicer.
    
    Layout:
    - Center: 3D Viewport (PyVistaQt)
    - Left Dock: Scene Browser (tree of loaded models)
    - Right Dock: Slicer Settings (parameters + slice button)
    - Menu Bar: File, Edit, View, Slicer, Help
    """
    
    def __init__(
        self,
        scene: SceneManager,
        slicer_service: SlicerService,
        asset_loader: AssetLoader,
    ):
        """
        Initialize the main window (Dependency Injection).
        
        Parameters
        ----------
        scene : SceneManager
            Application-layer scene manager
        slicer_service : SlicerService
            Application-layer slicer service
        asset_loader : AssetLoader
            Infrastructure-layer asset loader
        """
        super().__init__()
        
        # Store references (Clean Architecture - GUI only talks to Application layer)
        self.scene = scene
        self.slicer = slicer_service
        self.loader = asset_loader
        
        # State
        self._slicing_thread: Optional[SlicingThread] = None
        self._current_params = {
            "layer_thickness": 0.030,
            "laser_power": 200.0,
            "scan_speed": 1000.0,
            "hatch_spacing": 0.10,
            "hatch_angle_increment": 67.0,
            "contour_count": 1,
            "contour_offset": 0.05,
            "island_scanning": False,
            "island_size": 5.0,
        }
        
        # Setup UI
        self.setWindowTitle("PySLM Industrial Slicer — PySide6 + PyVistaQt")
        self.resize(1400, 900)
        
        self._create_viewport()
        self._create_docks()
        self._create_menu_bar()
        self._create_status_bar()
        
        # Initial scene render
        self.viewport.rebuild_scene()
    
    # ========================================================================
    #  UI Construction
    # ========================================================================
    
    def _create_viewport(self) -> None:
        """Create and set the central 3D viewport widget."""
        self.viewport = SLMViewport(self.scene, parent=self)
        self.setCentralWidget(self.viewport)
        
        # Connect signals
        self.viewport.object_selected.connect(self._on_object_selected)
    
    def _create_docks(self) -> None:
        """Create left and right docking panels."""
        # LEFT DOCK: Scene Browser
        self.scene_dock = QDockWidget("Scene Browser", self)
        self.scene_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Tree widget for object list
        self.scene_tree = QTreeWidget()
        self.scene_tree.setHeaderLabels(["Object", "Triangles"])
        self.scene_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.scene_dock.setWidget(self.scene_tree)
        
        self.addDockWidget(Qt.LeftDockWidgetArea, self.scene_dock)
        
        # RIGHT DOCK: Slicer Settings
        self.settings_dock = QDockWidget("Slicer Settings", self)
        self.settings_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        settings_widget = self._create_settings_panel()
        self.settings_dock.setWidget(settings_widget)
        
        self.addDockWidget(Qt.RightDockWidgetArea, self.settings_dock)
    
    def _create_settings_panel(self) -> QWidget:
        """
        Build the right-side settings panel widget.
        
        Returns
        -------
        QWidget
            The settings panel
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # === Parameters Summary ===
        form = QFormLayout()
        
        self.param_labels = {}
        
        # Layer thickness
        self.param_labels["layer_thickness"] = QLabel("0.030 mm")
        form.addRow("Layer Thickness:", self.param_labels["layer_thickness"])
        
        # Laser power
        self.param_labels["laser_power"] = QLabel("200.0 W")
        form.addRow("Laser Power:", self.param_labels["laser_power"])
        
        # Scan speed
        self.param_labels["scan_speed"] = QLabel("1000.0 mm/s")
        form.addRow("Scan Speed:", self.param_labels["scan_speed"])
        
        # Hatch spacing
        self.param_labels["hatch_spacing"] = QLabel("0.10 mm")
        form.addRow("Hatch Spacing:", self.param_labels["hatch_spacing"])
        
        layout.addLayout(form)
        
        # === Action Buttons ===
        
        # Edit Settings button
        edit_btn = QPushButton("Edit Settings...")
        edit_btn.clicked.connect(self._on_edit_settings)
        layout.addWidget(edit_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        # Slice button
        self.slice_btn = QPushButton("Slice Now")
        self.slice_btn.setStyleSheet("QPushButton { font-size: 14pt; padding: 10px; }")
        self.slice_btn.clicked.connect(self._on_slice)
        layout.addWidget(self.slice_btn)
        
        # Add stretch at bottom
        layout.addStretch()
        
        return widget
    
    def _create_menu_bar(self) -> None:
        """Create the main menu bar."""
        menubar = self.menuBar()
        
        # === FILE MENU ===
        file_menu = menubar.addMenu("&File")
        
        # Open
        open_action = QAction("&Open STL/3MF...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Save Project
        save_action = QAction("&Save Project...", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)
        
        # Export CLI
        export_action = QAction("Export &CLI...", self)
        export_action.triggered.connect(self._on_export_cli)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # Quit
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # === EDIT MENU ===
        edit_menu = menubar.addMenu("&Edit")
        
        # Undo
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)
        
        # Redo
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        # Delete
        delete_action = QAction("&Delete Selected", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self._on_delete_selected)
        edit_menu.addAction(delete_action)
        
        # Duplicate
        duplicate_action = QAction("Du&plicate", self)
        duplicate_action.setShortcut(QKeySequence("Ctrl+D"))
        duplicate_action.triggered.connect(self._on_duplicate)
        edit_menu.addAction(duplicate_action)
        
        # === VIEW MENU ===
        view_menu = menubar.addMenu("&View")
        
        # Camera presets
        view_menu.addAction("Front View", lambda: self.viewport.set_view("front"))
        view_menu.addAction("Top View", lambda: self.viewport.set_view("top"))
        view_menu.addAction("Left View", lambda: self.viewport.set_view("left"))
        view_menu.addAction("Right View", lambda: self.viewport.set_view("right"))
        view_menu.addAction("Isometric", lambda: self.viewport.set_view("iso"))
        
        view_menu.addSeparator()
        
        # Fit to scene
        fit_action = QAction("&Fit All", self)
        fit_action.setShortcut(QKeySequence("F"))
        fit_action.triggered.connect(self.viewport.fit_to_scene)
        view_menu.addAction(fit_action)
        
        # Reset camera
        reset_action = QAction("&Reset Camera", self)
        reset_action.setShortcut(QKeySequence("Home"))
        reset_action.triggered.connect(self.viewport.reset_view)
        view_menu.addAction(reset_action)
        
        view_menu.addSeparator()
        
        # Toggle docks
        view_menu.addAction(self.scene_dock.toggleViewAction())
        view_menu.addAction(self.settings_dock.toggleViewAction())
        
        # === SLICER MENU ===
        slicer_menu = menubar.addMenu("&Slicer")
        
        # Settings
        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self._on_edit_settings)
        slicer_menu.addAction(settings_action)
        
        # Material Library
        material_action = QAction("&Material Library...", self)
        material_action.triggered.connect(self._on_material_library)
        slicer_menu.addAction(material_action)
        
        # Quality Profiles
        profile_action = QAction("&Quality Profiles...", self)
        profile_action.triggered.connect(self._on_quality_profiles)
        slicer_menu.addAction(profile_action)
        
        slicer_menu.addSeparator()
        
        # Build Plate
        plate_action = QAction("&Build Plate...", self)
        plate_action.triggered.connect(self._on_build_plate_config)
        slicer_menu.addAction(plate_action)
        
        # === HELP MENU ===
        help_menu = menubar.addMenu("&Help")
        
        # About
        about_action = QAction("&About PySLM Slicer", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self) -> None:
        """Create status bar at bottom."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready", 5000)
    
    # ========================================================================
    #  Slots - File Operations
    # ========================================================================
    
    @Slot()
    def _on_open_file(self) -> None:
        """Open STL/3MF file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open 3D Model",
            str(Path.home()),
            "3D Models (*.stl *.STL *.3mf *.obj *.amf);;All Files (*.*)",
        )
        
        if not file_path:
            return
        
        try:
            self.status_bar.showMessage(f"Loading {Path(file_path).name}...")
            
            # Load mesh via infrastructure layer
            name, mesh = self.loader.load(file_path)
            
            # Add to scene (application layer)
            self.scene.add_mesh(name, mesh, source_path=file_path)
            
            # Update UI
            self._refresh_scene_tree()
            self.viewport.rebuild_scene()
            
            self.status_bar.showMessage(
                f"Loaded {name} ({mesh.faces.shape[0]:,} triangles)", 5000
            )
        
        except Exception as e:
            QMessageBox.critical(
                self, "Load Error", f"Failed to load file:\n{str(e)}"
            )
            self.status_bar.showMessage("Load failed", 5000)
    
    @Slot()
    def _on_save_project(self) -> None:
        """Save project as JSON."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            str(Path.home() / "pyslicer_project.json"),
            "JSON Files (*.json);;All Files (*.*)",
        )
        
        if not file_path:
            return
        
        try:
            import json
            
            # Serialize scene
            data = self.scene.serialize()
            data["params"] = self._current_params
            
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            
            self.status_bar.showMessage(f"Project saved to {Path(file_path).name}", 5000)
        
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Failed to save project:\n{str(e)}"
            )
    
    @Slot()
    def _on_export_cli(self) -> None:
        """Export sliced data to CLI format."""
        if not self.slicer.last_parts:
            QMessageBox.warning(
                self,
                "No Slice Data",
                "Please run Slice first before exporting."
            )
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export CLI File",
            str(Path.home() / "pyslicer_output.cli"),
            "CLI Files (*.cli);;All Files (*.*)",
        )
        
        if not file_path:
            return
        
        try:
            # Export via service
            layer_count = self.slicer.export_cli(file_path)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Exported {layer_count} layers to:\n{file_path}"
            )
            
            self.status_bar.showMessage("Export complete", 5000)
        
        except Exception as e:
            QMessageBox.critical(
                self, "Export Error", f"Failed to export:\n{str(e)}"
            )
    
    # ========================================================================
    #  Slots - Edit Operations
    # ========================================================================
    
    @Slot()
    def _on_undo(self) -> None:
        """Undo last transform operation."""
        label = self.scene.perform_undo()
        if label:
            self.status_bar.showMessage(f"Undo: {label}", 3000)
            self.viewport.rebuild_scene()
        else:
            self.status_bar.showMessage("Nothing to undo", 3000)
    
    @Slot()
    def _on_redo(self) -> None:
        """Redo last undone operation."""
        label = self.scene.perform_redo()
        if label:
            self.status_bar.showMessage(f"Redo: {label}", 3000)
            self.viewport.rebuild_scene()
        else:
            self.status_bar.showMessage("Nothing to redo", 3000)
    
    @Slot()
    def _on_delete_selected(self) -> None:
        """Delete the selected object."""
        if self.scene.remove_selected():
            self._refresh_scene_tree()
            self.viewport.rebuild_scene()
            self.status_bar.showMessage("Object deleted", 3000)
    
    @Slot()
    def _on_duplicate(self) -> None:
        """Duplicate the selected object."""
        obj = self.scene.duplicate_selected()
        if obj:
            self._refresh_scene_tree()
            self.viewport.rebuild_scene()
            self.status_bar.showMessage(f"Duplicated: {obj.name}", 3000)
    
    # ========================================================================
    #  Slots - Settings & Configuration
    # ========================================================================
    
    @Slot()
    def _on_edit_settings(self) -> None:
        """Open the settings dialog."""
        dialog = SettingsDialog(self._current_params, self)
        
        if dialog.exec() == SettingsDialog.Accepted:
            self._current_params = dialog.get_params()
            self._update_param_display()
            self.status_bar.showMessage("Settings updated", 3000)
    
    @Slot()
    def _on_material_library(self) -> None:
        """Open material library dialog."""
        from src.application.slicer_service import MATERIAL_PRESETS
        
        dialog = MaterialDialog(self)
        
        if dialog.exec() == MaterialDialog.Accepted and dialog.selected_material:
            # Load preset
            preset = MATERIAL_PRESETS[dialog.selected_material]
            self._current_params.update(preset)
            self._update_param_display()
            self.status_bar.showMessage(
                f"Material: {dialog.selected_material} loaded", 3000
            )
    
    @Slot()
    def _on_quality_profiles(self) -> None:
        """Open quality profile dialog."""
        from src.application.slicer_service import PROFILE_PRESETS
        
        dialog = ProfileDialog(self)
        
        if dialog.exec() == ProfileDialog.Accepted and dialog.selected_profile:
            # Load preset
            thickness = PROFILE_PRESETS[dialog.selected_profile]
            self._current_params["layer_thickness"] = thickness
            self._update_param_display()
            self.status_bar.showMessage(
                f"Profile: {dialog.selected_profile} loaded", 3000
            )
    
    @Slot()
    def _on_build_plate_config(self) -> None:
        """Open build plate configuration dialog."""
        plate = self.scene.build_plate
        
        dialog = BuildPlateDialog(plate.diameter_mm, plate.height_mm, self)
        
        if dialog.exec() == BuildPlateDialog.Accepted:
            plate.diameter_mm = dialog.diameter
            plate.height_mm = dialog.height
            
            # Rebuild viewport to show new plate
            self.viewport._create_build_plate()
            self.viewport.rebuild_scene()
            
            self.status_bar.showMessage("Build plate updated", 3000)
    
    @Slot()
    def _on_about(self) -> None:
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
    
    # ========================================================================
    #  Slots - Slicing
    # ========================================================================
    
    @Slot()
    def _on_slice(self) -> None:
        """Start slicing operation in background thread."""
        if self.scene.object_count == 0:
            QMessageBox.warning(
                self, "No Objects", "Please load at least one 3D model first."
            )
            return
        
        # Check if already slicing
        if self._slicing_thread and self._slicing_thread.isRunning():
            QMessageBox.warning(
                self, "Slicing...", "A slicing operation is already running."
            )
            return
        
        # Collect meshes for slicing
        mesh_items = self.scene.collect_for_slicing()
        
        # Create and start thread
        self._slicing_thread = SlicingThread(
            self.slicer,
            mesh_items,
            self._current_params,
            self,
        )
        
        # Connect signals
        self._slicing_thread.worker.progress_updated.connect(self._on_slice_progress)
        self._slicing_thread.worker.slicing_finished.connect(self._on_slice_finished)
        self._slicing_thread.worker.slicing_failed.connect(self._on_slice_failed)
        
        # Update UI
        self.slice_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Slicing started...")
        
        # Start
        self._slicing_thread.start()
    
    @Slot(int, str)
    def _on_slice_progress(self, percentage: int, message: str) -> None:
        """Update progress bar during slicing."""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
    
    @Slot(dict)
    def _on_slice_finished(self, result: dict) -> None:
        """Handle slicing completion."""
        # Reset UI
        self.slice_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        # Show summary
        total_layers = result.get("total_layers", "?")
        elapsed = result.get("elapsed_s", "?")
        est_build = result.get("est_build_time_h", "?")
        
        QMessageBox.information(
            self,
            "Slicing Complete",
            f"Slicing finished successfully!\n\n"
            f"Total Layers: {total_layers}\n"
            f"Compute Time: {elapsed:.2f} s\n"
            f"Est. Build Time: {est_build:.1f} h"
        )
        
        self.status_bar.showMessage(
            f"Slicing complete: {total_layers} layers in {elapsed:.1f}s", 5000
        )
    
    @Slot(str)
    def _on_slice_failed(self, error_msg: str) -> None:
        """Handle slicing failure."""
        # Reset UI
        self.slice_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        QMessageBox.critical(self, "Slicing Failed", error_msg)
        self.status_bar.showMessage("Slicing failed", 5000)
    
    # ========================================================================
    #  Slots - Scene Interaction
    # ========================================================================
    
    @Slot(str)
    def _on_object_selected(self, uid: str) -> None:
        """Handle object selection from viewport."""
        self.scene.select(uid)
        self._refresh_scene_tree()
        self.viewport.highlight_selected(uid)
        
        obj = self.scene.selected_object
        if obj:
            self.status_bar.showMessage(f"Selected: {obj.name}", 3000)
    
    @Slot(QTreeWidgetItem, int)
    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle selection from scene tree."""
        uid = item.data(0, Qt.UserRole)
        if uid:
            self.scene.select(uid)
            self.viewport.highlight_selected(uid)
            self.viewport.render()
    
    # ========================================================================
    #  Helper Methods
    # ========================================================================
    
    def _refresh_scene_tree(self) -> None:
        """Update the scene tree widget."""
        self.scene_tree.clear()
        
        for obj in self.scene.objects:
            item = QTreeWidgetItem([
                obj.name,
                f"{obj.mesh.faces.shape[0]:,}"
            ])
            item.setData(0, Qt.UserRole, obj.uid)
            
            if obj.selected:
                item.setSelected(True)
            
            self.scene_tree.addTopLevelItem(item)
    
    def _update_param_display(self) -> None:
        """Update parameter labels in the settings panel."""
        p = self._current_params
        
        self.param_labels["layer_thickness"].setText(f"{p['layer_thickness']:.3f} mm")
        self.param_labels["laser_power"].setText(f"{p['laser_power']:.1f} W")
        self.param_labels["scan_speed"].setText(f"{p['scan_speed']:.1f} mm/s")
        self.param_labels["hatch_spacing"].setText(f"{p['hatch_spacing']:.3f} mm")
    
    # ========================================================================
    #  Entry Point (replaces DearPyGui's run())
    # ========================================================================
    
    def run(self) -> None:
        """
        Show the window and enter Qt event loop.
        This is called from main.py instead of DearPyGui's dpg.start_dearpygui()
        
        Note: The actual QApplication.exec() is handled in main.py
        """
        self.show()
