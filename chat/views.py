

import json

import logging

import re

from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.http import JsonResponse, StreamingHttpResponse

from django.shortcuts import render, redirect

from django.views.decorators.http import require_http_methods, require_POST

from . import agents

from .models import Conversation, Message, Profile, Project
from .forms import CustomUserCreationForm

logger = logging.getLogger(__name__)

ARTIFACT_RE = re.compile(

    r"```([\w+#.-]*)\s*\n(.*?)```",

    re.DOTALL,

)

def _body(request):

    """Safely parse a JSON request body."""

    try:

        data = json.loads(request.body or b"{}")

        return data if isinstance(data, dict) else {}

    except (ValueError, TypeError):

        return {}



def register_view(request):
    """Register a new user and log them in."""
    if request.user.is_authenticated:
        return redirect("chat:index")

    form = CustomUserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("chat:index")

    return render(request, "chat/register.html", {"form": form})


def login_view(request):
    """Authenticate a user using their username or email."""
    if request.user.is_authenticated:
        return redirect("chat:index")

    error = ""
    if request.method == "POST":
        identifier = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user_obj = User.objects.filter(email__iexact=identifier).first()
        username = user_obj.username if user_obj else identifier
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("chat:index")

        error = "Invalid username/email or password."

    return render(request, "chat/login.html", {"error": error})


def logout_view(request):
    """Log out the current user; logout is accepted only via POST."""
    if request.method == "POST":
        logout(request)
        return redirect("chat:login")
    return redirect("chat:index")

@login_required(login_url="chat:login")
def index(request):

    """Render the main chat page."""

    user = request.user

    name = user.get_username() if user.is_authenticated else "Guest"

    email = (

        user.email

        if user.is_authenticated and user.email

        else "guest@example.com"

    )

    return render(

        request,

        "chat/index.html",

        {

            "user_name": name,

            "user_email": email,

        },

    )

# ============================================================

# CONVERSATIONS

# ============================================================

@require_http_methods(["GET"])

def conversations(request):

    """Return recent conversations."""

    items = Conversation.objects.all().order_by("-id")[:200]

    return JsonResponse({

        "conversations": [

            {"id": conv.id, "title": conv.title}

            for conv in items

        ]

    })

@require_http_methods(["GET", "DELETE", "PATCH"])

def conversation_detail(request, pk):

    """Load, rename, or delete a conversation."""

    conv = (

        Conversation.objects

        .filter(pk=pk)

        .select_related("project")

        .first()

    )

    if conv is None:

        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "DELETE":

        conv.delete()

        return JsonResponse({"ok": True})

    if request.method == "PATCH":

        data = _body(request)

        title = data.get("title")

        if isinstance(title, str) and title.strip():

            conv.title = title.strip()[:200]

            conv.save(update_fields=["title"])

        return JsonResponse({"ok": True})

    messages = [

        {

            "role": message.role,

            "content": message.content,

            "steps": message.steps,

        }

        for message in conv.messages.all().order_by("id")

    ]

    project = None

    if conv.project:

        project = {

            "id": conv.project.id,

            "name": conv.project.name,

        }

    return JsonResponse({

        "id": conv.id,

        "title": conv.title,

        "messages": messages,

        "project": project,

    })

# ============================================================

# SEARCH

# ============================================================

def _snippet(text, query):

    """Extract a short text snippet around the matching query."""

    index = text.lower().find(query.lower())

    if index < 0:

        return text[:140]

    start = max(0, index - 60)

    end = index + 100

    prefix = "…" if start > 0 else ""

    suffix = "…" if end < len(text) else ""

    return (

        prefix

        + text[start:end].replace("\n", " ")

        + suffix

    )

@require_http_methods(["GET"])

