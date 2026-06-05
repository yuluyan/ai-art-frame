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


def font(size=FONT_SIZE_BODY, weight="bold"):
    """A Tk / customtkinter font tuple drawn from the unified scale."""
    return (FONT_FAMILY, size, weight)
