import sys
import requests
import time
import hashlib
import os
import pygame
from gtts import gTTS
import google.generativeai as genai
import speech_recognition as sr
import threading
from langdetect import detect
import json
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS

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


class TheTherapist:
    def __init__(self):
        genai.configure(api_key=GOOGLE_API_KEY)  # type: ignore
        self.session_active = False
        self.SPEECH_CACHE = "speech_cache"
        self.WRITE_FOLDER = "convo"
        self.VOL = 0.8
        self.TIMEOUT_DURATION = 12
        self.response_cache = {}
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

    def set_mood(self, mood):
        """Set the user's mood and provide mood-specific feedback."""

        self.mood = mood

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

    def toggle_chat(self):
        """Toggle the chat session."""

        if self.session_active:
            self.session_active = False
            self.text_to_speech("Goodbye! Session ended.")
        else:
            self.session_active = True
            self.text_to_speech("Session started.")
            chat_thread = threading.Thread(target=self.chat)
            chat_thread.daemon = True
            chat_thread.start()

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

        user_input = self.speech_to_text()

    def process_user_input(self, user_input):
        """Process user input and generate response."""

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

            self.text_to_speech(goodbye_msg, self.current_language)
            self.toggle_chat()
            return

        # Get response in a separate thread
        response_thread = threading.Thread(target=self.get_response, args=(user_input,))
        response_thread.daemon = True
        response_thread.start()

    def get_response(self, user_input):
        """Get response from AI and update UI."""

        bot_response = self.bot(user_input, self.current_language)
        print(bot_response)

        self.text_to_speech(bot_response, self.current_language)
        return bot_response

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

    def chat(self) -> None:
        """Handle the chat session."""

        self.text_to_speech(
            "Welcome to the session. You can speak or type your messages."
        )
        self.text_to_speech("Hi, I am Rossane. Could you tell me your name?")

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


app = Flask(__name__)
CORS(app)


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    This is the API endpoint. It uses the global `analyzer_instance`
    to perform the analysis for each request.
    """

    print("in the route function")

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    text_to_analyze = data.get("text")

    if not text_to_analyze:
        return jsonify({"error": "Missing 'text' key in request"}), 400

    # Call the .predict() method on the single instance of your class
    chat = TheTherapist()
    resp = chat.get_response(text_to_analyze)

    result = {"data": resp}
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
