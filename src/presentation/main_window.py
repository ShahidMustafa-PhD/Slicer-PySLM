"""
main_window.py  --  Presentation Layer  (Exact Cura 5.x replica)
==================================================================

Layout mirrors Ultimaker Cura (from Cura.qml / MainWindowHeader.qml):

+------------------------------------------------------------------+
|  File  Edit  View  Settings  Extensions  Preferences  Help       |  <- ApplicationMenu
+------------------------------------------------------------------+
| [Logo] PySLM  |  PREPARE  PREVIEW  MONITOR  |  Marketplace  [?] |  <- MainWindowHeader (navy)
+---+------------------------------------------------------+-------+
| T |                                                      | Print |
| O |                                                      | Setup |
| O |               3D  VIEWPORT  (PyVista)                |       |
| L |               viewport_background #fafafa            | [Rec] |
| B |                                                      | [Cus] |
| A |                                                      |       |
| R |  [JobSpecs]                                          | Params|
|   |  [Front][Top][Left][Right][Home]   [ActionPanel]     | Slice |
+---+------------------------------------------------------+-------+
|  Status bar   ·  objects  ·  build plate                         |
+------------------------------------------------------------------+

Toolbar         : Move / Scale / Rotate / Mirror / Per-object / Support
PrintSetupSelector : Profile selector, Recommended/Custom, settings tree
ActionPanel     : "Slice" blue button with progress and estimates
ViewOrientationControls : Front / Top / Left / Right / Home camera presets
"""
from __future__ import annotations

import json
import os
import time
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import dearpygui.dearpygui as dpg

from src.application.scene_manager import SceneManager
from src.application.slicer_service import SlicerService, MATERIAL_PRESETS, PROFILE_PRESETS
from src.infrastructure.repositories.asset_loader import AssetLoader, AssetLoadError
from src.presentation.viewport_manager import ViewportManager
from src.presentation.theme import (
    C, Layout,
    apply_cura_theme,
    create_primary_button_theme,
    create_secondary_button_theme,
    create_danger_button_theme,
    create_flat_button_theme,
    create_toolbar_active_theme,
    create_panel_header_theme,
    create_header_bar_theme,
    create_stage_active_theme,
    create_stage_inactive_theme,
    create_view_btn_theme,
    create_action_panel_theme,
    create_status_bar_theme,
    create_viewport_area_theme,
    create_toolbar_panel_theme,
    create_right_panel_theme,
)


