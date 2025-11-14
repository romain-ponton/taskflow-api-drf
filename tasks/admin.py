from django.contrib import admin
from django.utils import timezone
from django.template.response import TemplateResponse
from .models import Task, Need, NeedTrace

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'created_at', 'owner')
    search_fields = ('title', 'status')
    list_filter = ('status', 'type', 'priority')


@admin.register(Need)
class NeedAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'is_validated', 'created_at', 'owner')
    search_fields = ('title', 'status')
    list_filter = ('status', 'is_validated')


@admin.register(NeedTrace)
class NeedTraceAdmin(admin.ModelAdmin):
    list_display = ('need', 'user', 'old_status', 'new_status', 'old_validated', 'new_validated', 'timestamp')
    search_fields = ('need__title', 'user__username')
    list_filter = ('new_status', 'new_validated')


# ------------------ Dashboard personnalisé ------------------
class TaskFlowAdmin(admin.AdminSite):
    site_header = "TaskFlow – Administration"
    site_title = "TaskFlow Admin"
    index_title = "Tableau de bord – Gestion des tâches"

    def index(self, request, extra_context=None):
        today = timezone.now().date()
        new_tasks = Task.objects.filter(created_at__date=today)
        new_needs = Need.objects.filter(created_at__date=today)

        # Regrouper les tâches par phase
        tasks_by_status = {}
        for status in ['À faire', 'En cours', 'Fait', 'Nouveau']:
            tasks_by_status[status] = new_tasks.filter(status=status)

        extra_context = extra_context or {}
        extra_context.update({
            'new_tasks': new_tasks,
            'tasks_by_status': tasks_by_status,
            'new_needs': new_needs,
            'today': today,
            'total_tasks_today': new_tasks.count(),
            'total_needs_today': new_needs.count(),
        })
        return super().index(request, extra_context=extra_context)


# Instanciation de notre site admin personnalisé
taskflow_admin = TaskFlowAdmin(name='taskflow_admin')
taskflow_admin.register(Task, TaskAdmin)
taskflow_admin.register(Need, NeedAdmin)
taskflow_admin.register(NeedTrace, NeedTraceAdmin)
