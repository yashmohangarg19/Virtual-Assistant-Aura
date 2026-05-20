import tkinter as tk
import threading
import speech_recognition as sr
import webbrowser
import pyttsx3
import time
import musicLibrary
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# ---------------- AI Setup ----------------
AI_MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
hf_pipe = None

def load_ai():
    global hf_pipe
    try:
        print("Loading local AI model... (first time may take a bit)")
        tok = AutoTokenizer.from_pretrained(AI_MODEL_ID)
        mdl = AutoModelForCausalLM.from_pretrained(
            AI_MODEL_ID,
            torch_dtype="auto",
            device_map="auto"
        )
        hf_pipe = pipeline(
            "text-generation",
            model=mdl,
            tokenizer=tok
        )
        print("AI model loaded.")
    except Exception as e:
        print("AI load error:", e)
        hf_pipe = None

def ask_ai(prompt: str) -> str:
    if hf_pipe is None:
        return "AI module not available right now."

    sys_inst = (
        "You are Jarvis, a helpful, concise voice assistant. "
        "Reply in short, clear Hinglish unless asked otherwise."
    )

    full_prompt = f"<|system|>\n{sys_inst}\n<|user|>\n{prompt}\n<|assistant|>\n"

    try:
        out = hf_pipe(
            full_prompt,
            max_new_tokens=120,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=hf_pipe.tokenizer.eos_token_id
        )
        text = out[0]["generated_text"]
        if "<|assistant|>" in text:
            text = text.split("<|assistant|>")[-1].strip()
        return text.split("</s>")[0].strip()
    except Exception as e:
        return f"Sorry, AI se reply laate time issue aaya: {e}"

# ---------------- TTS ----------------
def speak(text):
    engine = pyttsx3.init('sapi5')
    engine.setProperty('rate', 170)
    engine.setProperty('volume', 1.0)
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)  # male voice
    engine.say(text)
    engine.runAndWait()
    engine.stop()

# ---------------- Commands ----------------
def processCommand(c):
    c = c.lower()

    if "open google" in c:
        webbrowser.open("https://google.com")
        speak("Opening Google")
        return "Opening Google"
    elif "open facebook" in c:
        webbrowser.open("https://facebook.com")
        speak("Opening Facebook")
        return "Opening Facebook"
    elif "open youtube" in c:
        webbrowser.open("https://youtube.com")
        speak("Opening YouTube")
        return "Opening YouTube"
    elif "open insta" in c or "open instagram" in c:
        webbrowser.open("https://instagram.com")
        speak("Opening Instagram")
        return "Opening Instagram"
    elif "open linkedin" in c:
        webbrowser.open("https://linkedin.com")
        speak("Opening LinkedIn")
        return "Opening LinkedIn"

    if c.startswith("play "):
        song = c.replace("play ", "").strip()
        if song in musicLibrary.music:
            link = musicLibrary.music[song]
            webbrowser.open(link)
            speak(f"Playing {song}")
            return f"Playing {song}"
        else:
            speak(f"Sorry, mujhe {song} nahi mil raha aapki list me.")
            return f"Song {song} not found"

    if "hello" in c:
        msg = "Hello sir, how are you?"
        speak(msg)
        return msg
    if "how r you" in c:
        msg = "I am fine sir, thank you. How are you?"
        speak(msg)
        return msg
    if "who r you" in c:
        msg = "I am Jarvis, your personal assistant."
        speak(msg)
        return msg
    if "what is your name" in c:
        msg = "My name is Jarvis."
        speak(msg)
        return msg
    if "thank you" in c:
        msg = "You're welcome sir, always here to help."
        speak(msg)
        return msg
    if "who make you" in c or "who made you" in c or "who create you" in c:
        msg = "I was created by Sagar Chauhan, BCA 5th sem student."
        speak(msg)
        return msg
    if "exit" in c or "quit" in c:
        speak("Goodbye!")
        stop_jarvis()
        return "Goodbye!"

    # AI fallback
    ai_reply = ask_ai(c)
    speak(ai_reply)
    return ai_reply

# ---------------- Voice assistant loop ----------------
running = False  # Control flag
def jarvis_loop_update(status_label, chat_area):
    global running
    recognizer = sr.Recognizer()
    while running:
        status_label.config(text="Listening for the wake word... say 'jarvis'")
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                try:
                    word = recognizer.recognize_google(audio).lower()
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    status_label.config(text=f"Speech recognition error: {e}")
                    continue

                if "jarvis" in word:
                    chat_area.insert(tk.END, "Jarvis activated. Listening for your command...\n")
                    chat_area.see(tk.END)
                    speak("Yes sir...")

                    with sr.Microphone() as source2:
                        recognizer.adjust_for_ambient_noise(source2, duration=1)
                        audio2 = recognizer.listen(source2, timeout=7, phrase_time_limit=6)
                    try:
                        command = recognizer.recognize_google(audio2)
                        chat_area.insert(tk.END, f"Command: {command}\n")
                        chat_area.see(tk.END)
                        response = processCommand(command)
                        chat_area.insert(tk.END, f"Jarvis: {response}\n\n")
                        chat_area.see(tk.END)
                    except sr.UnknownValueError:
                        speak("Sorry, I could not understand your command.")
                    except sr.RequestError:
                        speak("Sorry, there was an error connecting to speech services.")
            except sr.WaitTimeoutError:
                continue

    status_label.config(text="Jarvis is stopped.")

def start_jarvis(status_label, chat_area):
    global running
    if running:
        return
    running = True
    threading.Thread(target=jarvis_loop_update, args=(status_label, chat_area), daemon=True).start()
    status_label.config(text="Jarvis is running...")

def stop_jarvis():
    global running
    running = False

# ---------------- GUI setup ----------------
import threading
import tkinter as tk
from tkinter import scrolledtext

def main():
    load_ai()

    root = tk.Tk()
    root.title("Jarvis Voice Assistant")

    chat_area = scrolledtext.ScrolledText(root, width=60, height=20, wrap=tk.WORD)
    chat_area.pack(pady=10)

    status_label = tk.Label(root, text="Jarvis is OFF")
    status_label.pack()

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    start_btn = tk.Button(btn_frame, text="ON", width=10, command=lambda: start_jarvis(status_label, chat_area))
    start_btn.pack(side=tk.LEFT, padx=5)

    stop_btn = tk.Button(btn_frame, text="OFF", width=10, command=stop_jarvis)
    stop_btn.pack(side=tk.LEFT, padx=5)

    root.mainloop()

if __name__ == "__main__":
    main()