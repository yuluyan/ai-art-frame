from PIL import Image

import tkinter as tk
import customtkinter as ctk


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class GalleryItem(ctk.CTkFrame):
    def __init__(self, master, image_width, image_height, uuid: str, prompt: str, path, display_command, delete_command, **kwargs):
        super().__init__(master, **kwargs)
        self.image_height_percent = 70
        self.label_wrap_length = 90

        self.configure(width=image_width, height=int(image_height / (self.image_height_percent / 100.0)), fg_color="#141414")

        self.grid_rowconfigure(0, weight=15)
        self.grid_rowconfigure(1, weight=self.image_height_percent)
        self.grid_rowconfigure(2, weight=15)
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)

        self.uuid = uuid

        display_text = prompt
        for char in ["\n", "`", "'"]:
            display_text = display_text.replace(char, " ")
        if len(display_text) > self.label_wrap_length:
            display_text = display_text[:self.label_wrap_length - 3].strip() + "..."

        self.label = ctk.CTkLabel(
            self, 
            text=display_text, 
            justify="center", 
            wraplength=image_width - 20, 
            pady=2, width=image_width, 
            height=40, 
            fg_color="#141414", 
            text_color="#fff7e3", 
            font=("Consolas", 12, "bold")
        )
        self.image = ctk.CTkImage(Image.open(path), size=(image_width, image_height))

        self.display_command = display_command
        self.delete_command = delete_command
        self.display_button = self.overlay_button("display", "#8df0ad", "#141414", command=self.display)
        self.delete_button = self.overlay_button("del", "#ff5447", "#141414", command=self.delete)
        
        self.label.grid(row=0, column=0, columnspan=2, sticky="nsew")

        self.image_label = ctk.CTkLabel(self, image=self.image, text="")
        self.image_label.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 10))

        self.display_button.grid(row=2, column=0, sticky="nsew")
        self.delete_button.grid(row=2, column=1, sticky="nsew")

    def overlay_button(self, text, bc, fc, command):
        text = " ".join([c for c in text.upper()])

        def _button_enter(e):
            button["background"] = bc
            button["foreground"] = fc

        def _button_leave(e):
            button["background"] = fc
            button["foreground"] = bc

        font = tk.font.Font(size=12, family="Consolas", weight="bold")
        button = tk.Button(self, text=text, font=font, fg=bc, bg=fc, border=0, activeforeground=fc, activebackground=bc, command=command)

        button.bind("<Enter>", _button_enter)
        button.bind("<Leave>", _button_leave)

        return button

    def display(self):
        self.display_command(self.uuid)

    def delete(self):
        self.delete_command(self.uuid)
        