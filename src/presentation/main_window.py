"""
main_window.py  --  Cura-Style PySide6 Main Window
===================================================
Industrial-grade SLM Slicer GUI modelled after Ultimaker Cura 5.x.

Layout
------
+--------------------------------------------------------------+
| Menu Bar                                                      |
+--------------------------------------------------------------+
| Header: [Logo]  PREPARE | PREVIEW   [Machine v] [Material v] |
+----+---------------------------------------------+-----------+
|Tool|                                             | Print     |
| bar|         3D Viewport (PyVistaQt)             | Setup     |
|    |                                             | Panel     |
|    |                                             | (310 px)  |
|    +---------------------------------------------+           |
|    | Object List            | View Controls      | [SLICE]   |
+----+---------------------------------------------+-----------+
| Status Bar                                                    |
+--------------------------------------------------------------+
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QPushButton, QLabel, QComboBox, QFormLayout,
    QProgressBar, QFileDialog, QMessageBox, QStatusBar,
    QScrollArea, QTreeWidget, QTreeWidgetItem, QButtonGroup,
    QDoubleSpinBox, QSizePolicy, QSpacerItem,
)
from PySide6.QtCore import Qt, Slot, QTimer, QSize
from PySide6.QtGui import QAction, QKeySequence, QFont

from src.presentation.viewport_widget import SLMViewport
from src.presentation.workers import SlicingThread
from src.presentation.dialogs import (
    SettingsDialog, MaterialDialog, ProfileDialog,
    BuildPlateDialog, AboutDialog,
)

if TYPE_CHECKING:
    from src.application.scene_manager import SceneManager
    from src.application.slicer_service import SlicerService
    from src.infrastructure.repositories.asset_loader import AssetLoader


# ======================================================================
#  Cura-inspired Stylesheet
# ======================================================================

_STYLESHEET = """
/* === Global ============================================= */
QMainWindow { background-color: #F5F5F5; }

/* === Menu bar =========================================== */
QMenuBar {
    background-color: #FAFAFA;
    border-bottom: 1px solid #D0D0D0;
    padding: 2px 4px;
    font-size: 13px;
}
QMenuBar::item {
    padding: 4px 10px;
    background: transparent;
    border-radius: 3px;
}
QMenuBar::item:selected { background-color: #E2E2E2; }
QMenu {
    background: #FFFFFF;
    border: 1px solid #D0D0D0;
    padding: 4px 0;
}
QMenu::item { padding: 6px 28px 6px 14px; }
QMenu::item:selected { background-color: #E8F0FE; }
QMenu::separator { height: 1px; background: #E0E0E0; margin: 4px 8px; }

/* === Header bar ========================================= */
#HeaderBar {
    background-color: #20232A;
    min-height: 46px;
    max-height: 46px;
}
#LogoLabel {
    color: #FFFFFF;
    font-size: 15px;
    font-weight: bold;
    padding-left: 14px;
}
#StageTab {
    background: transparent;
    color: #9DA5B4;
    border: none;
    padding: 6px 22px;
    font-size: 12px;
    font-weight: bold;
    border-radius: 4px;
    letter-spacing: 1px;
}
#StageTab:checked { background: #2688EB; color: #FFFFFF; }
#StageTab:hover:!checked { background: #333640; color: #D0D4DC; }
#HeaderCombo {
    background: #2E323C;
    color: #D0D4DC;
    border: 1px solid #444854;
    border-radius: 4px;
    padding: 3px 8px;
    min-width: 130px;
    font-size: 12px;
}
#HeaderCombo:hover { border-color: #2688EB; }
#HeaderCombo QAbstractItemView {
    background: #2E323C;
    color: #D0D4DC;
    selection-background-color: #2688EB;
}

/* === Tool sidebar ======================================= */
#ToolSidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #D0D0D0;
    min-width: 46px;
    max-width: 46px;
}
.ToolBtn {
    background: transparent;
    border: none;
    border-radius: 4px;
    min-width: 38px;  min-height: 38px;
    max-width: 38px;  max-height: 38px;
    font-size: 16px;
    color: #555555;
}
.ToolBtn:checked { background: #2688EB; color: #FFFFFF; }
.ToolBtn:hover:!checked { background: #E8E8E8; }

/* small camera-preset buttons */
.ViewBtn {
    background: #F2F2F2;
    border: 1px solid #D0D0D0;
    border-radius: 3px;
    min-width: 36px;  min-height: 24px;
    max-width: 36px;  max-height: 24px;
    font-size: 9px;
    color: #555555;
    padding: 0px;
}
.ViewBtn:hover { background: #2688EB; color: white; border-color: #2688EB; }

/* === Print-setup panel (right side) ===================== */
#PrintSetupPanel {
    background-color: #FFFFFF;
    border-left: 1px solid #D0D0D0;
    min-width: 310px;
    max-width: 310px;
}
#PanelTitle {
    font-size: 15px;
    font-weight: bold;
    color: #20232A;
    padding: 10px 14px 4px 14px;
}
#SectionHeader {
    background: #F0F0F0;
    border: 1px solid #D8D8D8;
    border-radius: 4px;
    padding: 8px 12px;
    font-weight: bold;
    font-size: 12px;
    text-align: left;
    color: #2B2B2B;
}
#SectionHeader:hover { background: #E4E4E4; }

