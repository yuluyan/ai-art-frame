import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import os
import speech_recognition as sr

from utils import resize_image, get_openai_key
from image_manager import ImageManager, ImageRecord
from voice import voice_to_prompt
from config_manager import ConfigManager


ctk.set_appearance_mode("System")  # Modes: system (default), light, dark
ctk.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green


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


class ScrollableGalleryFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, width, height, image_manager, display_command=None, delete_command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.configure(width=width, height=height, fg_color="#141414")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self.display_command = display_command
        self.delete_command = delete_command
        self.item_list = []

        self.image_manager = image_manager
        for record in self.image_manager.get_all_records():
            self.add_item(record)

    def add_item(self, record):
        item = GalleryItem(
            self, 
            192*2, 
            108*2, 
            record.uuid, 
            record.prompt, 
            self.image_manager.uuid_to_path(record.uuid), 
            display_command=self.display_command, 
            delete_command=self.delete_command
        )

        cur_len = len(self.item_list)
        target_row, target_col = divmod(cur_len, 3)
        item.grid(row=target_row, column=target_col, columnspan=1, pady=(25, 25), padx=(15, 15))
        self.item_list.append(item)

    def remove_item(self, uuid):
        for it in self.item_list:
            if uuid == it.uuid:
                it.destroy()
                self.item_list.remove(it)
                break

        for i, it in enumerate(self.item_list):
            target_row, target_col = divmod(i, 3)
            it.grid(row=target_row, column=target_col, columnspan=1, pady=(25, 25), padx=(15, 15))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.width = 1920
        self.height = 1080

        # self.attributes("-fullscreen", True)
        self.title("AI Art Frame")
        self.geometry(f"{self.width}x{self.height}")
        self.resizable(False, False)

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
        self.image_uuid = None

        self.menu_frame = tk.Frame(self, bg="#141414")
        self.reset_button = self.overlay_button("new", "#8df0ad", "#141414", command=self.generate_new_image)
        self.history_button = self.overlay_button("history", "#76b5c5", "#141414", command=self.show_history_frame)
        self.setting_button = self.overlay_button("setting", "#ffcc66", "#141414", command=lambda: print("Setting"))
        self.close_overlay_button = self.overlay_button("close", "#b3b3b3", "#141414", command=self.hide_overlay)
        self.exit_button = self.overlay_button("exit", "#ff5447", "#141414", command=self.exit)
        
        self.listen_frame = tk.Frame(self, bg="#141414")
        self.listen_text =  tk.StringVar()
        self.listen_status = tk.Label(self, textvariable=self.listen_text, bg="#141414", fg="#8df0ad", font=("Consolas", 12, "bold"), wraplength=500, justify="center")
        self.listen_progressbar = ctk.CTkProgressBar(self, mode="indeterminate", indeterminate_speed=1.5, width=400, height=20, progress_color="#8df0ad")

        self.image_manager: ImageManager = None
        self.config_manager: ConfigManager = None

        self.history_frame_width = int(self.width * 0.618)
        self.history_frame_height = self.height - 300
        self.history_frame = None
        self.history_close_button = self.overlay_button("close", "#b3b3b3", "#141414", command=self.hide_history_frame)

    def overlay_button(self, text, bc, fc, command):
        text = " ".join([c for c in text.upper()])

        def _button_enter(e):
            button["background"] = bc
            button["foreground"] = fc

        def _button_leave(e):
            button["background"] = fc
            button["foreground"] = bc

        font = tk.font.Font(size=15, family="Consolas", weight="bold")
        button = tk.Button(self, text=text, font=font, fg=bc, bg=fc, border=0, activeforeground=fc, activebackground=bc, command=command)

        button.bind("<Enter>", _button_enter)
        button.bind("<Leave>", _button_leave)

        return button

    def configure_general_configs(self):
        current_image_uuid = self.config_manager.get_config("current_image")
        if current_image_uuid:
            self.set_image(current_image_uuid)
        else:
            if last_record := self.image_manager.get_last_record():
                self.set_image(last_record.uuid)
            
    def set_managers(self, image_manager: ImageManager, config_manager: ConfigManager):
        self.image_manager = image_manager
        self.config_manager = config_manager
        self.image_manager.update_generator_config(self.config_manager)
        self.configure_general_configs()

        self.history_frame = ScrollableGalleryFrame(
            self, 
            self.history_frame_width, 
            self.history_frame_height, 
            self.image_manager, 
            display_command=self.gallary_display_command,
            delete_command=self.gallary_delete_command,
            label_text=" ", 
            label_font=("Consolas", 15, "bold"), 
            label_fg_color="#141414",
            border_width=0,
            corner_radius=0,
        )
    
    def gallary_display_command(self, uuid):
        self.set_image(uuid)
        self.hide_history_frame()
        self.hide_overlay()
    
    def gallary_delete_command(self, uuid):
        self.image_manager.delete_record(uuid)
        all_records = self.image_manager.get_all_records()

        if len(all_records) == 0:
            self.set_empty_image()
        else:
            if uuid == self.image_uuid:
                self.set_image(self.image_manager.get_last_record().uuid)

        self.history_frame.remove_item(uuid)
    
    def set_empty_image(self):
        self.picture_image_buffer = ImageTk.PhotoImage(Image.new("RGBA", (self.width, self.height), (0, 0, 0, 255)))
        self.canvas.itemconfig(self.picture_buffer, image=self.picture_image_buffer)
        self.image_uuid = None

    def set_image(self, image_uuid, do_resize=True):
        image_path = self.image_manager.uuid_to_path(image_uuid)
        try:
            image = Image.open(image_path)
        except Exception as e:
            print(e)
            image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 255))
            
        if do_resize:
            image = resize_image(image, self.width, self.height)
        self.picture_image_buffer = ImageTk.PhotoImage(image)
        self.canvas.itemconfig(self.picture_buffer, image=self.picture_image_buffer)
        self.image_uuid = image_uuid
        self.config_manager.set_config("current_image", image_uuid)

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

    def show_menu(self):
        top = (self.height - 600) // 2
        self.menu_frame.place(relx=0.5, y=top, anchor=tk.N, width=600, height=600)
        self.reset_button.place(relx=0.5, y=50 + top, anchor=tk.CENTER, width = 600, height = 100)
        self.history_button.place(relx=0.5, y=150 + top, anchor=tk.CENTER, width = 600, height = 100)
        self.setting_button.place(relx=0.5, y=250 + top, anchor=tk.CENTER, width = 600, height = 100)
        self.close_overlay_button.place(relx=0.5, y=350 + top, anchor=tk.CENTER, width = 600, height = 100)
        self.exit_button.place(relx=0.5, y=550 + top, anchor=tk.CENTER, width = 600, height = 100)
        
    def hide_menu(self):
        self.menu_frame.place_forget()
        self.reset_button.place_forget()
        self.history_button.place_forget()
        self.setting_button.place_forget()
        self.close_overlay_button.place_forget()
        self.exit_button.place_forget()

    def show_overlay(self, event=None):
        if not self.overlay_active:
            self.overlay_active = True
            self.fade("in")
            self.show_menu()

    def hide_overlay(self):
        if self.overlay_active:
            self.overlay_active = False
            self.hide_menu()
            self.fade("out")

    def show_listen_status(self):
        self.listen_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=600, height=300)
        self.listen_status.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=600, height=300)
        self.listen_text.set("Please wait...")
        self.update()

    def show_listen_progressbar(self):
        # self.listen_progressbar.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.listen_text.set("Start speaking")
        self.update()
        # self.listen_progressbar.start()
    
    def hide_listen_progressbar(self):
        # self.listen_progressbar.place_forget()
        self.listen_text.set("Speech detected, recognizing...")
        self.update()
        # self.listen_progressbar.stop()

    def update_listen_status(self, text):
        self.listen_text.set(text)
        self.update()

    def hide_listen_status(self):
        self.listen_status.place_forget()
        self.listen_frame.place_forget()
        self.update()

    def exit(self):
        self.destroy()

    def generate_new_image(self):
        self.hide_menu()
        self.show_listen_status()

        prompt = voice_to_prompt(self.show_listen_progressbar, self.hide_listen_progressbar, self.update_listen_status)
        
        record = self.image_manager.generate(prompt)
        self.set_image(record.uuid)
        self.history_frame.add_item(record)

        self.hide_listen_status()
        self.hide_overlay()

    def show_history_frame(self):
        yoffset = 50
        border_offset = 8
        self.hide_menu()
        self.history_frame.place(relx=0.5, y=self.height // 2 - yoffset, anchor=tk.CENTER)
        self.history_close_button.place(relx=0.5, y=self.history_frame_height // 2 + self.height // 2 + border_offset - yoffset, anchor=tk.N, width=self.history_frame_width + border_offset * 2, height=60)
    
    def hide_history_frame(self):
        self.history_frame.place_forget()
        self.history_close_button.place_forget()
        self.show_menu()
        

if __name__ == "__main__":
    import os
    from gui import App
    from generator import OpenAIImageGenerator, LocalStableDiffusionImageGenerator
    from image_manager import ImageManager

    image_manager = ImageManager(os.path.join(os.path.dirname(__file__), '..', 'imgs'), LocalStableDiffusionImageGenerator())
    config_manager = ConfigManager()

    app = App()
    app.set_managers(image_manager, config_manager)
    app.mainloop()