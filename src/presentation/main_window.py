"""
main_window.py  --  Presentation Layer  (Cura 5.x-inspired)
=============================================================

Layout (mirrors Ultimaker Cura):
+------------------------------------------------------------------+
|  [Logo]   Machine v  |  Material v  |  Profile v      [?] [=]   |   <- Header Bar
+---+----------------------------------------------------------+---+
| T |                                                          | S |
| O |                                                          | E |
| O |              3D  VIEWPORT  (PyVista)                     | T |
| L |                                                          | T |
| B |                                                          | I |
| A |                                                          | N |
| R |                                                          | G |
|   |                                                          | S |
+---+----------------------------------------------------------+---+
|        Status Bar  .  objects . triangles . build plate          |
+------------------------------------------------------------------+

Left Toolbar : Open / Move / Scale / Rotate / Mirror / Dup / Del
Right Panel  : Collapsible sections for Object Info, Transform,
               Process Parameters, Advanced, Slice button
Central      : PyVista off-screen rendered into DPG dynamic texture
"""
from __future__ import annotations

import os
import time
import threading
from typing import Optional

import numpy as np
import dearpygui.dearpygui as dpg

from src.application.scene_manager import SceneManager
from src.application.slicer_service import SlicerService
from src.infrastructure.repositories.asset_loader import AssetLoader, AssetLoadError
from src.presentation.viewport_manager import ViewportManager
from src.presentation.theme import (
    C, Layout,
    apply_cura_theme,
    create_cta_button_theme,
    create_danger_button_theme,
    create_flat_button_theme,
    create_panel_header_theme,
    create_status_bar_theme,
)


