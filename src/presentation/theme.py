"""
theme.py  --  Presentation Layer
Exact Ultimaker Cura 5.x light theme for Dear PyGui.

Palette extracted from:
  resources/themes/cura-light/theme.json  (Ultimaker/Cura GitHub)

  - White / light-gray backgrounds
  - Dark navy header (#08073F → #19175B gradient)
  - Blue accent (#196EF0) for primary buttons and selection
  - Light borders, subtle rounded corners, generous spacing
"""
from __future__ import annotations
import dearpygui.dearpygui as dpg


# =========================================================================
#  Colour Palette  (R, G, B, A  -- 0-255)
#  Values taken directly from Cura cura-light/theme.json
# =========================================================================
class C:
    """Namespace for Cura colour tokens used across the UI."""

    # ---- Backgrounds ----
    BG_1           = (255, 255, 255, 255)    # background_1  main_background
    BG_2           = (243, 243, 243, 255)    # background_2  detail / setting_control
    BG_3           = (232, 240, 253, 255)    # background_3  highlight
    BG_4           = (3, 12, 66, 255)        # background_4  dark navy

    # ---- Header (dark navy / indigo) ----
    HEADER_BG      = (8, 7, 63, 255)        # main_window_header_background
    HEADER_BG_GRAD = (25, 23, 91, 255)      # main_window_header_background_gradient
    HEADER_BTN_ACTIVE_TXT   = (8, 7, 63, 255)
    HEADER_BTN_INACTIVE_TXT = (255, 255, 255, 255)
    HEADER_BTN_ACTIVE_BG    = (255, 255, 255, 255)
    HEADER_BTN_INACTIVE_BG  = (255, 255, 255, 0)
    HEADER_BTN_HOVERED_BG   = (117, 114, 159, 255)

    # ---- Accent / primary ----
    ACCENT         = (25, 110, 240, 255)     # accent_1 / primary_button
    ACCENT_HOVER   = (16, 70, 156, 255)      # accent_2 / primary_button_hover
    ACCENT_ACTIVE  = (16, 70, 156, 255)

    # ---- Secondary button ----
    SECONDARY_BG      = (255, 255, 255, 255)
    SECONDARY_HOVER   = (232, 240, 253, 255)
    SECONDARY_TXT     = (25, 110, 240, 255)
    SECONDARY_SHADOW  = (216, 216, 216, 255)

    # ---- Action button (white outlined) ----
    ACTION_BG         = (255, 255, 255, 255)
    ACTION_HOVER      = (232, 242, 252, 255)
    ACTION_DISABLED   = (245, 245, 245, 255)
    ACTION_SHADOW     = (223, 223, 223, 255)

    # ---- Danger / error ----
    DANGER         = (218, 30, 40, 255)      # um_red_5
    DANGER_HOVER   = (251, 232, 233, 255)    # um_red_1
    DANGER_DARK    = (59, 31, 33, 255)       # um_red_9

    # ---- Warning / success ----
    WARNING        = (253, 209, 58, 255)     # um_yellow_5
    SUCCESS        = (36, 162, 73, 255)      # um_green_5

    # ---- Text ----
    TEXT_DEFAULT   = (0, 14, 26, 255)        # text_default (near-black)
    TEXT_PRIMARY   = (25, 25, 25, 255)       # text
    TEXT_MEDIUM    = (128, 128, 128, 255)    # text_medium
    TEXT_LIGHTER   = (108, 108, 108, 255)    # text_lighter
    TEXT_SECONDARY = (128, 128, 128, 255)    # alias
    TEXT_INACTIVE  = (174, 174, 174, 255)    # text_inactive
    TEXT_DISABLED  = (180, 180, 180, 255)    # text_disabled
    TEXT_ON_ACCENT = (255, 255, 255, 255)    # primary_button_text
    TEXT_MUTED     = (174, 174, 174, 255)

    # ---- Borders & separators ----
    BORDER         = (212, 212, 212, 255)    # border_main
    BORDER_FIELD   = (180, 180, 180, 255)    # border_field
    LINING         = (192, 193, 194, 255)    # lining
    SEPARATOR      = (212, 212, 212, 255)
    THICK_LINING   = (180, 180, 180, 255)

    # ---- Toolbar ----
    TOOLBAR_BG         = (255, 255, 255, 255)   # toolbar_background
    TOOLBAR_BTN_HOVER  = (232, 242, 252, 255)   # toolbar_button_hover
    TOOLBAR_BTN_ACTIVE = (232, 242, 252, 255)   # toolbar_button_active

    # ---- Viewport / build plate ----
    VP_BG          = (250, 250, 250, 255)    # viewport_background
    BUILDPLATE     = (244, 244, 244, 255)    # buildplate
    BUILDPLATE_GRID      = (180, 180, 180, 255)  # buildplate_grid
    BUILDPLATE_GRID_MINOR = (228, 228, 228, 255)

    # ---- Icon ----
    ICON           = (8, 7, 63, 255)         # icon

    # ---- Scrollbar ----
    SCROLLBAR_BG   = (255, 255, 255, 255)
    SCROLLBAR_HANDLE       = (10, 8, 80, 255)
    SCROLLBAR_HANDLE_HOVER = (50, 130, 255, 255)

    # ---- Slider ----
    SLIDER_GROOVE  = (223, 223, 223, 255)
    SLIDER_HANDLE  = (8, 7, 63, 255)
    SLIDER_ACTIVE  = (50, 130, 255, 255)

    # ---- Setting controls ----
    SETTING_CONTROL        = (243, 243, 243, 255)
    SETTING_CONTROL_HL     = (232, 240, 253, 255)
    SETTING_CONTROL_BORDER = (199, 199, 199, 255)
    SETTING_CONTROL_TEXT   = (35, 35, 35, 255)
    SETTING_CATEGORY       = (255, 255, 255, 255)
    SETTING_CATEGORY_HOVER = (243, 243, 243, 255)

    # ---- Progress bar ----
    PROGRESS_BG    = (245, 245, 245, 255)
    PROGRESS_BAR   = (50, 130, 255, 255)

    # ---- Checkbox ----
    CHECKBOX_BORDER = (180, 180, 180, 255)
    CHECKBOX_MARK   = (0, 14, 26, 255)

    # ---- Tooltip ----
    TOOLTIP_BG     = (25, 25, 25, 245)
    TOOLTIP_TEXT   = (255, 255, 255, 255)

    # ---- Small button (view orientation) ----
    SMALL_BTN_TEXT = (102, 102, 102, 255)
    SMALL_BTN_TXT_HOVER = (8, 7, 63, 255)

    # ---- Expandable ----
    EXPANDABLE_ACTIVE = (240, 240, 240, 255)
    EXPANDABLE_HOVER  = (232, 242, 252, 255)

    # ---- Selection ----
    SEL_ROW        = (25, 110, 240, 50)
    MODEL_SEL      = (50, 130, 255, 255)     # model_selection_outline

    # ---- Axis colours ----
    X_AXIS         = (218, 30, 40, 255)
    Y_AXIS         = (25, 110, 240, 255)
    Z_AXIS         = (36, 162, 73, 255)

    # ---- Backward-compat aliases ----
    CTA            = ACCENT              # slice button uses accent blue
    CTA_HOVER      = ACCENT_HOVER
    CTA_ACTIVE     = ACCENT_ACTIVE


