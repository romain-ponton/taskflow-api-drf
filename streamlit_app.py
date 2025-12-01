import os
import requests
import streamlit as st

# -----------------------------
# Config Streamlit
# -----------------------------
st.set_page_config(page_title="TaskFlow – Kanban Drag & Drop", layout="wide")
st.title("TaskFlow – Kanban (Trello-like)")

# URL du backend (Render ou local)
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
API_TIMEOUT = 8

ALL_STATUSES = ["Nouveau", "À faire", "En cours", "Fait"]

PRIORITY_COLOR = {
    "low": "#d3f9d8",
    "medium": "#fff3bf",
    "high": "#ffc9c9",
    "urgent": "#ff6b6b"
}

STATUS_BG_COLOR = {
    "Nouveau": "#f8f9fa",
    "À faire": "#e0f7fa",
    "En cours": "#fff3e0",
    "Fait": "#e8f5e9"
}

# -----------------------------
# API
# -----------------------------
@st.cache_data(ttl=30)
def fetch_tasks():
    """Récupère la liste des tâches depuis l'API"""
    try:
        resp = requests.get(f"{API_BASE}/api/tasks/", timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Impossible de récupérer les tâches : {e}")
        return []

def update_task_status(task_id: int, status: str):
    """Met à jour le statut d'une tâche via l'API"""
    try:
        url = f"{API_BASE}/api/tasks/{task_id}/"
        payload = {"status": status}
        resp = requests.patch(url, json=payload, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur API lors du déplacement : {e}")
        return None

def create_task(title: str, task_type: str, priority: str):
    """Crée une nouvelle tâche via l'API"""
    try:
        url = f"{API_BASE}/api/tasks/"
        payload = {"title": title, "type": task_type, "priority": priority, "status": "Nouveau"}
        resp = requests.post(url, json=payload, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur API lors de la création : {e}")
        return None

# -----------------------------
# Session State
# -----------------------------
if "tasks" not in st.session_state:
    st.session_state.tasks = fetch_tasks()
if "selected_task" not in st.session_state:
    st.session_state.selected_task = None

# -----------------------------
# Sidebar – Création de tâche
# -----------------------------
st.sidebar.subheader("Nouvelle tâche")
with st.sidebar.form("new_task"):
    new_title = st.text_input("Titre")
    new_type = st.selectbox("Type", ["task", "story", "subtask", "feature", "epic"])
    new_priority = st.selectbox("Priorité", ["low", "medium", "high", "urgent"])
    submitted_task = st.form_submit_button("Créer")
    if submitted_task:
        task = create_task(new_title, new_type, new_priority)
        if task:
            st.session_state.tasks.append(task)
            st.success("Tâche créée !")
            st.experimental_rerun()

# -----------------------------
# Metrics
# -----------------------------
st.subheader("Résumé des tâches")
col1, col2, col3 = st.columns(3)
tasks = st.session_state.tasks
col1.metric("Total", len(tasks))
col2.metric("En cours", len([t for t in tasks if t["status"] == "En cours"]))
col3.metric("Terminé", len([t for t in tasks if t["status"] == "Fait"]))

# -----------------------------
# Kanban Columns
# -----------------------------
st.subheader("Kanban")
cols = st.columns(len(ALL_STATUSES))

for idx, status in enumerate(ALL_STATUSES):
    with cols[idx]:
        st.markdown(f"### {status}")
        for task in [t for t in tasks if t["status"] == status]:
            color = PRIORITY_COLOR.get(task["priority"], STATUS_BG_COLOR.get(status, "#fff"))
            st.markdown(
                f"<div style='background:{color};padding:10px;border-radius:10px;margin-bottom:10px'>"
                f"<b>#{task['id']} – {task['title']}</b><br>"
                f"<span style='background:#007bff;color:white;padding:2px 6px;border-radius:4px;font-size:12px'>{task['type']}</span> "
                f"<span style='background:{PRIORITY_COLOR[task['priority']]};color:black;padding:2px 6px;border-radius:4px;font-size:12px'>{task['priority']}</span>"
                f"</div>", unsafe_allow_html=True
            )
            if st.button(f"Déplacer #{task['id']}", key=f"select_{task['id']}"):
                st.session_state.selected_task = task['id']

        # Bouton "Déposer ici"
        if st.session_state.selected_task and st.session_state.selected_task not in [t["id"] for t in tasks if t["status"] == status]:
            if st.button(f"Déposer ici", key=f"drop_{status}"):
                updated_task = update_task_status(st.session_state.selected_task, status)
                if updated_task:
                    for i, t in enumerate(tasks):
                        if t["id"] == updated_task["id"]:
                            st.session_state.tasks[i] = updated_task
                            break
                    st.session_state.selected_task = None
                    st.success("Tâche déplacée !")
                    st.experimental_rerun()
