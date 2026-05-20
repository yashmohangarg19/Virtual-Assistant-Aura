# ---------------- IMPORTS ----------------
import customtkinter as ctk
import threading
import speech_recognition as sr
import webbrowser
import pyttsx3
import torch
import pywhatkit
import os
import requests
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

try:
    import musicLibrary
except ImportError:
    class musicLibrary:
        music = {}


# ---------------- SETTINGS ----------------
AI_MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
WEATHER_API_KEY = "0742785315862a86e583ff087a1803d2"
DEFAULT_CITY = "Ghaziabad"

hf_pipe = None
running = False
is_ai_loading = False
current_theme_mode = "dark"

chat_sessions = []
session_counter = 1
thinking_labels = []
history_commands = []


# ---------------- SAFE UI HELPERS ----------------
def safe_config(widget, **kwargs):
    try:
        if widget and widget.winfo_exists():
            widget.after(0, lambda: widget.configure(**kwargs))
    except Exception as e:
        print("UI update error:", e)


def safe_clipboard(root, text):
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
    except Exception as e:
        print("Clipboard error:", e)


# ---------------- THEME HELPERS ----------------
def get_theme_colors():
    if current_theme_mode == "dark":
        return {
            "root_bg": "black",
            "sidebar_bg": "black",
            "main_bg": "black",
            "topbar_bg": "#111111",
            "input_wrap_bg": "#111111",
            "input_frame_bg": "#1a1a1a",
            "entry_bg": "#1a1a1a",
            "entry_text": "white",
            "primary_text": "white",
            "secondary_text": "#9ca3af",
            "status_text": "#93c5fd",
            "system_text": "#9ca3af",
            "assistant_bubble": "#2b2b2b",
            "assistant_name": "#d1d5db",
            "assistant_avatar": "#374151",
            "user_bubble": "#1f6aa5",
            "user_avatar": "#0f766e",
            "copy_btn": "#475569",
            "copy_hover": "#334155",
            "card_bg": "#1f2937",
            "quick_btn": "#374151",
            "quick_hover": "#1f2937",
            "note_text": "#6ee7b7",
            "history_bg": "#1a1a1a",
            "history_text": "white",
            "history_border": "#374151",
        }
    else:
        return {
            "root_bg": "white",
            "sidebar_bg": "white",
            "main_bg": "white",
            "topbar_bg": "#e5e5e5",
            "input_wrap_bg": "#e5e5e5",
            "input_frame_bg": "#f0f0f0",
            "entry_bg": "white",
            "entry_text": "black",
            "primary_text": "black",
            "secondary_text": "black",
            "status_text": "blue",
            "system_text": "#6b7280",
            "assistant_bubble": "#f1f1f1",
            "assistant_name": "black",
            "assistant_avatar": "#111827",
            "user_bubble": "#2563eb",
            "user_avatar": "#0f766e",
            "copy_btn": "#d1d5db",
            "copy_hover": "#9ca3af",
            "card_bg": "#f1f5f9",
            "quick_btn": "#e5e7eb",
            "quick_hover": "#d1d5db",
            "note_text": "green",
            "history_bg": "white",
            "history_text": "black",
            "history_border": "#d1d5db",
        }