class SlicerGUI:
    """
    Exact Cura 5.x presentation layer for the PySLM slicer.
    Receives all services via constructor (Dependency Injection).
    """

    def __init__(
        self,
        scene: SceneManager,
        slicer_service: SlicerService,
        asset_loader: AssetLoader,
    ) -> None:
        self.scene = scene
        self.slicer = slicer_service
        self.loader = asset_loader

        # Viewport renderer
        self.viewport = ViewportManager(
            scene, width=Layout.VP_W, height=Layout.VP_H,
        )

        # Component themes (set after DPG context)
        self._th_primary = None
        self._th_secondary = None
        self._th_danger = None
        self._th_flat = None
        self._th_toolbar_active = None
        self._th_header = None
        self._th_header_bar = None
        self._th_stage_active = None
        self._th_stage_inactive = None
        self._th_view_btn = None
        self._th_action_panel = None
        self._th_status = None
        self._th_viewport_area = None
        self._th_toolbar_panel = None
        self._th_right_panel = None

        # GUI state
        self._slice_running = False
        self._active_tool = "move"
        self._active_stage = "prepare"
        self._active_mode = "recommended"    # recommended | custom
        self._right_panel_visible = True
        self._slice_progress = 0.0
        self._current_dir = Path.home()
        self._nav_history: list[Path] = [self._current_dir]
        self._nav_index = 0
        self._file_dialog_dir_tag = "file_dialog_dir_entries"
        self._file_dialog_file_tag = "file_dialog_file_entries"
        self._file_dialog_path_tag = "file_dialog_path"
        self._file_dialog_status_tag = "file_dialog_status"
        self._mirror_axis = "x"             # current mirror axis

    # =====================================================================
    #  Entry point
    # =====================================================================
    def run(self) -> None:
        dpg.create_context()

        # --- Theme & fonts ---
        apply_cura_theme()
        self._th_primary        = create_primary_button_theme()
        self._th_secondary      = create_secondary_button_theme()
        self._th_danger         = create_danger_button_theme()
        self._th_flat           = create_flat_button_theme()
        self._th_toolbar_active = create_toolbar_active_theme()
        self._th_header         = create_panel_header_theme()
        self._th_header_bar     = create_header_bar_theme()
        self._th_stage_active   = create_stage_active_theme()
        self._th_stage_inactive = create_stage_inactive_theme()
        self._th_view_btn       = create_view_btn_theme()
        self._th_action_panel   = create_action_panel_theme()
        self._th_status         = create_status_bar_theme()
        self._th_viewport_area  = create_viewport_area_theme()
        self._th_toolbar_panel  = create_toolbar_panel_theme()
        self._th_right_panel    = create_right_panel_theme()

        # --- Texture ---
        self.viewport.register_texture()

        # --- UI ---
        self._build_main_window()
        self._build_file_dialog()
        self._register_handlers()
        self._register_keyboard_shortcuts()

        # --- Viewport ---
        dpg.create_viewport(
            title="PySLM Slicer  \u2014  Ultimaker Cura Style",
            width=Layout.WIN_W, height=Layout.WIN_H,
        )
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("primary", True)
        dpg.maximize_viewport()

        # Initial render
        self.viewport.rebuild_scene()

        dpg.start_dearpygui()
        self.viewport.shutdown()
        dpg.destroy_context()

    # =====================================================================
    #  Main window construction  (Cura.qml layout)
    # =====================================================================
    def _build_main_window(self) -> None:
        with dpg.window(tag="primary"):
            # ---------- ApplicationMenu (thin menu bar at very top) --------
            self._build_menu_bar()

            # ---------- MainWindowHeader (dark navy bar with stage tabs) ---
            self._build_header_bar()

            # ---------- Body: toolbar | viewport | print-setup ----------
            with dpg.group(horizontal=True, tag="body_group"):
                self._build_left_toolbar()
                self._build_viewport_area()
                self._build_right_panel()

            # ---------- Bottom status bar ----------
            self._build_status_bar()

    # -----------------------------------------------------------------
    #  APPLICATION MENU  (Cura ApplicationMenu.qml)
    # -----------------------------------------------------------------
    def _build_menu_bar(self) -> None:
        with dpg.menu_bar(tag="main_menu"):
            with dpg.menu(label="File"):
                dpg.add_menu_item(
                    label="Open File(s)...    Ctrl+O",
                    callback=self._cmd_import,
                )
                dpg.add_menu_item(
                    label="Open Recent",
                    tag="menu_open_recent",
                    callback=self._cmd_open_recent,
                )
                dpg.add_separator()
                dpg.add_menu_item(label="Save Project...", callback=self._cmd_save_build)
                dpg.add_menu_item(label="Save As...", callback=self._cmd_save_as)
                dpg.add_separator()
                dpg.add_menu_item(label="Export Sliced Data (CLI)...", callback=self._cmd_export_cli)
                dpg.add_menu_item(label="Export Layer SVG...",        callback=self._cmd_export_svg)
                dpg.add_separator()
                dpg.add_menu_item(label="Quit", callback=lambda: dpg.stop_dearpygui())

            with dpg.menu(label="Edit"):
                dpg.add_menu_item(label="Undo                Ctrl+Z", callback=self._cmd_undo, tag="menu_undo")
                dpg.add_menu_item(label="Redo                Ctrl+Y", callback=self._cmd_redo, tag="menu_redo")
                dpg.add_separator()
                dpg.add_menu_item(label="Select All          Ctrl+A", callback=self._cmd_select_all)
                dpg.add_menu_item(label="Clear Selection",            callback=self._cmd_deselect)
                dpg.add_separator()
                dpg.add_menu_item(label="Duplicate           Ctrl+D", callback=self._cmd_duplicate)
                dpg.add_menu_item(label="Delete              Del",    callback=self._cmd_delete)
                dpg.add_separator()
                dpg.add_menu_item(label="Arrange Objects",            callback=self._cmd_auto_arrange)
                dpg.add_menu_item(label="Clear Build Plate",          callback=self._cmd_clear_plate)

            with dpg.menu(label="View"):
                dpg.add_menu_item(label="Home                Home",   callback=self._cmd_reset_camera)
                dpg.add_menu_item(label="Front",                      callback=lambda: self._set_camera_view("front"))
                dpg.add_menu_item(label="Top",                        callback=lambda: self._set_camera_view("top"))
                dpg.add_menu_item(label="Left",                       callback=lambda: self._set_camera_view("left"))
                dpg.add_menu_item(label="Right",                      callback=lambda: self._set_camera_view("right"))
                dpg.add_separator()
                dpg.add_menu_item(label="Fit All             F",      callback=self._cmd_fit_all)
                dpg.add_menu_item(label="Toggle Print Setup",         callback=self._cmd_toggle_panel)

            with dpg.menu(label="Settings"):
                dpg.add_menu_item(label="Printer...",     callback=self._cmd_show_plate_settings)
                dpg.add_menu_item(label="Materials...",   callback=self._cmd_show_materials)
                dpg.add_menu_item(label="Profiles...",    callback=self._cmd_show_profiles)

            with dpg.menu(label="Extensions"):
                dpg.add_menu_item(label="Post Processing...",  callback=self._cmd_post_processing)
                dpg.add_menu_item(label="Toolpath Generator",  callback=self._cmd_toolpath_gen)

            with dpg.menu(label="Preferences"):
                dpg.add_menu_item(label="General",      callback=self._cmd_prefs_general)
                dpg.add_menu_item(label="Theme",        callback=self._cmd_prefs_theme)

            with dpg.menu(label="Help"):
                dpg.add_menu_item(label="About PySLM Slicer", callback=self._cmd_about)
                dpg.add_menu_item(label="Show Release Notes",  callback=self._cmd_release_notes)

    # -----------------------------------------------------------------
    #  MAIN WINDOW HEADER  (Cura MainWindowHeader.qml)
    #  Dark navy bar: [Logo] | Stage Tabs | Marketplace + Account
    # -----------------------------------------------------------------
    def _build_header_bar(self) -> None:
        hdr = dpg.add_child_window(
            height=Layout.HEADER_H, border=False,
            tag="header_bar", no_scrollbar=True,
        )
        dpg.bind_item_theme(hdr, self._th_header_bar)

        with dpg.group(horizontal=True, parent=hdr):
            # ---- Logo / branding (left) ----
            dpg.add_spacer(width=10)
            dpg.add_text("PySLM", color=(255, 255, 255, 255))
            dpg.add_spacer(width=6)
            dpg.add_text("Slicer", color=(180, 180, 220, 255))

            dpg.add_spacer(width=60)

            # ---- Stage tabs (center): PREPARE / PREVIEW / MONITOR ----
            self._stage_btn(
                "stage_prepare", "PREPARE",
                lambda: self._set_stage("prepare"),
            )
            dpg.add_spacer(width=4)
            self._stage_btn(
                "stage_preview", "PREVIEW",
                lambda: self._set_stage("preview"),
            )
            dpg.add_spacer(width=4)
            self._stage_btn(
                "stage_monitor", "MONITOR",
                lambda: self._set_stage("monitor"),
            )

            dpg.add_spacer(width=80)

            # ---- Machine selector (header combo) ----
            dpg.add_combo(
                items=["EOS M290 (120mm)", "SLM 280 (280mm)", "Custom"],
                default_value="EOS M290 (120mm)",
                tag="machine_combo", width=180,
                callback=self._on_machine_change,
            )

            dpg.add_spacer(width=100)

            # ---- Right side: Marketplace + About ----
            mkt = dpg.add_button(label="Marketplace", tag="marketplace_btn",
                                   callback=self._cmd_marketplace)
            dpg.bind_item_theme(mkt, self._th_stage_inactive)
            dpg.add_spacer(width=8)
            abt = dpg.add_button(label="?", tag="about_header_btn", callback=self._cmd_about)
            dpg.bind_item_theme(abt, self._th_stage_inactive)

        # Set initial active stage
        self._set_stage("prepare")

    def _stage_btn(self, tag, label, callback):
        """Create a stage tab button in the header."""
        btn = dpg.add_button(label=f"  {label}  ", tag=tag, callback=callback)
        dpg.bind_item_theme(btn, self._th_stage_inactive)

    # -----------------------------------------------------------------
    #  LEFT TOOLBAR  (Cura Toolbar.qml)
    #  Rounded white rectangle with tool icon buttons
    # -----------------------------------------------------------------
    def _build_left_toolbar(self) -> None:
        tb = dpg.add_child_window(
            width=Layout.LEFT_TOOLBAR_W, border=True,
            tag="left_toolbar", no_scrollbar=True,
        )
        dpg.bind_item_theme(tb, self._th_toolbar_panel)

        with dpg.group(parent=tb):
            dpg.add_spacer(height=8)

            self._toolbar_btn("tool_move",   "\u271a", "Move (G)",     lambda: self._set_tool("move"))
            self._toolbar_btn("tool_scale",  "S",      "Scale (S)",    lambda: self._set_tool("scale"))
            self._toolbar_btn("tool_rotate", "R",      "Rotate (R)",   lambda: self._set_tool("rotate"))
            self._toolbar_btn("tool_mirror", "M",      "Mirror",       lambda: self._set_tool("mirror"))

            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=4)

            self._toolbar_btn("tool_support",  "\u25a6", "Support Blocker",     lambda: self._set_tool("support"))
            self._toolbar_btn("tool_perobject", "\u2630", "Per Model Settings", lambda: self._set_tool("perobject"))

    def _toolbar_btn(self, tag, label, tooltip_text, cb):
        btn = dpg.add_button(label=f" {label} ", tag=tag, width=36, height=36, callback=cb)
        dpg.bind_item_theme(btn, self._th_flat)
        with dpg.tooltip(btn):
            dpg.add_text(tooltip_text, color=C.TOOLTIP_TEXT)

    # -----------------------------------------------------------------
    #  CENTRAL VIEWPORT  (Cura contentItem area)
    #  Contains: 3D image + overlays for JobSpecs, ViewOrientationControls, ActionPanel
    # -----------------------------------------------------------------
    def _build_viewport_area(self) -> None:
        vp = dpg.add_child_window(tag="viewport_area", border=False)
        dpg.bind_item_theme(vp, self._th_viewport_area)

        with dpg.group(parent=vp):
            # 3D viewport image
            dpg.add_image(
                self.viewport.texture_tag,
                tag="viewport_image",
            )

            dpg.add_spacer(height=4)

            # --- Layer preview slider (hidden by default, shown in PREVIEW stage) ---
            with dpg.group(tag="preview_controls_group", show=False):
                dpg.add_text("Layer Preview", tag="preview_label", color=C.ACCENT)
                with dpg.group(horizontal=True):
                    dpg.add_text("Layer:", color=C.TEXT_MEDIUM)
                    dpg.add_slider_int(
                        default_value=0, min_value=0, max_value=1,
                        tag="layer_slider", width=-120,
                        callback=self._on_layer_slider,
                    )
                    dpg.add_text("0 / 0", tag="layer_counter", color=C.TEXT_MEDIUM)

            # --- Monitor info (hidden by default, shown in MONITOR stage) ---
            with dpg.group(tag="monitor_info_group", show=False):
                dpg.add_text("Build Monitor", tag="monitor_label", color=C.ACCENT)
                dpg.add_text("Status: Idle — No active print job", tag="monitor_status_text", color=C.TEXT_MEDIUM)
                dpg.add_text("", tag="monitor_details", color=C.TEXT_MEDIUM, wrap=500)

            dpg.add_spacer(height=4)

            # Bottom overlay row: ViewOrientation (left) + ActionPanel (right)
            with dpg.group(horizontal=True):
                # ---- Bottom-left: Job specs + View orientation controls ----
                with dpg.group():
                    # Job specs (filename, face count)
                    with dpg.group(horizontal=True):
                        dpg.add_text("", tag="job_filename", color=C.TEXT_LIGHTER)
                        dpg.add_spacer(width=12)
                        dpg.add_text("", tag="job_faces", color=C.TEXT_LIGHTER)

                    dpg.add_spacer(height=2)

                    # ViewOrientationControls (Cura ViewOrientationControls.qml)
                    with dpg.group(horizontal=True, tag="view_controls"):
                        for view_name in ["Front", "Top", "Left", "Right", "Home"]:
                            btn = dpg.add_button(
                                label=f" {view_name} ",
                                tag=f"view_{view_name.lower()}",
                                callback=self._on_view_btn,
                                user_data=view_name.lower(),
                            )
                            dpg.bind_item_theme(btn, self._th_view_btn)

                dpg.add_spacer(width=40)

                # ---- Bottom-right: ActionPanel (Cura ActionPanelWidget.qml) ----
                ap = dpg.add_child_window(
                    width=Layout.ACTION_PANEL_W, height=100,
                    border=True, no_scrollbar=True,
                    tag="action_panel_area",
                )
                dpg.bind_item_theme(ap, self._th_action_panel)
                with dpg.group(parent=ap):
                    dpg.add_spacer(height=4)
                    dpg.add_text("", tag="vp_obj_count", color=C.TEXT_MEDIUM)
                    dpg.add_text("", tag="vp_tri_count", color=C.TEXT_MEDIUM)
                    dpg.add_spacer(height=4)
                    dpg.add_progress_bar(
                        default_value=0.0, tag="slice_progress",
                        overlay="", width=-1,
                    )
                    dpg.add_spacer(height=4)
                    slice_btn = dpg.add_button(
                        label="     Slice     ", tag="slice_btn",
                        width=-1, height=36, callback=self._cmd_slice,
                    )
                    dpg.bind_item_theme(slice_btn, self._th_primary)

    # -----------------------------------------------------------------
    #  RIGHT PANEL  (Cura PrintSetupSelector.qml)
    #  Profile selector, Recommended/Custom tabs, parameter sections
    # -----------------------------------------------------------------
    def _build_right_panel(self) -> None:
        rp = dpg.add_child_window(
            width=Layout.RIGHT_PANEL_W, tag="right_panel",
            border=True, no_scrollbar=False,
        )
        dpg.bind_item_theme(rp, self._th_right_panel)

        with dpg.group(parent=rp):
            # ---- Print Setup header ----
            dpg.add_text("Print Setup", color=C.TEXT_DEFAULT)
            dpg.add_separator()
            dpg.add_spacer(height=4)

            # ---- Profile / Quality selector ----
            dpg.add_text("Profile", color=C.TEXT_MEDIUM)
            dpg.add_combo(
                items=["Fine (20 \u00b5m)", "Normal (30 \u00b5m)", "Draft (50 \u00b5m)", "Custom"],
                default_value="Normal (30 \u00b5m)",
                tag="profile_combo", width=-1,
                callback=self._on_profile_change,
            )
            dpg.add_spacer(height=4)

            # ---- Material selector ----
            dpg.add_text("Material", color=C.TEXT_MEDIUM)
            dpg.add_combo(
                items=["Ti-6Al-4V", "316L Stainless", "AlSi10Mg", "IN718", "Custom"],
                default_value="Ti-6Al-4V",
                tag="material_combo", width=-1,
                callback=self._on_material_change,
            )
            dpg.add_spacer(height=4)

            # ---- Recommended / Custom toggle ----
            with dpg.group(horizontal=True, tag="mode_toggle"):
                rec_btn = dpg.add_button(
                    label="Recommended", tag="mode_recommended",
                    callback=self._cmd_mode_recommended, width=145,
                )
                dpg.bind_item_theme(rec_btn, self._th_primary)

                cust_btn = dpg.add_button(
                    label=" Custom ", tag="mode_custom",
                    callback=self._cmd_mode_custom, width=145,
                )
                dpg.bind_item_theme(cust_btn, self._th_secondary)

            dpg.add_spacer(height=8)

            # ---- Object Info ----
            hdr = dpg.add_collapsing_header(
                label="  Object Info", default_open=True, tag="sec_obj_info",
            )
            dpg.bind_item_theme(hdr, self._th_header)
            with dpg.group(parent=hdr):
                dpg.add_listbox(
                    items=[], num_items=4, tag="object_list",
                    callback=self._on_object_list_select, width=-1,
                )
                with dpg.group(horizontal=True):
                    imp_btn = dpg.add_button(label="Import", width=95, callback=self._cmd_import)
                    dpg.bind_item_theme(imp_btn, self._th_secondary)
                    dup_btn = dpg.add_button(label="Duplicate", width=95, callback=self._cmd_duplicate)
                    dpg.bind_item_theme(dup_btn, self._th_secondary)
                    del_btn = dpg.add_button(label="Delete", width=95, callback=self._cmd_delete)
                    dpg.bind_item_theme(del_btn, self._th_danger)
                dpg.add_spacer(height=4)
                dpg.add_text(
                    "", tag="info_text", color=C.TEXT_MEDIUM,
                    wrap=Layout.RIGHT_PANEL_W - 30,
                )

            dpg.add_spacer(height=4)

            # ---- Transform ----
            hdr2 = dpg.add_collapsing_header(
                label="  Transform", default_open=True, tag="sec_transform",
            )
            dpg.bind_item_theme(hdr2, self._th_header)
            with dpg.group(parent=hdr2):
                dpg.add_text("Position (mm)", color=C.TEXT_MEDIUM)
                dpg.add_input_floatx(
                    size=3, default_value=[0, 0, 0], tag="tf_pos",
                    callback=self._on_transform_change, on_enter=True, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Rotation (deg)", color=C.TEXT_MEDIUM)
                dpg.add_input_floatx(
                    size=3, default_value=[0, 0, 0], tag="tf_rot",
                    callback=self._on_transform_change, on_enter=True, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Scale", color=C.TEXT_MEDIUM)
                dpg.add_input_floatx(
                    size=3, default_value=[1, 1, 1], tag="tf_scale",
                    callback=self._on_transform_change, on_enter=True, width=-1,
                )
                dpg.add_spacer(height=2)
                ctr_btn = dpg.add_button(
                    label="Center on Plate", width=-1,
                    callback=self._cmd_center_on_plate,
                )
                dpg.bind_item_theme(ctr_btn, self._th_secondary)

            dpg.add_spacer(height=4)

            # ---- Process Parameters (Quality / Shell / Infill-like) ----
            hdr3 = dpg.add_collapsing_header(
                label="  Process Parameters", default_open=True, tag="sec_params",
            )
            dpg.bind_item_theme(hdr3, self._th_header)
            with dpg.group(parent=hdr3):
                dpg.add_text("Layer Thickness (mm)", color=C.TEXT_MEDIUM)
                dpg.add_input_float(
                    default_value=0.030, tag="param_layer_thickness",
                    format="%.3f", step=0.005, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Laser Power (W)", color=C.TEXT_MEDIUM)
                dpg.add_input_float(
                    default_value=200.0, tag="param_laser_power",
                    step=10, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Scan Speed (mm/s)", color=C.TEXT_MEDIUM)
                dpg.add_input_float(
                    default_value=1000.0, tag="param_scan_speed",
                    step=50, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Hatch Spacing (mm)", color=C.TEXT_MEDIUM)
                dpg.add_input_float(
                    default_value=0.10, tag="param_hatch_spacing",
                    format="%.3f", step=0.01, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Hatch Angle Increment (deg)", color=C.TEXT_MEDIUM)
                dpg.add_input_float(
                    default_value=67.0, tag="param_hatch_angle",
                    step=1, width=-1,
                )

            dpg.add_spacer(height=4)

            # ---- Advanced (collapsed by default) ----
            hdr4 = dpg.add_collapsing_header(
                label="  Advanced", default_open=False, tag="sec_advanced",
            )
            dpg.bind_item_theme(hdr4, self._th_header)
            with dpg.group(parent=hdr4):
                dpg.add_text("Contour Count", color=C.TEXT_MEDIUM)
                dpg.add_input_int(
                    default_value=1, tag="param_contour_count",
                    width=-1, min_value=0, max_value=10,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Contour Offset (mm)", color=C.TEXT_MEDIUM)
                dpg.add_input_float(
                    default_value=0.05, tag="param_contour_offset",
                    format="%.3f", step=0.01, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_checkbox(
                    label="Island Scanning", tag="param_island",
                    default_value=False,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Island Size (mm)", color=C.TEXT_MEDIUM)
                dpg.add_input_float(
                    default_value=5.0, tag="param_island_size",
                    step=1, width=-1,
                )

            dpg.add_spacer(height=10)

            # ---- Slice summary text at bottom of panel ----
            dpg.add_text(
                "", tag="slice_summary",
                wrap=Layout.RIGHT_PANEL_W - 30, color=C.TEXT_MEDIUM,
            )

    # -----------------------------------------------------------------
    #  STATUS BAR  (Cura bottom overlay)
    # -----------------------------------------------------------------
    def _build_status_bar(self) -> None:
        sb = dpg.add_child_window(
            height=Layout.STATUS_H, border=False,
            tag="status_bar_area", no_scrollbar=True,
        )
        dpg.bind_item_theme(sb, self._th_status)
        with dpg.group(horizontal=True, parent=sb):
            dpg.add_text("Ready", tag="status_text", color=C.TEXT_LIGHTER)

    # -----------------------------------------------------------------
    #  CUSTOM FILE DIALOG  (Cura-styled light modal)
    # -----------------------------------------------------------------
    def _build_file_dialog(self) -> None:
        with dpg.window(
            label="Import Models",
            tag="file_dialog_win",
            width=900,
            height=540,
            show=False,
            modal=True,
            no_resize=True,
            no_collapse=True,
            pos=(Layout.WIN_W // 2 - 450, Layout.WIN_H // 2 - 270),
        ):
            dpg.add_separator()
            with dpg.group(horizontal=True):
                back_btn = dpg.add_button(label="\u2190 Back", callback=lambda: self._navigate_history(-1))
                dpg.bind_item_theme(back_btn, self._th_secondary)
                fwd_btn = dpg.add_button(label="Forward \u2192", callback=lambda: self._navigate_history(1))
                dpg.bind_item_theme(fwd_btn, self._th_secondary)
                up_btn = dpg.add_button(label="\u2191 Up", callback=self._cmd_navigate_up)
                dpg.bind_item_theme(up_btn, self._th_secondary)
                dpg.add_input_text(
                    tag=self._file_dialog_path_tag,
                    width=520,
                    default_value=str(self._current_dir),
                    on_enter=True,
                    callback=self._cmd_enter_path,
                )
                go_btn = dpg.add_button(label="Go", callback=self._cmd_enter_path)
                dpg.bind_item_theme(go_btn, self._th_primary)
            dpg.add_separator()

            with dpg.group(horizontal=True):
                # Left column: quick links + folder list
                with dpg.child_window(
                    width=260, border=True, autosize_y=False, height=390,
                    tag="file_dialog_left", no_scrollbar=False,
                ):
                    dpg.add_text("Quick Access", color=C.TEXT_MEDIUM)
                    for label, path in self._quick_links():
                        btn = dpg.add_button(
                            label=f"{label}",
                            callback=self._on_quick_link_click,
                            user_data=str(path),
                            tag=f"quick_{label.lower().replace(' ', '_')}",
                        )
                        dpg.bind_item_theme(btn, self._th_secondary)
                    dpg.add_separator()
                    dpg.add_text("Folders", color=C.ACCENT)
                    with dpg.group(tag=self._file_dialog_dir_tag):
                        pass

                # Right column: file listing
                with dpg.child_window(
                    width=600, height=390, border=True, autosize_y=False,
                    tag="file_dialog_right", no_scrollbar=False,
                ):
                    dpg.add_text("Files", color=C.ACCENT)
                    dpg.add_text("Click any file to import it into the build plate.", color=C.TEXT_MEDIUM)
                    dpg.add_separator()
                    with dpg.group(tag=self._file_dialog_file_tag):
                        pass

            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_text("Status:", color=C.TEXT_MEDIUM)
                dpg.add_text("Ready to browse", tag=self._file_dialog_status_tag)
                dpg.add_spacer(width=34)
                close_btn = dpg.add_button(label="Close", callback=lambda: dpg.hide_item("file_dialog_win"))
                dpg.bind_item_theme(close_btn, self._th_secondary)

    # =====================================================================
    #  Handlers
    # =====================================================================
    def _register_handlers(self) -> None:
        with dpg.handler_registry():
            dpg.add_mouse_down_handler(callback=self._mouse_down_cb)
            dpg.add_mouse_release_handler(callback=self._mouse_up_cb)
            dpg.add_mouse_move_handler(callback=self._mouse_move_cb)
            dpg.add_mouse_wheel_handler(callback=self._mouse_wheel_cb)

    def _register_keyboard_shortcuts(self) -> None:
        with dpg.handler_registry():
            dpg.add_key_press_handler(dpg.mvKey_O,      callback=self._kb_open)
            dpg.add_key_press_handler(dpg.mvKey_D,      callback=self._kb_duplicate)
            dpg.add_key_press_handler(dpg.mvKey_Delete, callback=lambda: self._cmd_delete())
            dpg.add_key_press_handler(dpg.mvKey_F,      callback=lambda: self._cmd_fit_all())
            dpg.add_key_press_handler(dpg.mvKey_Home,   callback=lambda: self._cmd_reset_camera())
            dpg.add_key_press_handler(dpg.mvKey_G,      callback=lambda: self._set_tool("move"))
            dpg.add_key_press_handler(dpg.mvKey_S,      callback=self._kb_scale)
            dpg.add_key_press_handler(dpg.mvKey_R,      callback=self._kb_rotate)
            dpg.add_key_press_handler(dpg.mvKey_A,      callback=self._kb_select_all)
            dpg.add_key_press_handler(dpg.mvKey_M,      callback=lambda: self._set_tool("mirror"))
            dpg.add_key_press_handler(dpg.mvKey_Z,      callback=self._kb_undo)
            dpg.add_key_press_handler(dpg.mvKey_Y,      callback=self._kb_redo)

    def _kb_open(self):
        if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            self._cmd_import()

    def _kb_duplicate(self):
        if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            self._cmd_duplicate()

    def _kb_scale(self):
        if not dpg.is_key_down(dpg.mvKey_LControl):
            self._set_tool("scale")

    def _kb_rotate(self):
        if not dpg.is_key_down(dpg.mvKey_LControl):
            self._set_tool("rotate")

    def _kb_select_all(self):
        if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            self._cmd_select_all()

    def _kb_undo(self):
        if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            self._cmd_undo()

    def _kb_redo(self):
        if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            self._cmd_redo()

    # -- Mouse --
    def _is_over_viewport(self) -> bool:
        try:
            return dpg.is_item_hovered("viewport_image")
        except Exception:
            return False

    def _mouse_down_cb(self, sender, app_data) -> None:
        if not self._is_over_viewport():
            return
        button = app_data
        pos = dpg.get_mouse_pos()
        if button == 0:
            uid = self.viewport.try_pick_object(pos)
            if uid:
                self.scene.select(uid)
                self.viewport.start_drag(uid)
                self._refresh_sidebar()
                self.viewport.rebuild_scene()
        self.viewport.on_mouse_down(button, pos)

    def _mouse_up_cb(self, sender, app_data) -> None:
        self.viewport.on_mouse_up(app_data)

    def _mouse_move_cb(self, sender, app_data) -> None:
        if not self._is_over_viewport():
            return
        self.viewport.on_mouse_move(dpg.get_mouse_pos(),
                                    on_transform_cb=self._refresh_sidebar)

    def _mouse_wheel_cb(self, sender, app_data) -> None:
        if not self._is_over_viewport():
            return
        self.viewport.on_mouse_wheel(app_data)

    # =====================================================================
    #  COMMANDS
    # =====================================================================
    def _cmd_import(self, sender=None, app_data=None) -> None:
        self._refresh_file_dialog()
        dpg.show_item("file_dialog_win")

    def _cmd_duplicate(self, sender=None, app_data=None) -> None:
        obj = self.scene.duplicate_selected()
        if obj:
            self._set_status(f"Duplicated \u2192 {obj.name}")
            self._refresh_all()

    def _cmd_delete(self, sender=None, app_data=None) -> None:
        if self.scene.remove_selected():
            self._set_status("Object removed")
            self._refresh_all()

    def _cmd_deselect(self, sender=None, app_data=None) -> None:
        self.scene.deselect_all()
        self._refresh_all()

    def _cmd_select_all(self, sender=None, app_data=None) -> None:
        for obj in self.scene.objects:
            obj.selected = True
        self._refresh_all()

    def _cmd_clear_plate(self, sender=None, app_data=None) -> None:
        for uid in [o.uid for o in self.scene.objects]:
            self.scene.remove(uid)
        self._set_status("Build plate cleared")
        self._refresh_all()

    def _cmd_reset_camera(self, sender=None, app_data=None) -> None:
        self.viewport.plotter.reset_camera()
        self.viewport.refresh()

    def _cmd_fit_all(self, sender=None, app_data=None) -> None:
        self.viewport.plotter.reset_camera()
        self.viewport.plotter.camera.Zoom(0.85)
        self.viewport.refresh()

    def _cmd_center_on_plate(self, sender=None, app_data=None) -> None:
        obj = self.scene.selected_object
        if obj:
            obj.transform.translation[0] = 0.0
            obj.transform.translation[1] = 0.0
            self._refresh_all()

    def _cmd_toggle_panel(self, sender=None, app_data=None) -> None:
        self._right_panel_visible = not self._right_panel_visible
        dpg.configure_item("right_panel", show=self._right_panel_visible)

    def _cmd_save_build(self, sender=None, app_data=None) -> None:
        """Save the current project (scene + params) as JSON."""
        save_dir = Path.home() / "Documents"
        save_path = save_dir / "pyslicer_project.json"
        try:
            data = self.scene.serialize()
            data["params"] = self._gather_slice_params()
            data["material"] = dpg.get_value("material_combo")
            data["profile"] = dpg.get_value("profile_combo")
            data["machine"] = dpg.get_value("machine_combo")
            with open(save_path, "w") as f:
                json.dump(data, f, indent=2)
            self._set_status(f"Project saved to {save_path.name}")
        except Exception as exc:
            self._set_status(f"Save failed: {exc}")

    def _cmd_save_as(self, sender=None, app_data=None) -> None:
        """Save As — writes project JSON to Documents."""
        self._cmd_save_build()

    def _cmd_export_cli(self, sender=None, app_data=None) -> None:
        """Export sliced data as CLI file."""
        if not self.slicer.last_parts:
            self._set_status("No slice data — run Slice first.")
            return
        out = Path.home() / "Documents" / "pyslicer_output.cli"
        try:
            n = self.slicer.export_cli(str(out))
            self._set_status(f"Exported {n} layers to {out.name}")
        except Exception as exc:
            self._set_status(f"Export failed: {exc}")

    def _cmd_export_svg(self, sender=None, app_data=None) -> None:
        """Export current preview layer as SVG."""
        if not self.slicer.last_parts:
            self._set_status("No slice data — run Slice first.")
            return
        idx = self.viewport.preview_layer_index if self.viewport.preview_layer_count > 0 else 0
        out = Path.home() / "Documents" / f"layer_{idx}.svg"
        try:
            ok = self.slicer.export_layer_svg(str(out), idx)
            if ok:
                self._set_status(f"Layer SVG saved to {out.name}")
            else:
                self._set_status("No contours to export for this layer.")
        except Exception as exc:
            self._set_status(f"SVG export failed: {exc}")

    def _cmd_open_recent(self, sender=None, app_data=None) -> None:
        """Show a popup with recently opened files."""
        recent = self.scene.recent_files
        if not recent:
            self._set_status("No recent files.")
            return
        if dpg.does_item_exist("recent_popup"):
            dpg.delete_item("recent_popup")
        with dpg.window(label="Open Recent", modal=True, tag="recent_popup",
                        width=500, height=300):
            dpg.add_text("Recent Files", color=C.ACCENT)
            dpg.add_separator()
            for fp in recent:
                p = Path(fp)
                dpg.add_button(
                    label=f"  {p.name}  ({p.parent})",
                    width=-1,
                    callback=self._on_recent_file_click,
                    user_data=fp,
                )
            dpg.add_spacer(height=8)
            close_btn = dpg.add_button(label="  Close  ",
                                       callback=lambda: dpg.delete_item("recent_popup"))
            dpg.bind_item_theme(close_btn, self._th_secondary)

    def _on_recent_file_click(self, sender, app_data, user_data) -> None:
        if dpg.does_item_exist("recent_popup"):
            dpg.delete_item("recent_popup")
        file_path = Path(user_data)
        if not file_path.exists():
            self._set_status(f"File not found: {file_path.name}")
            return
        self._load_file_direct(str(file_path))

    def _load_file_direct(self, file_path: str) -> None:
        """Load a mesh file directly (bypassing the file dialog)."""
        fp = Path(file_path)
        self._set_status(f"Loading {fp.name} ...")
        try:
            name, mesh = self.loader.load(str(fp))
        except AssetLoadError as exc:
            self._set_status(f"Load error: {exc}")
            return
        self.scene.add_mesh(name, mesh, source_path=str(fp))
        info = (
            f"Loaded: {name}\n"
            f"Vertices : {mesh.vertices.shape[0]:,}\n"
            f"Faces    : {mesh.faces.shape[0]:,}\n"
            f"Size     : {mesh.extents.round(2)} mm"
        )
        dpg.set_value("info_text", info)
        self._set_status(f"Imported {name} ({mesh.faces.shape[0]:,} triangles)")
        self._refresh_all()

    def _cmd_undo(self, sender=None, app_data=None) -> None:
        label = self.scene.perform_undo()
        if label:
            self._set_status(f"Undo: {label}")
            self._refresh_all()
        else:
            self._set_status("Nothing to undo")

    def _cmd_redo(self, sender=None, app_data=None) -> None:
        label = self.scene.perform_redo()
        if label:
            self._set_status(f"Redo: {label}")
            self._refresh_all()
        else:
            self._set_status("Nothing to redo")

    def _cmd_auto_arrange(self, sender=None, app_data=None) -> None:
        self.scene.auto_arrange()
        self._set_status("Objects auto-arranged")
        self._refresh_all()

    def _cmd_mode_recommended(self, sender=None, app_data=None) -> None:
        """Switch to Recommended mode — hide Advanced, simplify parameters."""
        self._active_mode = "recommended"
        dpg.bind_item_theme("mode_recommended", self._th_primary)
        dpg.bind_item_theme("mode_custom", self._th_secondary)
        # Hide advanced section, collapse process params
        if dpg.does_item_exist("sec_advanced"):
            dpg.configure_item("sec_advanced", show=False)
        # Show simplified info text
        if dpg.does_item_exist("sec_params"):
            dpg.configure_item("sec_params", default_open=False, closable=False)
        self._set_status("Recommended mode — simplified settings")

    def _cmd_mode_custom(self, sender=None, app_data=None) -> None:
        """Switch to Custom mode (shows all settings)."""
        self._active_mode = "custom"
        dpg.bind_item_theme("mode_custom", self._th_primary)
        dpg.bind_item_theme("mode_recommended", self._th_secondary)
        # Show all sections
        if dpg.does_item_exist("sec_advanced"):
            dpg.configure_item("sec_advanced", show=True)
        if dpg.does_item_exist("sec_params"):
            dpg.configure_item("sec_params", default_open=True)
        self._set_status("Custom mode — all parameters visible")

    def _cmd_show_plate_settings(self, sender=None, app_data=None) -> None:
        if dpg.does_item_exist("plate_popup"):
            dpg.delete_item("plate_popup")
        with dpg.window(
            label="Printer Settings", modal=True,
            tag="plate_popup", width=380, height=220,
        ):
            dpg.add_text("Configure the build plate dimensions", color=C.TEXT_MEDIUM)
            dpg.add_spacer(height=6)
            dpg.add_text("Diameter (mm)", color=C.TEXT_MEDIUM)
            dpg.add_input_float(
                default_value=self.scene.build_plate.diameter_mm,
                tag="plate_dia", width=200,
            )
            dpg.add_text("Height (mm)", color=C.TEXT_MEDIUM)
            dpg.add_input_float(
                default_value=self.scene.build_plate.height_mm,
                tag="plate_h", width=200,
            )
            dpg.add_spacer(height=8)
            apply_btn = dpg.add_button(label="  Apply  ", callback=self._apply_plate_settings)
            dpg.bind_item_theme(apply_btn, self._th_primary)

    def _apply_plate_settings(self, sender=None, app_data=None) -> None:
        self.scene.build_plate.diameter_mm = dpg.get_value("plate_dia")
        self.scene.build_plate.height_mm = dpg.get_value("plate_h")
        dpg.delete_item("plate_popup")
        self._refresh_all()
        self._set_status(f"Plate updated: {self.scene.build_plate.diameter_mm:.0f} mm")

    def _cmd_about(self, sender=None, app_data=None) -> None:
        if dpg.does_item_exist("about_popup"):
            dpg.delete_item("about_popup")
        with dpg.window(
            label="About PySLM Slicer", modal=True,
            tag="about_popup", width=420, height=240,
        ):
            dpg.add_text("PySLM Industrial Slicer", color=C.ACCENT)
            dpg.add_text("Version 0.1.0", color=C.TEXT_MEDIUM)
            dpg.add_spacer(height=6)
            dpg.add_text(
                "Clean Architecture  |  DDD  |  PySLM Engine",
                color=C.TEXT_MEDIUM,
            )
            dpg.add_text(
                "GUI: Dear PyGui  |  3D: PyVista (VTK)",
                color=C.TEXT_MEDIUM,
            )
            dpg.add_text(
                "Theme: Ultimaker Cura 5.x Light",
                color=C.TEXT_MEDIUM,
            )
            dpg.add_spacer(height=10)
            close_btn = dpg.add_button(
                label="  Close  ",
                callback=lambda: dpg.delete_item("about_popup"),
            )
            dpg.bind_item_theme(close_btn, self._th_secondary)

    # -- Stage selection (Cura PREPARE / PREVIEW / MONITOR) --
    def _set_stage(self, stage: str) -> None:
        self._active_stage = stage
        for s in ["prepare", "preview", "monitor"]:
            tag = f"stage_{s}"
            if dpg.does_item_exist(tag):
                dpg.bind_item_theme(
                    tag,
                    self._th_stage_active if s == stage else self._th_stage_inactive,
                )
        self._set_status(f"Stage: {stage.upper()}")

    # -- Tool selection (Cura Toolbar.qml) --
    def _set_tool(self, tool: str) -> None:
        self._active_tool = tool
        self._set_status(f"Active tool: {tool.capitalize()}")
        mapping = {
            "move": "tool_move", "scale": "tool_scale",
            "rotate": "tool_rotate", "mirror": "tool_mirror",
            "support": "tool_support", "perobject": "tool_perobject",
        }
        for name, tag in mapping.items():
            if dpg.does_item_exist(tag):
                dpg.bind_item_theme(
                    tag, self._th_toolbar_active if name == tool else self._th_flat,
                )

    # -- Camera view presets (Cura ViewOrientationControls.qml) --
    def _on_view_btn(self, sender, app_data, user_data) -> None:
        self._set_camera_view(user_data)

    def _set_camera_view(self, view: str) -> None:
        cam = self.viewport.plotter.camera
        r = self.scene.build_plate.radius
        dist = r * 3
        fp = (0, 0, r * 0.15)

        presets = {
            "front": [(0, -dist, fp[2]),  fp, (0, 0, 1)],
            "top":   [(0, 0, dist),       fp, (0, -1, 0)],
            "left":  [(-dist, 0, fp[2]),  fp, (0, 0, 1)],
            "right": [(dist, 0, fp[2]),   fp, (0, 0, 1)],
            "home":  [(dist*0.7, -dist*0.7, dist*0.6), fp, (0, 0, 1)],
        }
        if view in presets:
            pos, focal, up = presets[view]
            self.viewport.plotter.camera_position = [pos, focal, up]
            self.viewport.plotter.reset_camera_clipping_range()
            self.viewport.refresh()
            self._set_status(f"View: {view.capitalize()}")

    # -- Header combo callbacks --
    def _on_machine_change(self, sender, app_data) -> None:
        presets = {
            "EOS M290 (120mm)": (120.0, 20.0),
            "SLM 280 (280mm)":  (280.0, 25.0),
        }
        if app_data in presets:
            d, h = presets[app_data]
            self.scene.build_plate.diameter_mm = d
            self.scene.build_plate.height_mm = h
            self._set_status(f"Machine: {app_data}")
            self._refresh_all()

    def _on_profile_change(self, sender, app_data) -> None:
        presets = {
            "Fine (20 um)":   0.020,
            "Normal (30 um)": 0.030,
            "Draft (50 um)":  0.050,
        }
        lt = presets.get(app_data)
        if lt:
            dpg.set_value("param_layer_thickness", lt)
            self._set_status(f"Profile: {app_data}")

    # =====================================================================
    #  SLICING
    # =====================================================================
    def _cmd_slice(self, sender=None, app_data=None) -> None:
        if self._slice_running:
            self._set_status("Slicing is already running...")
            return
        if self.scene.object_count == 0:
            self._set_status("Nothing to slice \u2014 import a model first.")
            return

        params = self._gather_slice_params()
        meshes = self.scene.collect_for_slicing()

        self._slice_running = True
        dpg.set_value("slice_progress", 0.0)
        dpg.configure_item("slice_progress", overlay="Preparing...")
        dpg.configure_item("slice_btn", label="  Slicing...  ", enabled=False)
        self._set_status("Slicing started...")
        dpg.set_value("slice_summary", "")

        def _worker():
            try:
                t0 = time.perf_counter()
                dpg.set_value("slice_progress", 0.1)
                dpg.configure_item("slice_progress", overlay="Slicing...")

                result = self.slicer.slice(meshes, params)

                dpg.set_value("slice_progress", 1.0)
                elapsed = time.perf_counter() - t0
                dpg.configure_item(
                    "slice_progress", overlay=f"Done in {elapsed:.1f}s",
                )

                summary = (
                    f"Slicing complete!\n"
                    f"Parts       : {len(meshes)}\n"
                    f"Total Layers: {result.get('total_layers', '?')}\n"
                    f"Thickness   : {params['layer_thickness']} mm\n"
                    f"Time        : {elapsed:.2f} s"
                )
                dpg.set_value("slice_summary", summary)
                dpg.set_value("info_text", summary)
                self._set_status(
                    f"Slicing finished \u2014 "
                    f"{result.get('total_layers', '?')} layers in {elapsed:.1f}s"
                )
            except Exception as exc:
                dpg.set_value("slice_progress", 0.0)
                dpg.configure_item("slice_progress", overlay="Failed")
                dpg.set_value("slice_summary", f"ERROR: {exc}")
                self._set_status(f"Slice failed: {exc}")
            finally:
                self._slice_running = False
                dpg.configure_item(
                    "slice_btn", label="    Slice Now    ", enabled=True,
                )

        threading.Thread(target=_worker, daemon=True).start()

    # =====================================================================
    #  File dialog helpers
    # =====================================================================
    def _refresh_file_dialog(self) -> None:
        if dpg.does_item_exist(self._file_dialog_path_tag):
            dpg.set_value(self._file_dialog_path_tag, str(self._current_dir))
        if dpg.does_item_exist(self._file_dialog_status_tag):
            dpg.set_value(self._file_dialog_status_tag, f"Browsing {self._current_dir}")
        self._refresh_dir_panel()
        self._refresh_file_panel()

    def _refresh_dir_panel(self) -> None:
        if not dpg.does_item_exist(self._file_dialog_dir_tag):
            return
        self._clear_container(self._file_dialog_dir_tag)
        directories = self._list_directories(self._current_dir)
        if not directories:
            dpg.add_text("No folders", parent=self._file_dialog_dir_tag, color=C.TEXT_MEDIUM)
            return
        for entry in directories:
            btn = dpg.add_button(
                label=f"\U0001f4c1  {entry.name}",
                parent=self._file_dialog_dir_tag,
                callback=self._on_dir_selected,
                user_data=str(entry),
                width=-1,
            )
            dpg.bind_item_theme(btn, self._th_flat)

    def _refresh_file_panel(self) -> None:
        if not dpg.does_item_exist(self._file_dialog_file_tag):
            return
        self._clear_container(self._file_dialog_file_tag)
        files = self._list_files(self._current_dir)
        if not files:
            dpg.add_text("No supported files", parent=self._file_dialog_file_tag, color=C.TEXT_MEDIUM)
            return
        for sample in files:
            size_kb = sample.stat().st_size / 1024
            mod_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(sample.stat().st_mtime))
            with dpg.group(parent=self._file_dialog_file_tag):
                file_btn = dpg.add_button(
                    label=f"\U0001f4e6  {sample.name}",
                    width=-1,
                    height=34,
                    callback=self._load_asset_file,
                    user_data=str(sample),
                )
                dpg.bind_item_theme(file_btn, self._th_flat)
                with dpg.tooltip(file_btn):
                    dpg.add_text(str(sample), color=C.TOOLTIP_TEXT)
                    dpg.add_text(f"Size: {size_kb:.1f} KB", color=C.TOOLTIP_TEXT)
                    dpg.add_text(f"Modified: {mod_time}", color=C.TOOLTIP_TEXT)
                dpg.add_text(f"Size: {size_kb:.1f} KB  \u00b7  Modified: {mod_time}", color=C.TEXT_MEDIUM)
                dpg.add_separator()

    def _clear_container(self, tag: str) -> None:
        if not dpg.does_item_exist(tag):
            return
        children = dpg.get_item_children(tag)
        if not children:
            return
        # DPG returns (slot_count, [child_ids])
        child_list = children[1] if isinstance(children, tuple) and len(children) > 1 else []
        if not child_list:
            return
        for child in child_list:
            if dpg.does_item_exist(child):
                dpg.delete_item(child)

    def _list_directories(self, root: Path) -> list[Path]:
        dirs = []
        try:
            for item in root.iterdir():
                if item.is_dir():
                    dirs.append(item)
        except PermissionError:
            return []
        return sorted(dirs, key=lambda p: p.name.lower())[:30]

    def _list_files(self, root: Path) -> list[Path]:
        allowed = {".stl", ".3mf", ".obj", ".amf"}
        files = []
        try:
            for item in root.iterdir():
                if item.is_file() and item.suffix.lower() in allowed:
                    files.append(item)
        except PermissionError:
            return []
        return sorted(files, key=lambda p: p.name.lower())[:32]

    def _navigate_to(self, target: Path, record: bool = True) -> None:
        target = target.expanduser()
        if not target.exists() or not target.is_dir():
            self._set_status(f"Cannot access {target}")
            return
        self._current_dir = target
        if record:
            self._record_history(target)
        self._refresh_file_dialog()

    def _record_history(self, target: Path) -> None:
        if self._nav_history and self._nav_history[self._nav_index] == target:
            return
        self._nav_history = self._nav_history[: self._nav_index + 1]
        self._nav_history.append(target)
        self._nav_index = len(self._nav_history) - 1

    def _navigate_history(self, delta: int) -> None:
        idx = self._nav_index + delta
        if idx < 0 or idx >= len(self._nav_history):
            return
        self._nav_index = idx
        self._current_dir = self._nav_history[idx]
        self._refresh_file_dialog()

    def _cmd_enter_path(self, sender=None, app_data=None, user_data=None) -> None:
        text = dpg.get_value(self._file_dialog_path_tag)
        if not text:
            return
        path = Path(text)
        self._navigate_to(path)

    def _cmd_navigate_up(self, sender=None, app_data=None, user_data=None) -> None:
        parent = self._current_dir.parent
        if parent and parent != self._current_dir:
            self._navigate_to(parent)

    def _on_dir_selected(self, sender, app_data, user_data) -> None:
        self._navigate_to(Path(user_data))

    def _on_quick_link_click(self, sender, app_data, user_data) -> None:
        self._navigate_to(Path(user_data))

    def _load_asset_file(self, sender, app_data, user_data) -> None:
        file_path = Path(user_data)
        if not file_path.exists():
            self._set_status(f"File removed: {file_path.name}")
            return
        self._set_status(f"Loading {file_path.name} ...")
        try:
            name, mesh = self.loader.load(str(file_path))
        except AssetLoadError as exc:
            self._set_status(f"Load error: {exc}")
            dpg.set_value("info_text", str(exc))
            return

        self.scene.add_mesh(name, mesh)
        info = (
            f"Loaded: {name}\n"
            f"Vertices : {mesh.vertices.shape[0]:,}\n"
            f"Faces    : {mesh.faces.shape[0]:,}\n"
            f"Size     : {mesh.extents.round(2)} mm"
        )
        dpg.set_value("info_text", info)
        self._set_status(
            f"Imported {name} ({mesh.faces.shape[0]:,} triangles)"
        )
        self._refresh_all()

    def _quick_links(self) -> list[tuple[str, Path]]:
        home = Path.home()
        links = []
        candidates = [
            ("Home", home),
            ("Desktop", home / "Desktop"),
            ("Documents", home / "Documents"),
            ("Downloads", home / "Downloads"),
        ]
        for label, path in candidates:
            if path.exists():
                links.append((label, path))
        if os.name == "nt":
            roots = [Path(f"{chr(letter)}:/") for letter in range(67, 70)]
            links.extend((f"Drive {root.drive}", root) for root in roots if root.exists())
        return links

    # =====================================================================
    #  Sidebar sync
    # =====================================================================
    def _on_object_list_select(self, sender, app_data) -> None:
        label = app_data
        for obj in self.scene.objects:
            if f"[{obj.uid}] {obj.name}" == label:
                self.scene.select(obj.uid)
                self._refresh_sidebar()
                self.viewport.rebuild_scene()
                return

    def _on_transform_change(self, sender=None, app_data=None) -> None:
        obj = self.scene.selected_object
        if obj is None:
            return
        self.scene.set_transform(
            obj.uid,
            translation=np.array(dpg.get_value("tf_pos"), dtype=np.float64),
            rotation_deg=np.array(dpg.get_value("tf_rot"), dtype=np.float64),
            scale=np.array(dpg.get_value("tf_scale"), dtype=np.float64),
        )
        self.viewport.rebuild_scene()

    def _refresh_sidebar(self) -> None:
        items = [f"[{o.uid}] {o.name}" for o in self.scene.objects]
        dpg.configure_item("object_list", items=items)

        obj = self.scene.selected_object
        if obj:
            dpg.set_value("tf_pos",   list(obj.transform.translation))
            dpg.set_value("tf_rot",   list(obj.transform.rotation_deg))
            dpg.set_value("tf_scale", list(obj.transform.scale))
        else:
            dpg.set_value("tf_pos",   [0, 0, 0])
            dpg.set_value("tf_rot",   [0, 0, 0])
            dpg.set_value("tf_scale", [1, 1, 1])

    def _refresh_all(self) -> None:
        self._refresh_sidebar()
        self.viewport.rebuild_scene()
        self._update_counters()

    # =====================================================================
    #  Status / counters
    # =====================================================================
    def _set_status(self, msg: str) -> None:
        if not dpg.does_item_exist("status_text"):
            return
        plate = self.scene.build_plate
        txt = (
            f"{msg}   \u00b7   "
            f"Objects: {self.scene.object_count}   \u00b7   "
            f"Build plate: \u00d8{plate.diameter_mm:.0f} mm"
        )
        dpg.set_value("status_text", txt)

    def _update_counters(self) -> None:
        total_tris = sum(o.mesh.faces.shape[0] for o in self.scene.objects)
        dpg.set_value("vp_obj_count", f"Objects: {self.scene.object_count}")
        dpg.set_value("vp_tri_count", f"Triangles: {total_tris:,}")

        # Update job specs (Cura JobSpecs.qml)
        obj = self.scene.selected_object
        if obj:
            dpg.set_value("job_filename", obj.name)
            dpg.set_value("job_faces", f"{obj.mesh.faces.shape[0]:,} faces")
        else:
            dpg.set_value("job_filename", "")
            dpg.set_value("job_faces", "")

        self._set_status("Ready")

    def _gather_slice_params(self) -> dict:
        return {
            "layer_thickness":       dpg.get_value("param_layer_thickness"),
            "laser_power":           dpg.get_value("param_laser_power"),
            "scan_speed":            dpg.get_value("param_scan_speed"),
            "hatch_spacing":         dpg.get_value("param_hatch_spacing"),
            "hatch_angle_increment": dpg.get_value("param_hatch_angle"),
            "contour_count":         dpg.get_value("param_contour_count"),
            "contour_offset":        dpg.get_value("param_contour_offset"),
            "island_scanning":       dpg.get_value("param_island"),
            "island_size":           dpg.get_value("param_island_size"),
        }
