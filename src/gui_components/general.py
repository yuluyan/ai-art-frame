import tkinter as tk

from gui_components import theme


class BlockButton(tk.Button):
    def __init__(self, master, text, bc, fs=theme.FONT_SIZE_BODY, command=None, **kwargs):
        self.bc = bc
        self.fc = "#141414"

        super().__init__(
            master,
            text=" ".join([c for c in text.upper()]),
            font=theme.font(fs),
            fg=self.bc, 
            bg=self.fc, 
            border=0, 
            activeforeground=self.fc, 
            activebackground=self.bc,
            highlightthickness=0,
            command=command, 
            **kwargs
        )
        
        self.bind("<Enter>", self._button_enter)
        self.bind("<Leave>", self._button_leave)

    def _button_enter(self, e):
        self["background"] = self.bc
        self["foreground"] = self.fc

    def _button_leave(self, e):
        self["background"] = self.fc
        self["foreground"] = self.bc


class StyleTile(tk.Button):
    """Square, tappable tile for the NEW style picker.

    Like BlockButton it inverts colors on touch/hover, but it is sized in pixels
    (placed by the caller) and borderless, so a grid of tiles tiles its container
    edge-to-edge. The label is not letter-spaced, so multi-word style names wrap
    cleanly onto two lines.
    """

    def __init__(self, master, text, bc, command, **kwargs):
        self.bc = bc
        self.fc = "#141414"

        super().__init__(
            master,
            text=text.upper(),
            font=theme.font(theme.FONT_SIZE_BODY),
            fg=self.bc,
            bg=self.fc,
            border=0,
            activeforeground=self.fc,
            activebackground=self.bc,
            highlightthickness=0,
            wraplength=200,
            justify="center",
            command=command,
            **kwargs
        )

        self.bind("<Enter>", self._tile_enter)
        self.bind("<Leave>", self._tile_leave)

    def _tile_enter(self, e):
        self["background"] = self.bc
        self["foreground"] = self.fc

    def _tile_leave(self, e):
        self["background"] = self.fc
        self["foreground"] = self.bc
