import os
import requests
import streamlit as st

st.set_page_config(page_title="TaskFlow – Kanban simulé", layout="wide")
st.title("TaskFlow – Kanban (simulé)")

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
API_TIMEOUT = 8

ALL_STATUSES = ["Nouveau", "À faire", "En cours", "Fait"]
PRIORITY_COLOR = {
    "low": "#d3f9d8",
    "medium": "#fff3bf",
    "high": "#ffc9c9",
    "urgent": "#ff6b6b"
}
PRIORITY_KEYS = list(PRIORITY_COLOR.keys())

# =========================
# API helpers
# =========================
@st.cache_data(ttl=15)
def fetch_tasks():
    url = f"{API_BASE}/api/tasks/"
    resp = requests.get(url, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def create_task(title: str, task_type: str, priority: str):
    url = f"{API_BASE}/api/tasks/"
    payload = {"title": title, "type": task_type, "priority": priority, "status": "Nouveau"}
    resp = requests.post(url, json=payload, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def update_task_status(task_id: int, new_status: str):
    url = f"{API_BASE}/api/tasks/{task_id}/"
    resp = requests.patch(url, json={"status": new_status}, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()

# =========================
# SESSION STATE
# =========================
if "tasks" not in st.session_state:
    try:
        st.session_state.tasks = fetch_tasks()
    except Exception as e:
        st.error(f"Impossible de récupérer les tâches: {e}")
        st.session_state.tasks = []

# =========================
# SIDEBAR: Filtrage + création
# =========================
st.sidebar.subheader("Filtrer les tâches")
status_filter = st.sidebar.multiselect("Statuts", ALL_STATUSES, default=ALL_STATUSES)
priority_filter = st.sidebar.multiselect("Priorités", PRIORITY_KEYS, default=PRIORITY_KEYS)

st.sidebar.markdown("---")
st.sidebar.subheader("Créer une nouvelle tâche")
with st.sidebar.form("new_task"):
    new_title = st.text_input("Titre")
    new_type = st.selectbox("Type", ["task", "story", "subtask", "feature", "epic"])
    new_priority = st.selectbox("Priorité", PRIORITY_KEYS, index=1)
    submitted = st.form_submit_button("Créer")
    if submitted:
        if not new_title.strip():
            st.warning("Donne un titre à la tâche.")
        else:
            try:
                task = create_task(new_title.strip(), new_type, new_priority)
                st.session_state.tasks.append(task)
                st.success("Tâche créée.")
            except Exception as e:
                st.error(f"Erreur création tâche : {e}")

# =========================
# Filtrage côté Python
# =========================
def get_filtered_tasks():
    return [
        t for t in st.session_state.tasks
        if (t.get("status") in status_filter) and (t.get("priority") in priority_filter)
    ]

filtered_tasks = get_filtered_tasks()

# =========================
# Metrics
# =========================
st.subheader("Résumé des tâches")
col1, col2, col3 = st.columns(3)
col1.metric("Total", len(filtered_tasks))
col2.metric("En cours", len([t for t in filtered_tasks if t.get("status") == "En cours"]))
col3.metric("Terminé", len([t for t in filtered_tasks if t.get("status") == "Fait"]))

# =========================
# Kanban simulé
# =========================
cols = st.columns(len(ALL_STATUSES))
for i, status in enumerate(ALL_STATUSES):
    with cols[i]:
        st.markdown(f"### {status}")
        tasks_in_status = [t for t in filtered_tasks if t["status"] == status]
        for idx, task in enumerate(tasks_in_status):
            # Affichage tâche
            st.markdown(
                f"<div style='padding:8px;margin-bottom:6px;border-radius:6px;background:{PRIORITY_COLOR.get(task['priority'],'#eee')};'>"
                f"<b>#{task['id']}</b> {task['title']}<br>"
                f"<small>{task['type']} | {task['priority']}</small></div>", unsafe_allow_html=True
            )

            # Selectbox pour déplacer la tâche (clé unique)
            new_status = st.selectbox(
                f"Déplacer #{task['id']}_{status}_{idx}",
                [status] + [s for s in ALL_STATUSES if s != status],
                key=f"move_{task['id']}_{status}_{idx}"
            )

            # Bouton pour déposer la tâche (clé unique)
            if st.button("Déposé ici", key=f"btn_{task['id']}_{status}_{idx}"):
                if new_status != status:
                    try:
                        update_task_status(task["id"], new_status)
                        # Mise à jour locale
                        for t in st.session_state.tasks:
                            if t["id"] == task["id"]:
                                t["status"] = new_status
                        # Recalcul immédiat des tâches filtrées
                        filtered_tasks = get_filtered_tasks()
                        st.success(f"Tâche #{task['id']} déplacée en '{new_status}'")
                        st.experimental_rerun = lambda: None  # workaround pour Streamlit 1.51+
                    except Exception as e:
                        st.error(f"Erreur lors du déplacement : {e}")