# =========================================================================
#  Layout constants
# =========================================================================
class Layout:
    WIN_W          = 1600
    WIN_H          = 950
    LEFT_TOOLBAR_W = 52         # icon-strip on the far left
    RIGHT_PANEL_W  = 340        # settings panel (Cura print-setup sidebar)
    HEADER_H       = 48         # main_window_header height
    MENUBAR_H      = 30         # thin application menu bar
    STATUS_H       = 28         # bottom status bar
    VP_W           = 1024
    VP_H           = 740
    ROUNDING       = 4          # Cura uses 0.25 * base ≈ 3-4px
    FRAME_PAD      = (8, 6)
    ITEM_SPACE     = (8, 6)
    INDENT         = 16
    ACTION_PANEL_W = 260        # bottom-right action panel width


# =========================================================================
#  Apply global theme  (Cura Light)
# =========================================================================
def apply_cura_theme() -> int:
    """Call AFTER dpg.create_context(). Returns the theme tag."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Window backgrounds  -- WHITE
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,       C.BG_1)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,        C.BG_1)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,        C.BG_1)
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg,      C.BG_2)

            # Borders -- light gray
            dpg.add_theme_color(dpg.mvThemeCol_Border,         C.LINING)
            dpg.add_theme_color(dpg.mvThemeCol_Separator,      C.LINING)

            # Text -- dark
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C.TEXT_PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled,   C.TEXT_DISABLED)

            # Frame (input fields, combo) -- BG_2 light gray
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,        C.BG_2)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, C.SETTING_CONTROL_HL)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive,  C.BG_3)

            # Button (default = primary blue)
            dpg.add_theme_color(dpg.mvThemeCol_Button,         C.ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C.ACCENT_ACTIVE)

            # Headers (collapsing) -- white, hover gray
            dpg.add_theme_color(dpg.mvThemeCol_Header,         C.BG_1)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,  C.BG_2)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,   C.EXPANDABLE_HOVER)

            # Tabs
            dpg.add_theme_color(dpg.mvThemeCol_Tab,            C.BG_2)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered,     C.EXPANDABLE_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive,      C.BG_1)

            # Scrollbar -- white bg, dark navy handle
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,    C.SCROLLBAR_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,  C.SCROLLBAR_HANDLE)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, C.SCROLLBAR_HANDLE_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive,  C.SLIDER_ACTIVE)

            # Title bar
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,        C.BG_2)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive,  C.BG_1)

            # Slider / drag -- dark navy handle
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,     C.SLIDER_HANDLE)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, C.SLIDER_ACTIVE)

            # Check / radio -- dark navy mark
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark,      C.CHECKBOX_MARK)

            # Nav highlight
            dpg.add_theme_color(dpg.mvThemeCol_NavHighlight,   C.ACCENT)

            # Progress bar
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram,  C.PROGRESS_BAR)

            # ----- Style vars -----
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,     Layout.ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,      Layout.ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,      3)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding,      Layout.ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding,  6)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding,       3)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding,        3)

            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   *Layout.FRAME_PAD)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,    *Layout.ITEM_SPACE)
            dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing,  Layout.INDENT)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize,  12)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize,  1)

    dpg.bind_theme(global_theme)
    return global_theme


# =========================================================================
#  Component-level themes  (call after apply_cura_theme)
# =========================================================================

def create_primary_button_theme() -> int:
    """Blue primary action button (Cura primary_button)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C.ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C.ACCENT_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C.TEXT_ON_ACCENT)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   16, 10)
    return t


