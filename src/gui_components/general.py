import tkinter as tk

class BlockButton(tk.Button):
    def __init__(self, master, text, bc, fs, command, **kwargs):
        self.bc = bc
        self.fc = "#141414"

        super().__init__(
            master, 
            text=" ".join([c for c in text.upper()]), 
            font=tk.font.Font(size=fs, family="Consolas", weight="bold"), 
            fg=self.bc, 
            bg=self.fc, 
            border=0, 
            activeforeground=self.fc, 
            activebackground=self.bc, 
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