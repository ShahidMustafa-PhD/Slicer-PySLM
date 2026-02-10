"""
dialogs.py  --  Cura-Style Qt Dialogs for SLM Slicer
=====================================================
Modal dialogs for settings, materials, profiles, build-plate
configuration, and application info.  Styled to match the Cura
industrial aesthetic with proper input validation.
"""
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QGroupBox, QCheckBox, QFrame, QScrollArea,
    QSizePolicy, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.application.slicer_service import MATERIAL_PRESETS, PROFILE_PRESETS


# ======================================================================
#  Shared dialog stylesheet
# ======================================================================

_DIALOG_STYLE = """
QDialog {
    background-color: #FFFFFF;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #D0D0D0;
    border-radius: 5px;
    margin-top: 12px;
    padding: 14px 10px 10px 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}
QPushButton {
    padding: 6px 16px;
    border-radius: 4px;
    border: 1px solid #D0D0D0;
    background: #F5F5F5;
    font-size: 12px;
}
QPushButton:hover { background: #E8E8E8; }
QPushButton:pressed { background: #D8D8D8; }
#PrimaryBtn {
    background: #2688EB;
    color: #FFFFFF;
    border: none;
    font-weight: bold;
}
#PrimaryBtn:hover { background: #1A75D2; }
#PrimaryBtn:pressed { background: #1565B5; }
QDoubleSpinBox, QSpinBox {
    padding: 4px 8px;
    border: 1px solid #D0D0D0;
    border-radius: 4px;
    min-height: 24px;
}
QDoubleSpinBox:focus, QSpinBox:focus { border-color: #2688EB; }
QLabel { font-size: 13px; }
"""


# ======================================================================
#  Settings Dialog
# ======================================================================