# Backward-compat alias
create_cta_button_theme = create_primary_button_theme


def create_secondary_button_theme() -> int:
    """White outlined button (Cura secondary_button)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C.SECONDARY_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.SECONDARY_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C.BG_3)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C.SECONDARY_TXT)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   12, 8)
    return t


def create_danger_button_theme() -> int:
    """Red destructive action button (Cura error / um_red_5)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C.DANGER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  (190, 25, 35, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   (170, 20, 30, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text,           (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  4)
    return t


def create_flat_button_theme() -> int:
    """Transparent / toolbar button (Cura toolbar_button)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.TOOLBAR_BTN_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C.TOOLBAR_BTN_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C.ICON)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   6, 6)
    return t


def create_toolbar_active_theme() -> int:
    """Active/selected toolbar button (light blue bg)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C.TOOLBAR_BTN_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.TOOLBAR_BTN_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C.BG_3)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C.ICON)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   6, 6)
    return t


def create_panel_header_theme() -> int:
    """Collapsing section header (Cura setting_category white bg)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvCollapsingHeader):
            dpg.add_theme_color(dpg.mvThemeCol_Header,         C.SETTING_CATEGORY)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,  C.SETTING_CATEGORY_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,   C.EXPANDABLE_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C.TEXT_DEFAULT)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  3)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   10, 8)
    return t


def create_header_bar_theme() -> int:
    """Dark navy header bar (Cura main_window_header_background)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,  C.HEADER_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Text,     (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button,   C.HEADER_BTN_INACTIVE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C.HEADER_BTN_HOVERED_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,  C.HEADER_BTN_ACTIVE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Border,   (70, 66, 126, 200))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3)
    return t


def create_stage_active_theme() -> int:
    """Active stage tab button in header (white bg, dark navy text)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C.HEADER_BTN_ACTIVE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.HEADER_BTN_ACTIVE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C.HEADER_BTN_ACTIVE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C.HEADER_BTN_ACTIVE_TXT)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  3)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   14, 8)
    return t


def create_stage_inactive_theme() -> int:
    """Inactive stage tab button in header (transparent bg, white text)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C.HEADER_BTN_INACTIVE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.HEADER_BTN_HOVERED_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C.HEADER_BTN_ACTIVE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C.HEADER_BTN_INACTIVE_TXT)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  3)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   14, 8)
    return t


def create_view_btn_theme() -> int:
    """Small view-orientation button (Cura small_button)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C.BG_1)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C.BG_2)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C.EXPANDABLE_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C.SMALL_BTN_TEXT)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  3)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   8, 6)
    return t


def create_action_panel_theme() -> int:
    """Action panel area (white bg, thin border, Cura action panel)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,  C.BG_1)
            dpg.add_theme_color(dpg.mvThemeCol_Border,   C.LINING)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,  4)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
    return t


def create_status_bar_theme() -> int:
    """Bottom status bar (viewport_overlay color)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (246, 246, 246, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text,    C.TEXT_LIGHTER)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 4)
    return t


def create_viewport_area_theme() -> int:
    """Viewport container (Cura viewport_background)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, C.VP_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Border,  (0, 0, 0, 0))
    return t


def create_toolbar_panel_theme() -> int:
    """Left toolbar container (Cura toolbar_background = white)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, C.TOOLBAR_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Border,  C.LINING)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,  6)
    return t


def create_right_panel_theme() -> int:
    """Right print-setup sidebar (white bg, left border)."""
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, C.BG_1)
            dpg.add_theme_color(dpg.mvThemeCol_Border,  C.LINING)
    return t
