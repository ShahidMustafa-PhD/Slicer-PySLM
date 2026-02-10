"""
dialogs.py  --  Qt Dialogs for Settings and Configuration
Modal dialogs for machine parameters, materials, and preferences.
"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QGroupBox,
)
from PySide6.QtCore import Qt

from src.application.slicer_service import MATERIAL_PRESETS, PROFILE_PRESETS


class SettingsDialog(QDialog):
    """
    Dialog for editing machine and process parameters.
    Validates all inputs to ensure positive float values.
    """
    
    def __init__(self, current_params: Dict[str, float], parent=None):
        """
        Initialize the settings dialog.
        
        Parameters
        ----------
        current_params : dict
            Current parameter values to display
        parent : QWidget, optional
            Parent widget
        """
        super().__init__(parent)
        
        self.setWindowTitle("Slicer Settings")
        self.setModal(True)
        self.resize(400, 300)
        
        self.params = current_params.copy()
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout for parameters
        form = QFormLayout()
        
        # Layer thickness
        self.layer_thickness_spin = QDoubleSpinBox()
        self.layer_thickness_spin.setRange(0.001, 1.0)
        self.layer_thickness_spin.setDecimals(3)
        self.layer_thickness_spin.setSingleStep(0.005)
        self.layer_thickness_spin.setSuffix(" mm")
        self.layer_thickness_spin.setValue(self.params.get("layer_thickness", 0.030))
        form.addRow("Layer Thickness:", self.layer_thickness_spin)
        
        # Laser power
        self.laser_power_spin = QDoubleSpinBox()
        self.laser_power_spin.setRange(1.0, 500.0)
        self.laser_power_spin.setDecimals(1)
        self.laser_power_spin.setSingleStep(10.0)
        self.laser_power_spin.setSuffix(" W")
        self.laser_power_spin.setValue(self.params.get("laser_power", 200.0))
        form.addRow("Laser Power:", self.laser_power_spin)
        
        # Scan speed
        self.scan_speed_spin = QDoubleSpinBox()
        self.scan_speed_spin.setRange(1.0, 5000.0)
        self.scan_speed_spin.setDecimals(1)
        self.scan_speed_spin.setSingleStep(50.0)
        self.scan_speed_spin.setSuffix(" mm/s")
        self.scan_speed_spin.setValue(self.params.get("scan_speed", 1000.0))
        form.addRow("Scan Speed:", self.scan_speed_spin)
        
        # Hatch spacing
        self.hatch_spacing_spin = QDoubleSpinBox()
        self.hatch_spacing_spin.setRange(0.01, 1.0)
        self.hatch_spacing_spin.setDecimals(3)
        self.hatch_spacing_spin.setSingleStep(0.01)
        self.hatch_spacing_spin.setSuffix(" mm")
        self.hatch_spacing_spin.setValue(self.params.get("hatch_spacing", 0.10))
        form.addRow("Hatch Spacing:", self.hatch_spacing_spin)
        
        # Hatch angle
        self.hatch_angle_spin = QDoubleSpinBox()
        self.hatch_angle_spin.setRange(0.0, 180.0)
        self.hatch_angle_spin.setDecimals(1)
        self.hatch_angle_spin.setSingleStep(5.0)
        self.hatch_angle_spin.setSuffix(" °")
        self.hatch_angle_spin.setValue(self.params.get("hatch_angle_increment", 67.0))
        form.addRow("Hatch Angle Increment:", self.hatch_angle_spin)
        
        layout.addLayout(form)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def _on_accept(self) -> None:
        """Validate and accept the dialog."""
        # All validation is handled by spinboxes, so just accept
        self.params["layer_thickness"] = self.layer_thickness_spin.value()
        self.params["laser_power"] = self.laser_power_spin.value()
        self.params["scan_speed"] = self.scan_speed_spin.value()
        self.params["hatch_spacing"] = self.hatch_spacing_spin.value()
        self.params["hatch_angle_increment"] = self.hatch_angle_spin.value()
        
        self.accept()
    
    def get_params(self) -> Dict[str, float]:
        """
        Get the updated parameters.
        
        Returns
        -------
        dict
            Updated parameter dictionary
        """
        return self.params


class MaterialDialog(QDialog):
    """Dialog for selecting material presets."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Material Library")
        self.setModal(True)
        self.resize(400, 300)
        
        self.selected_material = None
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Info label
        info = QLabel("Select a material preset to load recommended parameters:")
        layout.addWidget(info)
        
        # Material list
        for mat_name, params in MATERIAL_PRESETS.items():
            group = QGroupBox(mat_name)
            group_layout = QVBoxLayout()
            
            # Display parameters
            for key, value in params.items():
                label = key.replace("_", " ").title()
                text = QLabel(f"{label}: {value}")
                group_layout.addWidget(text)
            
            # Apply button
            apply_btn = QPushButton(f"Apply {mat_name}")
            apply_btn.clicked.connect(
                lambda checked, m=mat_name: self._on_apply(m)
            )
            group_layout.addWidget(apply_btn)
            
            group.setLayout(group_layout)
            layout.addWidget(group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
    
    def _on_apply(self, material_name: str) -> None:
        """Handle material selection."""
        self.selected_material = material_name
        self.accept()


class ProfileDialog(QDialog):
    """Dialog for selecting quality/layer thickness profiles."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Quality Profiles")
        self.setModal(True)
        self.resize(350, 250)
        
        self.selected_profile = None
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        
        info = QLabel("Select a layer thickness profile:")
        layout.addWidget(info)
        
        # Profile buttons
        for profile_name, thickness in PROFILE_PRESETS.items():
            btn = QPushButton(f"{profile_name}  —  {thickness * 1000:.0f} µm layer")
            btn.clicked.connect(
                lambda checked, p=profile_name: self._on_apply(p)
            )
            layout.addWidget(btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
    
    def _on_apply(self, profile_name: str) -> None:
        """Handle profile selection."""
        self.selected_profile = profile_name
        self.accept()


class BuildPlateDialog(QDialog):
    """Dialog for configuring build plate dimensions."""
    
    def __init__(self, current_diameter: float, current_height: float, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Build Plate Configuration")
        self.setModal(True)
        self.resize(300, 150)
        
        self.diameter = current_diameter
        self.height = current_height
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Build the dialog UI."""
        layout = QFormLayout(self)
        
        # Diameter
        self.diameter_spin = QDoubleSpinBox()
        self.diameter_spin.setRange(10.0, 500.0)
        self.diameter_spin.setDecimals(1)
        self.diameter_spin.setSuffix(" mm")
        self.diameter_spin.setValue(self.diameter)
        layout.addRow("Diameter:", self.diameter_spin)
        
        # Height
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1.0, 100.0)
        self.height_spin.setDecimals(1)
        self.height_spin.setSuffix(" mm")
        self.height_spin.setValue(self.height)
        layout.addRow("Height:", self.height_spin)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        
        layout.addRow(button_box)
    
    def _on_accept(self) -> None:
        """Accept and store values."""
        self.diameter = self.diameter_spin.value()
        self.height = self.height_spin.value()
        self.accept()


class AboutDialog(QDialog):
    """About dialog showing application information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("About PySLM Slicer")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>PySLM Industrial Slicer</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Info
        info = QLabel(
            "<p><b>Version:</b> 0.3.0 - PySide6 Migration</p>"
            "<p><b>Architecture:</b> Clean Architecture + DDD</p>"
            "<p><b>Engine:</b> PySLM</p>"
            "<p><b>GUI:</b> PySide6 + PyVistaQt</p>"
            "<p><b>3D Rendering:</b> VTK via PyVista</p>"
            "<hr>"
            "<p>An industrial-grade selective laser melting slicer "
            "with a modern Qt-based interface.</p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