def apply_theme_colors(
    root,
    sidebar,
    main_area,
    topbar,
    input_wrap,
    input_frame,
    command_entry,
    header,
    title,
    subtitle,
    chats_title,
    controls_title,
    cmd_history_title,
    quick_title,
    note,
    clock_label,
    status_label,
    history_box,
    history_panel,
    quick_buttons
):
    colors = get_theme_colors()

    root.configure(fg_color=colors["root_bg"])
    sidebar.configure(fg_color=colors["sidebar_bg"])
    main_area.configure(fg_color=colors["main_bg"])
    topbar.configure(fg_color=colors["topbar_bg"])
    input_wrap.configure(fg_color=colors["input_wrap_bg"])
    input_frame.configure(fg_color=colors["input_frame_bg"])
    history_panel.configure(fg_color="transparent")

    command_entry.configure(
        fg_color=colors["entry_bg"],
        text_color=colors["entry_text"],
        placeholder_text_color=colors["secondary_text"]
    )

    header.configure(text_color=colors["primary_text"])
    title.configure(text_color=colors["primary_text"])
    subtitle.configure(text_color=colors["secondary_text"])
    chats_title.configure(text_color=colors["primary_text"])
    controls_title.configure(text_color=colors["primary_text"])
    cmd_history_title.configure(text_color=colors["primary_text"])
    quick_title.configure(text_color=colors["primary_text"])
    note.configure(text_color=colors["note_text"])
    clock_label.configure(text_color=colors["primary_text"])
    status_label.configure(text_color=colors["status_text"])

    history_box.configure(
        fg_color=colors["history_bg"],
        text_color=colors["history_text"],
        border_color=colors["history_border"]
    )

    for btn in quick_buttons:
        btn.configure(
            fg_color=colors["quick_btn"],
            hover_color=colors["quick_hover"],
            text_color=colors["primary_text"]
        )


def toggle_theme(
    theme_btn,
    root,
    sidebar,
    main_area,
    topbar,
    input_wrap,
    input_frame,
    command_entry,
    header,
    title,
    subtitle,
    chats_title,
    controls_title,
    cmd_history_title,
    quick_title,
    note,
    clock_label,
    status_label,
    history_box,
    history_panel,
    quick_buttons
):
    global current_theme_mode

    if current_theme_mode == "dark":
        current_theme_mode = "light"
        ctk.set_appearance_mode("light")
        theme_btn.configure(text="☀ Light Mode")
    else:
        current_theme_mode = "dark"
        ctk.set_appearance_mode("dark")
        theme_btn.configure(text="🌙 Dark Mode")

    apply_theme_colors(
        root,
        sidebar,
        main_area,
        topbar,
        input_wrap,
        input_frame,
        command_entry,
        header,
        title,
        subtitle,
        chats_title,
        controls_title,
        cmd_history_title,
        quick_title,
        note,
        clock_label,
        status_label,
        history_box,
        history_panel,
        quick_buttons
    )


# ---------------- AI SETUP ----------------
def load_ai(status_label=None):
    global hf_pipe, is_ai_loading

    if is_ai_loading or hf_pipe is not None:
        return

    is_ai_loading = True

    try:
        safe_config(status_label, text="Loading AI...")
        tok = AutoTokenizer.from_pretrained(AI_MODEL_ID)
        mdl = AutoModelForCausalLM.from_pretrained(
            AI_MODEL_ID,
            torch_dtype="auto",
            device_map="auto"
        )
        hf_pipe = pipeline("text-generation", model=mdl, tokenizer=tok)
        print("AI Loaded")
        safe_config(status_label, text="AI Ready | Idle")
    except Exception as e:
        hf_pipe = None
        print("AI load failed:", e)
        safe_config(status_label, text="AI Unavailable | Idle")
    finally:
        is_ai_loading = False


def ask_ai(prompt: str) -> str:
    if hf_pipe is None:
        return "AI unavailable right now."

    try:
        full_prompt = f"<|user|>\n{prompt}\n<|assistant|>\n"
        out = hf_pipe(
            full_prompt,
            max_new_tokens=80,
            do_sample=True,
            temperature=0.7,
            pad_token_id=hf_pipe.tokenizer.eos_token_id
        )
        result = out[0]["generated_text"].split("<|assistant|>")[-1].strip()
        return result if result else "I could not generate a response."
    except Exception as e:
        print("AI response error:", e)
        return "AI error occurred."


# ---------------- LOCATION + WEATHER ----------------
def get_current_city():
    try:
        response = requests.get("http://ip-api.com/json/", timeout=5)
        data = response.json()

        if data.get("status") == "success":
            city = data.get("city", "").strip()
            if city:
                return city

        return DEFAULT_CITY

    except Exception as e:
        print("Location error:", e)
        return DEFAULT_CITY


