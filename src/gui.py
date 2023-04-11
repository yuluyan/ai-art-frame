import datetime
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import os
import speech_recognition as sr

from utils import resize_image, get_openai_key
from image_manager import ImageManager, ImageRecord
from voice import voice_to_prompt
from config_manager import ConfigManager

from gui_components.general import BlockButton
from gui_components.history import GalleryItem
from gui_components.setting import SettingGroupLabel, SettingItem

ctk.set_appearance_mode("dark")

class ScrollableGalleryFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, width, height, aspect_ratio, image_manager, display_command=None, delete_command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.width = width
        self.height = height
        self.aspect_ratio = aspect_ratio
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
            self.width / 3 - 30, 
            (self.width / 3 - 30) * self.aspect_ratio, 
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


class ScrollableSettingFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, width: int, height: int, config_manager: ConfigManager, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(width=width, height=height, fg_color="#141414", corner_radius=0, border_width=0)

        self.width = width
        self.height = height

        self.config_manager = config_manager

        self.has_change = False

        self.setting_items = {}
        self.update_setting()

    def _on_change(self):
        self.has_change = True

    def update_setting(self):
        self.setting_items = {}
        row_id = 0
        for config_group in self.config_manager.get_all_configs():
            setting_group_label = SettingGroupLabel(self, self.width, 50, config_group.label)
            setting_group_label.grid(row=row_id, column=0, pady=(35, 0))
            row_id += 1
            for config in config_group.items:
                self.setting_items[config.name] = SettingItem(self, self.width, 50, config, command=self._on_change)
                self.setting_items[config.name].set(config.value)
                self.setting_items[config.name].grid(row=row_id, column=0)
                row_id += 1

    def save_setting(self):
        if self.has_change:
            for key, item in self.setting_items.items():
                self.config_manager.set_config_value(key, item.get())
            self.has_change = False


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.width, self.height = 720, 1280
        # self.width, self.height = 1920, 1080
        
        self.header_height = int(self.height * (1 - 0.65) * 0.4)
        self.footer_height = int(self.height * (1 - 0.65) * 0.6)

        self.image_height = self.height - self.header_height - self.footer_height

        # self.attributes("-fullscreen", True)
        self.title("AI Art Frame")
        self.geometry(f"{self.width}x{self.height}")
        self.resizable(False, False)
        self.iconbitmap(os.path.join(os.path.dirname(__file__), '..', 'icon.ico'))

        self.canvas = tk.Canvas(self, width=self.width, height=self.height, highlightthickness=0)
        self.canvas.bind("<Button-1>", self.show_overlay)
        # self.canvas.pack(fill="both", expand=True)
        self.canvas.place(relx=0.5, y=self.header_height, anchor="n", width=self.width, height=self.height - self.header_height - self.footer_height)

        # header
        self.header = tk.Frame(self, width=self.width, height=self.header_height, bg="#fffef5")
        self.header.place(relx=0.5, y=0, anchor="n", width=self.width, height=self.header_height)
        self.header_title = tk.Label(self.header, text="", font=("Cormorant Garamond", 35), bg="#fffef5", padx=30)
        self.header_subtitle = tk.Label(self.header, text="", font=("Cormorant Garamond SemiBold", 15), bg="#fffef5", padx=30)
        if self.header_height > 0:
            self.header_title.place(relx=1, rely=0.4, anchor="e")
            self.header_subtitle.place(relx=1, rely=0.75, anchor="e")

        # footer
        self.footer = tk.Frame(self, width=self.width, height=self.footer_height, bg="#fffef5")
        self.footer.place(relx=0.5, y=self.height, anchor="s", width=self.width, height=self.footer_height)
        self.footer_title = tk.Label(self.footer, text="", font=("Cormorant Garamond", 15), bg="#fffef5", padx=30)
        self.footer_subtitle = tk.Label(self.footer,  text="", font=("Cormorant Garamond", 11), bg="#fffef5", padx=30, wraplength=self.width - 60, justify="left")
        if self.footer_height > 0:
            self.footer_title.place(relx=0, y=20, anchor="nw")
            self.footer_subtitle.place(relx=0, y=60, anchor="nw")

        self.picture_image_buffer = ImageTk.PhotoImage(Image.new("RGB", (self.width, self.image_height), (255, 254, 245)))
        self.picture_buffer = self.canvas.create_image(self.width // 2, self.image_height // 2, image=self.picture_image_buffer, anchor=tk.CENTER)

        self.overlay_active = False
        self.overlay_image_buffer = []
        self.overlay_buffer = []
        for alpha in range(0, 150, 15):
            image = Image.new("RGBA", (self.width, self.image_height), (0, 0, 0, alpha))
            self.overlay_image_buffer.append(ImageTk.PhotoImage(image))
            overlay_step = self.canvas.create_image(0, 0, image=self.overlay_image_buffer[-1], anchor="nw")
            self.canvas.itemconfig(overlay_step, state='hidden')
            self.overlay_buffer.append(overlay_step)
        self.image_uuid = None
        self.do_resize = True
        
        self.enable_chatgpt = True
        
        self.menu_frame = tk.Frame(self, bg="#141414")
        self.reset_button = BlockButton(self, "new", "#8df0ad", 15, command=self.generate_new_image)
        self.history_button = BlockButton(self, "history", "#76b5c5", 15, command=self.show_history_frame)
        self.setting_button = BlockButton(self, "setting", "#ffcc66", 15, command=self.show_setting_frame)
        self.close_overlay_button = BlockButton(self, "close", "#b3b3b3", 15, command=self.hide_overlay)
        self.exit_button = BlockButton(self, "exit", "#ff5447", 15, command=self.exit)
        
        self.listen_frame = tk.Frame(self, bg="#141414")
        self.listen_text =  tk.StringVar()
        self.listen_status = tk.Label(self, textvariable=self.listen_text, bg="#141414", fg="#8df0ad", font=("Consolas", 12, "bold"), wraplength=500, justify="center")
        self.listen_progressbar = ctk.CTkProgressBar(self, mode="indeterminate", indeterminate_speed=1.5, width=400, height=20, progress_color="#8df0ad")

        self.image_manager: ImageManager = None
        self.config_manager: ConfigManager = None

        self.history_frame_width = int(self.width * 0.8)
        self.history_frame_height = int(self.height * 0.65)
        self.history_frame = None
        self.history_close_button = BlockButton(self, "close", "#b3b3b3", 15, command=self.hide_history_frame)

        self.setting_frame_width = min(760, self.width * 0.75)
        self.setting_frame_height = min(650, self.height * 0.75)
        self.setting_frame = None
        self.setting_changed = tk.BooleanVar(value=False)
        self.setting_save_button = BlockButton(self, "save", "#8df0ad", 15, command=self.save_setting)
        self.setting_close_button = BlockButton(self, "cancel", "#ff5447", 15, command=self.hide_setting_frame)

    def configure_general_configs(self):
        do_resize = self.config_manager.get_config_value("do_resize", do_raise=False)
        if do_resize is not None:
            self.do_resize = do_resize

        current_image_uuid = self.config_manager.get_config_value("current_image", do_raise=False)
        if current_image_uuid:
            self.set_image(current_image_uuid)
        else:
            if last_record := self.image_manager.get_last_record():
                self.set_image(last_record.uuid)

        self.enable_chatgpt = self.config_manager.get_config_value("enable_chatgpt", do_raise=False)

    def set_managers(self, image_manager: ImageManager, config_manager: ConfigManager):
        self.image_manager = image_manager
        self.config_manager = config_manager
        self.image_manager.update_generator_config(self.config_manager)
        self.configure_general_configs()

        self.history_frame = ScrollableGalleryFrame(
            self, 
            self.history_frame_width, 
            self.history_frame_height,
            float(self.image_height) / float(self.width), 
            self.image_manager, 
            display_command=self.gallary_display_command,
            delete_command=self.gallary_delete_command,
            label_text=" ", 
            label_font=("Consolas", 15, "bold"), 
            label_fg_color="#141414",
            border_width=0,
            corner_radius=0,
        )

        self.setting_frame = ScrollableSettingFrame(
            self, 
            self.setting_frame_width, 
            self.setting_frame_height, 
            self.config_manager
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
        self.picture_image_buffer = ImageTk.PhotoImage(Image.new("RGBA", (self.width, self.image_height), (0, 0, 0, 255)))
        self.canvas.itemconfig(self.picture_buffer, image=self.picture_image_buffer)
        self.image_uuid = None

    def set_image(self, image_uuid):
        image_path = self.image_manager.uuid_to_path(image_uuid)
        try:
            image = Image.open(image_path)
        except Exception as e:
            print(e)
            image = Image.new("RGBA", (self.width, self.image_height), (0, 0, 0, 255))

        if self.do_resize:
            image = resize_image(image, self.width, self.image_height)
        self.picture_image_buffer = ImageTk.PhotoImage(image)
        self.canvas.itemconfig(self.picture_buffer, image=self.picture_image_buffer)
        self.image_uuid = image_uuid
        self.config_manager.set_config_value("current_image", image_uuid)

        record = self.image_manager.get_record(image_uuid)
        if record:
            self.header_title.configure(text=(record.title or "").title())
            self.header_subtitle.configure(text=(record.model or "").replace("_", " ").replace("-", " "))
            self.footer_title.configure(text=(record.date or datetime.date.today()).strftime("%B %d, %Y"))
            self.footer_subtitle.configure(text=record.prompt)

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

        title, prompt = voice_to_prompt(self.show_listen_progressbar, self.hide_listen_progressbar, self.update_listen_status, self.enable_chatgpt)
        
        record = self.image_manager.generate(title, prompt)
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
        
    def show_setting_frame(self):
        yoffset = 50
        border_offset = 4
        self.hide_menu()
        self.setting_frame.update_setting()
        self.setting_frame.place(relx=0.5, y=self.height // 2 - yoffset, anchor=tk.CENTER)
        self.setting_save_button.place(relx=0.5, y=self.setting_frame_height // 2 + self.height // 2 - yoffset + 30, anchor=tk.E, width=self.setting_frame_width // 2 + border_offset * 2, height=60)
        self.setting_close_button.place(relx=0.5, y=self.setting_frame_height // 2 + self.height // 2 - yoffset + 30, anchor=tk.W, width=self.setting_frame_width // 2 + border_offset * 2, height=60)
    
    def hide_setting_frame(self):
        self.setting_frame.place_forget()
        self.setting_save_button.place_forget()
        self.setting_close_button.place_forget()
        self.show_menu()

    def save_setting(self):
        self.setting_frame.save_setting()
        self.image_manager.update_generator_config(self.config_manager)
        self.configure_general_configs()
        self.hide_setting_frame()
        self.hide_menu()
        self.hide_overlay()


if __name__ == "__main__":
    import os
    from generator import OpenAIImageGenerator, LocalStableDiffusionImageGenerator
    from image_manager import ImageManager

    image_manager = ImageManager(os.path.join(os.path.dirname(__file__), '..', 'imgs'), LocalStableDiffusionImageGenerator())
    config_manager = ConfigManager()

    app = App()
    app.set_managers(image_manager, config_manager)
    app.mainloop()