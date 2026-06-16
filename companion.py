import os
import sys
import json
import webbrowser
import threading
import time
import socket
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import requests

# Chat SSE timeouts: (connect, read) — Ollama cold-start can exceed 15s.
CHAT_CONNECT_TIMEOUT = 5
CHAT_READ_TIMEOUT = 300
CHAT_TIMEOUT = (CHAT_CONNECT_TIMEOUT, CHAT_READ_TIMEOUT)

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

class DesktopCompanion:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cursor Co-pilot")
        
        # Hide from taskbar and make frameless
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", "white")
        
        # Get server port
        self.port = self.get_server_port()
        self.api_base = f"http://127.0.0.1:{self.port}"
        
        # Load and resize mascot PNG (true PNG converted from JPEG)
        self.mascot_path = ROOT / "static" / "mascot.png"
        if not self.mascot_path.exists():
            print(f"Error: Mascot image not found at {self.mascot_path}")
            sys.exit(1)
            
        self.mascot_raw = tk.PhotoImage(file=str(self.mascot_path))
        # mascot.png is 1024x1024, subsample(8) yields 128x128
        self.mascot_img = self.mascot_raw.subsample(8)
        
        # Screen dimensions and initial position (bottom right)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.w, self.h = 130, 130
        self.x = screen_w - self.w - 50
        self.y = screen_h - self.h - 120
        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        
        # Draw Mascot Canvas
        self.canvas = tk.Canvas(self.root, width=self.w, height=self.h, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Transparent background circle and image
        self.avatar = self.canvas.create_image(self.w//2, self.h//2, image=self.mascot_img)
        
        # Bindings for dragging
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<Double-Button-1>", self.open_dashboard)
        self.canvas.bind("<Button-3>", self.toggle_chat) # Right click to chat
        
        # Glow ring around mascot
        self.glow_ring = self.canvas.create_oval(
            self.w//2 - 62, self.h//2 - 62, 
            self.w//2 + 62, self.h//2 + 62, 
            outline="#f06432", width=2, state="hidden"
        )
        self.canvas.bind("<Enter>", self.on_hover)
        self.canvas.bind("<Leave>", self.on_leave)
        
        # Initialize speech bubble window
        self.bubble = None
        self.bubble_timeout = None
        
        # Initialize chat window
        self.chat_win = None
        self.chat_history = []
        
        # Greet on launch
        self.root.after(1000, self.project_greeting)

    def get_server_port(self):
        port_file = ROOT / ".cursor" / "port.json"
        if port_file.exists():
            try:
                return json.loads(port_file.read_text(encoding="utf-8"))["port"]
            except Exception:
                pass
        return 59712

    def start_drag(self, event):
        self._drag_start_x = event.x_root - self.root.winfo_x()
        self._drag_start_y = event.y_root - self.root.winfo_y()

    def drag(self, event):
        self.x = event.x_root - self._drag_start_x
        self.y = event.y_root - self._drag_start_y
        self.root.geometry(f"+{self.x}+{self.y}")
        self.update_sub_windows_position()

    def update_sub_windows_position(self):
        if self.bubble and self.bubble.winfo_exists():
            bx = self.x - 220
            by = self.y - 10
            self.bubble.geometry(f"200x110+{bx}+{by}")
        if self.chat_win and self.chat_win.winfo_exists():
            cx = self.x - 310
            cy = self.y + 70
            self.chat_win.geometry(f"300x50+{cx}+{cy}")

    def on_hover(self, event):
        self.canvas.itemconfig(self.glow_ring, state="normal")
        self.root.config(cursor="hand2")

    def on_leave(self, event):
        self.canvas.itemconfig(self.glow_ring, state="hidden")
        self.root.config(cursor="")

    def open_dashboard(self, event=None):
        webbrowser.open(self.api_base)
        self.speak("Opening full co-pilot control center!")

    def speak(self, text, duration_ms=6000):
        if self.bubble_timeout:
            self.root.after_cancel(self.bubble_timeout)
            
        if not self.bubble or not self.bubble.winfo_exists():
            self.bubble = tk.Toplevel(self.root)
            self.bubble.overrideredirect(True)
            self.bubble.wm_attributes("-topmost", True)
            self.bubble.config(bg="#141311")
            
            # Draw rounded panel border
            self.bubble_frame = tk.Frame(self.bubble, bg="#141311", highlightbackground="#262420", highlightthickness=1)
            self.bubble_frame.pack(fill="both", expand=True)
            
            self.bubble_label = tk.Label(
                self.bubble_frame, text="", bg="#141311", fg="#f5f3ef", 
                font=("Inter", 9), wraplength=180, justify="left"
            )
            self.bubble_label.pack(padx=10, pady=10, fill="both", expand=True)
            
        self.bubble_label.config(text=text)
        self.update_sub_windows_position()
        self.bubble.deiconify()
        
        self.bubble_timeout = self.root.after(duration_ms, self.hide_bubble)

    def hide_bubble(self):
        if self.bubble and self.bubble.winfo_exists():
            self.bubble.withdraw()

    def toggle_chat(self, event=None):
        if self.chat_win and self.chat_win.winfo_exists():
            self.chat_win.destroy()
            self.chat_win = None
        else:
            self.chat_win = tk.Toplevel(self.root)
            self.chat_win.overrideredirect(True)
            self.chat_win.wm_attributes("-topmost", True)
            self.chat_win.config(bg="#141311")
            
            frame = tk.Frame(self.chat_win, bg="#141311", highlightbackground="#f06432", highlightthickness=1)
            frame.pack(fill="both", expand=True)
            
            # Help Label
            lbl = tk.Label(frame, text="Ask Co-pilot:", bg="#141311", fg="#a9a59d", font=("Outfit", 8))
            lbl.pack(anchor="w", padx=8, pady=(4, 0))
            
            # Input Entry
            self.entry = tk.Entry(
                frame, bg="#1c1a16", fg="#f5f3ef", insertbackground="#f5f3ef",
                font=("Inter", 9), borderwidth=0, highlightthickness=0
            )
            self.entry.pack(fill="x", padx=8, pady=(0, 6))
            self.entry.focus_set()
            
            self.entry.bind("<Return>", self.send_chat)
            self.entry.bind("<Escape>", lambda e: self.toggle_chat())
            
            self.update_sub_windows_position()

    def send_chat(self, event):
        query = self.entry.get().strip()
        if not query:
            return
        
        self.entry.delete(0, tk.END)
        self.chat_history.append({"role": "user", "content": query})
        
        # Start streaming thread
        self.speak("Thinking...")
        threading.Thread(target=self.stream_chat_response, args=(query,), daemon=True).start()

    def stream_chat_response(self, query):
        url = f"{self.api_base}/api/chat"
        payload = {
            "message": query,
            "history": self.chat_history[:-1]
        }
        
        try:
            r = requests.post(url, json=payload, stream=True, timeout=CHAT_TIMEOUT)
            r.raise_for_status()
            
            full_response = ""
            error_message = ""
            current_event = ""
            for line in r.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8")
                if line_str.startswith("event: "):
                    current_event = line_str[7:].strip()
                    continue
                if line_str.startswith("data: "):
                    data_body = line_str[6:]
                    if current_event == "error":
                        try:
                            error_message = json.loads(data_body)
                        except json.JSONDecodeError:
                            error_message = data_body
                        continue
                    if current_event == "token":
                        try:
                            token = json.loads(data_body)
                            if isinstance(token, str):
                                full_response += token
                                self.root.after(0, self.update_bubble_text, full_response)
                        except json.JSONDecodeError:
                            pass
            
            if full_response:
                self.chat_history.append({"role": "assistant", "content": full_response})
            elif error_message:
                self.root.after(0, self.speak, str(error_message)[:500])
            else:
                self.root.after(0, self.speak, "I couldn't generate a response. Please check your backend connections.")
                
        except Exception as e:
            self.root.after(0, self.speak, f"Connection error: {e}")

    def update_bubble_text(self, text):
        self.speak(text, duration_ms=12000)

    def project_greeting(self):
        # Scan local project status via Flask API
        try:
            resp = requests.get(f"{self.api_base}/api/project/status", timeout=2)
            if resp.ok:
                data = resp.json()
                workspace = data.get("workspace", {})
                if workspace and not workspace.get("configured"):
                    self.speak(
                        "Set your active project in the dashboard so I scan the right codebase."
                    )
                    return

                profile = data.get("profile", {})
                langs = profile.get("languages", [])
                frameworks = profile.get("frameworks", [])
                
                # Check for notebook out-of-order cells
                notebooks = profile.get("notebooks", [])
                unhealthy = [n["filename"] for n in notebooks if n.get("execution_health") == "out_of_order"]
                
                if unhealthy:
                    msg = f"Alert! I detected out-of-order execution in notebook: {', '.join(unhealthy)}. This might cause state bugs!"
                elif langs:
                    msg = f"Co-pilot loaded! I see you are coding in {', '.join(langs[:3])}."
                    if frameworks:
                        msg += f" Using {', '.join(frameworks[:2])} framework."
                else:
                    msg = "Hi! I am your active co-pilot. Right-click me to ask a question, or double-click to open my dashboard!"
                    try:
                        br = requests.get(f"{self.api_base}/api/brainstorm?limit=1", timeout=10)
                        if br.ok:
                            ideas = br.json().get("suggestions") or []
                            if ideas:
                                msg = f"Idea: {ideas[0].get('title', '')}"
                    except Exception:
                        pass
                    
                self.speak(msg)
                return
        except Exception:
            pass
            
        self.speak("Hey there! I'm floating here ready to assist. Double-click me to open the web dashboard or right-click to chat!")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    # Check if another companion is running
    # Simple socket lock to prevent multiple widgets running
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.bind(("127.0.0.1", 52809))
    except socket.error:
        print("Companion is already running.")
        sys.exit(0)
        
    app = DesktopCompanion()
    app.run()
