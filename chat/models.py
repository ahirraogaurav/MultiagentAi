from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class Conversation(models.Model):
    title = models.CharField(max_length=200, default="New chat")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=10)  # "user" | "assistant"
    content = models.TextField()
    steps = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class Profile(models.Model):
    """Single-row settings used by the Customize page."""
    display_name = models.CharField(max_length=80, blank=True)
    instructions = models.TextField(blank=True)
    style = models.CharField(max_length=20, default="normal")
    disabled_agents = models.JSONField(default=list, blank=True)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]
