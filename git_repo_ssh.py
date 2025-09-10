"""
git_chat_ssh.py

Chat client that uses a Git repo (via SSH + system git) as a message store.

Requirements:
    - Python 3
    - Git installed (in PATH)
    - Repo cloned locally (~/Desktop/RepoChat)
    - SSH keys set up with GitHub

Usage:
    python git_chat_ssh.py
"""

import os
import subprocess
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext

# --- CONFIG ---
REPO_DIR = os.path.expanduser("~/Desktop/RepoChat")
TEXT_FILE = os.path.join(REPO_DIR, "texts.txt")
AUTO_REFRESH_INTERVAL = 10  # seconds
MAX_RETRIES = 3

REMOTE_NAME = "origin"
REMOTE_BRANCH = "main"

# --- Git helpers ---
def run_git_command(args, cwd=REPO_DIR):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        text=True,
        capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git error: {result.stderr.strip()}")
    return result.stdout.strip()

def git_pull():
    """Pull latest changes from main/main with auto-upstream fix."""
    try:
        return run_git_command(["pull", REMOTE_NAME, REMOTE_BRANCH])
    except RuntimeError as e:
        if "refs/head" in str(e) or "no upstream" in str(e).lower():
            branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
            run_git_command(["branch", "--set-upstream-to", f"{REMOTE_NAME}/{REMOTE_BRANCH}", branch])
            return run_git_command(["pull", REMOTE_NAME, REMOTE_BRANCH])
        else:
            raise

def git_commit_and_push(message):
    run_git_command(["add", TEXT_FILE])
    run_git_command(["commit", "-m", message])
    run_git_command(["push", REMOTE_NAME, REMOTE_BRANCH])

# --- File helpers ---
def read_chat_file():
    if not os.path.exists(TEXT_FILE):
        return ""
    with open(TEXT_FILE, "r", encoding="utf-8") as f:
        return f.read()

