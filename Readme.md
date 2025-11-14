# TaskFlow API

## 1. Description

**TaskFlow** est une API REST de gestion de projet inspirée de Jira et YouTrack.
Elle permet de gérer des tâches hiérarchiques, avec relations entre tâches, métadonnées avancées, et vues Kanban/Gantt.

Fonctionnalités principales :

* Types de tâches : Epic, User Story, Feature, Tâche, Sous-tâche
* Hiérarchie infinie (parent → enfants)
* Relations entre tâches : bloque, dépend de, relatif à
* Métadonnées : priorité, version cible, module, rapporteur
* Upload de fichiers/screenshots pour une tâche
* Vues projet : Kanban et Gantt
* Gestion des besoins (Need) avec trace d’historique

---

## 2. Installation

### Prérequis

* Python 3.10+
* Django 4.x
* Django REST Framework
* Django Filter
* drf-yasg (Swagger / Redoc)

### Installation

```bash
# Cloner le projet
git clone <url-du-projet>
cd taskflow-api

# Créer et activer l'environnement virtuel
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows

# Installer les dépendances
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Créer un superuser
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver
```

---

## 3. Endpoints API

Base URL : `/api/`

### 3.1 Tasks

| Endpoint                      | Méthode | Description                                  |
| ----------------------------- | ------- | -------------------------------------------- |
| `/tasks/`                     | GET     | Liste toutes les tâches                      |
| `/tasks/`                     | POST    | Crée une tâche                               |
| `/tasks/{id}/`                | GET     | Détail d’une tâche                           |
| `/tasks/{id}/`                | PATCH   | Met à jour une tâche                         |
| `/tasks/{id}/`                | DELETE  | Supprime une tâche (sauf si "En cours")      |
| `/tasks/{id}/children/`       | GET     | Récupère les sous-tâches                     |
| `/tasks/{id}/link/`           | POST    | Crée un lien entre tâches (`target`, `type`) |
| `/tasks/{id}/upload/`         | POST    | Upload d’un fichier (`file`)                 |
| `/tasks/kanban/?project=<id>` | GET     | Vue Kanban filtrée par projet                |
| `/tasks/gantt/?project=<id>`  | GET     | Vue Gantt filtrée par projet                 |

### 3.2 Needs

| Endpoint               | Méthode | Description                          |
| ---------------------- | ------- | ------------------------------------ |
| `/needs/`              | GET     | Liste tous les besoins               |
| `/needs/`              | POST    | Crée un besoin                       |
| `/needs/{id}/`         | GET     | Détail d’un besoin                   |
| `/needs/{id}/`         | PATCH   | Met à jour un besoin + trace         |
| `/needs/{id}/destroy/` | POST    | Supprime un besoin (sauf "En cours") |

---

## 4. Exemples JSON

### 4.1 Créer une tâche

```json
{
  "title": "Nouvelle tâche",
  "status": "À faire",
  "type": "task",
  "priority": "medium",
  "module": "API",
  "target_version": "v1.0",
  "owner": 1,
  "reporter": 2,
  "parent": null,
  "project": 1,
  "start_date": "2025-11-15",
  "due_date": "2025-11-30",
  "progress": 0
}
```

### 4.2 Créer un lien entre tâches

```json
{
  "target": 2,
  "type": "blocks"
}
```

### 4.3 Upload d’un fichier

* Form-data : `file=<fichier>`
* Réponse : JSON avec URL du fichier

---

## 5. Tests

### 5.1 Tests unitaires

* Utiliser `pytest` et `pytest-django`
* Exemple :

```bash
pytest tasks/tests.py
```

### 5.2 Cas de tests fonctionnels

* Hiérarchie : `children` renvoie bien toutes les sous-tâches
* Lien : `link` interdit self-link et duplicata
* Kanban : renvoie les colonnes correctes
* Gantt : renvoie toutes les tâches avec dates et progress
* Upload : vérifie la présence de l’URL dans le JSON

---

## 6. Documentation Swagger / Redoc

* Swagger UI : `/swagger/`
* Redoc : `/redoc/`
* JSON Schema : `/swagger.json/`

---

## 7. Points à améliorer / extensions possibles

* Authentification avancée et permissions
* Assignation multiple
* Commentaires et historique des modifications
* Filtres avancés sur Kanban/Gantt


