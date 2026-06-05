import logging
import queue
import random
import threading

import qrcode
from PIL import Image, ImageTk

import tkinter as tk
import customtkinter as ctk

from managers.image_manager import ImageManager
from managers.config_manager import ConfigManager
from managers.voice_manager import VoiceManager, standard_recognize
from managers import sync_manager
from prompt import speech_to_prompt, STYLE_ORDER, STYLE_PRESETS, STYLE_PLAIN
from utils import fit_image

from gui_components import theme
from gui_components.general import BlockButton, StyleTile
from gui_components.history import GalleryItem
from gui_components.setting import SettingGroupLabel, SettingItem

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")

# Accent color per style tile on the NEW picker (UI-only; keyed by style id).
STYLE_TILE_COLORS = {
    "plain": "#b3b3b3",
    "realistic": "#8df0ad",
    "oil": "#ffcc66",
    "watercolor": "#76b5c5",
    "anime": "#ff8ab3",
    "popart": "#c792ea",
    "impressionist": "#82aaff",
    "pixel": "#f0a868",
    "minimalist": "#dcdcdc",
}


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
            try:
                self.add_item(record)
            except Exception as e:
                logger.warning(f"Skipping gallery item {record.uuid}: {e}")

    def add_item(self, record):
        item = GalleryItem(
            self, 
            self.width / 3 - 30, 
            (self.width / 3 - 30) * self.aspect_ratio, 
            record.uuid, 
            record.title, 
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

        self.image_uuid = None
        self.do_resize = True
        self.enable_chatgpt = True

        self.image_manager: ImageManager = None
        self.config_manager: ConfigManager = None

        self.upload_server = None

        # Cross-thread GUI updates (upload server / sync worker) are marshaled
        # onto the Tk main thread through this queue, drained by _drain_ui_queue.
        self._ui_queue = queue.Queue()

        # Auto-rotation (slideshow) state.
        self.rotation_enabled = False
        self.rotation_mode = "sequential"
        self.rotation_interval = 10
        self._rotation_after_id = None

        self.qr_image_buffer = None

        # Style chosen on the NEW picker for the next generation (see prompt.py).
        self._pending_style = STYLE_PLAIN

        self.voice_control = VoiceManager()
        self.voice_control.register_trigger_phrases(
            ["generate"], self.voice_callback_newimage,
            wait_start_callback=lambda: self.run_on_ui(self.show_listen_progressbar),
            wait_end_callback=lambda: self.run_on_ui(self.hide_listen_progressbar),
            modal=True
        )
        self.voice_control.start()

        # self.width, self.height = 720, 1280
        self.width, self.height = 1080, 1920
        # self.width, self.height = 1920, 1080
        
        self.image_height = self.height

        self.attributes("-fullscreen", True)
        self.config(cursor="none")

        self.title("AI Art Frame")
        self.geometry(f"{self.width}x{self.height}")
        self.resizable(False, False)
        # self.iconbitmap(os.path.join(os.path.dirname(__file__), '..', 'icon.ico'))
        self.protocol("WM_DELETE_WINDOW", self.exit)
        
        # canvas
        self.canvas = tk.Canvas(self, width=self.width, height=self.height, highlightthickness=0)
        self.canvas.bind("<Button-1>", self.show_overlay)
        # self.canvas.pack(fill="both", expand=True)
        self.canvas.place(relx=0.5, y=0, anchor="n", width=self.width, height=self.height)

        # picture
        self.picture_image_buffer = ImageTk.PhotoImage(Image.new("RGB", (self.width, self.image_height), (0, 0, 0)))
        self.picture_buffer = self.canvas.create_image(self.width // 2, self.image_height // 2, image=self.picture_image_buffer, anchor=tk.CENTER)

        # overlay: a single dim layer behind the menu, toggled by fade()
        self.overlay_active = False
        self.overlay_image_buffer = ImageTk.PhotoImage(
            Image.new("RGBA", (self.width, self.image_height), (0, 0, 0, 110))
        )
        self.overlay_item = self.canvas.create_image(0, 0, image=self.overlay_image_buffer, anchor="nw")
        self.canvas.itemconfig(self.overlay_item, state='hidden')

        # menu buttons
        self.menu_frame = tk.Frame(self, bg="#141414")
        self.reset_button = BlockButton(self, "new", "#8df0ad", theme.FONT_SIZE_BODY, command=self.button_command_newimage)
        self.upload_button = BlockButton(self, "upload", "#c792ea", theme.FONT_SIZE_BODY, command=self.button_command_upload)
        self.history_button = BlockButton(self, "history", "#76b5c5", theme.FONT_SIZE_BODY, command=self.show_history_frame)
        self.setting_button = BlockButton(self, "setting", "#ffcc66", theme.FONT_SIZE_BODY, command=self.show_setting_frame)
        self.sync_button = BlockButton(self, "sync", "#82aaff", theme.FONT_SIZE_BODY, command=self.button_command_sync)
        self.close_overlay_button = BlockButton(self, "close", "#b3b3b3", theme.FONT_SIZE_BODY, command=self.hide_overlay)
        self.exit_button = BlockButton(self, "exit", "#ff5447", theme.FONT_SIZE_BODY, command=self.exit)
        
        # listen status
        self.listen_frame = tk.Frame(self, bg="#141414")
        self.listen_text =  tk.StringVar()
        self.listen_status = tk.Label(self, textvariable=self.listen_text, bg="#141414", fg="#fff7e3", font=theme.font(theme.FONT_SIZE_CAPTION), wraplength=500, justify="center")
        self.listen_progressbar = ctk.CTkProgressBar(self, mode="indeterminate", indeterminate_speed=1.5, width=400, height=20, progress_color="#fff7e3", corner_radius=0)

        # history frame
        self.history_frame_width = int(self.width * 0.8)
        self.history_frame_height = int(self.height * 0.65)
        self.history_frame = None
        self.history_close_button = BlockButton(self, "close", "#b3b3b3", theme.FONT_SIZE_BODY, command=self.hide_history_frame)

        # setting frame
        self.setting_frame_width = min(760, self.width * 0.75)
        self.setting_frame_height = min(650, self.height * 0.75)
        self.setting_frame = None
        self.setting_changed = tk.BooleanVar(value=False)
        self.setting_save_button = BlockButton(self, "save", "#8df0ad", theme.FONT_SIZE_BODY, command=self.save_setting)
        self.setting_close_button = BlockButton(self, "cancel", "#ff5447", theme.FONT_SIZE_BODY, command=self.hide_setting_frame)

        # upload info overlay (URL + QR code)
        self.upload_frame = tk.Frame(self, bg="#141414")
        self.upload_qr_label = tk.Label(self, bg="#fffef5", bd=0, highlightthickness=0)
        self.upload_title_label = tk.Label(self, text="UPLOAD IMAGES", bg="#141414", fg="#fff7e3", font=theme.font(theme.FONT_SIZE_TITLE))
        self.upload_url_label = tk.Label(self, bg="#141414", fg="#8df0ad", font=theme.font(theme.FONT_SIZE_HEADING))
        self.upload_hint_label = tk.Label(self, bg="#141414", fg="#b9b29c", font=theme.font(theme.FONT_SIZE_CAPTION, "normal"), wraplength=560, justify="center")
        self.upload_close_button = BlockButton(self, "close", "#b3b3b3", theme.FONT_SIZE_BODY, command=self.hide_upload_info)

        # style picker (NEW -> choose a style): a borderless 3x3 grid of tiles
        # (Plain in the center) that fills its container edge-to-edge, with a
        # full-width cancel bar flush beneath it.
        self.style_tiles = []
        for sid in STYLE_ORDER:
            color = STYLE_TILE_COLORS.get(sid, "#b3b3b3")
            tile = StyleTile(
                self, STYLE_PRESETS[sid]["label"], color,
                command=lambda s=sid: self._on_style_selected(s),
            )
            self.style_tiles.append(tile)
        self.style_cancel_button = BlockButton(self, "cancel", "#ff5447", theme.FONT_SIZE_BODY, command=self.hide_style_picker)

        # Drain cross-thread UI work on the main loop.
        self.after(50, self._drain_ui_queue)

    def _drain_ui_queue(self):
        try:
            while True:
                fn = self._ui_queue.get_nowait()
                try:
                    fn()
                except Exception as e:
                    logger.error(f"UI task error: {e}")
        except queue.Empty:
            pass
        self.after(50, self._drain_ui_queue)

    def run_on_ui(self, fn):
        """Schedule `fn` to run on the Tk main thread (safe from any thread)."""
        self._ui_queue.put(fn)

    def set_upload_server(self, server):
        self.upload_server = server

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

        enable_chatgpt = self.config_manager.get_config_value("enable_chatgpt", do_raise=False)
        self.enable_chatgpt = True if enable_chatgpt is None else enable_chatgpt

        self.rotation_enabled = bool(self.config_manager.get_config_value("rotation_enabled", do_raise=False))
        self.rotation_mode = self.config_manager.get_config_value("rotation_mode", do_raise=False) or "sequential"
        self.rotation_interval = self.config_manager.get_config_value("rotation_interval", do_raise=False) or 10
        self._reschedule_rotation()

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
            label_font=theme.font(theme.FONT_SIZE_BODY),
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
            logger.warning(f"Could not open image {image_uuid}: {e}")
            image = Image.new("RGBA", (self.width, self.image_height), (0, 0, 0, 255))

        if self.do_resize:
            image = fit_image(image, self.width, self.image_height)
        self.picture_image_buffer = ImageTk.PhotoImage(image)
        self.canvas.itemconfig(self.picture_buffer, image=self.picture_image_buffer)
        self.image_uuid = image_uuid
        self.config_manager.set_config_value("current_image", image_uuid)

    def fade(self, direction):
        state = 'normal' if direction == "in" else 'hidden'
        self.canvas.itemconfig(self.overlay_item, state=state)
        self.canvas.update()

    def show_menu(self):
        menu_h = 680
        top = (self.height - menu_h) // 2
        self.menu_frame.place(relx=0.5, y=top, anchor=tk.N, width=600, height=menu_h)
        self.reset_button.place(relx=0.5, y=50 + top, anchor=tk.CENTER, width=600, height=80)
        self.upload_button.place(relx=0.5, y=140 + top, anchor=tk.CENTER, width=600, height=80)
        self.history_button.place(relx=0.5, y=230 + top, anchor=tk.CENTER, width=600, height=80)
        self.setting_button.place(relx=0.5, y=320 + top, anchor=tk.CENTER, width=600, height=80)
        self.sync_button.place(relx=0.5, y=410 + top, anchor=tk.CENTER, width=600, height=80)
        self.close_overlay_button.place(relx=0.5, y=500 + top, anchor=tk.CENTER, width=600, height=80)
        self.exit_button.place(relx=0.5, y=620 + top, anchor=tk.CENTER, width=600, height=80)

    def hide_menu(self):
        self.menu_frame.place_forget()
        self.reset_button.place_forget()
        self.upload_button.place_forget()
        self.history_button.place_forget()
        self.setting_button.place_forget()
        self.sync_button.place_forget()
        self.close_overlay_button.place_forget()
        self.exit_button.place_forget()

    def show_overlay(self, event=None):
        if not self.overlay_active:
            self.overlay_active = True
            self._cancel_rotation()
            self.fade("in")
            self.show_menu()

    def hide_overlay(self):
        if self.overlay_active:
            self.overlay_active = False
            self.hide_menu()
            self.fade("out")
            self._reschedule_rotation()

    def show_listen_status(self):
        self.listen_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=600, height=400)
        self.listen_status.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=600, height=400)
        self.listen_text.set("Please wait...")
        self.update()
    
    def show_listen_progressbar(self, y=0):
        # y=0 -> centered (listening). During generation the status box shows the
        # title/prompt text, so the caller passes y=165 to drop the bar near the
        # bottom of the 400px box instead of covering that text.
        self.listen_progressbar.place(relx=0.5, rely=0.5, y=y, anchor=tk.CENTER)
        self.update()
        self.listen_progressbar.start()
    
    def hide_listen_progressbar(self):
        self.listen_progressbar.place_forget()
        self.update()
        self.listen_progressbar.stop()

    def update_listen_status(self, text):
        self.listen_text.set(text)
        self.update()

    def hide_listen_status(self):
        self.listen_status.place_forget()
        self.listen_frame.place_forget()
        self.update()

    def _dismiss_status_overlay(self):
        self.hide_listen_progressbar()
        self.hide_listen_status()
        self.hide_overlay()

    # ---- image upload (web) ----
    def button_command_upload(self):
        self.hide_menu()
        if self.upload_server is None:
            self.show_listen_status()
            self.update_listen_status("Upload server is not running.")
            self.after(2500, self._dismiss_status_overlay)
            return
        self.show_upload_info(self.upload_server.get_url())

    def show_upload_info(self, url):
        try:
            qr = qrcode.make(url).convert("RGB").resize((460, 460), Image.NEAREST)
            self.qr_image_buffer = ImageTk.PhotoImage(qr)
            self.upload_qr_label.configure(image=self.qr_image_buffer)
        except Exception as e:
            logger.warning(f"QR generation failed: {e}")
            self.qr_image_buffer = None

        fw, fh = 640, 820
        top = (self.height - fh) // 2
        self.upload_frame.place(relx=0.5, y=top, anchor=tk.N, width=fw, height=fh)
        self.upload_title_label.place(relx=0.5, y=top + 40, anchor=tk.N)
        if self.qr_image_buffer is not None:
            self.upload_qr_label.place(relx=0.5, y=top + 100, anchor=tk.N, width=460, height=460)
        self.upload_url_label.configure(text=url)
        self.upload_url_label.place(relx=0.5, y=top + 590, anchor=tk.N)
        self.upload_hint_label.configure(text="Open this address on a phone on the same Wi-Fi, then pick images to send.")
        self.upload_hint_label.place(relx=0.5, y=top + 630, anchor=tk.N, width=560)
        self.upload_close_button.place(relx=0.5, y=top + 730, anchor=tk.N, width=300, height=70)
        self.update()

    def hide_upload_info(self):
        self.upload_frame.place_forget()
        self.upload_qr_label.place_forget()
        self.upload_title_label.place_forget()
        self.upload_url_label.place_forget()
        self.upload_hint_label.place_forget()
        self.upload_close_button.place_forget()
        self.show_menu()

    def handle_uploaded_image(self, pil_image, title):
        """Ingest an uploaded image. Called from the web-server worker thread."""
        record = self.image_manager.save_uploaded_image(pil_image, title)

        def _apply():
            self.history_frame.add_item(record)
            if not self.overlay_active:
                self.set_image(record.uuid)

        self.run_on_ui(_apply)

    # ---- code sync ----
    def button_command_sync(self):
        self.hide_menu()
        self.show_listen_status()
        self.update_listen_status("Starting sync...")
        threading.Thread(target=self._run_sync, daemon=True).start()

    def _run_sync(self):
        result = sync_manager.perform_sync(
            status=lambda msg: self.run_on_ui(lambda m=msg: self.update_listen_status(m))
        )

        def _finish():
            self.update_listen_status(result["message"])
            if result["ok"] and result["updated"]:
                self.after(1200, self._restart_app)
            else:
                self.after(3500, self._dismiss_sync)

        self.run_on_ui(_finish)

    def _dismiss_sync(self):
        self.hide_listen_status()
        self.hide_overlay()

    def _restart_app(self):
        try:
            self.voice_control.stop()
        except Exception:
            pass
        try:
            self.destroy()
        finally:
            sync_manager.restart_process()

    # ---- auto-rotation (slideshow) ----
    def _cancel_rotation(self):
        if self._rotation_after_id is not None:
            try:
                self.after_cancel(self._rotation_after_id)
            except Exception:
                pass
            self._rotation_after_id = None

    def _reschedule_rotation(self):
        self._cancel_rotation()
        if self.rotation_enabled:
            interval_ms = max(1, int(self.rotation_interval)) * 60 * 1000
            self._rotation_after_id = self.after(interval_ms, self._rotate)

    def _rotate(self):
        self._rotation_after_id = None
        if (self.rotation_enabled and not self.overlay_active
                and self.image_manager is not None and not self.image_manager.is_generating):
            records = self.image_manager.get_all_records()
            if len(records) >= 2:
                next_uuid = self._pick_next_image(records)
                if next_uuid:
                    self.set_image(next_uuid)
        self._reschedule_rotation()

    def _pick_next_image(self, records):
        uuids = [r.uuid for r in records]
        if self.rotation_mode == "shuffle":
            candidates = [u for u in uuids if u != self.image_uuid] or uuids
            return random.choice(candidates)
        ordered = list(reversed(uuids)) if self.rotation_mode == "newest" else uuids
        if self.image_uuid in ordered:
            idx = ordered.index(self.image_uuid)
            return ordered[(idx + 1) % len(ordered)]
        return ordered[0]

    def exit(self):
        self._cancel_rotation()
        self.voice_control.stop()
        self.destroy()

    def button_command_newimage(self):
        self.hide_menu()
        if not self.voice_control.available:
            self.show_listen_status()
            self.update_listen_status("Microphone not available.")
            self.after(2500, self._dismiss_status_overlay)
            return
        self.show_style_picker()

    # ---- style picker (NEW -> choose a style) ----
    def show_style_picker(self):
        # Borderless, gapless: 3x3 tiles fill the grid block, cancel spans its
        # full width directly beneath. Anchored on relx=0.5 (like the menu) so it
        # stays centered even when the fullscreen window is wider than self.width.
        tile = 240
        cancel_h = 96
        grid = 3 * tile
        half = grid // 2
        top = (self.height - (grid + cancel_h)) // 2

        for idx, t in enumerate(self.style_tiles):
            row, col = divmod(idx, 3)
            t.place(relx=0.5, x=-half + col * tile, y=top + row * tile, anchor=tk.NW, width=tile, height=tile)
        self.style_cancel_button.place(relx=0.5, x=-half, y=top + grid, anchor=tk.NW, width=grid, height=cancel_h)
        self.update()

    def _hide_style_widgets(self):
        for t in self.style_tiles:
            t.place_forget()
        self.style_cancel_button.place_forget()

    def hide_style_picker(self):
        # Cancel: dismiss the picker and return to the menu.
        self._hide_style_widgets()
        self.show_menu()

    def _on_style_selected(self, style_id):
        # Set before triggering so the worker thread reads the right style.
        self._pending_style = style_id
        self._hide_style_widgets()
        self.voice_control.trigger("generate")

    def voice_callback_newimage(self, speech, mic, rec):
        # Runs on the voice manager's background thread. Tk is NOT thread-safe
        # (touching it off the main thread crashes X11 on Linux), so every UI
        # call is marshaled onto the main thread via run_on_ui. The blocking
        # work (listen, prompt, generate) stays here, off the main loop.
        self.run_on_ui(self.show_listen_status)

        def _status_callback(msg):
            logger.info(msg)
            self.run_on_ui(lambda m=msg: self.update_listen_status(m))

        speech = standard_recognize(
            mic, rec, timeout=45,
            start_callback=lambda: self.run_on_ui(self.show_listen_progressbar),
            end_callback=lambda: self.run_on_ui(self.hide_listen_progressbar),
        )

        if not speech:
            _status_callback("No speech detected. Tap NEW and speak after the tone.")
            self.run_on_ui(lambda: self.after(3000, self._dismiss_status_overlay))
            return

        _status_callback(f"Detected speech: {speech}")
        speech = speech.strip(",.?!;:")

        if "title" in speech:
            speech_splited = speech.split("title")
            speech = " ".join(speech_splited[:-1]).strip(",.?!;:")
            title = speech_splited[-1].strip(",.?!;:")
        else:
            title = speech

        if "verbose" in speech or not self.enable_chatgpt:
            speech = speech.replace("verbose", "").strip(",.?!;:")
            _status_callback(f"Verbose mode: {speech}")
            prompt = speech
        else:
            style = self._pending_style
            style_label = STYLE_PRESETS.get(style, {}).get("label", "Plain")
            try:
                prompt = speech_to_prompt(speech, style=style)
                _status_callback(f"Style: {style_label}\nTitle: {title}\nGenerated prompt: {prompt}")
            except Exception as e:
                _status_callback(f"Could not generate prompt: {e}")
                prompt = speech

        # gpt-image-2 has no progress endpoint, so show an indeterminate spinner
        # while the single blocking generate() call runs. Drop it to the bottom of
        # the box (y=165) so it sits below the title/prompt text already shown.
        self.run_on_ui(lambda: self.show_listen_progressbar(y=165))
        try:
            record = self.image_manager.generate(title, prompt)
        except Exception as e:
            _status_callback(f"Generation failed: {e}")
            self.run_on_ui(self.hide_listen_progressbar)
            self.run_on_ui(lambda: self.after(3500, self._dismiss_status_overlay))
            return

        def _finish():
            self.hide_listen_progressbar()
            self.hide_listen_status()
            self.set_image(record.uuid)
            self.history_frame.add_item(record)
            self.hide_overlay()

        self.run_on_ui(_finish)

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