class SlicerGUI:
    """
    Cura-style presentation layer for the PySLM slicer.
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
        self._th_cta = None
        self._th_danger = None
        self._th_flat = None
        self._th_header = None
        self._th_status = None

        # GUI state
        self._slice_running = False
        self._active_tool = "move"
        self._right_panel_visible = True
        self._slice_progress = 0.0

    # =====================================================================
    #  Entry point
    # =====================================================================
    def run(self) -> None:
        dpg.create_context()

        # --- Theme & fonts ---
        apply_cura_theme()
        self._th_cta    = create_cta_button_theme()
        self._th_danger  = create_danger_button_theme()
        self._th_flat    = create_flat_button_theme()
        self._th_header  = create_panel_header_theme()
        self._th_status  = create_status_bar_theme()

        # --- Texture ---
        self.viewport.register_texture()

        # --- UI ---
        self._build_main_window()
        self._build_file_dialog()
        self._register_handlers()
        self._register_keyboard_shortcuts()

        # --- Viewport ---
        dpg.create_viewport(
            title="PySLM Slicer",
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
    #  Main window construction
    # =====================================================================
    def _build_main_window(self) -> None:
        with dpg.window(tag="primary"):
            # ---------- Menu bar (must be direct child of window) ----------
            self._build_menu_bar()
            
            # ---------- Top header bar ----------
            self._build_header_bar()

            # ---------- Body: toolbar | viewport | settings ----------
            with dpg.group(horizontal=True, tag="body_group"):
                self._build_left_toolbar()
                self._build_viewport_area()
                self._build_right_panel()

            # ---------- Bottom status bar ----------
            self._build_status_bar()

    # -----------------------------------------------------------------
    #  MENU BAR (must be direct child of window)
    # -----------------------------------------------------------------
    def _build_menu_bar(self) -> None:
        with dpg.menu_bar(tag="main_menu"):
            with dpg.menu(label="File"):
                dpg.add_menu_item(
                    label="Open Model(s)...    Ctrl+O",
                    callback=self._cmd_import,
                )
                dpg.add_menu_item(label="Open Recent", enabled=False)
                dpg.add_separator()
                dpg.add_menu_item(label="Save Build File...", callback=self._cmd_save_build)
                dpg.add_separator()
                dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())

            with dpg.menu(label="Edit"):
                dpg.add_menu_item(label="Select All          Ctrl+A", callback=self._cmd_select_all)
                dpg.add_menu_item(label="Deselect All",                callback=self._cmd_deselect)
                dpg.add_separator()
                dpg.add_menu_item(label="Duplicate           Ctrl+D", callback=self._cmd_duplicate)
                dpg.add_menu_item(label="Delete              Del",     callback=self._cmd_delete)
                dpg.add_separator()
                dpg.add_menu_item(label="Clear Build Plate",           callback=self._cmd_clear_plate)

            with dpg.menu(label="View"):
                dpg.add_menu_item(label="Reset Camera        Home", callback=self._cmd_reset_camera)
                dpg.add_menu_item(label="Fit All             F",    callback=self._cmd_fit_all)
                dpg.add_separator()
                dpg.add_menu_item(label="Toggle Settings Panel",    callback=self._cmd_toggle_panel)

            with dpg.menu(label="Settings"):
                dpg.add_menu_item(label="Build Plate...", callback=self._cmd_show_plate_settings)
                dpg.add_menu_item(label="About",          callback=self._cmd_about)

    # -----------------------------------------------------------------
    #  HEADER BAR (combos and title)
    # -----------------------------------------------------------------
    def _build_header_bar(self) -> None:
        with dpg.child_window(
            height=Layout.HEADER_H, border=False,
            tag="header_bar", no_scrollbar=True,
        ):
            with dpg.group(horizontal=True):
                # Logo / title
                dpg.add_text("  PySLM Slicer", color=C.ACCENT)
                dpg.add_spacer(width=30)

                # Machine selector
                dpg.add_combo(
                    items=["EOS M290 (120mm)", "SLM 280 (280mm)", "Custom"],
                    default_value="EOS M290 (120mm)",
                    tag="machine_combo", width=180,
                    callback=self._on_machine_change,
                )
                dpg.add_spacer(width=16)

                # Material profile
                dpg.add_combo(
                    items=["Ti-6Al-4V", "316L Stainless", "AlSi10Mg", "IN718", "Custom"],
                    default_value="Ti-6Al-4V",
                    tag="material_combo", width=160,
                )
                dpg.add_spacer(width=16)

                # Quality profile
                dpg.add_combo(
                    items=["Fine (20 um)", "Normal (30 um)", "Draft (50 um)", "Custom"],
                    default_value="Normal (30 um)",
                    tag="profile_combo", width=160,
                    callback=self._on_profile_change,
                )

    # -----------------------------------------------------------------
    #  LEFT TOOLBAR  (Cura icon strip)
    # -----------------------------------------------------------------
    def _build_left_toolbar(self) -> None:
        with dpg.child_window(
            width=Layout.LEFT_TOOLBAR_W, border=False,
            tag="left_toolbar", no_scrollbar=True,
        ):
            dpg.add_spacer(height=8)
            self._toolbar_btn("open_btn",  "O", "Open File (Ctrl+O)", self._cmd_import)
            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=4)

            self._toolbar_btn("move_btn",  "+", "Move (G)",     lambda: self._set_tool("move"))
            self._toolbar_btn("scale_btn", "S", "Scale (S)",    lambda: self._set_tool("scale"))
            self._toolbar_btn("rot_btn",   "R", "Rotate (R)",   lambda: self._set_tool("rotate"))
            self._toolbar_btn("mir_btn",   "M", "Mirror",       lambda: self._set_tool("mirror"))

            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=4)

            self._toolbar_btn("dup_btn", "D", "Duplicate (Ctrl+D)", self._cmd_duplicate)
            self._toolbar_btn("del_btn", "X", "Delete (Del)",       self._cmd_delete, danger=True)

            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=4)

            self._toolbar_btn("fit_btn", "#", "Fit View (F)", self._cmd_fit_all)

    def _toolbar_btn(self, tag, label, tooltip_text, cb, danger=False):
        btn = dpg.add_button(label=f" {label} ", tag=tag, width=36, height=36, callback=cb)
        dpg.bind_item_theme(btn, self._th_danger if danger else self._th_flat)
        with dpg.tooltip(btn):
            dpg.add_text(tooltip_text)

    # -----------------------------------------------------------------
    #  CENTRAL VIEWPORT
    # -----------------------------------------------------------------
    def _build_viewport_area(self) -> None:
        with dpg.child_window(tag="viewport_area", border=False):
            dpg.add_image(
                self.viewport.texture_tag,
                tag="viewport_image",
            )
            dpg.add_spacer(height=4)
            with dpg.group(horizontal=True):
                dpg.add_text("Objects: 0",   tag="vp_obj_count", color=C.TEXT_SECONDARY)
                dpg.add_spacer(width=20)
                dpg.add_text("Triangles: 0", tag="vp_tri_count", color=C.TEXT_SECONDARY)

    # -----------------------------------------------------------------
    #  RIGHT SETTINGS PANEL
    # -----------------------------------------------------------------
    def _build_right_panel(self) -> None:
        with dpg.child_window(
            width=Layout.RIGHT_PANEL_W, tag="right_panel",
            border=True, no_scrollbar=False,
        ):
            # ---- Object Info ----
            hdr = dpg.add_collapsing_header(
                label="  Object Info", default_open=True, tag="sec_obj_info",
            )
            dpg.bind_item_theme(hdr, self._th_header)
            with dpg.group(parent=hdr):
                dpg.add_listbox(
                    items=[], num_items=5, tag="object_list",
                    callback=self._on_object_list_select, width=-1,
                )
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Import",   width=95, callback=self._cmd_import)
                    dpg.add_button(label="Duplicate", width=95, callback=self._cmd_duplicate)
                    b_del = dpg.add_button(label="Delete", width=95, callback=self._cmd_delete)
                    dpg.bind_item_theme(b_del, self._th_danger)
                dpg.add_spacer(height=4)
                dpg.add_text(
                    "", tag="info_text", color=C.TEXT_SECONDARY,
                    wrap=Layout.RIGHT_PANEL_W - 30,
                )

            dpg.add_spacer(height=6)

            # ---- Transform ----
            hdr2 = dpg.add_collapsing_header(
                label="  Transform", default_open=True, tag="sec_transform",
            )
            dpg.bind_item_theme(hdr2, self._th_header)
            with dpg.group(parent=hdr2):
                dpg.add_text("Position (mm)", color=C.TEXT_SECONDARY)
                dpg.add_input_floatx(
                    size=3, default_value=[0, 0, 0], tag="tf_pos",
                    callback=self._on_transform_change, on_enter=True, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Rotation (deg)", color=C.TEXT_SECONDARY)
                dpg.add_input_floatx(
                    size=3, default_value=[0, 0, 0], tag="tf_rot",
                    callback=self._on_transform_change, on_enter=True, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Scale", color=C.TEXT_SECONDARY)
                dpg.add_input_floatx(
                    size=3, default_value=[1, 1, 1], tag="tf_scale",
                    callback=self._on_transform_change, on_enter=True, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_button(
                    label="Center on Plate", width=-1,
                    callback=self._cmd_center_on_plate,
                )

            dpg.add_spacer(height=6)

            # ---- Process Parameters ----
            hdr3 = dpg.add_collapsing_header(
                label="  Process Parameters", default_open=True, tag="sec_params",
            )
            dpg.bind_item_theme(hdr3, self._th_header)
            with dpg.group(parent=hdr3):
                dpg.add_text("Layer Thickness (mm)", color=C.TEXT_SECONDARY)
                dpg.add_input_float(
                    default_value=0.030, tag="param_layer_thickness",
                    format="%.3f", step=0.005, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Laser Power (W)", color=C.TEXT_SECONDARY)
                dpg.add_input_float(
                    default_value=200.0, tag="param_laser_power",
                    step=10, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Scan Speed (mm/s)", color=C.TEXT_SECONDARY)
                dpg.add_input_float(
                    default_value=1000.0, tag="param_scan_speed",
                    step=50, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Hatch Spacing (mm)", color=C.TEXT_SECONDARY)
                dpg.add_input_float(
                    default_value=0.10, tag="param_hatch_spacing",
                    format="%.3f", step=0.01, width=-1,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Hatch Angle Increment (deg)", color=C.TEXT_SECONDARY)
                dpg.add_input_float(
                    default_value=67.0, tag="param_hatch_angle",
                    step=1, width=-1,
                )

            dpg.add_spacer(height=6)

            # ---- Advanced (collapsed) ----
            hdr4 = dpg.add_collapsing_header(
                label="  Advanced", default_open=False, tag="sec_advanced",
            )
            dpg.bind_item_theme(hdr4, self._th_header)
            with dpg.group(parent=hdr4):
                dpg.add_text("Contour Count", color=C.TEXT_SECONDARY)
                dpg.add_input_int(
                    default_value=1, tag="param_contour_count",
                    width=-1, min_value=0, max_value=10,
                )
                dpg.add_spacer(height=2)
                dpg.add_text("Contour Offset (mm)", color=C.TEXT_SECONDARY)
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
                dpg.add_text("Island Size (mm)", color=C.TEXT_SECONDARY)
                dpg.add_input_float(
                    default_value=5.0, tag="param_island_size",
                    step=1, width=-1,
                )

            dpg.add_spacer(height=10)

            # ---- Progress bar & Slice button ----
            dpg.add_progress_bar(
                default_value=0.0, tag="slice_progress",
                overlay="", width=-1,
            )
            dpg.add_spacer(height=4)
            slice_btn = dpg.add_button(
                label="    Slice Now    ", tag="slice_btn",
                width=-1, height=44, callback=self._cmd_slice,
            )
            dpg.bind_item_theme(slice_btn, self._th_cta)

            dpg.add_spacer(height=6)
            dpg.add_text(
                "", tag="slice_summary",
                wrap=Layout.RIGHT_PANEL_W - 30, color=C.TEXT_SECONDARY,
            )

    # -----------------------------------------------------------------
    #  STATUS BAR
    # -----------------------------------------------------------------
    def _build_status_bar(self) -> None:
        sb = dpg.add_child_window(
            height=Layout.STATUS_H, border=False,
            tag="status_bar_area", no_scrollbar=True,
        )
        dpg.bind_item_theme(sb, self._th_status)
        with dpg.group(horizontal=True, parent=sb):
            dpg.add_text("Ready", tag="status_text", color=C.TEXT_SECONDARY)

    # -----------------------------------------------------------------
    #  FILE DIALOG
    # -----------------------------------------------------------------
    def _build_file_dialog(self) -> None:
        with dpg.file_dialog(
            directory_selector=False, show=False,
            callback=self._on_file_selected,
            cancel_callback=lambda: None,
            tag="file_dialog", width=750, height=450,
        ):
            dpg.add_file_extension(".stl", color=(0, 255, 0, 255))
            dpg.add_file_extension(".3mf", color=(0, 200, 255, 255))
            dpg.add_file_extension(".obj", color=(255, 255, 0, 255))
            dpg.add_file_extension(".amf", color=(255, 128, 0, 255))
            dpg.add_file_extension("",     color=(180, 180, 180, 255))

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
        self.viewport.on_mouse_move(dpg.get_mouse_pos())

    def _mouse_wheel_cb(self, sender, app_data) -> None:
        if not self._is_over_viewport():
            return
        self.viewport.on_mouse_wheel(app_data)

    # =====================================================================
    #  COMMANDS
    # =====================================================================
    def _cmd_import(self, sender=None, app_data=None) -> None:
        dpg.show_item("file_dialog")

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
        self._set_status("Save Build File: not yet implemented")

    def _cmd_show_plate_settings(self, sender=None, app_data=None) -> None:
        if dpg.does_item_exist("plate_popup"):
            dpg.delete_item("plate_popup")
        with dpg.window(
            label="Build Plate Settings", modal=True,
            tag="plate_popup", width=380, height=220,
        ):
            dpg.add_text("Configure the build plate dimensions", color=C.TEXT_SECONDARY)
            dpg.add_spacer(height=6)
            dpg.add_text("Diameter (mm)", color=C.TEXT_SECONDARY)
            dpg.add_input_float(
                default_value=self.scene.build_plate.diameter_mm,
                tag="plate_dia", width=200,
            )
            dpg.add_text("Height (mm)", color=C.TEXT_SECONDARY)
            dpg.add_input_float(
                default_value=self.scene.build_plate.height_mm,
                tag="plate_h", width=200,
            )
            dpg.add_spacer(height=8)
            dpg.add_button(label="  Apply  ", callback=self._apply_plate_settings)

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
            tag="about_popup", width=420, height=220,
        ):
            dpg.add_text("PySLM Industrial Slicer", color=C.ACCENT)
            dpg.add_text("Version 0.1.0", color=C.TEXT_SECONDARY)
            dpg.add_spacer(height=6)
            dpg.add_text(
                "Clean Architecture  |  DDD  |  PySLM Engine",
                color=C.TEXT_SECONDARY,
            )
            dpg.add_text(
                "GUI: Dear PyGui  |  3D: PyVista (VTK)",
                color=C.TEXT_SECONDARY,
            )
            dpg.add_spacer(height=10)
            dpg.add_button(
                label="  Close  ",
                callback=lambda: dpg.delete_item("about_popup"),
            )

    # -- Tool selection --
    def _set_tool(self, tool: str) -> None:
        self._active_tool = tool
        self._set_status(f"Active tool: {tool.capitalize()}")
        mapping = {
            "move": "move_btn", "scale": "scale_btn",
            "rotate": "rot_btn", "mirror": "mir_btn",
        }
        for name, tag in mapping.items():
            if dpg.does_item_exist(tag):
                dpg.bind_item_theme(
                    tag, self._th_cta if name == tool else self._th_flat,
                )

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
    #  File dialog callback
    # =====================================================================
    def _on_file_selected(self, sender, app_data) -> None:
        selections = app_data.get("selections", {})
        if not selections:
            return

        for file_name, file_path in selections.items():
            self._set_status(f"Loading {os.path.basename(file_path)} ...")
            try:
                name, mesh = self.loader.load(file_path)
            except AssetLoadError as exc:
                self._set_status(f"Load error: {exc}")
                dpg.set_value("info_text", str(exc))
                continue

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
