import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from tasks.models import Task, Need, Project, Attachment, TaskLink

@pytest.mark.django_db
def test_full_taskflow(users, tmp_path):
    # -----------------------------
    # Utilisateurs et projet
    # -----------------------------
    romain = users['romain']
    tata = users['tata']
    toto = users['toto']

    client = APIClient()
    client.force_authenticate(user=romain)

    project = Project.objects.create(name="Project Test", owner=romain)

    # -----------------------------
    # Création de plusieurs tâches
    # -----------------------------
    tasks_data = [
        {"title": "Epic du Jour", "status": "Nouveau", "type": "epic", "priority": "high", "owner": romain.id, "reporter": romain.id, "project": project.id},
        {"title": "User Story Intégration", "status": "À faire", "type": "story", "priority": "medium", "owner": tata.id, "reporter": tata.id, "project": project.id},
        {"title": "Feature Auth", "status": "En cours", "type": "feature", "priority": "urgent", "owner": toto.id, "reporter": toto.id, "project": project.id},
        {"title": "Sous-tâche Front", "status": "À faire", "type": "subtask", "priority": "low", "owner": romain.id, "reporter": tata.id, "project": project.id},
        {"title": "Backend API", "status": "Fait", "type": "task", "priority": "high", "owner": tata.id, "reporter": romain.id, "project": project.id},
    ]

    resp = client.post('/api/tasks/', {"tasks": tasks_data}, format='json')
    assert resp.status_code == 201
    created_tasks = Task.objects.filter(project=project)
    assert created_tasks.count() == 5

    # -----------------------------
    # Vérification des owners et statuts
    # -----------------------------
    for t_data in tasks_data:
        t = Task.objects.get(title=t_data["title"])
        assert t.owner.id == t_data["owner"]
        assert t.status == t_data["status"]
        assert t.type == t_data["type"]
        assert t.priority == t_data["priority"]

    # -----------------------------
    # Création de lien parent/enfant et "blocks"
    # -----------------------------
    parent_task = Task.objects.get(title="Epic du Jour")
    child_task = Task.objects.get(title="User Story Intégration")
    child_task.parent = parent_task
    child_task.save()

    resp_link = client.post(f'/api/tasks/{parent_task.id}/link/', {"target": child_task.id, "type": "blocks"}, format='json')
    assert resp_link.status_code == 201
    link = TaskLink.objects.get(src_task=parent_task, dst_task=child_task)
    assert link.link_type == "blocks"

    # -----------------------------
    # Upload d'un fichier sur une tâche
    # -----------------------------
    task_file = Task.objects.get(title="Feature Auth")
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello TaskFlow")

    with open(test_file, 'rb') as f:
        resp_upload = client.post(f'/api/tasks/{task_file.id}/upload/', {'file': f}, format='multipart')

    assert resp_upload.status_code == 201
    attachment = Attachment.objects.get(task=task_file)
    assert attachment.file.name.endswith("test.txt")

    # -----------------------------
    # Création d'un besoin validé -> génère une tâche
    # -----------------------------
    need_data = {
        "title": "Besoin Critique",
        "status": "À faire",
        "is_validated": True
    }
    resp_need = client.post('/api/needs/', need_data, format='json')
    assert resp_need.status_code == 201
    need = Need.objects.get(title="Besoin Critique")

    # Vérifier que la tâche automatique a été créée
    auto_task = Task.objects.filter(title=need.title, owner=romain).first()
    assert auto_task is not None
    assert auto_task.status == "À faire"
