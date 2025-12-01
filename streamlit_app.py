import os
import uuid
import requests
import streamlit as st

st.set_page_config(page_title="TaskFlow – Kanban", layout="wide")
st.title("TaskFlow – Board (Jira-like)")

# ------------------------------
# CONFIG
# ------------------------------
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
DEMO_MODE = os.getenv("DEMO", "0") == "1"
API_TIMEOUT = 8

# Normalisation des statuts
AUTO_STATUS_CANON = {
    "a faire": "À faire",
    "à faire": "À faire",
    "A faire": "À faire",
    "À faire": "À faire",
    "Nouveau": "Nouveau",
    "En cours": "En cours",
    "Fait": "Fait"
}

# Colonnes Kanban
KANBAN_COLUMNS = {
    "Backlog": ["Nouveau", "À faire"],
    "Sélectionné": ["À faire"],
    "En cours": ["En cours"],
    "Terminé": ["Fait"],
}

# Couleurs par priorité
PRIORITY_COLOR = {
    "low": "#d3f9d8",
    "medium": "#fff3bf",
    "high": "#ffc9c9",
    "urgent": "#ff6b6b"
}

# ------------------------------
# API CALLS
# ------------------------------
@st.cache_data(ttl=30)
def fetch_tasks():
    if DEMO_MODE:
        import json
        with open("demo_tasks.json", "r", encoding="utf-8") as f:
            return json.load(f)
    resp = requests.get(f"{API_BASE}/api/tasks/", timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def update_task_status(task_id: int, status: str):
    url = f"{API_BASE}/api/tasks/{task_id}/"
    payload = {"status": status}
    resp = requests.patch(url, json=payload, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def create_task(title: str, task_type: str, priority: str):
    url = f"{API_BASE}/api/tasks/"
    payload = {"title": title, "type": task_type, "priority": priority, "status": "Nouveau"}
    resp = requests.post(url, json=payload, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()

# ------------------------------
# SIDEBAR – FILTRES + Création
# ------------------------------
st.sidebar.header("Filtres")
with st.sidebar.form("filters"):
    q = st.text_input("Recherche")
    priority_filter = st.selectbox("Priorité", ["", "low", "medium", "high", "urgent"])
    task_type_filter = st.selectbox("Type", ["", "task", "story", "subtask", "feature", "epic"])
    submitted_filter = st.form_submit_button("Appliquer")

st.sidebar.subheader("Nouvelle tâche")
with st.sidebar.form("new_task"):
    new_title = st.text_input("Titre")
    new_type = st.selectbox("Type", ["task", "story", "subtask", "feature", "epic"])
    new_priority = st.selectbox("Priorité", ["low", "medium", "high", "urgent"])
    submitted_task = st.form_submit_button("Créer")
    if submitted_task:
        try:
            create_task(new_title, new_type, new_priority)
            st.success("Tâche créée !")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Erreur création tâche : {e}")

# ------------------------------
# CHARGEMENT DES DONNÉES
# ------------------------------
try:
    tasks = fetch_tasks()
except Exception as e:
    st.error(f"Impossible de joindre l'API : {e}")
    st.stop()

# Normalisation des statuts
for task in tasks:
    raw = task.get("status", "")
    canon = AUTO_STATUS_CANON.get(raw, raw)
    task["status"] = canon

# ------------------------------
# FILTRES
# ------------------------------
def match_filters(t):
    if q and q.lower() not in t["title"].lower():
        return False
    if priority_filter and t["priority"] != priority_filter:
        return False
    if task_type_filter and t["type"] != task_type_filter:
        return False
    return True

filtered = [t for t in tasks if match_filters(t)]

# ------------------------------
# Metrics
# ------------------------------
st.subheader("Résumé des tâches")
col1, col2, col3 = st.columns(3)
col1.metric("Total", len(filtered))
col2.metric("En cours", len([t for t in filtered if t["status"]=="En cours"]))
col3.metric("Terminé", len([t for t in filtered if t["status"]=="Fait"]))

# ------------------------------
# Rendu des cartes
# ------------------------------
def render_task_card(task):
    color = PRIORITY_COLOR.get(task["priority"], "#f1f3f5")
    st.markdown(f"<div style='padding:10px; margin-bottom:10px; background-color:{color}; border-radius:8px;'>"
                f"<b>#{task['id']} – {task['title']}</b><br>"
                f"Type : {task['type']} • Priorité : {task['priority']}</div>", unsafe_allow_html=True)

    if "screenshot" in task and task["screenshot"]:
        st.image(task["screenshot"], width=200)

    # Sélecteur statut
    all_statuses = sorted({s for values in KANBAN_COLUMNS.values() for s in values})
    widget_key = f"select_{task['id']}_{uuid.uuid4()}"
    new_status = st.selectbox("Changer statut", options=[""] + all_statuses, index=0, key=widget_key)

    button_key = f"save_{task['id']}_{uuid.uuid4()}"
    if st.button("Enregistrer", key=button_key):
        if not new_status:
            st.warning("Choisir un statut.")
        else:
            try:
                update_task_status(task["id"], new_status)
                st.success("Statut mis à jour.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

# ------------------------------
# Affichage Kanban
# ------------------------------
st.subheader("Kanban")
cols = st.columns(len(KANBAN_COLUMNS))
for col_index, (col_name, statuses) in enumerate(KANBAN_COLUMNS.items()):
    with cols[col_index]:
        with st.expander(col_name, expanded=True):
            col_tasks = [t for t in filtered if t["status"] in statuses]
            if not col_tasks:
                st.caption("Aucune tâche")
            for task in col_tasks:
                render_task_card(task)