def get_weather(city=None):
    if city is None or not city.strip():
        city = get_current_city()

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": "metric"
        }

        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if response.status_code != 200:
            return f"Weather not found for {city}."

        temp = data["main"]["temp"]
        feels_like = data["main"].get("feels_like")
        desc = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        wind = data["wind"]["speed"]

        if feels_like is not None:
            return (
                f"Today's weather in {city} is {temp}°C with {desc}. "
                f"It feels like {feels_like}°C. "
                f"Humidity is {humidity}% and wind speed is {wind} m/s."
            )

        return (
            f"Today's weather in {city} is {temp}°C with {desc}. "
            f"Humidity is {humidity}% and wind speed is {wind} m/s."
        )

    except Exception as e:
        print("Weather error:", e)
        return "Unable to fetch weather right now."


# ---------------- TTS ----------------
def speak(text, status_label=None):
    def run():
        try:
            safe_config(status_label, text="Speaking...")
            engine = pyttsx3.init()
            engine.setProperty("rate", 180)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print("TTS error:", e)
        finally:
            safe_config(status_label, text="Idle")

    threading.Thread(target=run, daemon=True).start()


# ---------------- CHAT HELPERS ----------------
def add_system_message(chat_frame, text):
    colors = get_theme_colors()

    outer = ctk.CTkFrame(chat_frame, fg_color="transparent")
    outer.pack(fill="x", padx=18, pady=6)

    lbl = ctk.CTkLabel(
        outer,
        text=text,
        text_color=colors["system_text"],
        font=ctk.CTkFont(size=12, slant="italic")
    )
    lbl.pack()


