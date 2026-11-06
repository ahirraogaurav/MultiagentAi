
from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    # Main chatbot homepage
    path("", views.index, name="index"),

    # Authentication
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),

    # Conversations
    path(
        "api/conversations/",
        views.conversations,
        name="conversations",
    ),
    path(
        "api/conversations/<int:pk>/",
        views.conversation_detail,
        name="conversation_detail",
    ),

    # Search
    path(
        "api/search/",
        views.search,
        name="search",
    ),

    # Projects
    path(
        "api/projects/",
        views.projects,
        name="projects",
    ),
    path(
        "api/projects/<int:pk>/",
        views.project_detail,
        name="project_detail",
    ),

    # Code artifacts
    path(
        "api/artifacts/",
        views.artifacts,
        name="artifacts",
    ),

    # Profile and customization
    path(
        "api/profile/",
        views.profile,
        name="profile",
    ),

    # AI chat streaming
    path(
        "api/chat/",
        views.chat_stream,
        name="chat_stream",
    ),
    path("api/messages/<int:message_id>/feedback/", views.message_feedback, name="message_feedback"),
    path("feedback/<int:message_id>/", views.message_feedback, name="message_feedback"),
]
