from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone

# --- Statuts existants + extension Kanban ---
def validate_status(value):
    allowed = ["À faire", "En cours", "Fait", "Nouveau"]
    if value not in allowed:
        raise ValidationError(f"Statut invalide : {allowed}")

# --- Nouveau : type de tâche ---
TASK_TYPES = [
    ("epic", "Epic"),
    ("story", "User Story"),
    ("feature", "Feature"),
    ("task", "Tâche"),
    ("subtask", "Sous-tâche"),
]

# --- Nouveau : priorité ---
PRIORITY = [
    ("low", "Basse"),
    ("medium", "Moyenne"),
    ("high", "Haute"),
    ("urgent", "Urgente"),
]

# --- Projet ---
class Project(models.Model):
    # Identité
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, default="Default")   # exemple : TF, APP, CRM
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#3B82F6")  # couleur hex
    icon = models.CharField(max_length=50, default="folder")  # nom d'icône (frontend)

    # Organisation
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="owned_projects")
    members = models.ManyToManyField(User, through="ProjectMember", related_name="projects")

    # Gestion du temps
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} – {self.name}"

    @property
    def progression(self):
        """ % des tâches faites """
        tasks = self.tasks.all()
        if not tasks.exists():
            return 0
        done = tasks.filter(status="Fait").count()
        return round((done / tasks.count()) * 100)


class ProjectMember(models.Model):
    ROLE_CHOICES = [
        ("viewer", "Viewer"),
        ("developer", "Developer"),
        ("maintainer", "Maintainer"),
        ("owner", "Owner"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")

    class Meta:
        unique_together = ("user", "project")

    def __str__(self):
        return f"{self.user} – {self.project} ({self.role})"


# --- Tâche ---
class Task(models.Model):
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default="À faire", validators=[validate_status])
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")

    # Métadonnées
    type = models.CharField(max_length=20, choices=TASK_TYPES, default="task")
    priority = models.CharField(max_length=10, choices=PRIORITY, default="medium")
    target_version = models.CharField(max_length=50, blank=True, null=True)
    module = models.CharField(max_length=100, blank=True, null=True)
    reporter = models.ForeignKey(User, related_name="reported_tasks", on_delete=models.SET_NULL, null=True, blank=True)

    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    progress = models.PositiveSmallIntegerField(default=0)

    # Hiérarchie infinie
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="children", null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.parent and self.parent_id == self.id:
            raise ValidationError("Une tâche ne peut pas être son propre parent.")
        ancestor = self.parent
        while ancestor:
            # comparer par pk est plus sûr
            if ancestor.pk == (self.pk or None):
                raise ValidationError("Cycle détecté dans la hiérarchie.")
            ancestor = ancestor.parent
        if not (0 <= self.progress <= 100):
            raise ValidationError("Le champ 'progress' doit être entre 0 et 100.")

    def __str__(self):
        return f"{self.title} (id={self.id})"


# --- Relations entre tâches ---
class TaskLink(models.Model):
    LINK_TYPES = [
        ("blocks", "Bloque"),
        ("depends_on", "Dépend de"),
        ("relates", "Relatif à"),
    ]
    src_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="links_from")
    dst_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="links_to")
    link_type = models.CharField(max_length=20, choices=LINK_TYPES)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("src_task", "dst_task", "link_type")

    def clean(self):
        if self.src_task == self.dst_task:
            raise ValidationError("Impossible de créer un lien vers la même tâche.")

    def __str__(self):
        return f"{self.src_task_id} -> {self.dst_task_id} ({self.link_type})"


# --- Attachments ---
def attachment_path(instance, filename):
    return f"attachments/task_{instance.task.id}/{filename}"


class Attachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=attachment_path)
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Attachment {self.id} for Task {self.task.id}"


# --- Need / NeedTrace ---
class Need(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_validated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="needs")
    status = models.CharField(max_length=20, default="Nouveau", validators=[validate_status])

    def __str__(self):
        return self.title


class NeedTrace(models.Model):
    need = models.ForeignKey(Need, on_delete=models.CASCADE, related_name="traces")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    old_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20, blank=True, null=True)
    old_validated = models.BooleanField(default=False)
    new_validated = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trace Need #{self.need.id} – {self.timestamp:%Y-%m-%d %H:%M:%S}"
