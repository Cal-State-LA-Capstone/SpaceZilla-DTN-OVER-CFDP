import tkinter as tk

class TestUI:
    def __init__(self, backend):
        self.backend = backend

        self.root = tk.Tk()
        self.root.title("SpaceZilla")

        self.entry = tk.Entry(self.root)
        self.entry.pack(pady=20)

        btn = tk.Button(self.root, text="Send Message", command=self.on_button_click)
        btn.pack()

    def on_button_click(self):
        payload = self.entry.get()
        self.backend.sendMessage("ipn:1.2", payload)

    def run(self):
        self.root.mainloop()