def search(request):

    """Search conversation titles and message contents."""

    query = (request.GET.get("q") or "").strip()

    if not query:

        items = Conversation.objects.all().order_by("-id")[:20]

        return JsonResponse({

            "results": [

                {

                    "id": conv.id,

                    "title": conv.title,

                    "snippet": "",

                }

                for conv in items

            ]

        })

    found = (

        Conversation.objects

        .filter(

            Q(title__icontains=query)

            | Q(messages__content__icontains=query)

        )

        .distinct()

        .order_by("-id")[:50]

    )

    results = []

    for conv in found:

        message = (

            conv.messages

            .filter(content__icontains=query)

            .order_by("id")

            .first()

        )

        results.append({

            "id": conv.id,

            "title": conv.title,

            "snippet": (

                _snippet(message.content, query)

                if message

                else ""

            ),

        })

    return JsonResponse({"results": results})

# ============================================================

# PROJECTS

# ============================================================

def _project(project):

    return {

        "id": project.id,

        "name": project.name,

        "description": project.description,

        "instructions": project.instructions,

        "chat_count": project.conversations.count(),

    }

@require_http_methods(["GET", "POST"])

def projects(request):

    """List projects or create a project."""

    if request.method == "POST":

        data = _body(request)

        name = (data.get("name") or "").strip()

        if not name:

            return JsonResponse(

                {"error": "Name is required"},

                status=400,

            )

        project = Project.objects.create(

            name=name[:120],

            description=(data.get("description") or "")[:300],

            instructions=data.get("instructions") or "",

        )

        return JsonResponse(_project(project), status=201)

    items = Project.objects.all().order_by("id")

    return JsonResponse({

        "projects": [_project(project) for project in items]

    })

@require_http_methods(["GET", "PATCH", "DELETE"])

def project_detail(request, pk):

    """View, update, or delete a project."""

    project = Project.objects.filter(pk=pk).first()

    if project is None:

        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "DELETE":

        project.delete()

        return JsonResponse({"ok": True})

    if request.method == "PATCH":

        data = _body(request)

        if "name" in data:

            name = data.get("name") or ""

            if name.strip():

                project.name = name.strip()[:120]

        if "description" in data:

            project.description = (

                data.get("description") or ""

            )[:300]

        if "instructions" in data:

            project.instructions = data.get("instructions") or ""

        project.save()

    result = _project(project)

    result["chats"] = [

        {"id": conv.id, "title": conv.title}

        for conv in project.conversations.all().order_by("-id")

    ]

    return JsonResponse(result)

# ============================================================

# CODE ARTIFACTS

# ============================================================

@require_http_methods(["GET"])

def artifacts(request):

    """Find code blocks in saved assistant responses."""

    output = []

    messages = (

        Message.objects

        .filter(role="assistant", content__contains="```")

        .select_related("conversation")

        .order_by("-id")[:300]

    )

    for message in messages:

        matches = ARTIFACT_RE.findall(message.content)

        for index, (language, code) in enumerate(matches):

            code = code.rstrip("\n")

            if len(code.splitlines()) < 5:

                continue

            output.append({

                "id": f"{message.id}-{index}",

                "language": language or "text",

                "code": code,

                "title": f"{(language or 'code').capitalize()} snippet",

                "chat": message.conversation.title,

                "conversation_id": message.conversation_id,

            })

    return JsonResponse({"artifacts": output[:100]})

# ============================================================

# PROFILE AND CUSTOMIZATION

# ============================================================

def _profile(profile_obj):

    return {

        "display_name": profile_obj.display_name,

        "instructions": profile_obj.instructions,

        "style": profile_obj.style,

        "disabled_agents": profile_obj.disabled_agents,

        "styles": list(agents.STYLES.keys()),

        "agents": [

            {

                "id": key,

                "name": value["name"],

                "description": value["description"],

            }

            for key, value in agents.AGENTS.items()

        ],

    }

@require_http_methods(["GET", "PATCH"])

def profile(request):

    """Read or update chat preferences."""

    profile_obj = Profile.load()

    if request.method == "PATCH":

        data = _body(request)

        if "display_name" in data:

            profile_obj.display_name = (

                data.get("display_name") or ""

            )[:80]

        if "instructions" in data:

            profile_obj.instructions = (

                data.get("instructions") or ""

            )

        if data.get("style") in agents.STYLES:

            profile_obj.style = data["style"]

        if isinstance(data.get("disabled_agents"), list):

            profile_obj.disabled_agents = [

                item

                for item in data["disabled_agents"]

                if item in agents.AGENTS

            ]

        profile_obj.save()

    return JsonResponse(_profile(profile_obj))

