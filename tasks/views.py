from rest_framework.exceptions import APIException
from rest_framework import status, filters, viewsets
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Task, Need, NeedTrace, TaskLink, Attachment
from .serializers import TaskSerializer, NeedSerializer, TaskLinkSerializer, AttachmentSerializer

# ============================================================================ #
# EXCEPTION MÉTIER
# ============================================================================ #
class BusinessRuleException(APIException):
    status_code = 400
    default_detail = "Règle métier non respectée."


# ============================================================================ #
# TASK VIEWSET AVANCÉ
# ============================================================================ #
class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by('-id')
    serializer_class = TaskSerializer

    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['title', 'status']
    ordering_fields = ['created_at', 'title']
    filterset_fields = ['status']

    # ----------------- CREATE -----------------
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"message": "Tâche créée", "data": serializer.data}, status=status.HTTP_201_CREATED)
# ----------------- OVERRIDE perform_create POUR OWNER -----------------
    def perform_create(self, serializer):
        """
        Assigne automatiquement l'owner si l'utilisateur est authentifié
        et si owner n'est pas fourni dans les données.
        """
        if not serializer.validated_data.get('owner') and self.request.user.is_authenticated:
            serializer.save(owner=self.request.user)
        else:
            serializer.save()

    # ----------------- DESTROY -----------------
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == "En cours":
            raise BusinessRuleException("Impossible de supprimer une tâche 'En cours'.")
        return super().destroy(request, *args, **kwargs)

    # ----------------- CHILDREN -----------------
    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        task = self.get_object()
        children = task.children.all()
        serializer = TaskSerializer(children, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ----------------- LINK -----------------
    @action(detail=True, methods=["post"])
    def link(self, request, pk=None):
        src = self.get_object()
        target_id = request.data.get("target")
        link_type = request.data.get("type")

        if not target_id or not link_type:
            return Response({"error": "Champs requis : target, type"}, status=status.HTTP_400_BAD_REQUEST)

        dst = get_object_or_404(Task, pk=target_id)
        payload = {"src_task": src.id, "dst_task": dst.id, "link_type": link_type}

        serializer = TaskLinkSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                link = serializer.save()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TaskLinkSerializer(link).data, status=status.HTTP_201_CREATED)

    # ----------------- UPLOAD -----------------
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request, pk=None):
        task = self.get_object()
        file = request.FILES.get("file", None)

        if not file:
            return Response({"error": "Aucun fichier envoyé."}, status=status.HTTP_400_BAD_REQUEST)

        attachment = Attachment(task=task, file=file, uploaded_by=request.user if request.user.is_authenticated else None)
        attachment.save()
        serializer = AttachmentSerializer(attachment, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ----------------- KANBAN -----------------
    @action(detail=False, methods=["get"])
    def kanban(self, request):
        project_id = request.query_params.get("project")
        qs = self.queryset
        if project_id:
            qs = qs.filter(project_id=project_id)

        board = {"À faire": [], "En cours": [], "Fait": [], "Nouveau": []}
        for task in qs:
            board.get(task.status, []).append(TaskSerializer(task).data)

        return Response(board, status=status.HTTP_200_OK)

    # ----------------- GANTT -----------------
    @action(detail=False, methods=["get"])
    def gantt(self, request):
        project_id = request.query_params.get("project")
        qs = self.queryset.filter(start_date__isnull=False, due_date__isnull=False)
        if project_id:
            qs = qs.filter(project_id=project_id)

        result = [
            {
                "id": t.id,
                "title": t.title,
                "start_date": t.start_date,
                "due_date": t.due_date,
                "progress": t.progress,
                "parent": t.parent_id,
            }
            for t in qs
        ]
        return Response(result, status=status.HTTP_200_OK)


# ============================================================================ #
# NEED VIEWSET
# ============================================================================ #
class NeedViewSet(viewsets.ModelViewSet):
    queryset = Need.objects.all().order_by('-id')
    serializer_class = NeedSerializer

    # ----------------- CREATE -----------------
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"message": "Besoin créé", "data": serializer.data}, status=status.HTTP_201_CREATED, headers=headers)

    # ----------------- UPDATE + TRACE -----------------
    def perform_update(self, serializer):
        instance = serializer.instance
        old_status = instance.status
        old_validated = instance.is_validated

        need = serializer.save()
        new_status = need.status
        new_validated = need.is_validated

        # Trace historique
        NeedTrace.objects.create(
            need=need,
            user=self.request.user if self.request.user.is_authenticated else None,
            old_status=old_status,
            new_status=new_status,
            old_validated=old_validated,
            new_validated=new_validated,
        )

        # Création automatique d'une tâche si besoin validé
        if not old_validated and new_validated and new_status == "À faire":
            if not Task.objects.filter(title=need.title, owner=need.owner).exists():
                task = Task.objects.create(
                    title=need.title,
                    status="À faire",
                    owner=need.owner or (self.request.user if self.request.user.is_authenticated else None),
                )
                print(f"[TRACE] Tâche auto-créée (id={task.id}) depuis Need {need.id}")

    # ----------------- DESTROY -----------------
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == "En cours":
            raise BusinessRuleException("Impossible de supprimer un besoin 'En cours'.")
        return super().destroy(request, *args, **kwargs)
