from django.urls import path
from .views import ChatBotAPIView, StartChatBotAPIView, EndChatBotAPIView

chatbot_routes = [
    path('chat/<uuid:chatbot_session_id>/end/', EndChatBotAPIView.as_view(), name='chatbot_end'),
    path('chat/<uuid:chatbot_session_id>/', ChatBotAPIView.as_view(), name='chatbot_start'),
    path('chat/', StartChatBotAPIView.as_view(), name='chatbot_message'),
]