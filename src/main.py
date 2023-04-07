from gui import App
from generator import OpenAIImageGenerator


def main():
    generator = OpenAIImageGenerator()
    app = App()
    app.set_generator(generator)
    app.mainloop()


if __name__ == "__main__":
    main()