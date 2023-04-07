import tkinter as tk
import os

import tkinter as tk

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Viewer")
        self.geometry("1920x1080")

        # Create the image canvas
        self.image_canvas = tk.Canvas(self, width=1920, height=1080)
        self.image_canvas.pack()

        # Draw the image
        self.image = tk.PhotoImage(file="C:\\Users\\yuluy\\Desktop\\ai-art-frame\\ai-art-frame\\src\\example.png")
        self.image_canvas.create_image(0, 0, anchor=tk.NW, image=self.image)

        # Bind the click event to show the overlay
        self.image_canvas.bind("<Button-1>", self.show_overlay)

        # Create the overlay frame
        self.overlay_frame = FadingFrame(self, bg="black", bd=1, relief=tk.RAISED)
        self.overlay_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Create the overlay buttons
        self.favorite_button = tk.Button(self.overlay_frame, text="Favorite", image=self.get_heart_icon(), compound=tk.LEFT)
        self.favorite_button.pack(side=tk.LEFT, padx=10)
        self.new_button = tk.Button(self.overlay_frame, text="New", compound=tk.LEFT)
        self.new_button.pack(side=tk.LEFT, padx=10)
        self.setting_button = tk.Button(self.overlay_frame, text="Setting", compound=tk.LEFT)
        self.setting_button.pack(side=tk.LEFT, padx=10)

        # Create the close button
        self.close_button = tk.Button(self.overlay_frame, text="X", font=("Arial", 12), bg="black", fg="white", bd=0, command=self.hide_overlay)
        self.close_button.place(relx=1.0, rely=0.0, anchor=tk.NE)

        # Hide the overlay initially
        self.hide_overlay()

    def show_overlay(self, event):
        # Show the overlay
        self.overlay_frame.lift()
        self.overlay_frame.update_idletasks()
        self.overlay_frame.place_forget()
        self.overlay_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.image_canvas.itemconfigure(self.image_canvas.find_all(), state="hidden")
        self.overlay_frame.update()
        self.overlay_frame.configure(bg="#000", opacity=0)
        self.overlay_frame.fade_in(0.5)

    def hide_overlay(self):
        # Hide the overlay
        self.overlay_frame.fade_out(0.5, callback=lambda: self.image_canvas.itemconfigure(self.image_canvas.find_all(), state="normal"))

    def get_heart_icon(self):
        # Create the heart icon
        heart_icon = tk.PhotoImage(width=24, height=24)
        heart_icon.put("#f00", (12, 12))
        heart_icon.put("#f00", (11, 11))
        heart_icon.put("#f00", (10, 10))
        heart_icon.put("#f00", (9, 9))
        heart_icon.put("#f00", (8, 8))
        heart_icon.put("#f00", (7, 7))
        heart_icon.put("#f00", (6, 6))
        heart_icon.put("#f00", (5, 5))
        heart_icon.put("#f00", (4, 4))
        heart_icon.put("#f00", (3, 3))
        heart_icon.put("#f00", (2, 2))
        heart_icon.put("#f00", (1, 1))
        heart_icon.put("#f00", (0, 0))
        return heart_icon

    def get_refresh_icon(self):
        # Create the refresh icon
        refresh_icon = tk.PhotoImage(width=24, height=24)
        refresh_icon.create_polygon(4, 4, 4, 20, 12, 16, 20, 20, 20, 4, fill="#00f")
        refresh_icon.create_polygon(8, 8, 8, 12, 16, 8, fill="#fff")
        refresh_icon.create_polygon(16, 16, 16, 12, 8, 16, fill="#fff")
        return refresh_icon

    def get_gear_icon(self):
        # Create the gear icon
        gear_icon = tk.PhotoImage(width=24, height=24)
        gear_icon.create_arc(4, 4, 20, 20, start=0, extent=270, fill="#aaa", width=2, style=tk.ARC)
        gear_icon.create_arc(6, 6, 18, 18, start=0, extent=270, fill="#ccc", width=2, style=tk.ARC)
        gear_icon.create_arc(8, 8, 16, 16, start=0, extent=270, fill="#eee", width=2, style=tk.ARC)
        gear_icon.create_polygon(14, 12, 18, 12, 16, 14, fill="#000")
        gear_icon.create_polygon(10, 12, 6, 12, 8, 14, fill="#000")
        gear_icon.create_polygon(12, 14, 12, 18, 10, 16, fill="#000")
        return gear_icon

class FadingFrame(tk.Frame):
    def fade_in(self, duration):
        self.fade(duration, 0, 1)

    def fade_out(self, duration, callback=None):
        self.fade(duration, 1, 0, callback=callback)

    def fade(self, duration, start_alpha, end_alpha, callback=None):
        steps = duration * 10
        delay = int(duration / steps * 1000)
        alpha_step = (end_alpha - start_alpha) / steps
        alpha = start_alpha
        for i in range(steps):
            alpha += alpha_step
            self.configure(opacity=alpha)
            self.update()
            self.after(delay)
        self.configure(opacity=end_alpha)
        self.update()
        if callback is not None:
            callback()

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
