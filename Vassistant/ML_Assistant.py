    import customtkinter as ctk
    import threading
    import speech_recognition as sr
    import pyttsx3
    import webbrowser
    import pywhatkit
    from PIL import Image, ImageTk
    import requests
    from io import BytesIO

    # ---------------- Music Library (for playback only) ----------------
    music = {
        "paro": "https://www.youtube.com/watch?v=DxsDekHDKXo",
        "1000 mile": "https://www.youtube.com/watch?v=EWRBHho2b_E&list=RDEWRBHho2b_E&start_radio=1",
        "thousand mile": "https://www.youtube.com/watch?v=EWRBHho2b_E&list=RDEWRBHho2b_E&start_radio=1",
        "love dose": "https://youtu.be/TvngY4unjn4?si=a6iLBEaKUWcAnlw7",
        "blue eyes": "https://youtu.be/NbyHNASFi6U?si=AcbqeC1e5dwTBq2Y",
        "na ja": "https://www.youtube.com/watch?v=Q-GOFPM01d0&list=RDQ-GOFPM01d0&start_radio=1",
        "sakhiyan": "https://www.youtube.com/watch?v=S-ezhTXPVGU&list=RDS-ezhTXPVGU&start_radio=1",
        "khwab": "https://youtu.be/2eliQ_KR8yA?si=hdBIqeY3ZmjUT6i6",
        "bacha lo": "https://youtu.be/SdO4L0IVsGs?si=CIoTpiq-3CIE1psl",
        "sadgi": "https://youtu.be/3_jrHiKTMPU?si=iBuCKPYpSu7InW92",
        "she don't know": "https://youtu.be/_P3R63mmakg?si=7X0dpGDk1_QbPwDx",
        "nazar lag jayegi": "https://youtu.be/kckDWrICC4s?si=NWj0i8OGatmrN9Mu",
        "all black": "https://youtu.be/ReXw6TOnUOc?si=9lgmDhpvcgS2a2Wu",
        "pal pal dil ke paas": "https://youtu.be/f5dw3nafOuo?si=-Jf_not-G5XdVec5",
    }

    # ---------------- TTS Engine ----------------
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)

    def speak(text):
        """Speak text asynchronously"""
        def run_speech():
            engine.say(text)
            engine.runAndWait()
        threading.Thread(target=run_speech, daemon=True).start()

    # ---------------- Voice Recognition ----------------
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    listening = False

    # ---------------- GUI Setup ----------------
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.geometry("700x700")
    app.title(" Music Assistant Pro")

    # ---------------- Status Label ----------------
    status_label = ctk.CTkLabel(app, text="Status: Idle", font=("Arial", 14))
    status_label.pack(pady=10)

    # ---------------- Text Box for Logs ----------------
    text_box = ctk.CTkTextbox(app, width=650, height=150)
    text_box.pack(pady=10)

    # ---------------- Album Art Display ----------------
    album_art_label = ctk.CTkLabel(app, text="Album Art will appear here", font=("Arial", 12))
    album_art_label.pack(pady=10)

    def display_thumbnail(youtube_url):
        try:
            video_id = youtube_url.split("v=")[1].split("&")[0]
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/0.jpg"
            response = requests.get(thumbnail_url)
            img_data = Image.open(BytesIO(response.content))
            img_data = img_data.resize((300, 200))
            img = ImageTk.PhotoImage(img_data)
            album_art_label.configure(image=img, text="")
            album_art_label.image = img
        except:
            album_art_label.configure(text="No thumbnail available", image="")

    # ---------------- Functions ----------------
    def update_text(msg):
        text_box.configure(state="normal")
        text_box.insert("end", msg + "\n")
        text_box.see("end")
        text_box.configure(state="disabled")

    def update_status(msg):
        status_label.configure(text=f"Status: {msg}")

    def play_song(song_name):
        """Play song from library or YouTube and speak immediately"""
        song_name_lower = song_name.lower()
        matched_songs = [name for name in music if song_name_lower in name]

        if matched_songs:
            song = matched_songs[0]
            url = music[song]
            speak(f"Playing {song}")
            update_status(f"Playing {song} from library")
            update_text(f"Playing {song} from your library")
            display_thumbnail(url)
            threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
        else:
            speak(f"Playing {song_name}")
            update_status(f"Playing {song_name} from YouTube")
            update_text(f"Playing {song_name} from YouTube")
            threading.Thread(target=lambda: pywhatkit.playonyt(song_name), daemon=True).start()

    # ---------------- Voice Recognition ----------------
    def listen():
        global listening
        listening = True
        speak("Hello Yash! I am your music assistant. Say a song name to play.")
        update_status("Listening...")

        while listening:
            try:
                with mic as source:
                    recognizer.adjust_for_ambient_noise(source)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    command = recognizer.recognize_google(audio)
                    update_text(f"You said: {command}")
                    
                    if any(word in command.lower() for word in ["exit", "quit", "stop", "bye"]):
                        speak("Goodbye!")
                        update_status("Stopped listening")
                        break

                    # Process command
                    play_song(command)

            except sr.UnknownValueError:
                update_status("Sorry, I could not understand. Try again.")
            except sr.RequestError:
                update_status("Network error.")
            except Exception as e:
                update_status(f"Error: {str(e)}")

    def start_listening():
        threading.Thread(target=listen, daemon=True).start()

    def stop_listening():
        global listening
        listening = False
        update_status("Stopped listening")

    def clear_logs():
        text_box.configure(state="normal")
        text_box.delete("0.0", "end")
        text_box.configure(state="disabled")

    # ---------------- Control Buttons ----------------
    button_frame = ctk.CTkFrame(app)
    button_frame.pack(pady=10)

    start_btn = ctk.CTkButton(button_frame, text="Start Listening", command=start_listening)
    start_btn.grid(row=0, column=0, padx=10)

    stop_btn = ctk.CTkButton(button_frame, text="Stop Listening", command=stop_listening)
    stop_btn.grid(row=0, column=1, padx=10)

    clear_btn = ctk.CTkButton(button_frame, text="Clear Logs", command=clear_logs)
    clear_btn.grid(row=0, column=2, padx=10)

    # ---------------- Search Bar ----------------
    search_frame = ctk.CTkFrame(app)
    search_frame.pack(pady=10)

    search_entry = ctk.CTkEntry(search_frame, width=400, placeholder_text="Type a song name here...")
    search_entry.grid(row=0, column=0, padx=10)

    def search_play():
        song_name = search_entry.get()
        if song_name:
            play_song(song_name)
            search_entry.delete(0, "end")

    search_btn = ctk.CTkButton(search_frame, text="Play Song", command=search_play)
    search_btn.grid(row=0, column=1, padx=5)

    # ---------------- Run GUI ----------------
    # Start listening automatically
    start_listening()

    app.mainloop()