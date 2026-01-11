import ttkbootstrap as ttkb
from core import RegistryCleaner


def main():
    root = ttkb.Window(themename="flatly")
    RegistryCleaner(root)
    root.mainloop()


if __name__ == "__main__":
    main()
