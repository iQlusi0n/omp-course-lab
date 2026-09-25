#!/usr/bin/env python3
"""Computer-use fixture: a one-button Tk window.

    python3 bin/gui-demo.py

Window title "Lab GUI Demo"; a label reading "Ready" and a button "Click me".
Clicking the button changes the label to "Clicked!". Requires the ``tkinter``
module (Debian/Ubuntu: ``apt install python3-tk``); without it the script
prints a message and exits 1.
"""

import sys

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError as e:  # pragma: no cover - depends on the machine
    print(f"tkinter is not available: {e}")
    sys.exit(1)


def main() -> int:
    root = tk.Tk()
    root.title("Lab GUI Demo")
    root.geometry("320x160")

    label = ttk.Label(root, text="Ready", font=("TkDefaultFont", 16))
    label.pack(pady=(30, 10))

    def on_click():
        label.config(text="Clicked!")

    button = ttk.Button(root, text="Click me", command=on_click)
    button.pack()

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