def add_message(chat_frame, message, sender="assistant", root=None):
    colors = get_theme_colors()

    bubble_color = colors["assistant_bubble"] if sender == "assistant" else colors["user_bubble"]
    anchor_side = "w" if sender == "assistant" else "e"
    name = "Aura" if sender == "assistant" else "You"
    avatar_text = "A" if sender == "assistant" else "Y"
    avatar_color = colors["assistant_avatar"] if sender == "assistant" else colors["user_avatar"]
    sender_text_color = colors["assistant_name"] if sender == "assistant" else "white"
    message_text_color = colors["primary_text"] if sender == "assistant" else "white"

    outer = ctk.CTkFrame(chat_frame, fg_color="transparent")
    outer.pack(fill="x", padx=18, pady=8)

    row = ctk.CTkFrame(outer, fg_color="transparent")
    row.pack(anchor=anchor_side)

    if sender == "assistant":
        avatar = ctk.CTkLabel(
            row,
            text=avatar_text,
            width=34,
            height=34,
            corner_radius=17,
            fg_color=avatar_color,
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        avatar.pack(side="left", padx=(0, 8))

    bubble = ctk.CTkFrame(row, fg_color=bubble_color, corner_radius=18)
    bubble.pack(side="left")

    top = ctk.CTkFrame(bubble, fg_color="transparent")
    top.pack(fill="x", padx=12, pady=(8, 0))

    sender_label = ctk.CTkLabel(
        top,
        text=name,
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=sender_text_color
    )
    sender_label.pack(side="left")

    if sender == "assistant" and root is not None:
        copy_btn = ctk.CTkButton(
            top,
            text="Copy",
            width=48,
            height=24,
            corner_radius=8,
            fg_color=colors["copy_btn"],
            hover_color=colors["copy_hover"],
            text_color=colors["primary_text"],
            font=ctk.CTkFont(size=11),
            command=lambda m=message: safe_clipboard(root, m)
        )
        copy_btn.pack(side="right")

    msg_label = ctk.CTkLabel(
        bubble,
        text=message,
        wraplength=760,
        justify="left",
        text_color=message_text_color,
        font=ctk.CTkFont(size=14)
    )
    msg_label.pack(anchor="w", padx=14, pady=(4, 10))

    if sender == "user":
        avatar = ctk.CTkLabel(
            row,
            text=avatar_text,
            width=34,
            height=34,
            corner_radius=17,
            fg_color=avatar_color,
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        avatar.pack(side="left", padx=(8, 0))

    chat_frame.update_idletasks()


def clear_chat(chat_frame):
    for widget in chat_frame.winfo_children():
        widget.destroy()


def show_typing_loader(chat_frame):
    colors = get_theme_colors()

    outer = ctk.CTkFrame(chat_frame, fg_color="transparent")
    outer.pack(fill="x", padx=18, pady=8)

    row = ctk.CTkFrame(outer, fg_color="transparent")
    row.pack(anchor="w")

    avatar = ctk.CTkLabel(
        row,
        text="A",
        width=34,
        height=34,
        corner_radius=17,
        fg_color=colors["assistant_avatar"],
        text_color="white",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    avatar.pack(side="left", padx=(0, 8))

    bubble = ctk.CTkFrame(row, fg_color=colors["assistant_bubble"], corner_radius=18)
    bubble.pack(side="left")

    lbl = ctk.CTkLabel(
        bubble,
        text="Aura is thinking",
        font=ctk.CTkFont(size=13, slant="italic"),
        text_color=colors["primary_text"]
    )
    lbl.pack(anchor="w", padx=14, pady=10)

    thinking_labels.append(lbl)
    animate_typing(lbl, 0)

    chat_frame.update_idletasks()
    return outer, lbl


def animate_typing(label, step):
    try:
        if not label.winfo_exists():
            return
        dots = "." * (step % 4)
        label.configure(text=f"Aura is thinking{dots}")
        label.after(400, lambda: animate_typing(label, step + 1))
    except Exception:
        pass


# ---------------- SIDEBAR / HISTORY ----------------
def add_chat_session(history_panel, title_text):
    colors = get_theme_colors()

    card = ctk.CTkFrame(history_panel, corner_radius=10, fg_color=colors["card_bg"])
    card.pack(fill="x", padx=6, pady=5)

    lbl = ctk.CTkLabel(
        card,
        text=title_text,
        anchor="w",
        justify="left",
        text_color=colors["primary_text"],
        font=ctk.CTkFont(size=12)
    )
    lbl.pack(fill="x", padx=10, pady=8)

    chat_sessions.append(title_text)


def add_to_command_history(history_box, cmd):
    if not cmd.strip():
        return

    history_commands.append(cmd)

    try:
        history_box.configure(state="normal")
        history_box.insert("1.0", f"• {cmd}\n")
        history_box.configure(state="disabled")
    except Exception as e:
        print("History box error:", e)


# ---------------- HELPERS ----------------
def open_folder(folder_path, folder_name, status_label=None):
    try:
        if os.path.exists(folder_path):
            os.startfile(folder_path)
            speak(f"Opening {folder_name}", status_label)
            return f"Opening {folder_name}."
        return f"{folder_name} not found."
    except Exception as e:
        print(f"{folder_name} open error:", e)
        return f"Could not open {folder_name}."


def on_closing(root):
    global running
    running = False
    root.destroy()


# ---------------- COMMANDS ----------------
def processCommand(cmd, status_label=None):
    cmd = cmd.lower().strip()
    print("Command received:", cmd)

    sites = {
        "google": "https://google.com",
        "youtube": "https://youtube.com",
        "facebook": "https://facebook.com",
        "instagram": "https://instagram.com",
        "linkedin": "https://linkedin.com",
        "github": "https://github.com"
    }

    for name, link in sites.items():
        if f"open {name}" in cmd:
            webbrowser.open(link)
            speak(f"Opening {name}", status_label)
            return f"Opening {name}."

    if (
        "weather" in cmd
        or "today weather" in cmd
        or "today's weather" in cmd
        or "todays weather" in cmd
    ):
        city = None

        if " in " in cmd:
            city = cmd.split(" in ", 1)[1].strip()

        result = get_weather(city)
        speak(result, status_label)
        return result

    if cmd.startswith("play "):
        song = cmd.replace("play ", "").strip()
        try:
            if song in getattr(musicLibrary, "music", {}):
                webbrowser.open(musicLibrary.music[song])
            else:
                pywhatkit.playonyt(song)

            speak(f"Playing {song}", status_label)
            return f"Playing {song}."
        except Exception as e:
            print("Music error:", e)
            return "Could not play the song."

    if "open notepad" in cmd:
        os.system("notepad")
        speak("Opening Notepad", status_label)
        return "Opening Notepad."

    if "open calculator" in cmd:
        os.system("calc")
        speak("Opening Calculator", status_label)
        return "Opening Calculator."

    if "open cmd" in cmd or "open command prompt" in cmd:
        os.system("start cmd")
        speak("Opening Command Prompt", status_label)
        return "Opening Command Prompt."

    if "open excel" in cmd:
        os.system("start excel")
        speak("Opening Excel", status_label)
        return "Opening Excel."

    if "open powerpoint" in cmd:
        os.system("start powerpnt")
        speak("Opening PowerPoint", status_label)
        return "Opening PowerPoint."

    if "open word" in cmd:
        os.system("start winword")
        speak("Opening Word", status_label)
        return "Opening Word."

    if "open chrome" in cmd:
        os.system("start chrome")
        speak("Opening Chrome", status_label)
        return "Opening Chrome."

    if "open control panel" in cmd:
        os.system("control")
        speak("Opening Control Panel", status_label)
        return "Opening Control Panel."

    if "open settings" in cmd:
        os.system("start ms-settings:")
        speak("Opening Settings", status_label)
        return "Opening Settings."

    user_profile = os.environ.get("USERPROFILE", "")

    if "open" in cmd and ("download" in cmd or "downloads" in cmd):
        return open_folder(os.path.join(user_profile, "Downloads"), "Downloads folder", status_label)

    if "open" in cmd and ("document" in cmd or "documents" in cmd):
        return open_folder(os.path.join(user_profile, "Documents"), "Documents folder", status_label)

    if "open" in cmd and "desktop" in cmd:
        return open_folder(os.path.join(user_profile, "Desktop"), "Desktop folder", status_label)

    if "open" in cmd and ("picture" in cmd or "pictures" in cmd):
        folder_path = os.path.join(user_profile, "Pictures")
        if not os.path.exists(folder_path):
            folder_path = os.path.join(user_profile, "OneDrive", "Pictures")
        return open_folder(folder_path, "Pictures folder", status_label)

    if "open" in cmd and ("video" in cmd or "videos" in cmd):
        return open_folder(os.path.join(user_profile, "Videos"), "Videos folder", status_label)

    if "open" in cmd and ("music folder" in cmd or "open music" in cmd):
        return open_folder(os.path.join(user_profile, "Music"), "Music folder", status_label)

    if "shutdown pc" in cmd or "shutdown computer" in cmd:
        speak("Shutting down the computer", status_label)
        os.system("shutdown /s /t 5")
        return "Shutting down the computer in 5 seconds."

    if "restart pc" in cmd or "restart computer" in cmd:
        speak("Restarting the computer", status_label)
        os.system("shutdown /r /t 5")
        return "Restarting the computer in 5 seconds."

    if "cancel shutdown" in cmd:
        os.system("shutdown /a")
        speak("Shutdown cancelled", status_label)
        return "Shutdown cancelled."

    if "exit" in cmd or "quit" in cmd:
        speak("Goodbye", status_label)
        stop_Aura()
        return "Goodbye."

    if "hello" in cmd or "hi" in cmd:
        speak("Hello", status_label)
        return "Hello."

    reply = ask_ai(cmd)
    speak(reply, status_label)
    return reply


# ---------------- VOICE LOOP ----------------
def Aura_loop(status_label, chat_frame, history_box, root):
    global running

    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.8
    recognizer.energy_threshold = 300

    try:
        with sr.Microphone() as source:
            safe_config(status_label, text="Calibrating microphone...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
    except Exception as e:
        print("Mic calibration error:", e)
        add_system_message(chat_frame, "Microphone calibration failed.")

    while running:
        try:
            safe_config(status_label, text="Waiting for wake word 'Aura'...")

            with sr.Microphone() as source:
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)

            text = recognizer.recognize_google(audio).lower()

            if "aura" in text:
                safe_config(status_label, text="Wake word detected")
                add_system_message(chat_frame, "Wake word detected.")
                speak("Yes", status_label)

                safe_config(status_label, text="Listening command...")
                with sr.Microphone() as source2:
                    audio2 = recognizer.listen(source2, timeout=5, phrase_time_limit=6)

                command = recognizer.recognize_google(audio2)

                add_to_command_history(history_box, command)
                add_message(chat_frame, command, "user", root=root)

                typing_widget, _ = show_typing_loader(chat_frame)
                response = processCommand(command, status_label)
                typing_widget.destroy()

                add_message(chat_frame, response, "assistant", root=root)

        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            print("Speech recognition service error:", e)
            safe_config(status_label, text="Speech service error")
            add_system_message(chat_frame, "Speech recognition service error.")
        except Exception as e:
            print("Voice loop error:", e)
            add_system_message(chat_frame, f"Voice loop error: {e}")


def start_Aura(status_label, chat_frame, history_box, root):
    global running
    if running:
        safe_config(status_label, text="Already listening...")
        return

    running = True
    safe_config(status_label, text="Starting Aura...")
    add_system_message(chat_frame, "Voice assistant started.")
    threading.Thread(
        target=Aura_loop,
        args=(status_label, chat_frame, history_box, root),
        daemon=True
    ).start()


def stop_Aura():
    global running
    running = False


# ---------------- MANUAL SEND ----------------
def send_manual_command(entry, chat_frame, status_label, history_box, root):
    cmd = entry.get().strip()
    if not cmd:
        return

    entry.delete(0, "end")
    add_to_command_history(history_box, cmd)
    add_message(chat_frame, cmd, "user", root=root)

    typing_widget, _ = show_typing_loader(chat_frame)
    safe_config(status_label, text="Processing...")

    def worker():
        response = processCommand(cmd, status_label)

        def finish():
            try:
                typing_widget.destroy()
            except Exception:
                pass
            add_message(chat_frame, response, "assistant", root=root)
            safe_config(status_label, text="Idle")

        chat_frame.after(0, finish)

    threading.Thread(target=worker, daemon=True).start()


def quick_command(cmd, entry, chat_frame, status_label, history_box, root):
    entry.delete(0, "end")
    entry.insert(0, cmd)
    send_manual_command(entry, chat_frame, status_label, history_box, root)


# ---------------- CLOCK ----------------
def update_clock(clock_label):
    def refresh():
        try:
            now = datetime.now().strftime("%I:%M:%S %p")
            if clock_label.winfo_exists():
                clock_label.configure(text=now)
                clock_label.after(1000, refresh)
        except Exception as e:
            print("Clock update error:", e)
    refresh()


# ---------------- NEW CHAT ----------------
def create_new_chat(chat_frame, history_panel, root, status_label=None):
    global session_counter
    clear_chat(chat_frame)

    session_counter += 1
    title = f"Chat {session_counter}"
    add_chat_session(history_panel, title)

    welcome_text = "Hello, I am Aura. How can I help you today?"
    add_message(chat_frame, welcome_text, "assistant", root=root)

    if status_label is not None:
        speak(welcome_text, status_label)


# ---------------- SPLASH SCREEN ----------------
def show_splash():
    splash = ctk.CTk()
    splash.geometry("460x260")
    splash.title("Aura Loading")
    splash.resizable(False, False)

    frame = ctk.CTkFrame(splash, corner_radius=18)
    frame.pack(fill="both", expand=True, padx=18, pady=18)

    title = ctk.CTkLabel(
        frame,
        text="Aura",
        font=ctk.CTkFont(size=34, weight="bold")
    )
    title.pack(pady=(40, 8))

    subtitle = ctk.CTkLabel(
        frame,
        text="Premium AI Desktop Assistant",
        text_color="#94a3b8",
        font=ctk.CTkFont(size=14)
    )
    subtitle.pack()

    loading = ctk.CTkLabel(
        frame,
        text="Launching...",
        font=ctk.CTkFont(size=13)
    )
    loading.pack(pady=(24, 0))

    splash.after(1800, splash.destroy)
    splash.mainloop()


# ---------------- MAIN GUI ----------------
def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1450x830")
    root.minsize(1200, 720)
    root.title("Aura Assistant")
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root))

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)

    # ---------------- SIDEBAR ----------------
    sidebar = ctk.CTkFrame(root, width=320, corner_radius=0)
    sidebar.grid(row=0, column=0, sticky="nsw")
    sidebar.grid_propagate(False)

    title = ctk.CTkLabel(
        sidebar,
        text="Aura",
        font=ctk.CTkFont(size=30, weight="bold")
    )
    title.pack(anchor="w", padx=22, pady=(20, 2))

    subtitle = ctk.CTkLabel(
        sidebar,
        text="Premium AI Desktop Assistant",
        font=ctk.CTkFont(size=13)
    )
    subtitle.pack(anchor="w", padx=22, pady=(0, 14))

    chats_title = ctk.CTkLabel(
        sidebar,
        text="Chats",
        font=ctk.CTkFont(size=16, weight="bold")
    )
    chats_title.pack(anchor="w", padx=22, pady=(16, 6))

    history_panel = ctk.CTkScrollableFrame(sidebar, height=150, fg_color="transparent")
    history_panel.pack(fill="x", padx=18, pady=(0, 8))

    controls_title = ctk.CTkLabel(
        sidebar,
        text="Controls",
        font=ctk.CTkFont(size=16, weight="bold")
    )
    controls_title.pack(anchor="w", padx=22, pady=(10, 6))

    theme_btn = ctk.CTkButton(
        sidebar,
        text="🌙 Dark Mode",
        height=40,
        corner_radius=12,
        fg_color="#374151",
        hover_color="#1f2937"
    )
    theme_btn.pack(fill="x", padx=20, pady=8)

    new_chat_btn = ctk.CTkButton(sidebar, text="+ New Chat", height=42, corner_radius=12)
    new_chat_btn.pack(fill="x", padx=20, pady=6)

    start_btn = ctk.CTkButton(sidebar, text="▶ Start Listening", height=42, corner_radius=12)
    start_btn.pack(fill="x", padx=20, pady=6)

    stop_btn = ctk.CTkButton(
        sidebar,
        text="■ Stop Listening",
        height=42,
        corner_radius=12,
        fg_color="#b91c1c",
        hover_color="#991b1b",
        command=stop_Aura
    )
    stop_btn.pack(fill="x", padx=20, pady=6)

    cmd_history_title = ctk.CTkLabel(
        sidebar,
        text="Command History",
        font=ctk.CTkFont(size=16, weight="bold")
    )
    cmd_history_title.pack(anchor="w", padx=22, pady=(16, 6))

    history_box = ctk.CTkTextbox(sidebar, height=140, corner_radius=12, border_width=1)
    history_box.pack(fill="x", padx=20, pady=(0, 8))
    history_box.configure(state="disabled")

    quick_title = ctk.CTkLabel(
        sidebar,
        text="Quick Commands",
        font=ctk.CTkFont(size=16, weight="bold")
    )
    quick_title.pack(anchor="w", padx=22, pady=(10, 6))

    quick_wrap = ctk.CTkFrame(sidebar, fg_color="transparent")
    quick_wrap.pack(fill="x", padx=18)

    note = ctk.CTkLabel(
        sidebar,
        text="Say 'Aura' before voice command.",
        wraplength=250,
        justify="left",
        font=ctk.CTkFont(size=12)
    )
    note.pack(anchor="w", padx=22, pady=(14, 0))

    # ---------------- MAIN AREA ----------------
    main_area = ctk.CTkFrame(root, corner_radius=0)
    main_area.grid(row=0, column=1, sticky="nsew")
    main_area.grid_rowconfigure(1, weight=1)
    main_area.grid_columnconfigure(0, weight=1)

    topbar = ctk.CTkFrame(main_area, height=66, corner_radius=0)
    topbar.grid(row=0, column=0, sticky="ew")
    topbar.grid_columnconfigure(0, weight=1)

    header = ctk.CTkLabel(
        topbar,
        text="Aura Assistant",
        font=ctk.CTkFont(size=23, weight="bold")
    )
    header.grid(row=0, column=0, sticky="w", padx=20, pady=16)

    clock_label = ctk.CTkLabel(
        topbar,
        text="--:--:--",
        font=ctk.CTkFont(size=13)
    )
    clock_label.grid(row=0, column=1, sticky="e", padx=(0, 16), pady=16)

    status_label = ctk.CTkLabel(
        topbar,
        text="Starting...",
        font=ctk.CTkFont(size=13)
    )
    status_label.grid(row=0, column=2, sticky="e", padx=20, pady=16)

    chat_container = ctk.CTkScrollableFrame(
        main_area,
        corner_radius=0
    )
    chat_container.grid(row=1, column=0, sticky="nsew")

    chat_messages = ctk.CTkFrame(chat_container, fg_color="transparent")
    chat_messages.pack(fill="both", expand=True)

    input_wrap = ctk.CTkFrame(main_area, height=104, corner_radius=0)
    input_wrap.grid(row=2, column=0, sticky="ew")
    input_wrap.grid_columnconfigure(0, weight=1)

    input_frame = ctk.CTkFrame(input_wrap, corner_radius=20)
    input_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=18)
    input_frame.grid_columnconfigure(0, weight=1)

    command_entry = ctk.CTkEntry(
        input_frame,
        placeholder_text="Message Aura...",
        height=52,
        corner_radius=15,
        border_width=0,
        font=ctk.CTkFont(size=15)
    )
    command_entry.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=8)

    mic_btn = ctk.CTkButton(
        input_frame,
        text="🎤",
        width=50,
        height=50,
        corner_radius=15
    )
    mic_btn.grid(row=0, column=1, padx=6, pady=8)

    send_btn = ctk.CTkButton(
        input_frame,
        text="➤",
        width=50,
        height=50,
        corner_radius=15
    )
    send_btn.grid(row=0, column=2, padx=(0, 10), pady=8)

    quick_buttons = []
    quick_commands = [
        "weather",
        "today weather",
        "open google",
        "weather in delhi",
        "open notepad",
        "open downloads",
        "play believer",
        "open excel"
    ]

    for cmd in quick_commands:
        btn = ctk.CTkButton(
            quick_wrap,
            text=cmd,
            height=34,
            corner_radius=10,
            command=lambda c=cmd: quick_command(c, command_entry, chat_messages, status_label, history_box, root)
        )
        btn.pack(fill="x", pady=4)
        quick_buttons.append(btn)

    # ---------------- THEME APPLY ----------------
    apply_theme_colors(
        root,
        sidebar,
        main_area,
        topbar,
        input_wrap,
        input_frame,
        command_entry,
        header,
        title,
        subtitle,
        chats_title,
        controls_title,
        cmd_history_title,
        quick_title,
        note,
        clock_label,
        status_label,
        history_box,
        history_panel,
        quick_buttons
    )

    # ---------------- BINDINGS ----------------
    theme_btn.configure(command=lambda: toggle_theme(
        theme_btn,
        root,
        sidebar,
        main_area,
        topbar,
        input_wrap,
        input_frame,
        command_entry,
        header,
        title,
        subtitle,
        chats_title,
        controls_title,
        cmd_history_title,
        quick_title,
        note,
        clock_label,
        status_label,
        history_box,
        history_panel,
        quick_buttons
    ))
    new_chat_btn.configure(command=lambda: create_new_chat(chat_messages, history_panel, root, status_label))
    start_btn.configure(command=lambda: start_Aura(status_label, chat_messages, history_box, root))
    mic_btn.configure(command=lambda: start_Aura(status_label, chat_messages, history_box, root))
    send_btn.configure(command=lambda: send_manual_command(command_entry, chat_messages, status_label, history_box, root))
    command_entry.bind(
        "<Return>",
        lambda event: send_manual_command(command_entry, chat_messages, status_label, history_box, root)
    )

    add_chat_session(history_panel, "Chat 1")
    welcome_text = "Hello, I am Aura. How can I help you today?"
    add_message(chat_messages, welcome_text, "assistant", root=root)

    update_clock(clock_label)
    threading.Thread(target=load_ai, args=(status_label,), daemon=True).start()

    # app open hote hi greeting बोले
    root.after(700, lambda: speak(welcome_text, status_label))

    # app open hote hi voice assistant automatically start
    root.after(1800, lambda: start_Aura(status_label, chat_messages, history_box, root))

    root.mainloop()


if __name__ == "__main__":
    show_splash()
    main()