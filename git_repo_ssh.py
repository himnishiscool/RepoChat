"""
git_chat_ssh.py

Chat client that uses a Git repo (via SSH + system git) as a message store.

Requirements:
    - Python 3
    - Git installed (in PATH)
    - Repo cloned locally
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
from tkinter import ttk, scrolledtext, messagebox

# --- CONFIG ---
REPO_DIR = os.path.expanduser("~/Desktop/RepoChat")
TEXT_FILE = os.path.join(REPO_DIR, "texts.txt")
AUTO_REFRESH_INTERVAL = 10  # seconds
MAX_RETRIES = 3
# ----------------

# --- Git helpers ---
def run_git_command(args, cwd=REPO_DIR):
    """Run a git command and return output (raises on error)."""
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
    return run_git_command(["pull", "--rebase"])

def git_commit_and_push(message):
    run_git_command(["add", TEXT_FILE])
    run_git_command(["commit", "-m", message])
    run_git_command(["push"])

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
