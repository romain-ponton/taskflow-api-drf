from django.contrib import admin
from django.utils import timezone
from django.urls import path
from django.template.response import TemplateResponse
from .models import Task, Need, NeedTrace, Project

# ---------------- Admin existants ----------------
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'created_at')
    search_fields = ('title', 'status')

@admin.register(Need)
class NeedAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'is_validated', 'created_at')
    search_fields = ('title', 'status')
    list_filter = ('status', 'is_validated')

@admin.register(NeedTrace)
class NeedTraceAdmin(admin.ModelAdmin):
    list_display = ('need', 'user', 'old_status', 'new_status', 'old_validated', 'new_validated', 'timestamp')
    search_fields = ('need__title', 'user__username')
    list_filter = ('new_status', 'new_validated')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')

# ---------------- Personnalisation du site ----------------
admin.site.site_header = "TaskFlow – Administration"
admin.site.site_title = "TaskFlow Admin"
admin.site.index_title = "Tableau de bord – Gestion des tâches"

# ---------------- Tableau de bord enrichi ----------------
def dashboard_view(request):
    today = timezone.now().date()

    # Tâches et besoins créés aujourd'hui
    new_tasks = Task.objects.filter(created_at__date=today)
    new_needs = Need.objects.filter(created_at__date=today)

    # Couleurs par status
    board_colors = {
        'À faire': '#f39c12',
        'En cours': '#3498db',
        'Fait': '#2ecc71',
        'Nouveau': '#9b59b6',
    }

    # Organiser les tâches par status et sérialiser pour JSON
    tasks_by_status = {}
    for status in ['À faire', 'En cours', 'Fait', 'Nouveau']:
        tasks = new_tasks.filter(status=status)
        tasks_by_status[status] = {
            'tasks': [
                {
                    'id': t.id,
                    'title': t.title,
                    'owner': t.owner.username if t.owner else None
                } for t in tasks
            ],
            'color': board_colors.get(status, 'gray')
        }

    context = {
        **admin.site.each_context(request),
        'today': today,
        'total_tasks_today': new_tasks.count(),
        'total_needs_today': new_needs.count(),
        'tasks_by_status': tasks_by_status,
        'new_needs': new_needs,
    }

    return TemplateResponse(request, "admin/dashboard.html", context)

# ---------------- Remplacer l’URL index par le dashboard ----------------
def get_admin_urls(urls):
    def get_urls():
        return [path('', dashboard_view, name='dashboard')] + urls
    return get_urls

admin.site.get_urls = get_admin_urls(admin.site.get_urls())
