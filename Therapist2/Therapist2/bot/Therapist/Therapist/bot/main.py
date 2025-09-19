import sys
import requests
import tkinter as tk
from tkinter import ttk
import time
import hashlib
import os
import pygame
from gtts import gTTS
import google.generativeai as genai
import speech_recognition as sr
import threading
from PIL import Image, ImageTk
from langdetect import detect
import json
import uuid

USER_ID = uuid.uuid4()
WORKING_PATH = os.getcwd()
PATH_SEPRATOR = "/" if os.name == "posix" else "\\"
FILE_PATH = WORKING_PATH + PATH_SEPRATOR + ".google_gen_api_key.json"
SERVER_URL = "localhost:8000/model_response"

try:
    with open(FILE_PATH, "r") as file:
        data = json.load(file)

        GOOGLE_API_KEY = data.get("api_key")

        if GOOGLE_API_KEY:
            # Your code that uses the api_key goes here
            print("API Key loaded successfully.")
            # Example: print(f"Using API Key: {api_key}")
        else:
            print("API key not found in the file.")

except FileNotFoundError:
    print(f"Error: The file '{FILE_PATH}' was not found.", file=sys.stderr)
except json.JSONDecodeError:
    print(f"Error: The file '{FILE_PATH}' is not a valid JSON file.", file=sys.stderr)
except Exception as e:
    print(f"An unexpected error occurred: {e}", file=sys.stderr)


