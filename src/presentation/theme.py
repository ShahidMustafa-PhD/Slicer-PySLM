"""
theme.py  --  Presentation Layer
Centralized Cura-inspired dark theme for Dear PyGui.

The palette mirrors Ultimaker Cura 5.x:
  - Dark charcoal background (#1F1F1F)
  - Sidebar panels slightly lighter (#2B2B2B)
  - Accent blue (#328CE4) for primary actions and selection
  - Warm orange (#FF9F1C) for the slice button CTA
  - Subtle borders, rounded corners, generous spacing
"""
from __future__ import annotations
import dearpygui.dearpygui as dpg


# =========================================================================
#  Colour Palette  (R, G, B, A  -- 0-255)
# =========================================================================
class C:
    """Namespace for the colour tokens used across the UI."""
    # Backgrounds
    BG_DARK        = (31, 31, 31, 255)       # #1F1F1F  main window
    BG_PANEL       = (43, 43, 43, 255)       # #2B2B2B  sidebars / cards
    BG_INPUT       = (55, 55, 55, 255)       # #373737  input fields
    BG_HEADER      = (38, 38, 38, 255)       # #262626  collapsing headers

    # Accent
    ACCENT         = (50, 140, 228, 255)     # #328CE4  primary blue
    ACCENT_HOVER   = (70, 160, 248, 255)
    ACCENT_ACTIVE  = (40, 120, 200, 255)

    # CTA (Slice button)
    CTA            = (255, 159, 28, 255)     # #FF9F1C  warm orange
    CTA_HOVER      = (255, 180, 70, 255)
    CTA_ACTIVE     = (220, 140, 20, 255)

    # Danger
    DANGER         = (220, 60, 60, 255)
    DANGER_HOVER   = (240, 80, 80, 255)

    # Text
    TEXT_PRIMARY   = (230, 230, 230, 255)
    TEXT_SECONDARY = (160, 160, 160, 255)
    TEXT_MUTED     = (110, 110, 110, 255)
    TEXT_ON_ACCENT = (255, 255, 255, 255)

    # Borders & separators
    BORDER         = (60, 60, 60, 255)
    SEPARATOR      = (55, 55, 55, 255)

    # Viewport
    VP_BG_TOP      = (30, 30, 35, 255)
    VP_BG_BOT      = (22, 22, 26, 255)

    # Misc
    SCROLLBAR      = (55, 55, 55, 180)
    SCROLLBAR_GRAB = (80, 80, 80, 200)
    TAB_ACTIVE     = (50, 140, 228, 255)
    TAB_INACTIVE   = (50, 50, 50, 255)
    TOOLTIP_BG     = (50, 50, 55, 245)

    # Object list highlights
    SEL_ROW        = (50, 140, 228, 80)


# =========================================================================
#  Layout constants
# =========================================================================
class Layout:
    WIN_W          = 1600
    WIN_H          = 950
    LEFT_TOOLBAR_W = 52         # icon-strip on the far left
    RIGHT_PANEL_W  = 340        # settings panel (Cura-style right side)
    HEADER_H       = 48         # top header bar height
    STATUS_H       = 28         # bottom status bar
    VP_W           = 1024
    VP_H           = 740
    ROUNDING       = 6          # corner rounding (px)
    FRAME_PAD      = (8, 6)     # frame padding (x, y)
    ITEM_SPACE     = (8, 6)     # item spacing
    INDENT         = 16


# =========================================================================
#  Apply global theme
# =========================================================================
def apply_cura_theme() -> int:
    """Call AFTER dpg.create_context(). Returns the theme tag."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Window
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,           C.BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,            C.BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,            C.BG_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg,          C.BG_HEADER)

            # Borders
            dpg.add_theme_color(dpg.mvThemeCol_Border,             C.BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_Separator,          C.SEPARATOR)

            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text,               C.TEXT_PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled,       C.TEXT_MUTED)

            # Frame (input fields, combo, etc.)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,            C.BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,     (65, 65, 65, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive,      (75, 75, 75, 255))

            # Button (default)
            dpg.add_theme_color(dpg.mvThemeCol_Button,             C.ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,      C.ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,       C.ACCENT_ACTIVE)

            # Headers (collapsing header, tree node)
            dpg.add_theme_color(dpg.mvThemeCol_Header,             C.BG_HEADER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,      (55, 55, 60, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,       C.ACCENT_ACTIVE)

            # Tabs
            dpg.add_theme_color(dpg.mvThemeCol_Tab,                C.TAB_INACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered,         C.ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive,          C.TAB_ACTIVE)

            # Scrollbar
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,        (30, 30, 30, 200))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,      C.SCROLLBAR_GRAB)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (100, 100, 100, 220))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive,  C.ACCENT)

            # Title bar
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,            C.BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive,      C.BG_HEADER)

            # Slider / drag
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,         C.ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive,   C.ACCENT_HOVER)

            # Check / radio
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark,          C.ACCENT)

            # Menu item hover
            dpg.add_theme_color(dpg.mvThemeCol_NavHighlight,       C.ACCENT)

            # Tooltip
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,            C.TOOLTIP_BG)

            # ----- Style vars -----
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,     Layout.ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,      Layout.ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,      4)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding,      Layout.ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding,  8)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding,       4)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding,        4)

            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,       *Layout.FRAME_PAD)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,        *Layout.ITEM_SPACE)
            dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing,      Layout.INDENT)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize,      14)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize,   0)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize,    1)

    dpg.bind_theme(global_theme)
    return global_theme


# =========================================================================
#  Component-level themes  (call after apply_cura_theme)
# =========================================================================
def create_cta_button_theme() -> int:
    """Orange call-to-action button (Slice Now)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C.CTA)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.CTA_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C.CTA_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   16, 10)
    return t


def create_danger_button_theme() -> int:
    """Red delete / destructive action button."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C.DANGER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.DANGER_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   (200, 50, 50, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  4)
    return t


def create_flat_button_theme() -> int:
    """Transparent background button for toolbar icons."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  (255, 255, 255, 30))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   (255, 255, 255, 50))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   6, 6)
    return t


def create_panel_header_theme() -> int:
    """Slightly brighter header for collapsing sections."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvCollapsingHeader):
            dpg.add_theme_color(dpg.mvThemeCol_Header,         (50, 50, 55, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,   (60, 60, 68, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,    C.ACCENT)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,   4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,    10, 8)
    return t


def create_status_bar_theme() -> int:
    """Bottom status bar with darker background."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (25, 25, 28, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text,    C.TEXT_SECONDARY)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 4)
    return t