/* === Slice / action button ============================== */
#SliceButton {
    background-color: #2688EB;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 12px 16px;
    font-size: 14px;
    font-weight: bold;
    min-height: 42px;
}
#SliceButton:hover { background-color: #1A75D2; }
#SliceButton:pressed { background-color: #1565B5; }
#SliceButton:disabled { background-color: #B0C4DE; color: #F0F0F0; }

/* === Progress bar ======================================= */
QProgressBar {
    border: 1px solid #D0D0D0;
    border-radius: 4px;
    text-align: center;
    height: 18px;
    background: #F0F0F0;
    font-size: 11px;
}
QProgressBar::chunk { background: #2688EB; border-radius: 3px; }

/* === Object list ======================================== */
#ObjectListPanel {
    background: #FFFFFF;
    border-top: 1px solid #D0D0D0;
    max-height: 160px;
}
#ObjectListToggle {
    background: #F5F5F5;
    border: none;
    border-top: 1px solid #D0D0D0;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: bold;
    text-align: left;
    color: #555555;
}
#ObjectListToggle:hover { background: #EAEAEA; }
QTreeWidget {
    border: none;
    background: #FFFFFF;
    font-size: 12px;
    outline: none;
}
QTreeWidget::item { padding: 3px 0; }
QTreeWidget::item:selected { background: #E8F0FE; color: #1A1A2E; }

/* === Spin boxes ========================================= */
QDoubleSpinBox, QSpinBox {
    padding: 3px 6px;
    border: 1px solid #D0D0D0;
    border-radius: 4px;
    background: #FFFFFF;
    min-height: 22px;
}
QDoubleSpinBox:focus, QSpinBox:focus { border-color: #2688EB; }

/* === Status bar ========================================= */
QStatusBar {
    background: #FAFAFA;
    border-top: 1px solid #D0D0D0;
    color: #737373;
    font-size: 12px;
    padding: 2px 8px;
}

/* === Scroll bars ======================================== */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #F5F5F5;  width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #C0C0C0;  border-radius: 4px;  min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #A0A0A0; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }
"""


# ======================================================================
#  Collapsible section helper
# ======================================================================

class CollapsibleSection(QWidget):
    """Cura-style collapsible settings section with a toggle header."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._collapsed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(0)

        self.toggle_btn = QPushButton(f"\u25BC  {title}")
        self.toggle_btn.setObjectName("SectionHeader")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self.toggle_btn)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(10, 6, 10, 10)
        self.content_layout.setSpacing(6)
        layout.addWidget(self.content)

    def _toggle(self) -> None:
        self._collapsed = not self._collapsed
        self.content.setVisible(not self._collapsed)
        glyph = "\u25B6" if self._collapsed else "\u25BC"
        self.toggle_btn.setText(f"{glyph}  {self._title}")

    def add_row(self, label: str, widget: QWidget) -> None:
        """Add a label + widget row inside this section."""
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setMinimumWidth(115)
        row.addWidget(lbl)
        row.addWidget(widget, stretch=1)
        self.content_layout.addLayout(row)

    def add_widget(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)


# ======================================================================
#  Main Window
# ======================================================================

class SlicerGUI(QMainWindow):
    """
    Cura-style main window for the PySLM SLM slicer.

    The GUI communicates exclusively through the Application-layer
    services (SceneManager, SlicerService) -- no direct PySLM imports.
    """

    STAGE_PREPARE = 0
    STAGE_PREVIEW = 1

    def __init__(
        self,
        scene: "SceneManager",
        slicer_service: "SlicerService",
        asset_loader: "AssetLoader",
    ):
        super().__init__()
        self.scene = scene
        self.slicer = slicer_service
        self.loader = asset_loader

        self._slicing_thread: Optional[SlicingThread] = None
        self._current_stage = self.STAGE_PREPARE

        self._current_params: dict = {
            "layer_thickness": 0.030,
            "laser_power": 200.0,
            "scan_speed": 1000.0,
            "hatch_spacing": 0.10,
            "hatch_angle_increment": 67.0,
            "contour_count": 1,
            "contour_offset": 0.05,
        }

        self.setWindowTitle("PySLM Industrial Slicer")
        self.setMinimumSize(1100, 700)
        self.resize(1440, 900)
        self.setStyleSheet(_STYLESHEET)

        self._build_ui()
        self._create_menu_bar()
        self._create_status_bar()

        # Deferred first render (after Qt event-loop tick)
        QTimer.singleShot(100, self._initial_scene_load)

    # ------------------------------------------------------------------
    #  Deferred init
    # ------------------------------------------------------------------

    def _initial_scene_load(self) -> None:
        self.viewport.rebuild_scene()
        self._refresh_object_list()
        self._update_param_display()

    # ==================================================================
    #  UI Construction
    # ==================================================================

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Header bar (dark) ----
        root.addWidget(self._build_header())

        # ---- Content: tools | viewport | panel ----
        content = QWidget()
        content_lay = QHBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)

        content_lay.addWidget(self._build_tool_sidebar())

        # Viewport + object list
        vp_area = QWidget()
        vp_lay = QVBoxLayout(vp_area)
        vp_lay.setContentsMargins(0, 0, 0, 0)
        vp_lay.setSpacing(0)

        self.viewport = SLMViewport(self.scene, parent=vp_area)
        self.viewport.object_selected.connect(self._on_object_selected)
        vp_lay.addWidget(self.viewport, stretch=1)
        vp_lay.addWidget(self._build_object_list())

        content_lay.addWidget(vp_area, stretch=1)
        content_lay.addWidget(self._build_print_setup_panel())

        root.addWidget(content, stretch=1)

    # ------------------------------------------------------------------
    #  Header bar
    # ------------------------------------------------------------------

    def _build_header(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("HeaderBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 12, 0)
        lay.setSpacing(0)

        # Logo
        logo = QLabel("  PySLM  Slicer")
        logo.setObjectName("LogoLabel")
        lay.addWidget(logo)
        lay.addSpacing(28)

        # Stage tabs
        self._stage_group = QButtonGroup(bar)
        self._stage_group.setExclusive(True)

        self.btn_prepare = QPushButton("PREPARE")
        self.btn_prepare.setObjectName("StageTab")
        self.btn_prepare.setCheckable(True)
        self.btn_prepare.setChecked(True)
        self._stage_group.addButton(self.btn_prepare, self.STAGE_PREPARE)
        lay.addWidget(self.btn_prepare)

        self.btn_preview = QPushButton("PREVIEW")
        self.btn_preview.setObjectName("StageTab")
        self.btn_preview.setCheckable(True)
        self._stage_group.addButton(self.btn_preview, self.STAGE_PREVIEW)
        lay.addWidget(self.btn_preview)

        self._stage_group.idClicked.connect(self._on_stage_changed)

        lay.addStretch()

        # Machine selector
        lay.addWidget(self._header_label("Machine:"))
        self.machine_combo = QComboBox()
        self.machine_combo.setObjectName("HeaderCombo")
        self.machine_combo.addItems(["EOS M290", "SLM 280", "Concept Laser M2"])
        lay.addWidget(self.machine_combo)
        lay.addSpacing(12)

        # Material selector
        lay.addWidget(self._header_label("Material:"))
        self.material_combo = QComboBox()
        self.material_combo.setObjectName("HeaderCombo")
        from src.application.slicer_service import MATERIAL_PRESETS
        self.material_combo.addItems(list(MATERIAL_PRESETS.keys()))
        self.material_combo.currentTextChanged.connect(self._on_material_header_changed)
        lay.addWidget(self.material_combo)
        lay.addSpacing(12)

        # Profile selector
        lay.addWidget(self._header_label("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setObjectName("HeaderCombo")
        from src.application.slicer_service import PROFILE_PRESETS
        self.profile_combo.addItems(list(PROFILE_PRESETS.keys()))
        self.profile_combo.setCurrentIndex(1)  # Normal
        self.profile_combo.currentTextChanged.connect(self._on_profile_header_changed)
        lay.addWidget(self.profile_combo)

        return bar

    @staticmethod
    def _header_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #9DA5B4; font-size: 11px; padding: 0 4px;")
        return lbl

    # ------------------------------------------------------------------
    #  Tool sidebar (left)
    # ------------------------------------------------------------------

    def _build_tool_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("ToolSidebar")
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(4)

        self._tool_group = QButtonGroup(sidebar)
        self._tool_group.setExclusive(True)

        tools = [
            ("\u2725", "Move (T)",    0),   # ✥
            ("\u2B21", "Scale (S)",   1),   # ⬡
            ("\u27F2", "Rotate (R)",  2),   # ⟲
            ("\u21D4", "Mirror (M)",  3),   # ⇔
        ]
        for icon, tip, tid in tools:
            btn = QPushButton(icon)
            btn.setProperty("class", "ToolBtn")
            btn.setCheckable(True)
            btn.setToolTip(tip)
            self._tool_group.addButton(btn, tid)
            lay.addWidget(btn, alignment=Qt.AlignHCenter)

        lay.addStretch()

        # --- Camera presets (bottom of toolbar) ---
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #D0D0D0;")
        lay.addWidget(sep)
        lay.addSpacing(4)

        grid = QGridLayout()
        grid.setSpacing(2)
        views = [
            ("F", "front", 0, 0), ("T", "top",   0, 1),
            ("L", "left",  1, 0), ("R", "right", 1, 1),
            ("I", "iso",   2, 0), ("B", "back",  2, 1),
        ]
        for label, direction, r, c in views:
            btn = QPushButton(label)
            btn.setProperty("class", "ViewBtn")
            btn.setToolTip(f"{direction.capitalize()} view")
            btn.clicked.connect(lambda _=False, d=direction: self.viewport.set_view(d))
            grid.addWidget(btn, r, c)
        lay.addLayout(grid)
        lay.addSpacing(4)

        return sidebar

    # ------------------------------------------------------------------
    #  Object list (bottom of viewport)
    # ------------------------------------------------------------------

    def _build_object_list(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("ObjectListPanel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._obj_toggle = QPushButton("\u25BC  Objects (0)")
        self._obj_toggle.setObjectName("ObjectListToggle")
        self._obj_toggle.setCursor(Qt.PointingHandCursor)
        self._obj_toggle.clicked.connect(self._toggle_object_list)
        lay.addWidget(self._obj_toggle)

        self.scene_tree = QTreeWidget()
        self.scene_tree.setHeaderLabels(["Name", "Triangles"])
        self.scene_tree.setColumnWidth(0, 160)
        self.scene_tree.setRootIsDecorated(False)
        self.scene_tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.scene_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.scene_tree.setMaximumHeight(120)
        lay.addWidget(self.scene_tree)

        return panel

    def _toggle_object_list(self) -> None:
        vis = not self.scene_tree.isVisible()
        self.scene_tree.setVisible(vis)
        n = self.scene.object_count
        glyph = "\u25BC" if vis else "\u25B6"
        self._obj_toggle.setText(f"{glyph}  Objects ({n})")

    # ------------------------------------------------------------------
    #  Print-setup panel (right side)
    # ------------------------------------------------------------------

    def _build_print_setup_panel(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("PrintSetupPanel")
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        title = QLabel("Print Setup")
        title.setObjectName("PanelTitle")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        self._panel_lay = QVBoxLayout(inner)
        self._panel_lay.setContentsMargins(10, 6, 10, 6)
        self._panel_lay.setSpacing(6)

        # ---- Quality section ----
        sec_qual = CollapsibleSection("Quality")
        self.lbl_layer = QLabel(self._fmt_lt())
        sec_qual.add_row("Layer thickness:", self.lbl_layer)
        self._panel_lay.addWidget(sec_qual)

        # ---- Material section ----
        sec_mat = CollapsibleSection("Material")
        self.lbl_material = QLabel("Ti-6Al-4V")
        sec_mat.add_row("Active:", self.lbl_material)
        btn_mat = QPushButton("Material Library\u2026")
        btn_mat.clicked.connect(self._on_material_library)
        sec_mat.add_widget(btn_mat)
        self._panel_lay.addWidget(sec_mat)

        # ---- Process Parameters section ----
        sec_params = CollapsibleSection("Process Parameters")
        self.param_labels: dict = {}

        self.param_labels["laser_power"] = QLabel("200.0 W")
        sec_params.add_row("Laser power:", self.param_labels["laser_power"])

        self.param_labels["scan_speed"] = QLabel("1000.0 mm/s")
        sec_params.add_row("Scan speed:", self.param_labels["scan_speed"])

        self.param_labels["hatch_spacing"] = QLabel("0.100 mm")
        sec_params.add_row("Hatch spacing:", self.param_labels["hatch_spacing"])

        self.param_labels["hatch_angle"] = QLabel("67.0\u00B0")
        sec_params.add_row("Hatch angle:", self.param_labels["hatch_angle"])

        self.param_labels["contour_count"] = QLabel("1")
        sec_params.add_row("Contour count:", self.param_labels["contour_count"])

        btn_edit = QPushButton("Edit All Settings\u2026")
        btn_edit.clicked.connect(self._on_edit_settings)
        sec_params.add_widget(btn_edit)
        self._panel_lay.addWidget(sec_params)

        # ---- Build Plate section ----
        sec_plate = CollapsibleSection("Build Plate")
        self.lbl_plate = QLabel(
            f"\u2300 {self.scene.build_plate.diameter_mm:.0f} mm  \u00D7  "
            f"{self.scene.build_plate.height_mm:.0f} mm"
        )
        sec_plate.add_row("Dimensions:", self.lbl_plate)
        btn_plate = QPushButton("Configure\u2026")
        btn_plate.clicked.connect(self._on_build_plate_config)
        sec_plate.add_widget(btn_plate)
        self._panel_lay.addWidget(sec_plate)

        self._panel_lay.addStretch()

        # ---- Action area ----
        action_frame = QFrame()
        action_lay = QVBoxLayout(action_frame)
        action_lay.setContentsMargins(0, 8, 0, 0)
        action_lay.setSpacing(6)

        # Build-time estimate
        self.lbl_estimate = QLabel("")
        self.lbl_estimate.setStyleSheet("color: #737373; font-size: 12px;")
        self.lbl_estimate.setAlignment(Qt.AlignCenter)
        action_lay.addWidget(self.lbl_estimate)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        action_lay.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #555; font-size: 11px;")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setVisible(False)
        action_lay.addWidget(self.progress_label)

        # Slice button
        self.slice_btn = QPushButton("Slice")
        self.slice_btn.setObjectName("SliceButton")
        self.slice_btn.setCursor(Qt.PointingHandCursor)
        self.slice_btn.clicked.connect(self._on_slice)
        action_lay.addWidget(self.slice_btn)

        self._panel_lay.addWidget(action_frame)

        scroll.setWidget(inner)
        outer.addWidget(scroll, stretch=1)
        return wrapper

    # ------------------------------------------------------------------
    #  Menu bar
    # ------------------------------------------------------------------

    def _create_menu_bar(self) -> None:
        mb = self.menuBar()

        # ---- File ----
        fm = mb.addMenu("&File")
        act = QAction("&Open STL / 3MF\u2026", self)
        act.setShortcut(QKeySequence.Open)
        act.triggered.connect(self._on_open_file)
        fm.addAction(act)
        fm.addSeparator()
        act = QAction("&Save Project\u2026", self)
        act.setShortcut(QKeySequence.Save)
        act.triggered.connect(self._on_save_project)
        fm.addAction(act)
        act = QAction("Export &CLI\u2026", self)
        act.triggered.connect(self._on_export_cli)
        fm.addAction(act)
        fm.addSeparator()
        act = QAction("&Quit", self)
        act.setShortcut(QKeySequence("Ctrl+Q"))
        act.triggered.connect(self.close)
        fm.addAction(act)

        # ---- Edit ----
        em = mb.addMenu("&Edit")
        act = QAction("&Undo", self)
        act.setShortcut(QKeySequence.Undo)
        act.triggered.connect(self._on_undo)
        em.addAction(act)
        act = QAction("&Redo", self)
        act.setShortcut(QKeySequence.Redo)
        act.triggered.connect(self._on_redo)
        em.addAction(act)
        em.addSeparator()
        act = QAction("&Delete Selected", self)
        act.setShortcut(QKeySequence.Delete)
        act.triggered.connect(self._on_delete_selected)
        em.addAction(act)
        act = QAction("Du&plicate", self)
        act.setShortcut(QKeySequence("Ctrl+D"))
        act.triggered.connect(self._on_duplicate)
        em.addAction(act)
        em.addSeparator()
        act = QAction("Select &All", self)
        act.setShortcut(QKeySequence.SelectAll)
        em.addAction(act)
        act = QAction("&Arrange All on Build Plate", self)
        act.triggered.connect(self._on_arrange_all)
        em.addAction(act)

        # ---- View ----
        vm = mb.addMenu("&View")
        for name, key, direction in [
            ("Front",     "Ctrl+1", "front"),
            ("Top",       "Ctrl+2", "top"),
            ("Left",      "Ctrl+3", "left"),
            ("Right",     "Ctrl+4", "right"),
            ("Isometric", "Ctrl+5", "iso"),
        ]:
            a = QAction(f"{name} View", self)
            a.setShortcut(QKeySequence(key))
            a.triggered.connect(lambda _=False, d=direction: self.viewport.set_view(d))
            vm.addAction(a)
        vm.addSeparator()
        act = QAction("&Fit All", self)
        act.setShortcut(QKeySequence("F"))
        act.triggered.connect(self.viewport.fit_to_scene)
        vm.addAction(act)
        act = QAction("&Reset Camera", self)
        act.setShortcut(QKeySequence("Home"))
        act.triggered.connect(self.viewport.reset_view)
        vm.addAction(act)

        # ---- Slicer ----
        sm = mb.addMenu("&Slicer")
        act = QAction("&Settings\u2026", self)
        act.triggered.connect(self._on_edit_settings)
        sm.addAction(act)
        act = QAction("&Material Library\u2026", self)
        act.triggered.connect(self._on_material_library)
        sm.addAction(act)
        act = QAction("&Quality Profiles\u2026", self)
        act.triggered.connect(self._on_quality_profiles)
        sm.addAction(act)
        sm.addSeparator()
        act = QAction("&Build Plate\u2026", self)
        act.triggered.connect(self._on_build_plate_config)
        sm.addAction(act)

        # ---- Help ----
        hm = mb.addMenu("&Help")
        act = QAction("&About PySLM Slicer\u2026", self)
        act.triggered.connect(self._on_about)
        hm.addAction(act)

    # ------------------------------------------------------------------
    #  Status bar
    # ------------------------------------------------------------------

    def _create_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready", 5000)

    # ==================================================================
    #  Slots  --  File operations
    # ==================================================================

    @Slot()
    def _on_open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open 3D Model", str(Path.home()),
            "3D Models (*.stl *.STL *.3mf *.obj *.amf);;All Files (*.*)",
        )
        if not path:
            return
        try:
            self.status_bar.showMessage(f"Loading {Path(path).name}\u2026")
            name, mesh = self.loader.load(path)
            self.scene.add_mesh(name, mesh, source_path=path)
            self._refresh_object_list()
            self.viewport.rebuild_scene()
            self.status_bar.showMessage(
                f"Loaded {name}  ({mesh.faces.shape[0]:,} triangles)", 5000,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Load Error",
                                 f"Failed to load file:\n{exc}")
            self.status_bar.showMessage("Load failed", 5000)

    @Slot()
    def _on_save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project",
            str(Path.home() / "pyslicer_project.json"),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not path:
            return
        try:
            import json
            data = self.scene.serialize()
            data["params"] = self._current_params
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            self.status_bar.showMessage(
                f"Project saved to {Path(path).name}", 5000,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Save Error",
                                 f"Failed to save project:\n{exc}")

    @Slot()
    def _on_export_cli(self) -> None:
        if not self.slicer.last_parts:
            QMessageBox.warning(self, "No Slice Data",
                                "Please run Slice first before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CLI File",
            str(Path.home() / "pyslicer_output.cli"),
            "CLI Files (*.cli);;All Files (*.*)",
        )
        if not path:
            return
        try:
            layer_count = self.slicer.export_cli(path)
            QMessageBox.information(
                self, "Export Successful",
                f"Exported {layer_count} layers to:\n{path}",
            )
            self.status_bar.showMessage("CLI export complete", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "Export Error",
                                 f"Failed to export:\n{exc}")

    # ==================================================================
    #  Slots  --  Edit operations
    # ==================================================================

    @Slot()
    def _on_undo(self) -> None:
        label = self.scene.perform_undo()
        if label:
            self.viewport.rebuild_scene()
            self.status_bar.showMessage(f"Undo: {label}", 3000)
        else:
            self.status_bar.showMessage("Nothing to undo", 3000)

    @Slot()
    def _on_redo(self) -> None:
        label = self.scene.perform_redo()
        if label:
            self.viewport.rebuild_scene()
            self.status_bar.showMessage(f"Redo: {label}", 3000)
        else:
            self.status_bar.showMessage("Nothing to redo", 3000)

    @Slot()
    def _on_delete_selected(self) -> None:
        if self.scene.remove_selected():
            self._refresh_object_list()
            self.viewport.rebuild_scene()
            self.status_bar.showMessage("Object deleted", 3000)

    @Slot()
    def _on_duplicate(self) -> None:
        obj = self.scene.duplicate_selected()
        if obj:
            self._refresh_object_list()
            self.viewport.rebuild_scene()
            self.status_bar.showMessage(f"Duplicated: {obj.name}", 3000)

    @Slot()
    def _on_arrange_all(self) -> None:
        self.scene.auto_arrange()
        self.viewport.rebuild_scene()
        self.status_bar.showMessage("Objects arranged on build plate", 3000)

    # ==================================================================
    #  Slots  --  Settings / Configuration
    # ==================================================================

    @Slot()
    def _on_edit_settings(self) -> None:
        dlg = SettingsDialog(self._current_params, self)
        if dlg.exec() == SettingsDialog.Accepted:
            self._current_params = dlg.get_params()
            self._update_param_display()
            self.status_bar.showMessage("Settings updated", 3000)

    @Slot()
    def _on_material_library(self) -> None:
        dlg = MaterialDialog(self)
        if dlg.exec() == MaterialDialog.Accepted and dlg.selected_material:
            from src.application.slicer_service import MATERIAL_PRESETS
            self._current_params.update(MATERIAL_PRESETS[dlg.selected_material])
            self.lbl_material.setText(dlg.selected_material)
            idx = self.material_combo.findText(dlg.selected_material)
            if idx >= 0:
                self.material_combo.blockSignals(True)
                self.material_combo.setCurrentIndex(idx)
                self.material_combo.blockSignals(False)
            self._update_param_display()
            self.status_bar.showMessage(
                f"Material: {dlg.selected_material}", 3000,
            )

    @Slot()
    def _on_quality_profiles(self) -> None:
        dlg = ProfileDialog(self)
        if dlg.exec() == ProfileDialog.Accepted and dlg.selected_profile:
            from src.application.slicer_service import PROFILE_PRESETS
            self._current_params["layer_thickness"] = \
                PROFILE_PRESETS[dlg.selected_profile]
            idx = self.profile_combo.findText(dlg.selected_profile)
            if idx >= 0:
                self.profile_combo.blockSignals(True)
                self.profile_combo.setCurrentIndex(idx)
                self.profile_combo.blockSignals(False)
            self._update_param_display()
            self.status_bar.showMessage(
                f"Profile: {dlg.selected_profile}", 3000,
            )

    @Slot()
    def _on_build_plate_config(self) -> None:
        plate = self.scene.build_plate
        dlg = BuildPlateDialog(plate.diameter_mm, plate.height_mm, self)
        if dlg.exec() == BuildPlateDialog.Accepted:
            plate.diameter_mm = dlg.diameter
            plate.height_mm = dlg.height
            self.lbl_plate.setText(
                f"\u2300 {plate.diameter_mm:.0f} mm  \u00D7  "
                f"{plate.height_mm:.0f} mm"
            )
            self.viewport._create_build_plate()
            self.viewport._create_floor_grid()
            self.viewport.rebuild_scene()
            self.status_bar.showMessage("Build plate updated", 3000)

    @Slot()
    def _on_about(self) -> None:
        AboutDialog(self).exec()

    # ==================================================================
    #  Slots  --  Header combo changes
    # ==================================================================

    @Slot(str)
    def _on_material_header_changed(self, material_name: str) -> None:
        from src.application.slicer_service import MATERIAL_PRESETS
        if material_name in MATERIAL_PRESETS:
            self._current_params.update(MATERIAL_PRESETS[material_name])
            self.lbl_material.setText(material_name)
            self._update_param_display()
            self.status_bar.showMessage(f"Material: {material_name}", 3000)

    @Slot(str)
    def _on_profile_header_changed(self, profile_name: str) -> None:
        from src.application.slicer_service import PROFILE_PRESETS
        if profile_name in PROFILE_PRESETS:
            self._current_params["layer_thickness"] = \
                PROFILE_PRESETS[profile_name]
            self._update_param_display()
            self.status_bar.showMessage(f"Profile: {profile_name}", 3000)

    # ==================================================================
    #  Slots  --  Stage switching
    # ==================================================================

    @Slot(int)
    def _on_stage_changed(self, stage_id: int) -> None:
        self._current_stage = stage_id
        if stage_id == self.STAGE_PREVIEW:
            self.status_bar.showMessage("Preview stage (layer view)", 3000)
        else:
            self.status_bar.showMessage("Prepare stage", 3000)

    # ==================================================================
    #  Slots  --  Slicing
    # ==================================================================

    @Slot()
    def _on_slice(self) -> None:
        if self.scene.object_count == 0:
            QMessageBox.warning(self, "No Objects",
                                "Please load at least one 3D model first.")
            return

        if self._slicing_thread and self._slicing_thread.isRunning():
            QMessageBox.warning(self, "Busy",
                                "A slicing operation is already running.")
            return

        mesh_items = self.scene.collect_for_slicing()
        self._slicing_thread = SlicingThread(
            self.slicer, mesh_items, self._current_params, self,
        )
        self._slicing_thread.worker.progress_updated.connect(
            self._on_slice_progress)
        self._slicing_thread.worker.slicing_finished.connect(
            self._on_slice_finished)
        self._slicing_thread.worker.slicing_failed.connect(
            self._on_slice_failed)

        self.slice_btn.setEnabled(False)
        self.slice_btn.setText("Slicing\u2026")
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_estimate.setText("")
        self.status_bar.showMessage("Slicing started\u2026")
        self._slicing_thread.start()

    @Slot(int, str)
    def _on_slice_progress(self, pct: int, msg: str) -> None:
        self.progress_bar.setValue(pct)
        self.progress_label.setText(msg)

    @Slot(dict)
    def _on_slice_finished(self, result: dict) -> None:
        self.slice_btn.setEnabled(True)
        self.slice_btn.setText("Slice")
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        layers = result.get("total_layers", "?")
        elapsed = result.get("elapsed_s", 0)
        est_h = result.get("est_build_time_h", 0)

        self.lbl_estimate.setText(
            f"{layers} layers  \u2022  ~{est_h:.1f} h build time"
        )

        QMessageBox.information(
            self, "Slicing Complete",
            f"Slicing finished successfully!\n\n"
            f"Total Layers:  {layers}\n"
            f"Compute Time:  {elapsed:.2f} s\n"
            f"Est. Build Time:  {est_h:.1f} h",
        )
        self.status_bar.showMessage(
            f"Slicing complete \u2014 {layers} layers in {elapsed:.1f} s", 5000,
        )

        # Auto-switch to Preview stage
        self.btn_preview.setChecked(True)
        self._on_stage_changed(self.STAGE_PREVIEW)

    @Slot(str)
    def _on_slice_failed(self, err: str) -> None:
        self.slice_btn.setEnabled(True)
        self.slice_btn.setText("Slice")
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        QMessageBox.critical(self, "Slicing Failed", err)
        self.status_bar.showMessage("Slicing failed", 5000)

    # ==================================================================
    #  Slots  --  Scene interaction
    # ==================================================================

    @Slot(str)
    def _on_object_selected(self, uid: str) -> None:
        self.scene.select(uid)
        self._refresh_object_list()
        self.viewport.highlight_selected(uid)
        obj = self.scene.selected_object
        if obj:
            self.status_bar.showMessage(f"Selected: {obj.name}", 3000)

    @Slot(QTreeWidgetItem, int)
    def _on_tree_item_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        uid = item.data(0, Qt.UserRole)
        if uid:
            self.scene.select(uid)
            self.viewport.highlight_selected(uid)
            self.viewport.render()

    # ==================================================================
    #  Helper utilities
    # ==================================================================

    def _refresh_object_list(self) -> None:
        self.scene_tree.clear()
        for obj in self.scene.objects:
            item = QTreeWidgetItem([obj.name,
                                    f"{obj.mesh.faces.shape[0]:,}"])
            item.setData(0, Qt.UserRole, obj.uid)
            if obj.selected:
                item.setSelected(True)
            self.scene_tree.addTopLevelItem(item)

        n = self.scene.object_count
        vis = self.scene_tree.isVisible()
        glyph = "\u25BC" if vis else "\u25B6"
        self._obj_toggle.setText(f"{glyph}  Objects ({n})")

    def _update_param_display(self) -> None:
        p = self._current_params
        self.lbl_layer.setText(self._fmt_lt())
        self.param_labels["laser_power"].setText(f"{p['laser_power']:.1f} W")
        self.param_labels["scan_speed"].setText(f"{p['scan_speed']:.1f} mm/s")
        self.param_labels["hatch_spacing"].setText(
            f"{p['hatch_spacing']:.3f} mm")
        self.param_labels["hatch_angle"].setText(
            f"{p['hatch_angle_increment']:.1f}\u00B0")
        self.param_labels["contour_count"].setText(
            str(int(p.get("contour_count", 1))))

    def _fmt_lt(self) -> str:
        lt_mm = self._current_params["layer_thickness"]
        return f"{lt_mm:.3f} mm  ({lt_mm * 1000:.0f} \u00B5m)"

    # ==================================================================
    #  Entry point
    # ==================================================================

    def run(self) -> None:
        """Show the window.  QApplication.exec() is called in main.py."""
        self.show()
