import tkinter as tk
from PIL import Image, ImageTk
import os
import time
import threading
import speech_recognition as sr

from utils import resize_image, get_openai_key
from image_manager import ImageManager
from voice import voice_to_prompt


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.width = 1920
        self.height = 1080

        # self.attributes("-fullscreen", True)
        self.title("AI Art Frame")
        self.geometry(f"{self.width}x{self.height}")

        self.canvas = tk.Canvas(self, width=self.width, height=self.height)
        self.canvas.bind("<Button-1>", self.show_overlay)
        self.canvas.pack(fill="both", expand=True)
        
        self.picture_image_buffer = ImageTk.PhotoImage(Image.new("RGBA", (self.width, self.height), (0, 0, 0, 255)))
        self.picture_buffer = self.canvas.create_image(0, 0, image=self.picture_image_buffer, anchor="nw")

        self.overlay_active = False
        self.overlay_image_buffer = []
        self.overlay_buffer = []
        for alpha in range(0, 150, 15):
            image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, alpha))
            self.overlay_image_buffer.append(ImageTk.PhotoImage(image))
            overlay_step = self.canvas.create_image(0, 0, image=self.overlay_image_buffer[-1], anchor="nw")
            self.canvas.itemconfig(overlay_step, state='hidden')
            self.overlay_buffer.append(overlay_step)

        self.favorite_button = tk.Button(self, text="Favorite", bg="white", command=lambda: print("Favorite"))
        self.reset_button = tk.Button(self, text="Reset", bg="white", command=self.generate_new_image)
        self.setting_button = tk.Button(self, text="Setting", bg="white", command=lambda: print("Setting"))
        self.close_overlay_button = tk.Button(self, text="x", command=self.hide_overlay,
                                      borderwidth=0, relief="flat", 
                                      highlightthickness=0, overrelief="", padx=50, pady=50)
        self.exit_button = tk.Button(self, text="<-", command=self.exit,
                                      borderwidth=0, relief="flat", 
                                      highlightthickness=0, overrelief="", padx=50, pady=50)

        self.image_manager: ImageManager = None
    
    def set_image_manager(self, image_manager: ImageManager):
        self.image_manager = image_manager
        if last_record := self.image_manager.get_last_record():
            self.set_image(self.image_manager.uuid_to_path(last_record.uuid))

    def set_image(self, image_path, do_resize=True):
        image = Image.open(image_path)
        if do_resize:
            image = resize_image(image, self.width, self.height)
        self.picture_image_buffer = ImageTk.PhotoImage(image)
        self.canvas.itemconfig(self.picture_buffer, image=self.picture_image_buffer)

    def fade(self, dir):
        if dir == "in":
            for i in range(len(self.overlay_buffer)):
                if i > 0:
                    self.canvas.itemconfig(self.overlay_buffer[i - 1], state='hidden')
                self.canvas.itemconfig(self.overlay_buffer[i], state='normal')
                self.canvas.update()
        elif dir == "out":
            for i in range(len(self.overlay_buffer) - 1, -1, -1):
                if i < len(self.overlay_buffer) - 1:
                    self.canvas.itemconfig(self.overlay_buffer[i + 1], state='hidden')
                self.canvas.itemconfig(self.overlay_buffer[i], state='normal')
                self.canvas.update()

    def show_overlay(self, event=None):
        if not self.overlay_active:
            self.overlay_active = True
            self.fade("in")
            self.favorite_button.place(x=860, y=10)
            self.reset_button.place(x=860, y=50)
            self.setting_button.place(x=860, y=150)
            self.close_overlay_button.place(x=1800, y=10)
            self.exit_button.place(x=60, y=10)

    def hide_overlay(self):
        if self.overlay_active:
            self.overlay_active = False
            self.fade("out")
            self.favorite_button.place_forget()
            self.reset_button.place_forget()
            self.setting_button.place_forget()
            self.close_overlay_button.place_forget()
            self.exit_button.place_forget()

    def exit(self):
        self.destroy()

    def generate_new_image(self):
        prompt = voice_to_prompt()

        image_uuid = self.image_manager.generate(prompt)
        image_path = self.image_manager.uuid_to_path(image_uuid)
        self.set_image(image_path)
        self.hide_overlay()


if __name__ == "__main__":
    app = App()
    app.mainloop()
