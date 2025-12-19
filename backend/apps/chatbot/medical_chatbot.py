import re

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from apps.doctors.models import Specialty  # Import your Specialty model
from icecream import ic


# Dictionary to store chat sessions in memory
chat_sessions = {}

MODEL = "gemini-3-flash-preview"

class MedicalChatBot:
    def __init__(self, chatbot_session_id):
        self.chatbot_session_id = chatbot_session_id

        # Initialize conversation history if it doesn't exist
        if chatbot_session_id not in chat_sessions:
            chat_sessions[chatbot_session_id] = [
                SystemMessage(
                    content=(
                        "You are a highly empathetic and professional virtual doctor assistant. "
                        "Your role is to engage with patients in a natural, human-like manner to gather relevant symptom details. "
                        "Follow these strict guidelines:\n\n"
                        "- Ask only one question at a time to keep the conversation smooth and engaging.\n"
                        "- Never suggest a specific doctor or provide direct medical recommendations.\n"
                        "- Your goal is to collect symptoms and determine the most suitable medical specialty.\n"
                        "- Do not discuss anything unrelated to diagnosing the patient.\n"
                        "- Instead of a thorough medical examination, ask enough targeted questions to narrow down the issue efficiently.\n"
                        "- Avoid excessive questioning—focus on key symptoms and quickly reach a conclusion.\n"
                        "- Always use a warm, conversational tone, avoiding robotic phrasing.\n"
                        "- You can communicate in any language the patient prefers, ensuring accessibility and clarity.\n"
                        "- However, when stating the medical specialty, always return it in English, surrounded by triple asterisks (e.g., ***Cardiology***).\n"
                        "- You must never provide the specialty in any other format or language.\n"
                        "- Once you have identified the specialty, clearly indicate the end of the diagnostic process by saying: '[DIAGNOSIS COMPLETE]'."
                    )
                ),
                AIMessage(
                    content="Hello! I'm your virtual health assistant. How are you feeling today?"
                ),
            ]

        # Load conversation history from the dictionary
        self.messages = chat_sessions[chatbot_session_id]

    def chat(self, user_input):
        """Processes user input, generates AI response, and checks for final diagnosis."""
        # Add user input to conversation history
        self.messages.append(HumanMessage(content=user_input))

        # Generate AI response
        model = ChatGoogleGenerativeAI(model=MODEL, temperature=0.5)
        response = model.invoke(self.messages)
        response_text = response.content

        # Store AI's response
        self.messages.append(AIMessage(content=response_text))

        # Check if diagnosis is complete
        if "[DIAGNOSIS COMPLETE]" in response_text:
            ic(response_text)
            specialty = self.extract_specialty(response_text)
            matched_specialty = self.match_specialty_with_ai(specialty)
            return f"Diagnosis: {matched_specialty}"

        # Update the session in the dictionary
        chat_sessions[self.chatbot_session_id] = self.messages

        return response_text

    def extract_specialty(self, response_text):
        """Extracts the specialty from the AI response."""
        match = re.search(r"\*\*\*(.*?)\*\*\*", response_text)
        return match.group(1) if match else None

    def match_specialty_with_ai(self, specialty):
        """Uses AI to match the extracted specialty with the available ones in the Specialty model."""
        if not specialty:
            return "no-specialty"

        # Get all available specialties from the database
        available_specialties = list(Specialty.objects.values_list("name", flat=True))
        if not available_specialties:
            return "no-specialty"

        # Ask AI to match the specialty
        model = ChatGoogleGenerativeAI(model=MODEL, temperature=0.3)
        matching_prompt = (
            f"The identified specialty is '{specialty}'. Here is a list of available specialties: {available_specialties}. "
            "Which specialty from the list best matches the identified specialty? "
            "If there is no close match, respond with 'no-specialty'."
        )
        response = model.invoke(matching_prompt)
        detected_specialty = response.content.strip()
        if detected_specialty == "no-specialty":
            return specialty

        return detected_specialty

    @staticmethod
    def delete_chatbot_session(chatbot_session_id):
        """Delete the session history from memory."""
        if chatbot_session_id in chat_sessions:
            chat_sessions.pop(chatbot_session_id)
