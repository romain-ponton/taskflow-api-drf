import os
import requests
import streamlit as st

# -----------------------------
# Config Streamlit
# -----------------------------
st.set_page_config(page_title="TaskFlow – Kanban Drag & Drop", layout="wide")
st.title("TaskFlow – Kanban (Trello-like)")

# Backend local par defaut. Surcharger avec API_BASE en production.
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
API_TIMEOUT = 20  # Timeout plus long pour éviter les erreurs

ALL_STATUSES = ["Nouveau", "À faire", "En cours", "Fait"]
ALL_TYPES = ["task", "story", "subtask", "feature", "epic"]
ALL_PRIORITIES = ["low", "medium", "high", "urgent"]

PRIORITY_COLOR = {"low":"#d3f9d8","medium":"#fff3bf","high":"#ffc9c9","urgent":"#ff6b6b"}
STATUS_BG_COLOR = {"Nouveau":"#f8f9fa","À faire":"#e0f7fa","En cours":"#fff3e0","Fait":"#e8f5e9"}

# -----------------------------
# Session State
# -----------------------------
if "tasks" not in st.session_state: st.session_state.tasks = []
if "selected_task" not in st.session_state: st.session_state.selected_task = None
if "token" not in st.session_state: st.session_state.token = None

# -----------------------------
# Sidebar – login
# -----------------------------
st.sidebar.subheader("Connexion API")
if st.session_state.token is None:
    with st.sidebar.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        login_btn = st.form_submit_button("Se connecter")
        if login_btn:
            try:
                resp = requests.post(
                    f"{API_BASE}/api/token/",
                    json={"username": username, "password": password},
                    timeout=API_TIMEOUT
                )
                resp.raise_for_status()
                st.session_state.token = resp.json()["access"]
                st.success("Connecté avec succès !")
                st.rerun()
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion : {e}")
else:
    st.sidebar.success("Connecté à l'API")

# -----------------------------
# API
# -----------------------------
def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}

@st.cache_data(ttl=30)
def fetch_tasks():
    if st.session_state.token is None:
        return []
    try:
        tasks = []
        url = f"{API_BASE}/api/tasks/"
        while url:
            resp = requests.get(url, headers=get_headers(), timeout=API_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, dict) and "results" in payload:
                tasks.extend(payload["results"])
                url = payload.get("next")
            elif isinstance(payload, list):
                tasks.extend(payload)
                url = None
            else:
                return []
        return tasks
    except requests.exceptions.RequestException as e:
        st.error(f"Impossible de récupérer les tâches : {e}")
        return []

def extract_task(payload):
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    if isinstance(payload, dict):
        return payload
    return None

def create_task(title: str, task_type: str, priority: str):
    if st.session_state.token is None:
        st.error("Veuillez vous connecter pour créer une tâche")
        return None
    try:
        resp = requests.post(
            f"{API_BASE}/api/tasks/",
            json={"title": title, "type": task_type, "priority": priority, "status": "Nouveau"},
            headers=get_headers(),
            timeout=API_TIMEOUT
        )
        resp.raise_for_status()
        return extract_task(resp.json())
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur API lors de la création : {e}")
        return None

def update_task_status(task_id: int, status: str):
    if st.session_state.token is None:
        st.error("Veuillez vous connecter pour déplacer une tâche")
        return None
    try:
        url = f"{API_BASE}/api/tasks/{task_id}/"
        resp = requests.patch(url, json={"status": status}, headers=get_headers(), timeout=API_TIMEOUT)
        resp.raise_for_status()
        return extract_task(resp.json())
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur API lors du déplacement : {e}")
        return None

# -----------------------------
# Récupérer les tâches
# -----------------------------
if st.session_state.token and not st.session_state.tasks:
    st.session_state.tasks = fetch_tasks()

if isinstance(st.session_state.tasks, dict):
    st.session_state.tasks = st.session_state.tasks.get("results", [])

# -----------------------------
# Sidebar – création tâche
# -----------------------------
st.sidebar.subheader("Nouvelle tâche")
with st.sidebar.form("new_task"):
    new_title = st.text_input("Titre")
    new_type = st.selectbox("Type", ALL_TYPES)
    new_priority = st.selectbox("Priorité", ALL_PRIORITIES)
    if st.form_submit_button("Créer"):
        task = create_task(new_title, new_type, new_priority)
        if task:
            st.session_state.tasks.append(task)
            st.success("Tâche créée !")
            st.rerun()

# -----------------------------
# Sidebar – filtres
# -----------------------------
st.sidebar.subheader("Filtres")
filter_type = st.sidebar.multiselect("Filtrer par type", options=ALL_TYPES, default=ALL_TYPES)
filter_priority = st.sidebar.multiselect("Filtrer par priorité", options=ALL_PRIORITIES, default=ALL_PRIORITIES)

# Appliquer le filtrage
filtered_tasks = [
    t for t in st.session_state.tasks
    if isinstance(t, dict) and t.get("type") in filter_type and t.get("priority") in filter_priority
]

# -----------------------------
# Metrics
# -----------------------------
st.subheader("Résumé des tâches")
cols = st.columns(3)
tasks = [t for t in st.session_state.tasks if isinstance(t, dict)]
cols[0].metric("Total", len(tasks))
cols[1].metric("En cours", len([t for t in tasks if isinstance(t, dict) and t.get("status")=="En cours"]))
cols[2].metric("Terminé", len([t for t in tasks if t["status"]=="Fait"]))

# -----------------------------
# Kanban
# -----------------------------
st.subheader("Kanban")
cols = st.columns(len(ALL_STATUSES))

for idx, status in enumerate(ALL_STATUSES):
    with cols[idx]:
        st.markdown(f"### {status}")
        for task in [t for t in filtered_tasks if t.get("status")==status]:
            color = PRIORITY_COLOR.get(task.get("priority"), STATUS_BG_COLOR.get(status, "#fff"))
            st.markdown(
                f"<div style='background:{color};padding:10px;border-radius:10px;margin-bottom:10px'>"
                f"<b>#{task['id']} – {task['title']}</b><br>"
                f"<span style='background:#007bff;color:white;padding:2px 6px;border-radius:4px;font-size:12px'>{task.get('type')}</span> "
                f"<span style='background:{PRIORITY_COLOR.get(task.get('priority'), '#fff')};color:black;padding:2px 6px;border-radius:4px;font-size:12px'>{task.get('priority')}</span>"
                f"</div>", unsafe_allow_html=True
            )
            if st.button(f"Déplacer #{task['id']}", key=f"select_{task['id']}"):
                st.session_state.selected_task = task['id']

        if st.session_state.selected_task and st.session_state.selected_task not in [t.get("id") for t in filtered_tasks if t.get("status")==status]:
            if st.button(f"Déposer ici", key=f"drop_{status}"):
                updated = update_task_status(st.session_state.selected_task, status)
                if updated:
                    for i, t in enumerate(st.session_state.tasks):
                        if isinstance(t, dict) and t.get("id") == updated.get("id"):
                            st.session_state.tasks[i] = updated
                            break
                    st.session_state.selected_task = None
                    st.success("Tâche déplacée !")
                    st.rerun()
