"""Central typography for the Tk UI.

A single, unified type scale so every label, button and input draws from the
same four semantic sizes instead of ad-hoc per-widget values. Change a size
here and it updates everywhere that role is used.
"""

FONT_FAMILY = "Consolas"

# Unified type scale (point sizes), smallest to largest.
FONT_SIZE_CAPTION = 14   # secondary text & compact buttons: gallery titles/buttons, status, hints
FONT_SIZE_BODY = 16      # default controls: menu buttons, style tiles, setting inputs
FONT_SIZE_HEADING = 20   # emphasis: setting names, upload URL
FONT_SIZE_TITLE = 24     # overlay titles & section headers

# Global UI scale. 1.0 on the frame (fullscreen); the PC `--windowed` debug mode
# sets this below 1.0 so the whole UI — pixel geometry (px) AND fonts (font) —
# shrinks uniformly. At 1.0 both helpers are the identity, so the frame is
# unaffected.
_SCALE = 1.0


def set_scale(scale):
    """Set the global UI scale. Call once at startup, before building widgets."""
    global _SCALE
    _SCALE = scale


def px(value):
    """Scale an absolute pixel measurement by the active UI scale."""
    return max(1, round(value * _SCALE))


def font(size=FONT_SIZE_BODY, weight="bold"):
    """A Tk / customtkinter font tuple drawn from the unified scale, scaled."""
    return (FONT_FAMILY, max(1, round(size * _SCALE)), weight)