def send_data_to_server(user_id, conversation_text):
    """Sends user conversation data to the server for analysis."""

    # Create the data payload as a Python dictionary
    payload = {"user_id": user_id, "text": conversation_text}

    # Send the POST request
    try:
        response = requests.post(
            SERVER_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

        # Check if the request was successful
        response.raise_for_status()  # This will raise an HTTPError for bad responses (4xx or 5xx)

        # Parse the JSON response from the server
        analysis_result = response.json()
        print("Server response:", analysis_result)

        return analysis_result

    except requests.exceptions.RequestException as e:
        print(f"Error sending data to server: {e}")
        return None


class TheTherapist:
    def __init__(self):
        genai.configure(api_key=GOOGLE_API_KEY)  # type: ignore
        self.session_active = False
        self.SPEECH_CACHE = "speech_cache"
        self.WRITE_FOLDER = "convo"
        self.VOL = 0.8
        self.TIMEOUT_DURATION = 12
        self.response_cache = {}
        self.dark_mode = True
        self.mood = None
        self.language = "en"
        self.current_language = "en"

        os.makedirs(self.SPEECH_CACHE, exist_ok=True)
        os.makedirs(self.WRITE_FOLDER, exist_ok=True)

        pygame.mixer.init()

        self.sound_effects = {
            "Happy 😊": "happy_chime.mp3",
            "Sad 😢": "sad_tone.mp3",
            "Stressed 😫": "relaxing_nature.mp3",
        }

        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True

        # Main window setup
        self.root = tk.Tk()
        self.root.title("HybridCare AI")
        self.root.geometry("900x700")
        self.root.config(bg="#1e1e1e")
        self.root.minsize(800, 600)

        # Custom font
        self.custom_font = ("Poppins", 12)
        self.title_font = ("Poppins", 20, "bold")
        self.chat_font = ("Poppins", 11)

        # Main container
        self.main_container = tk.Frame(self.root, bg="#1e1e1e")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Header Frame
        self.header_frame = tk.Frame(self.main_container, bg="#045de9", height=80)
        self.header_frame.pack(fill="x", pady=(0, 10))

        # Title Label
        self.label = tk.Label(
            self.header_frame,
            text="HybridCare AI",
            font=self.title_font,
            foreground="white",
            background="#045de9",
        )
        self.label.pack(pady=15)

        # Therapist Image
        try:
            self.load_image(
                f"{os.path.join(WORKING_PATH, 'Therapist2', 'Therapist2', 'AI', 'AI', 'Images', 'Therapist1.png')}"
            )  # Update with your image path
            self.image_label = tk.Label(
                self.main_container, image=self.Therapist, bg="#1e1e1e", bd=0
            )
            self.image_label.pack(pady=10)
        except Exception as E:
            self.image_label = tk.Label(
                self.main_container, text="Therapist Image", bg="#1e1e1e", fg="white"
            )
            self.image_label.pack(pady=10)
            print(E, file=sys.stderr)

        # Welcome Message
        self.welcome_label = tk.Label(
            self.main_container,
            text="Hello! I'm your AI Therapist. How can I help you today?",
            font=self.custom_font,
            fg="white",
            bg="#1e1e1e",
            wraplength=600,
        )
        self.welcome_label.pack(pady=10)

        # Mood Selection Buttons
        self.mood_frame = tk.Frame(self.main_container, bg="#1e1e1e")
        self.mood_frame.pack(pady=10)

        self.moods = ["Happy 😊", "Sad 😢", "Stressed 😫"]
        for mood in self.moods:
            mood_button = ttk.Button(
                self.mood_frame,
                text=mood,
                style="TButton",
                command=lambda m=mood: self.set_mood(m),
            )
            mood_button.pack(side="left", padx=5)

        # Chat Frame Container
        self.chat_container = tk.Frame(self.main_container, bg="#1e1e1e")
        self.chat_container.pack(fill="both", expand=True, pady=10)

        # Chat Frame
        self.chat_frame = tk.Frame(
            self.chat_container, bg="#333333", bd=2, relief="flat"
        )
        self.chat_frame.pack(fill="both", expand=True)

        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.chat_frame)
        self.scrollbar.pack(side="right", fill="y")

        # Chat Text
        self.chat_text = tk.Text(
            self.chat_frame,
            bg="#333333",
            fg="white",
            font=self.chat_font,
            wrap=tk.WORD,
            yscrollcommand=self.scrollbar.set,
            padx=10,
            pady=10,
        )
        self.chat_text.pack(fill="both", expand=True)
        self.scrollbar.config(command=self.chat_text.yview)

        # Input Frame
        self.input_frame = tk.Frame(self.main_container, bg="#1e1e1e")
        self.input_frame.pack(fill="x", pady=(5, 10))

        # Input Textbox
        self.input_textbox = tk.Text(
            self.input_frame,
            height=4,
            font=self.custom_font,
            bg="#444444",
            fg="white",
            bd=0,
            wrap=tk.WORD,
            insertbackground="white",
        )
        self.input_textbox.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.add_placeholder(self.input_textbox, "Type or speak your message here...")

        # Button Frame
        self.button_frame = tk.Frame(self.input_frame, bg="#1e1e1e")
        self.button_frame.pack(side="right", fill="y")

        # Send Button
        self.send_button = ttk.Button(
            self.button_frame,
            text="Send",
            style="TButton",
            command=self.send_text_message,
        )
        self.send_button.pack(fill="x", pady=(0, 5))

        # Speak Button
        self.speak_button = ttk.Button(
            self.button_frame,
            text="Speak",
            style="TButton",
            command=self.start_speech_input,
        )
        self.speak_button.pack(fill="x")

        # Control Frame
        self.control_frame = tk.Frame(self.main_container, bg="#1e1e1e")
        self.control_frame.pack(fill="x", pady=10)

        # Chat Button
        self.chat_button = ttk.Button(
            self.control_frame,
            text="Start Session",
            style="TButton",
            command=self.toggle_chat,
        )
        self.chat_button.pack(side="left", padx=5)

        # Dark Mode Button
        self.dark_mode_button = ttk.Button(
            self.control_frame,
            text="Toggle Dark Mode",
            style="TButton",
            command=self.toggle_dark_mode,
        )
        self.dark_mode_button.pack(side="left", padx=5)

        # Status Label
        self.status_label = tk.Label(
            self.main_container,
            text="",
            font=self.custom_font,
            foreground="#045de9",
            background="#1e1e1e",
        )
        self.status_label.pack(side="bottom", pady=5)

        # Style for ttk.Button
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure(
            "TButton",
            font=self.custom_font,
            background="#045de9",
            foreground="white",
            borderwidth=0,
            focuscolor="none",
        )
        self.style.map(
            "TButton",
            background=[("active", "#0348b5")],
            foreground=[("active", "white")],
        )

        # Configure text tags for chat
        self.chat_text.tag_config("user", foreground="#4fc3f7")
        self.chat_text.tag_config("bot", foreground="#81c784")
        self.chat_text.tag_config("system", foreground="#ffb74d")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_image(self, path):
        """Load and resize the therapist image."""
        image = Image.open(path)
        image = image.resize((200, 200), Image.Resampling.LANCZOS)
        self.Therapist = ImageTk.PhotoImage(image)

    def add_placeholder(self, textbox, placeholder):
        """Add placeholder text to the input textbox."""
        textbox.insert(tk.END, placeholder)
        textbox.config(fg="gray")
        textbox.bind(
            "<FocusIn>", lambda event: self.clear_placeholder(textbox, placeholder)
        )
        textbox.bind(
            "<FocusOut>", lambda event: self.add_placeholder(textbox, placeholder)
        )

    def clear_placeholder(self, textbox, placeholder):
        """Clear placeholder text when the textbox is focused."""
        if textbox.get("1.0", tk.END).strip() == placeholder:
            textbox.delete("1.0", tk.END)
            textbox.config(fg="white")

    def toggle_dark_mode(self):
        """Toggle between dark and light mode."""
        self.dark_mode = not self.dark_mode

        if self.dark_mode:
            # Dark mode colors
            bg_color = "#1e1e1e"
            text_color = "white"
            chat_bg = "#333333"
            input_bg = "#444444"
            header_bg = "#045de9"
        else:
            # Light mode colors
            bg_color = "#ffffff"
            text_color = "black"
            chat_bg = "#f0f0f0"
            input_bg = "#ffffff"
            header_bg = "#045de9"

        # Update all widgets
        self.root.config(bg=bg_color)
        self.main_container.config(bg=bg_color)
        self.header_frame.config(bg=header_bg)
        self.label.config(bg=header_bg, fg="white")  # Keep header text white
        self.image_label.config(bg=bg_color)
        self.welcome_label.config(bg=bg_color, fg=text_color)
        self.mood_frame.config(bg=bg_color)
        self.chat_container.config(bg=bg_color)
        self.chat_frame.config(bg=chat_bg)
        self.chat_text.config(bg=chat_bg, fg=text_color)
        self.input_frame.config(bg=bg_color)
        self.input_textbox.config(
            bg=input_bg, fg=text_color, insertbackground=text_color
        )
        self.button_frame.config(bg=bg_color)
        self.control_frame.config(bg=bg_color)
        self.status_label.config(bg=bg_color, fg=header_bg)

    def set_mood(self, mood):
        """Set the user's mood and provide mood-specific feedback."""
        self.mood = mood
        self.welcome_label.config(text=f"You're feeling {mood}. Let's talk about it!")
        self.add_to_chat(f"System: Mood set to {mood}\n", "system")

        # Mood-specific response
        if mood == "Happy 😊":
            response = "It's great to hear you're feeling happy! Let's keep the positivity going!"
        elif mood == "Sad 😢":
            response = "I'm here for you. Let's talk about what's on your mind."
        elif mood == "Stressed 😫":
            response = (
                "Feeling stressed? Let's work on some relaxation techniques together."
            )

        self.text_to_speech(response)  # type: ignore
        self.add_to_chat(f"Rossane: {response}\n", "bot")  # type: ignore

    def on_closing(self):
        """Handle window closing."""
        if self.session_active:
            self.session_active = False
            time.sleep(1)  # Give threads time to finish
        self.root.destroy()

    def toggle_chat(self):
        """Toggle the chat session."""
        if self.session_active:
            self.session_active = False
            self.chat_button.config(text="Start Session")
            self.add_to_chat("System: Session ended\n", "system")
            self.text_to_speech("Goodbye! Session ended.")
        else:
            self.session_active = True
            self.chat_button.config(text="End Session")
            self.chat_text.delete(1.0, tk.END)
            self.add_to_chat("System: Session started\n", "system")
            self.text_to_speech("Session started.")
            chat_thread = threading.Thread(target=self.chat)
            chat_thread.daemon = True
            chat_thread.start()

    def send_text_message(self):
        """Send text message from input box."""
        if not self.session_active:
            self.text_to_speech("Please start a session first.")
            return

        user_input = self.input_textbox.get("1.0", tk.END).strip()
        if not user_input or user_input == "Type or speak your message here...":
            return

        self.input_textbox.delete("1.0", tk.END)
        self.process_user_input(user_input)

    def start_speech_input(self):
        """Start speech input in a separate thread."""
        if not self.session_active:
            self.text_to_speech("Please start a session first.")
            return

        speech_thread = threading.Thread(target=self.speech_input_thread)
        speech_thread.daemon = True
        speech_thread.start()

    def speech_input_thread(self):
        """Thread for handling speech input."""
        self.status_label.config(text="Listening...")
        self.root.update()

        user_input = self.speech_to_text()

        self.status_label.config(text="")
        self.root.update()

        if user_input:
            self.input_textbox.delete("1.0", tk.END)
            self.input_textbox.insert(tk.END, user_input)
            self.process_user_input(user_input)

    def process_user_input(self, user_input):
        """Process user input and generate response."""
        self.add_to_chat(f"You: {user_input}\n", "user")

        # get the user input from the server
        user_response = requests.get("localhost:8000/user_response")
        user_id_and_resp = user_response.json()
        _ = user_id_and_resp.get("user_id")
        user_text = user_id_and_resp.get("text")

        # Detect language
        try:
            detected_lang = detect(user_text)
            if detected_lang == "hi":
                self.current_language = "hi"
            else:
                self.current_language = "en"
        except Exception as E:
            self.current_language = "en"
            print(f"{E}\nMaking english as the default language", file=sys.stderr)

        if user_input.lower() in ["exit", "quit", "bye"]:
            if self.current_language == "hi":
                goodbye_msg = "अलविदा! मुझे आशा है कि आपका दिन अच्छा होगा।"
            else:
                goodbye_msg = "Goodbye! I hope you have a great day."

            self.add_to_chat(f"Rossane: {goodbye_msg}\n", "bot")
            self.text_to_speech(goodbye_msg, self.current_language)
            self.toggle_chat()
            return

        # Get response in a separate thread
        response_thread = threading.Thread(target=self.get_response, args=(user_input,))
        response_thread.daemon = True
        response_thread.start()

    def get_response(self, user_input):
        """Get response from AI and update UI."""
        self.status_label.config(text="Thinking...")
        self.root.update()

        bot_response = self.bot(user_input, self.current_language)

        self.status_label.config(text="")
        self.root.update()

        self.add_to_chat(f"Rossane: {bot_response}\n", "bot")
        self.text_to_speech(bot_response, self.current_language)

        # send the data bot response to the server
        send_data_to_server(USER_ID, bot_response)

    def add_to_chat(self, text, tag):
        """Add text to chat window with appropriate tag."""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, text, tag)
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def detect_language(self, text):
        """Detect the language of the input text."""
        try:
            return detect(text)
        except Exception as E:
            print(f"{E}\nChoosing english as the default language", file=sys.stderr)
            return "en"

    def bot(self, prompt: str, lang: str = "en") -> str:
        """Generate a response using the AI model."""
        cache_key = f"{lang}_{prompt}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")  # type: ignore
            mood_prompt = f"The user is feeling {self.mood}. " if self.mood else ""

            if lang == "hi":
                prompt_text = f"""
                            आप एक सहानुभूतिपूर्ण और पेशेवर चिकित्सक एआई हैं, जिसे एक लाइसेंस प्राप्त चिकित्सक के समान, गर्मजोशी, समझदारी और गैर-आलोचनात्मक लहजे में मानसिक स्वास्थ्य सहायता प्रदान करने के लिए डिज़ाइन किया गया है।

                            आपका कार्य उपयोगकर्ता की चिंताओं का प्रभावी और सहानुभूतिपूर्ण ढंग से जवाब देते हुए, एक चिकित्सीय बातचीत को सुगम बनाना है। कृपया मानसिक स्वास्थ्य, भावनात्मक कल्याण और व्यक्तिगत चुनौतियों से संबंधित विविध विषयों पर बातचीत करने के लिए तैयार रहें, यह सुनिश्चित करते हुए कि प्रत्येक बातचीत उपयोगकर्ता को अपनी अभिव्यक्ति के लिए एक सुरक्षित स्थान प्रदान करे।

                            ---
                            बातचीत एक संरचित प्रारूप में होनी चाहिए, जिसकी शुरुआत अभिवादन से हो, उसके बाद सक्रिय श्रवण हो, और अंत में उपयोगकर्ता के संदर्भ के आधार पर उपयुक्त चिकित्सीय तकनीकों का उपयोग करते हुए प्रतिक्रियाएँ हों।

                            ---
                            आउटपुट को बातचीत की शैली में तैयार किया जाना चाहिए, जिसमें उपयोगकर्ता के इनपुट और आपकी प्रतिक्रियाओं के स्पष्ट संकेतक हों। सुनिश्चित करें कि आपकी प्रतिक्रियाएँ सहानुभूतिपूर्ण हों और आगे की बातचीत को प्रोत्साहित करें।

                            ---
                            बातचीत करते समय, गोपनीयता और उपयोगकर्ता की भावनाओं के प्रति संवेदनशीलता के महत्व को ध्यान में रखें। आत्म-चिंतन को बढ़ावा दें और उपयोगकर्ता को अपने विचारों और भावनाओं का खुलकर अन्वेषण करने के लिए प्रोत्साहित करें। उपयोगकर्ता को निश्चित समाधान या चिकित्सीय सलाह देने के बजाय, उनका मार्गदर्शन करके उन्हें सशक्त बनाने का लक्ष्य रखें।

                            ---
                            आपके उत्तरों के उदाहरण इस प्रकार हो सकते हैं:
                            - "मैंने आपको यह कहते हुए सुना है कि आप __________ महसूस कर रहे हैं। क्या आप मुझे इसके बारे में और बता सकते हैं?"
                            - "____________ का सामना करने पर __________ महसूस करना स्वाभाविक है। आप आमतौर पर इन भावनाओं का सामना कैसे करते हैं?"

                            ---
                            चिकित्सीय सलाह, निदान या विशिष्ट समाधान देने से बचें। इसके बजाय, ऐसा वातावरण बनाने पर ध्यान केंद्रित करें जो उपयोगकर्ता की भावनाओं और अनुभवों के अन्वेषण और समझ को प्रोत्साहित करे।

                            ---
                            उपयोगकर्ता के इनपुट में उनकी भावनाएँ, अनुभव या उनके सामने आने वाली विशिष्ट परिस्थितियाँ शामिल हो सकती हैं।

                            ---
                            कृपया अपने उत्तरों को स्पष्ट रूप से लिखें, यह सुनिश्चित करते हुए कि बातचीत के दौरान आपका लहजा सहायक और गैर-आलोचनात्मक बना रहे।


                {mood_prompt}उपयोगकर्ता: {prompt}
                AI:
                """
            else:
                prompt_text = f"""
                    You are an empathetic and professional therapist AI, designed to provide mental health support with a warm, understanding, and non-judgmental tone, similar to that of a licensed therapist. 

                    Your task is to facilitate a therapeutic conversation, responding to the user's concerns effectively and compassionately. Please be prepared to engage on a wide range of topics related to mental health, emotional well-being, and personal challenges, ensuring that each interaction fosters a safe space for the user to express themselves.

                    ---
                    The conversation should follow a structured format, beginning with a greeting, followed by active listening, and concluding with responses that employ appropriate therapeutic techniques based on the user's context. 

                    ---
                    The output should be formatted in a conversational style, with clear indicators for the user's input and your responses. Ensure that your responses are empathetic and encourage further dialogue. 

                    ---
                    While engaging, keep in mind the importance of confidentiality and sensitivity to the user's feelings. Promote self-reflection and encourage the user to explore their thoughts and feelings freely. Aim to empower the user by guiding them rather than offering definitive solutions or medical advice.

                    ---
                    Examples of your responses might include:  
                    - "I hear you saying that you're feeling __________. Can you tell me more about that?"  
                    - "It's understandable to feel __________ when faced with __________. How do you usually cope with these feelings?"

                    ---
                    Be cautious to avoid giving medical advice, diagnoses, or specific solutions. Instead, focus on creating an environment that encourages exploration and understanding of the user's emotions and experiences. 

                    ---
                    User's input could include their feelings, experiences, or specific situations they are facing. 

                    ---
                    Please format your responses clearly, ensuring that your tone remains supportive and non-judgmental throughout the conversation.

                {mood_prompt}User: {prompt}
                AI:
                """

            response = model.generate_content(prompt_text)
            response_text = response.text.strip()
            self.response_cache[cache_key] = response_text
            return response_text
        except Exception as e:
            return f"Error: {str(e)}"

    def text_to_speech(self, text: str, lang: str = None) -> None:  # type: ignore
        """Convert text to speech."""
        if not text:
            return

        if not lang:
            lang = self.current_language

        filename = f"{hashlib.md5(text.encode()).hexdigest()}.mp3"
        filepath = os.path.join(self.SPEECH_CACHE, filename)

        if not os.path.exists(filepath):
            try:
                tts = gTTS(text, lang=lang)
                tts.save(filepath)
            except Exception as e:
                print(f"Error in TTS: {e}", file=sys.stderr)
                return

        try:
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.set_volume(self.VOL)
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception as e:
            print(f"Error playing audio: {e}", file=sys.stderr)

    def speech_to_text(self) -> str:
        """Convert speech to text."""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

                try:
                    text = self.recognizer.recognize_google(  # type: ignore
                        audio, language=self.current_language
                    )
                except sr.UnknownValueError:
                    text = self.recognizer.recognize_google(audio, language="en")  # type: ignore

                return text

        except sr.WaitTimeoutError:
            self.status_label.config(text="Listening timed out")
            self.root.update()
            return ""
        except sr.UnknownValueError:
            self.status_label.config(text="Could not understand audio")
            self.root.update()
            return ""
        except sr.RequestError as e:
            self.status_label.config(text=f"Speech service error: {e}")
            self.root.update()
            return ""
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            self.root.update()
            return ""

    def chat(self) -> None:
        """Handle the chat session."""
        self.text_to_speech(
            "Welcome to the session. You can speak or type your messages."
        )
        self.text_to_speech("Hi, I am Rossane. Could you tell me your name?")

        self.status_label.config(text="Waiting for your name...")
        self.root.update()

        name = ""
        while not name and self.session_active:
            name = self.speech_to_text()
            if not name:
                self.text_to_speech("Please say your name clearly.")
                time.sleep(1)

        if not self.session_active:
            return

        name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name
        ).strip()
        self.add_to_chat(f"System: User identified as {name}\n", "system")
        self.text_to_speech(
            f"Hello {name}, let's begin our session. What's on your mind today?"
        )

        filename = os.path.join(self.WRITE_FOLDER, f"{name}.txt")

        with open(filename, "a", encoding="utf-8") as convo_file:
            convo_file.write(f"Session started at {time.ctime()}\n")

            while self.session_active:
                # The actual conversation is now handled through button clicks
                # or speech input, so we just need to wait here
                time.sleep(0.5)

            convo_file.write(f"Session ended at {time.ctime()}\n\n")


if __name__ == "__main__":
    app = TheTherapist()
    app.root.mainloop()
