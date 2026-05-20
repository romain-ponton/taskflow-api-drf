from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import Need, NeedTrace, Project, Task, TaskLink


@override_settings(ALLOWED_HOSTS=["testserver"])
class AuthTests(APITestCase):
    def test_token_endpoint_returns_jwt_pair_for_valid_credentials(self):
        User.objects.create_user(username="romain", password="pwd12345")

        response = self.client.post(
            "/api/token/",
            {"username": "romain", "password": "pwd12345"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_endpoint_rejects_invalid_credentials(self):
        User.objects.create_user(username="romain", password="pwd12345")

        response = self.client.post(
            "/api/token/",
            {"username": "romain", "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)


@override_settings(ALLOWED_HOSTS=["testserver"])
class TaskApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="romain", password="pwd12345")

    def test_task_list_is_paginated(self):
        Task.objects.create(title="First task")

        response = self.client.get("/api/tasks/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "First task")

    def test_authenticated_task_create_sets_owner(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/tasks/",
            {"title": "Owned task", "status": "Nouveau"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = Task.objects.get(title="Owned task")
        self.assertEqual(task.owner, self.user)
        self.assertEqual(response.data["data"]["owner"]["username"], "romain")

    def test_bulk_task_create_accepts_owner_and_reporter_ids(self):
        reporter = User.objects.create_user(username="reporter", password="pwd12345")
        project = Project.objects.create(name="API", code="API", owner=self.user)

        response = self.client.post(
            "/api/tasks/",
            {
                "tasks": [
                    {
                        "title": "Bulk task",
                        "status": "À faire",
                        "owner": self.user.id,
                        "reporter": reporter.id,
                        "project": project.id,
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = Task.objects.get(title="Bulk task")
        self.assertEqual(task.owner, self.user)
        self.assertEqual(task.reporter, reporter)

    def test_link_endpoint_rejects_self_link(self):
        self.client.force_authenticate(user=self.user)
        task = Task.objects.create(title="Self linked task", owner=self.user)

        response = self.client.post(
            f"/api/tasks/{task.id}/link/",
            {"target": task.id, "type": "blocks"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(TaskLink.objects.exists())


@override_settings(ALLOWED_HOSTS=["testserver"])
class NeedApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="romain", password="pwd12345")
        self.client.force_authenticate(user=self.user)

    def test_need_update_creates_trace_and_task_when_validated(self):
        need = Need.objects.create(title="Validate me", status="Nouveau", owner=self.user)

        response = self.client.patch(
            f"/api/needs/{need.id}/",
            {"status": "À faire", "is_validated": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(NeedTrace.objects.filter(need=need, user=self.user).exists())
        self.assertTrue(Task.objects.filter(title="Validate me", owner=self.user).exists())
