from django.contrib import admin
from .models import Conversation, Message, Profile, Project

for m in (Conversation, Message, Project, Profile):
    admin.site.register(m)
