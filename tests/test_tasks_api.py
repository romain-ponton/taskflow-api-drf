import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from tasks.models import Task, Project

# ---------------------------
# Fixture utilisateurs
# ---------------------------
@pytest.fixture
def users(db):
    romain = User.objects.create_user(username="Romain.Ponton", email="romain.ponton3@gmail.com", password="pwd123")
    tata = User.objects.create_user(username="tata", password="pwd123")
    toto = User.objects.create_user(username="toto", email="toto@gmail.com", password="pwd123")
    return {"romain": romain, "tata": tata, "toto": toto}

# ---------------------------
# Tests
# ---------------------------
@pytest.mark.django_db
def test_get_tasks_empty():
    client = APIClient()
    resp = client.get('/api/tasks/')
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.django_db
def test_create_task_anonymous_owner_optional():
    client = APIClient()
    resp = client.post('/api/tasks/', {'title': 'T1', 'status': 'À faire'}, format='json')
    assert resp.status_code == 201
    data = resp.json()['data']
    assert data['title'] == 'T1'

@pytest.mark.django_db
def test_create_task_with_user_sets_owner(users):
    client = APIClient()
    user = users['tata']
    client.force_authenticate(user=user)
    project = Project.objects.create(name="Project 2")
    resp = client.post('/api/tasks/', {
        'title': 'T2',
        'status': 'En cours',
        'type': 'feature',
        'priority': 'high',
        'reporter': user.id,
        'project': project.id
    }, format='json')
    assert resp.status_code == 201
    data = resp.json()['data']
    t = Task.objects.get(title='T2')
    assert t.owner == user

@pytest.mark.django_db
def test_create_task_with_type_priority_and_owner(users):
    client = APIClient()
    romain = users['romain']
    client.force_authenticate(user=romain)
    project = Project.objects.create(name="Project 1")
    resp = client.post('/api/tasks/', {
        'title': 'T3',
        'status': 'À faire',
        'type': 'story',
        'priority': 'medium',
        'reporter': romain.id,
        'project': project.id
    }, format='json')
    assert resp.status_code == 201
    t = Task.objects.get(title='T3')
    assert t.owner == romain
    assert t.type == 'story'
    assert t.priority == 'medium'

@pytest.mark.django_db
def test_task_hierarchy_children_parent(users):
    client = APIClient()
    tata = users['tata']
    client.force_authenticate(user=tata)
    parent_task = Task.objects.create(title="Parent", owner=tata)
    child_task = Task.objects.create(title="Child", owner=tata, parent=parent_task)
    assert child_task.parent == parent_task
    assert parent_task.children.first() == child_task

@pytest.mark.django_db
def test_task_link_creation(users):
    client = APIClient()
    romain = users['romain']
    client.force_authenticate(user=romain)
    t1 = Task.objects.create(title="T1", owner=romain)
    t2 = Task.objects.create(title="T2", owner=romain)
    resp = client.post(f'/api/tasks/{t1.id}/link/', {'target': t2.id, 'type': 'blocks'}, format='json')
    assert resp.status_code == 201

@pytest.mark.django_db
def test_task_upload_attachment(users, tmp_path):
    client = APIClient()
    toto = users['toto']
    client.force_authenticate(user=toto)
    task = Task.objects.create(title="Task with Attachment", owner=toto)
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello")
    with open(test_file, 'rb') as f:
        resp = client.post(f'/api/tasks/{task.id}/upload/', {'file': f})
    assert resp.status_code == 201
