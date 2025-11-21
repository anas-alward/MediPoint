from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .medical_chatbot import MedicalChatBot
from rest_framework.permissions import IsAuthenticated
import uuid
from icecream import ic
from apps.doctors.models import Specialty

CHATBOT_SESSION_ID = "chatbot_session_id"


class StartChatBotAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Generate a unique session ID
        chatbot_session_id = str(uuid.uuid4())
        request.session[CHATBOT_SESSION_ID] = [chatbot_session_id]

        session_data = request.session.get(CHATBOT_SESSION_ID, [])
        ic(session_data)

        # Return the session ID to the user
        return Response(
            {CHATBOT_SESSION_ID: chatbot_session_id}, status=status.HTTP_200_OK
        )


class ChatBotAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Extract session ID from the request
        chatbot_session_id = str(kwargs.get(CHATBOT_SESSION_ID, ""))
        if not chatbot_session_id:
            return Response(
                {"message": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        session_data = request.session.get(CHATBOT_SESSION_ID, [])

        if chatbot_session_id not in session_data:
            return Response(
                {"error": "Chatbot Session with this ID does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract user input from the request
        user_input = request.data.get("message", "").strip()
        if not user_input:
            return Response(
                {"message": "Message is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Initialize or retrieve the chatbot for this session
        chatbot = MedicalChatBot(chatbot_session_id=chatbot_session_id)

        # Get the chatbot response
        try:
            bot_response = chatbot.chat(user_input)
            response = {
                "text": bot_response,
                "is_detected": False
            }
            ic(bot_response)
            if bot_response.startswith("Diagnosis:"):
                extracted_specialty = bot_response[10:].strip()
                ic(extracted_specialty)
                
                specialty = Specialty.objects.filter(name__icontains=extracted_specialty)                
                if specialty.count():
                    specialty_name = specialty[0].name
                    is_existed = True
                else:
                    is_existed = False
                    specialty_name = extracted_specialty
                    
                response['specialty'] = specialty_name
                response['is_existed'] = is_existed
                response["is_detected"] = True

            return Response({"response": response}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EndChatBotAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        chatbot_session_id = str(kwargs.get(CHATBOT_SESSION_ID))
        if not chatbot_session_id:
            return Response(
                {"error": "Chatbot Session ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_data = request.session.get(CHATBOT_SESSION_ID, [])
        if chatbot_session_id not in session_data:
            return Response(
                {"error": "Chatbot Session with this ID does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Delete the session using the MedicalChatBot method
            MedicalChatBot.delete_chatbot_session(chatbot_session_id=chatbot_session_id)
            request.session.pop(CHATBOT_SESSION_ID, None)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