class SettingsDialog(QDialog):
    """
    Comprehensive SLM process parameter editor.
    All numeric values validated with QDoubleSpinBox/QSpinBox.
    """

    def __init__(self, current_params: Dict[str, float], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Process Settings")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setStyleSheet(_DIALOG_STYLE)
        self.params = current_params.copy()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ---- Laser & Scanning ----
        grp_laser = QGroupBox("Laser && Scanning")
        form1 = QFormLayout(grp_laser)
        form1.setLabelAlignment(Qt.AlignRight)

        self.sp_layer = QDoubleSpinBox()
        self.sp_layer.setRange(0.005, 1.0)
        self.sp_layer.setDecimals(3)
        self.sp_layer.setSingleStep(0.005)
        self.sp_layer.setSuffix("  mm")
        self.sp_layer.setValue(self.params.get("layer_thickness", 0.030))
        form1.addRow("Layer Thickness:", self.sp_layer)

        self.sp_power = QDoubleSpinBox()
        self.sp_power.setRange(10.0, 1000.0)
        self.sp_power.setDecimals(1)
        self.sp_power.setSingleStep(10.0)
        self.sp_power.setSuffix("  W")
        self.sp_power.setValue(self.params.get("laser_power", 200.0))
        form1.addRow("Laser Power:", self.sp_power)

        self.sp_speed = QDoubleSpinBox()
        self.sp_speed.setRange(10.0, 10000.0)
        self.sp_speed.setDecimals(1)
        self.sp_speed.setSingleStep(50.0)
        self.sp_speed.setSuffix("  mm/s")
        self.sp_speed.setValue(self.params.get("scan_speed", 1000.0))
        form1.addRow("Scan Speed:", self.sp_speed)

        root.addWidget(grp_laser)

        # ---- Hatching ----
        grp_hatch = QGroupBox("Hatching")
        form2 = QFormLayout(grp_hatch)
        form2.setLabelAlignment(Qt.AlignRight)

        self.sp_hatch_sp = QDoubleSpinBox()
        self.sp_hatch_sp.setRange(0.01, 2.0)
        self.sp_hatch_sp.setDecimals(3)
        self.sp_hatch_sp.setSingleStep(0.01)
        self.sp_hatch_sp.setSuffix("  mm")
        self.sp_hatch_sp.setValue(self.params.get("hatch_spacing", 0.10))
        form2.addRow("Hatch Spacing:", self.sp_hatch_sp)

        self.sp_hatch_ang = QDoubleSpinBox()
        self.sp_hatch_ang.setRange(0.0, 180.0)
        self.sp_hatch_ang.setDecimals(1)
        self.sp_hatch_ang.setSingleStep(5.0)
        self.sp_hatch_ang.setSuffix("  \u00B0")
        self.sp_hatch_ang.setValue(
            self.params.get("hatch_angle_increment", 67.0))
        form2.addRow("Angle Increment:", self.sp_hatch_ang)

        root.addWidget(grp_hatch)

        # ---- Contours ----
        grp_contour = QGroupBox("Contours")
        form3 = QFormLayout(grp_contour)
        form3.setLabelAlignment(Qt.AlignRight)

        self.sp_contour_n = QSpinBox()
        self.sp_contour_n.setRange(0, 10)
        self.sp_contour_n.setValue(int(self.params.get("contour_count", 1)))
        form3.addRow("Contour Count:", self.sp_contour_n)

        self.sp_contour_off = QDoubleSpinBox()
        self.sp_contour_off.setRange(0.0, 2.0)
        self.sp_contour_off.setDecimals(3)
        self.sp_contour_off.setSingleStep(0.01)
        self.sp_contour_off.setSuffix("  mm")
        self.sp_contour_off.setValue(
            self.params.get("contour_offset", 0.05))
        form3.addRow("Contour Offset:", self.sp_contour_off)

        root.addWidget(grp_contour)

        # ---- Buttons ----
        bbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self._on_accept)
        bbox.rejected.connect(self.reject)
        root.addWidget(bbox)

    def _on_accept(self) -> None:
        self.params["layer_thickness"] = self.sp_layer.value()
        self.params["laser_power"] = self.sp_power.value()
        self.params["scan_speed"] = self.sp_speed.value()
        self.params["hatch_spacing"] = self.sp_hatch_sp.value()
        self.params["hatch_angle_increment"] = self.sp_hatch_ang.value()
        self.params["contour_count"] = self.sp_contour_n.value()
        self.params["contour_offset"] = self.sp_contour_off.value()
        self.accept()

    def get_params(self) -> Dict[str, float]:
        return self.params


# ======================================================================
#  Material Dialog
# ======================================================================

class MaterialDialog(QDialog):
    """
    Material library dialog with card-based preset selection.
    Each material shows recommended parameters and an Apply button.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Material Library")
        self.setModal(True)
        self.setMinimumSize(460, 420)
        self.setStyleSheet(_DIALOG_STYLE)
        self.selected_material: Optional[str] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        header = QLabel(
            "Select a material preset.  Parameters will be applied "
            "to the current process settings."
        )
        header.setWordWrap(True)
        header.setStyleSheet("color: #555555; font-size: 12px;")
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        scroll_lay = QVBoxLayout(container)
        scroll_lay.setSpacing(8)

        for mat_name, params in MATERIAL_PRESETS.items():
            card = QGroupBox(mat_name)
            card_lay = QVBoxLayout(card)

            for key, value in params.items():
                nice = key.replace("_", " ").title()
                unit = _param_unit(key)
                lbl = QLabel(f"{nice}:  {value} {unit}")
                lbl.setStyleSheet("font-size: 12px; color: #333;")
                card_lay.addWidget(lbl)

            btn = QPushButton(f"Apply {mat_name}")
            btn.setObjectName("PrimaryBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda _=False, m=mat_name: self._on_apply(m))
            card_lay.addWidget(btn)
            scroll_lay.addWidget(card)

        scroll_lay.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        root.addWidget(close_btn, alignment=Qt.AlignRight)

    def _on_apply(self, name: str) -> None:
        self.selected_material = name
        self.accept()


# ======================================================================
#  Profile Dialog
# ======================================================================

class ProfileDialog(QDialog):
    """Quality/layer-thickness profile selector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quality Profiles")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setStyleSheet(_DIALOG_STYLE)
        self.selected_profile: Optional[str] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        header = QLabel("Select a layer-thickness profile:")
        header.setStyleSheet("color: #555555; font-size: 12px;")
        root.addWidget(header)

        for name, thickness in PROFILE_PRESETS.items():
            btn = QPushButton(
                f"{name}   \u2014   {thickness * 1000:.0f} \u00B5m layer")
            btn.setMinimumHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda _=False, p=name: self._on_apply(p))
            root.addWidget(btn)

        root.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        root.addWidget(close_btn, alignment=Qt.AlignRight)

    def _on_apply(self, name: str) -> None:
        self.selected_profile = name
        self.accept()