def append_message(user, msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {user}: {msg}\n"
    with open(TEXT_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    return line

# --- Emoji picker ---
EMOJIS = (
    "😀😃😄😁😆😅😂🤣🥲☺️😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🥸🤩🥳😏😒😞😔😟😕🙁☹️"
    "😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕"
    "🤑🤠😈👿👹👺💀☠️👻👽👾🤖🎃😺😸😹😻😼😽🙀😿😾"
    "🐶🐱🐭🐹🐰🦊🐻🐼🐨🐯🦁🐮🐷🐸🐵🙈🙉🙊🐒🐔🐧🐦🐤🐣🐥🦆🦅🦉🦇🐺🐗🐴🦄🐝🐛🦋🐌🐞🐜🪲"
    "🍏🍎🍐🍊🍋🍌🍉🍇🍓🫐🥝🥭🍍🥥🥑🍆🥔🥕🌽🌶️🥒🥬🥦🧄🧅🍄🥜🌰🍞🥐🥖🥯🥞🧇"
    "🥩🍗🍖🥓🍔🍟🍕🌭🥪🌮🌯🥙🫔🥗🥘🥫🍝🍜🍲🍛🍣🍱🥟🦪🍤"
    "⚽🏀🏈⚾🥎🎾🏐🏉🥏🎱🪀🏓🏸🥅⛳🏹🎣🤿🥊🥋🎽🛹⛸️🛷🥌🎿⛷️🏂🪂🏋️‍♂️🏋️‍♀️🤼‍♂️🤼‍♀️🤸‍♂️🤸‍♀️"
    "🎯🎮🕹️🎲🧩🧸🪁🎻🎸🥁🎷🎺🎹🪕🎤🎧📯"
    "❤️🧡💛💚💙💜🖤🤍🤎💔❣️💕💞💓💗💖💘💝💟"
    "⭐🌟✨⚡🔥💥☄️💫🌈☀️🌤️⛅🌥️🌦️🌧️⛈️🌩️🌨️❄️☃️⛄🌬️💨🌪️🌫️"
)

def open_emoji_picker(entry_widget):
    """Open a scrollable emoji picker window."""
    picker = tk.Toplevel()
    picker.title("Emoji Picker")
    picker.geometry("400x300")

    canvas = tk.Canvas(picker)
    scrollbar = ttk.Scrollbar(picker, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0,0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Add emojis as buttons
    for i, em in enumerate(EMOJIS):
        btn = ttk.Button(scroll_frame, text=em, width=3)
        btn.grid(row=i//10, column=i%10, padx=2, pady=2)
        btn.config(command=lambda em=em: [entry_widget.insert(tk.END, em), picker.destroy()])

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# --- GUI ---
class GitChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GitHub SSH Chat")
        self.geometry("750x550")

        self._username = tk.StringVar(value="Anon")
        self._status_text = tk.StringVar(value="Ready")
        self._auto_refresh = tk.BooleanVar(value=True)
        self._current_content = ""

        self._build_ui()
        self._load_initial()

        self._stop_event = threading.Event()
        threading.Thread(target=self._auto_refresh_loop, daemon=True).start()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        ttk.Label(top, text="Name:").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self._username, width=18).pack(side=tk.LEFT, padx=(4, 10))

        ttk.Button(top, text="Refresh", command=self.refresh).pack(side=tk.LEFT)
        ttk.Checkbutton(top, text="Auto-refresh", variable=self._auto_refresh).pack(side=tk.LEFT, padx=(10,0))

        ttk.Label(top, textvariable=self._status_text).pack(side=tk.RIGHT, padx=8)

        self.chat_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, state="disabled", font=("Segoe UI", 10))
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))

        bottom = ttk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=8)

        self.entry = ttk.Entry(bottom)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda e: self.send())

        ttk.Button(bottom, text="Send", command=self.send).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(bottom, text="😊", command=lambda: open_emoji_picker(self.entry)).pack(side=tk.LEFT, padx=(6,0))

    def _set_status(self, msg):
        self._status_text.set(msg)

    def _set_chat_content(self, content):
        self.chat_area.config(state="normal")
        self.chat_area.delete(1.0, tk.END)
        self.chat_area.insert(tk.END, content)
        self.chat_area.config(state="disabled")
        self.chat_area.yview_moveto(1.0)

    def _load_initial(self):
        try:
            git_pull()
            content = read_chat_file()
            self._current_content = content
            self._set_chat_content(content)
            self._set_status("Loaded")
        except Exception as e:
            self._set_status(f"Init error: {e}")

    def refresh(self):
        def _do():
            try:
                git_pull()
                content = read_chat_file()
                self._current_content = content
                self._set_chat_content(content)
                self._set_status(f"Refreshed at {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                self._set_status(f"Refresh error: {e}")
        threading.Thread(target=_do, daemon=True).start()

    def send(self):
        msg = self.entry.get().strip()
        if not msg:
            return
        user = self._username.get().strip() or "Anon"
        line = append_message(user, msg)
        self.entry.delete(0, tk.END)

        def _do_send():
            for attempt in range(MAX_RETRIES):
                try:
                    git_commit_and_push(f"Message from {user} at {datetime.now().strftime('%H:%M:%S')}")
                    self._current_content += line
                    self._set_chat_content(self._current_content)
                    self._set_status("Sent ✓")
                    return
                except Exception as e:
                    self._set_status(f"Retry {attempt+1}/{MAX_RETRIES}: {e}")
                    time.sleep(2)
            self._set_status("Send failed after retries")
        threading.Thread(target=_do_send, daemon=True).start()

    def _auto_refresh_loop(self):
        while not self._stop_event.is_set():
            if self._auto_refresh.get():
                try:
                    git_pull()
                    content = read_chat_file()
                    if content != self._current_content:
                        self._current_content = content
                        self.after(0, lambda: self._set_chat_content(content))
                        self.after(0, lambda: self._set_status("Auto-updated"))
                except:
                    pass
            time.sleep(AUTO_REFRESH_INTERVAL)

    def on_quit(self):
        self._stop_event.set()
        self.destroy()

# --- main ---
if __name__ == "__main__":
    if not os.path.isdir(REPO_DIR):
        print(f"Error: Repo directory {REPO_DIR} not found. Clone your GitHub repo there first.")
        exit(1)
    app = GitChatApp()
    app.protocol("WM_DELETE_WINDOW", app.on_quit)
    app.mainloop()
