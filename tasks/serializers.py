from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Task, Need, NeedTrace, TaskLink, Attachment, Project, ProjectMember


# ----------------------------
# USER (utilisé pour owner/reporter)
# ----------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


# ----------------------------
# PROJECT SERIALIZER
# ----------------------------
class ProjectMemberSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = ProjectMember
        fields = ["id", "username", "role"]


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    progression = serializers.ReadOnlyField()
    members = ProjectMemberSerializer(source="projectmember_set", many=True, read_only=True)

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ["owner", "created_at", "progression"]



# ----------------------------
# ATTACHMENT SERIALIZER
# ----------------------------
class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "file", "url", "uploaded_at", "uploaded_by", "task"]
        read_only_fields = ["uploaded_at", "uploaded_by", "url"]

    def get_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


# ----------------------------
# TASK LINK SERIALIZER
# ----------------------------
class TaskLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskLink
        fields = ["id", "src_task", "dst_task", "link_type", "created_at"]
        read_only_fields = ["created_at"]

    def validate(self, data):
        if data["src_task"] == data["dst_task"]:
            raise serializers.ValidationError("Impossible de créer un lien vers soi-même.")
        return data


# ----------------------------
# TASK SERIALIZER
# ----------------------------
class TaskSerializer(serializers.ModelSerializer):

    owner = UserSerializer(read_only=True)
    reporter = UserSerializer(read_only=True)

    # liens + pièces jointes + sous-tâches
    children = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)
    links = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = "__all__"

    def get_children(self, obj):
        return TaskSerializer(obj.children.all(), many=True).data

    def get_links(self, obj):
        return [
            {
                "id": l.id,
                "type": l.link_type,
                "src": l.src_task_id,
                "dst": l.dst_task_id,
            }
            for l in obj.links_from.all()
        ]


# ----------------------------
# NEED SERIALIZER
# ----------------------------
class NeedSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Need
        fields = "__all__"
        read_only_fields = ["owner", "created_at"]


# ----------------------------
# NEED TRACE SERIALIZER
# ----------------------------
class NeedTraceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = NeedTrace
        fields = "__all__"