# ======================================================================
#  Build Plate Dialog
# ======================================================================

class BuildPlateDialog(QDialog):
    """Configure cylindrical build-plate dimensions."""

    def __init__(self, current_diameter: float,
                 current_height: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Build Plate Configuration")
        self.setModal(True)
        self.setMinimumWidth(340)
        self.setStyleSheet(_DIALOG_STYLE)
        self.diameter = current_diameter
        self.height = current_height
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        grp = QGroupBox("Cylindrical SLM Build Plate")
        form = QFormLayout(grp)
        form.setLabelAlignment(Qt.AlignRight)

        self.sp_dia = QDoubleSpinBox()
        self.sp_dia.setRange(10.0, 600.0)
        self.sp_dia.setDecimals(1)
        self.sp_dia.setSuffix("  mm")
        self.sp_dia.setValue(self.diameter)
        form.addRow("Diameter:", self.sp_dia)

        self.sp_h = QDoubleSpinBox()
        self.sp_h.setRange(1.0, 200.0)
        self.sp_h.setDecimals(1)
        self.sp_h.setSuffix("  mm")
        self.sp_h.setValue(self.height)
        form.addRow("Height:", self.sp_h)

        root.addWidget(grp)

        bbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self._on_accept)
        bbox.rejected.connect(self.reject)
        root.addWidget(bbox)

    def _on_accept(self) -> None:
        self.diameter = self.sp_dia.value()
        self.height = self.sp_h.value()
        self.accept()


# ======================================================================
#  About Dialog
# ======================================================================

class AboutDialog(QDialog):
    """Application information dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About PySLM Slicer")
        self.setModal(True)
        self.setFixedSize(440, 340)
        self.setStyleSheet(_DIALOG_STYLE)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel("PySLM Industrial Slicer")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #D0D0D0;")
        root.addWidget(sep)

        info = QLabel(
            "<table style='font-size:13px; line-height:1.6;'>"
            "<tr><td><b>Version:</b></td><td>1.0.0</td></tr>"
            "<tr><td><b>Architecture:</b></td>"
            "<td>Clean Architecture + DDD</td></tr>"
            "<tr><td><b>Engine:</b></td><td>PySLM / trimesh</td></tr>"
            "<tr><td><b>GUI Framework:</b></td>"
            "<td>PySide6 + PyVistaQt</td></tr>"
            "<tr><td><b>3D Rendering:</b></td>"
            "<td>VTK via PyVista</td></tr>"
            "<tr><td><b>Process:</b></td>"
            "<td>Selective Laser Melting (SLM)</td></tr>"
            "</table>"
        )
        info.setAlignment(Qt.AlignCenter)
        root.addWidget(info)

        root.addStretch()

        desc = QLabel(
            "An industrial-grade slicer for metal additive manufacturing "
            "with a Cura-inspired Qt interface."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #737373; font-size: 12px;")
        root.addWidget(desc)

        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        root.addWidget(btn, alignment=Qt.AlignCenter)


# ======================================================================
#  Utility
# ======================================================================

def _param_unit(key: str) -> str:
    """Return the display unit for a known parameter key."""
    units = {
        "laser_power": "W",
        "scan_speed": "mm/s",
        "hatch_spacing": "mm",
        "hatch_angle_increment": "\u00B0",
        "layer_thickness": "mm",
    }
    return units.get(key, "")
