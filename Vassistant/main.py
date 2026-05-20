import speech_recognition as sr
import webbrowser
import pyttsx3
import musicLibrary
import time

# Initialize recognizer and engine
recognizer = sr.Recognizer()
# engine = pyttsx3.init('sapi5')  #sapi5 for Windows,espeak for Linux,nsss for Mac
# engine.setProperty('rate', 170)  # For Normal Speed 
# engine.setProperty('volume', 1.0)

'''def speak(text):
    """Convert text to speech."""
    def run_speak():
        print(f"Jarvis: {text}")   # Debug
        engine.say(text)
        engine.runAndWait()
    #time.sleep(0.2)
    t = threading.Thread(target=run_speak)
    t.start()'''


def speak(text):
    print(f"Jarvis: {text}") # Debug
    engine = pyttsx3.init('sapi5')   # New engine is create at every call 
    engine.setProperty('rate', 170)
    engine.setProperty('volume', 1.0)

    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)  # 0 = male, 1 = female

    engine.say(text)
    engine.runAndWait()
    engine.stop()


def processCommand(c):
    """Process user commands."""
    c = c.lower()

    if "open google" in c:
        webbrowser.open("https://google.com")
    elif "open facebook" in c:
        webbrowser.open("https://facebook.com")
    elif "open youtube" in c:
        webbrowser.open("https://youtube.com")
    elif "open insta" in c or "open instagram" in c:
        webbrowser.open("https://instagram.com")
    elif "open linkedin" in c:
        webbrowser.open("https://linkedin.com")
    
    #for play my list
    elif c.startswith("play "):
        song = c.replace("play ", "").strip()  # supports multi-word songs
        if song in musicLibrary.music:
            link = musicLibrary.music[song]
            webbrowser.open(link)
            speak(f"Playing {song}")
        else:
            speak(f"Sorry, I don’t know the song {song}")

    #Smart Talk
    elif "hello" in c:
        speak("Hello sir, how are you?")
    elif "how are you" in c:
        speak("I am fine sir, thank you. How are you?")
    elif "who are you" in c:
        speak("I am Jarvis, your personal assistant.")
    elif "what is your name" in c:
        speak("My name is Jarvis.")
    elif "thank you" in c:
        speak("You're welcome sir, always here to help.")
    elif "who make you" in c or "who made you" in c or "who create you" in c :
        speak("the name of my crater is Sagar Chauhan who is a student of bca 5th sem bca")
    elif "exit" in c or "quit" in c:
        speak("Goodbye!")
        exit(0)
    else:
        speak("Sorry, I did not understand.")

if __name__ == "__main__":
    speak("Initializing Jarvis...")
    speak("hello Sir...")
    while True:
        try:
            with sr.Microphone() as source:
                print("Listening for the wake word... (say 'jarvis')")
                recognizer.adjust_for_ambient_noise(source, duration=1)  # reduces background noise
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)

            try:
                word = recognizer.recognize_google(audio).lower()
            except sr.UnknownValueError:
                continue  # Ignore noise / unrecognized speech
            except sr.RequestError as e:
                print(f"Speech recognition error: {e}")
                continue

            if word == "jarvis":
                print("Jarvis activated. Listening for your command...")
                speak("Yes sir...")

                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                    audio = recognizer.listen(source, timeout=7, phrase_time_limit=5)

                try:
                    command = recognizer.recognize_google(audio)
                    print(f"Command: {command}")
                    processCommand(command)
                except sr.UnknownValueError:
                    speak("Sorry, I could not understand your command.")
                except sr.RequestError as e:
                    speak("Sorry, there was an error connecting to speech services.")

        except sr.WaitTimeoutError:
            # No wake word spoken within timeout
            continue
        except KeyboardInterrupt:
            print("Exiting Jarvis...")
            speak("Goodbye sir!")
            break
