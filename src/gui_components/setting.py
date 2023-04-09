import typing

import tkinter as tk
import customtkinter as ctk


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class BaseSettingInput(ctk.CTkFrame):
    def __init__(self, master, width: int, height: int, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            width=width, 
            height=height, 
            fg_color="#141414", 
            corner_radius=0, 
            border_width=0
        )
    
    def get(self) -> typing.Any:
        return self.variable.get()

    def set(self, value: typing.Any) -> typing.Any:
        return self.variable.set(value)


class IntInput(BaseSettingInput):
    def __init__(self, master, width, height, min_value, max_value, step_size, command, **kwargs):
        super().__init__(master, width, height, **kwargs)

        self.min_value = min_value
        self.max_value = max_value

        self.variable = tk.IntVar(value=self.min_value)

        self.value_label = ctk.CTkLabel(
            self, 
            textvariable=self.variable, 
            width=50, 
            height=35, 
            font=("Consolas", 15, "bold"), 
            text_color="#fff7e3", 
            bg_color="#141414", 
            corner_radius=0, 
            justify="center"
        )

        self.slider = ctk.CTkSlider(
            self, 
            variable=self.variable,
            width=200, 
            height=20, 
            fg_color="#444444", 
            progress_color="#ffeabf", 
            button_color="#ffcc66",
            button_hover_color="#ffba30",
            corner_radius=0, 
            from_=self.min_value, 
            to=self.max_value, 
            number_of_steps=int((self.max_value - self.min_value) // step_size),
            command=command,
        )
        
        self.value_label.place(relx=0.2, rely=0.5, anchor="center")
        self.slider.place(relx=0.6, rely=0.5, anchor="center")


class FloatInput(BaseSettingInput):
    def __init__(self, master, width, height, min_value, max_value, step_size, command, **kwargs):
        super().__init__(master, width, height, **kwargs)

        self.min_value = min_value
        self.max_value = max_value

        self.variable = tk.DoubleVar(value=self.min_value)
        self.label_variable = tk.StringVar(value="{:.1f}".format(self.min_value))

        self.variable.trace_add("write", lambda *args: self.label_variable.set("{:.1f}".format(self.variable.get())))

        self.value_label = ctk.CTkLabel(
            self, 
            textvariable=self.label_variable, 
            width=50, 
            height=35, 
            font=("Consolas", 15, "bold"), 
            text_color="#fff7e3", 
            bg_color="#141414", 
            corner_radius=0, 
            justify="center"
        )

        self.slider = ctk.CTkSlider(
            self, 
            variable=self.variable,
            width=200, 
            height=20, 
            fg_color="#444444", 
            progress_color="#ffeabf", 
            button_color="#ffcc66",
            button_hover_color="#ffba30",
            corner_radius=0, 
            from_=self.min_value, 
            to=self.max_value,
            number_of_steps=int((self.max_value - self.min_value) // step_size),
            command=command,
        )

        self.value_label.place(relx=0.2, rely=0.5, anchor="center")
        self.slider.place(relx=0.6, rely=0.5, anchor="center")


class BoolInput(BaseSettingInput):
    def __init__(self, master, width, height, command, **kwargs):
        super().__init__(master, width, height, **kwargs)

        self.variable = tk.BooleanVar(value=False)
        self.checkbox_variable = tk.StringVar(value="OFF")
        self.checkbox_label = tk.StringVar(value="  OFF")

        self.variable.trace_add("write", lambda *args: self.checkbox_variable.set("ON" if self.variable.get() else "OFF"))
        self.checkbox_variable.trace_add("write", lambda *args: self.variable.set(self.checkbox_variable.get() == "ON"))
        self.checkbox_variable.trace_add("write", lambda *args: self.checkbox_label.set("  " + self.checkbox_variable.get()))

        self.checkbox = ctk.CTkCheckBox(
            self, 
            variable=self.checkbox_variable, 
            textvariable=self.checkbox_label,
            width=85,
            checkbox_width=30,
            checkbox_height=30,
            corner_radius=0,
            font=("Consolas", 15, "bold"),
            fg_color="#444444",
            hover_color="#ffba30",
            text_color="#fff7e3",
            onvalue="ON", 
            offvalue="OFF",
            command=command,
        )
        self.checkbox.place(relx=0.5, rely=0.5, anchor="center")


class StringInput(BaseSettingInput):
    def __init__(self, master, width, height, choices: typing.List[str], command, **kwargs):
        super().__init__(master, width, height, **kwargs)

        self.variable = tk.StringVar(value=choices[0])

        self.entry = ctk.CTkOptionMenu(
            self, 
            variable=self.variable, 
            values=choices,
            width=250, 
            height=35, 
            font=("Consolas", 15, "bold"), 
            dropdown_font=("Consolas", 15, "bold"),
            text_color="#fff7e3", 
            fg_color="#343434", 
            button_color="#ffcc66",
            button_hover_color="#ffba30",
            dropdown_fg_color="#141414",
            dropdown_hover_color="#ffba30",
            corner_radius=0,
            anchor="center",
            command=command,
        )
        self.entry.place(relx=0.5, rely=0.5, anchor="center")


class ReadonlyInput(BaseSettingInput):
    def __init__(self, master, width, height, value, command, **kwargs):
        super().__init__(master, width, height, **kwargs)

        self.variable = tk.StringVar(value=str(value))

        self.field = ctk.CTkEntry(
            self, 
            textvariable=self.variable, 
            state="disabled", 
            width=350,
            height=35,
            font=("Consolas", 15, "bold"), 
            text_color="#fff7e3", 
            fg_color="#343434",
            bg_color="#141414", 
            corner_radius=0,
            justify="center",
        )
        self.field.place(relx=0.5, rely=0.5, anchor="center")


class SettingItem(ctk.CTkFrame):
    def __init__(self, master, width, height, config_item, command, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(width=width, height=height, fg_color="#141414", corner_radius=0)

        self.label = ctk.CTkLabel(
            self, 
            text=config_item.label, 
            width=300, 
            font=("Consolas", 20, "bold"), 
            text_color="#fff7e3", 
            bg_color="#141414",
        )
        self.label.grid(row=0, column=0, in_=self, sticky="w", padx=(15, 15), pady=(15, 15))

        if config_item.editable:
            range = config_item.range
            if config_item.type == "int":
                if range is None:
                    range = (0, 100, 1)
                self.input = IntInput(self, 400, height, range[0], range[1], range[2], lambda *args: command())
            elif config_item.type == "float":
                if range is None:
                    range = (0, 10, 0.1)
                self.input = FloatInput(self, 400, height, range[0], range[1], range[2], lambda *args: command())
            elif config_item.type == "bool":
                self.input = BoolInput(self, 400, height, lambda *args: command())
            elif config_item.type == "str":
                if range is None:
                    range = ["None"]
                self.input = StringInput(self, 400, height, range, lambda *args: command())
            else:
                raise Exception(f"Unknown config type: {config_item.type}")
        else:
            self.input = ReadonlyInput(self, 400, height, config_item.value, lambda *args: command())

        self.input.grid(row=0, column=1, in_=self, sticky="nwse", padx=(15, 15), pady=(15, 15))

    def get(self):
        return self.input.get()

    def set(self, value: typing.Any):
        return self.input.set(value)


class SettingGroupLabel(ctk.CTkFrame):
    def __init__(self, master, width, height, text, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(width=width, height=height, fg_color="#141414", corner_radius=0, border_width=0)

        self.label = ctk.CTkLabel(
            self, 
            text=text, 
            width=width, 
            font=("Consolas", 25, "bold"), 
            text_color="#fff7e3", 
            bg_color="#141414"
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")
