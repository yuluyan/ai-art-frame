import tkinter as tk
from PIL import Image, ImageTk
import os
import time
import threading
import speech_recognition as sr

from utils import resize_image, get_openai_key


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.width = 1920
        self.height = 1080

        self.title("AI Art Frame")
        self.geometry(f"{self.width}x{self.height}")

        self.canvas = tk.Canvas(self, width=self.width, height=self.height)
        self.canvas.bind("<Button-1>", self.show_overlay)
        self.canvas.pack(fill="both", expand=True)
        
        self.image_buffer = None
        self.set_image(os.path.join(os.path.dirname(__file__), '..', 'imgs', 'art.png'))

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
        self.close_button = tk.Button(self, text="x", command=self.hide_overlay,
                                      borderwidth=0, relief="flat", 
                                      highlightthickness=0, overrelief="", padx=50, pady=50)

        self.image_generator = None
    
    def set_generator(self, generator):
        self.image_generator = generator

    def set_image(self, image_path, do_resize=True):
        image = Image.open(image_path)
        if do_resize:
            image = resize_image(image, self.width, self.height)
        self.image_buffer = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.image_buffer, anchor="nw")

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
            self.close_button.place(x=1800, y=10)

    def hide_overlay(self):
        if self.overlay_active:
            self.overlay_active = False
            self.fade("out")
            self.favorite_button.place_forget()
            self.reset_button.place_forget()
            self.setting_button.place_forget()
            self.close_button.place_forget()

    def generate_new_image(self):
        r = sr.Recognizer()
        r.pause_threshold = 1

        with sr.Microphone() as source:
            print("Say something!")
            audio = r.listen(source)
        
        try:
            speech = r.recognize_whisper_api(audio, api_key=get_openai_key())
            print(speech)
        except sr.RequestError as e:
            print(f"Could not request results from Whisper API: {e}")

        image_uuid = self.image_generator.generate(speech)
        image_path = os.path.join(os.path.dirname(__file__), '..', 'imgs', f"{image_uuid}.png")
        self.set_image(image_path)

if __name__ == "__main__":
    app = App()
    app.mainloop()