def _extra(profile_obj, project):

    """Build additional instructions for the selected assistant."""

    parts = []

    if profile_obj.display_name:

        parts.append(

            f"The user's preferred name is {profile_obj.display_name}."

        )

    if profile_obj.instructions.strip():

        parts.append(

            "The user's custom instructions:\n"

            + profile_obj.instructions.strip()

        )

    style = agents.STYLES.get(profile_obj.style, "")

    if style:

        parts.append(style)

    if project and project.instructions.strip():

        parts.append(

            f"Instructions for project '{project.name}':\n"

            + project.instructions.strip()

        )

    return "\n\n".join(parts)

# ============================================================

# SERVER-SENT EVENTS

# ============================================================

def _sse(data):

    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

# ============================================================

# CHAT STREAM

# ============================================================

@require_POST

def chat_stream(request):

    """

    Receive a message, call the agent backend, stream events,

    and save the completed assistant response.

    """

    body = _body(request)

    user_text = body.get("message")

    user_text = user_text.strip() if isinstance(user_text, str) else ""

    mode = body.get("agent") or "auto"

    if not user_text:

        return JsonResponse(

            {"error": "Empty message"},

            status=400,

        )

    # Validate the selected agent.

    allowed_modes = set(agents.AGENTS.keys()) | {"auto", "direct"}

    if mode not in allowed_modes:

        mode = "auto"

    # Load the existing conversation, if supplied.

    conv = None

    conversation_id = body.get("conversation_id")

    if conversation_id:

        try:

            conv = (

                Conversation.objects

                .filter(pk=conversation_id)

                .select_related("project")

                .first()

            )

        except (ValueError, TypeError):

            conv = None

    # Otherwise, create a new conversation.

    if conv is None:

        project = None

        project_id = body.get("project_id")

        if project_id:

            try:

                project = Project.objects.filter(pk=project_id).first()

            except (ValueError, TypeError):

                project = None

        conv = Conversation.objects.create(

            title=user_text[:60],

            project=project,

        )

    # Save the incoming user message.

    Message.objects.create(

        conversation=conv,

        role="user",

        content=user_text,

    )

    # Build model history in chronological order.

    history = [

        {

            "role": message.role,

            "content": message.content,

        }

        for message in conv.messages.all().order_by("id")

    ]

    profile_obj = Profile.load()

    extra = _extra(profile_obj, conv.project)

    disabled_agents = profile_obj.disabled_agents or []

    enabled = [

        key

        for key in agents.AGENTS

        if key not in disabled_agents

    ]

    def events():

        yield _sse({

            "type": "meta",

            "conversation_id": conv.id,

            "title": conv.title,

        })

        answer_parts = []

        steps = {}

        try:

            for event in agents.run(

                history,

                mode,

                extra,

                enabled,

            ):

                event_type = event.get("type")

                if event_type == "delta":

                    chunk = event.get(

                        "text",

                        event.get("content", ""),

                    )

                    if isinstance(chunk, str) and chunk:

                        answer_parts.append(chunk)

                elif event_type == "step":

                    # Error and done events may not contain an agent.

                    agent_name = event.get("agent", "system")

                    steps[agent_name] = event

                elif event_type == "error":

                    logger.error(

                        "Agent backend error: %s",

                        event.get("message", "Unknown error"),

                    )

                yield _sse(event)

        except Exception:

            logger.exception("Chat streaming failed")

            yield _sse({

                "type": "error",

                "message": (

                    "The assistant encountered an error. "

                    "Check the Django server terminal for details."

                ),

            })

        finally:

            answer = "".join(answer_parts)

            # Persist only non-empty assistant responses.

            if answer.strip():

                Message.objects.create(

                    conversation=conv,

                    role="assistant",

                    content=answer,

                    steps=list(steps.values()),

                )

                conv.save()

        yield _sse({"type": "done"})

    response = StreamingHttpResponse(

        events(),

        content_type="text/event-stream",

    )

    response["Cache-Control"] = "no-cache"

    response["X-Accel-Buffering"] = "no"

    return response
