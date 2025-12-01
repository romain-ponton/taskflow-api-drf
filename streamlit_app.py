# streamlit_app.py
import os
import requests
import streamlit as st
from typing import List, Dict, Any

st.set_page_config(page_title="TaskFlow – Board", layout="wide")
st.title("TaskFlow – Board (Jira-like)")

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
USE_DEMO = os.getenv("DEMO", "0") == "1"
API_TIMEOUT = 8  # seconds

# mapping colonnes -> valeurs de status attendues par l'API
STATUS_COLUMNS = [
    ("Backlog", ["À faire", "Nouveau"]),
    ("Sélectionné", ["Sélectionné", "À faire"]),
    ("En cours", ["En cours"]),
    ("Terminé", ["Fait", "Terminé"]),
]


@st.cache_data(ttl=60)
def fetch_tasks() -> List[Dict[str, Any]]:
    if USE_DEMO:
        import json
        demo_path = os.path.join(os.path.dirname(__file__), "demo_tasks.json")
        with open(demo_path, "r", encoding="utf-8") as f:
            return json.load(f)
    resp = requests.get(f"{API_BASE}/api/tasks/", timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def patch_task_status(task_id: int, new_status: str) -> Dict[str, Any]:
    """Envoie un PATCH simple pour mettre à jour le statut d'une tâche."""
    url = f"{API_BASE}/api/tasks/{task_id}/"
    payload = {"status": new_status}
    headers = {"Content-Type": "application/json"}
    resp = requests.patch(url, json=payload, headers=headers, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# Sidebar : filtres
st.sidebar.header("Filtres")
with st.sidebar.form(key="filters"):
    q = st.text_input("Recherche (titre / description)", value="")
    project = st.text_input("Projet (exact)", value="")
    task_type = st.text_input("Type (ex: Étude, Bug...)", value="")
    priority = st.selectbox("Priorité", options=["", "Basse", "Moyenne", "Haute"])
    show_screenshots = st.checkbox("Afficher screenshots (si fournis)", value=False)
    submitted = st.form_submit_button("Appliquer")

# Charger les tâches
with st.spinner("Chargement des tâches…"):
    try:
        tasks = fetch_tasks()
        st.success(f"{len(tasks)} tâches chargées.")
    except Exception as e:
        st.error(f"Impossible de joindre l'API : {e}")
        st.stop()

# Appliquer filtres localement
def matches(task):
    if q and not (q.lower() in (task.get("title") or "").lower() or q.lower() in (task.get("description") or "").lower()):
        return False
    if project and project != (task.get("project") or ""):
        return False
    if task_type and task_type != (task.get("task_type") or ""):
        return False
    if priority and priority != (task.get("priority") or ""):
        return False
    return True

filtered_tasks = [t for t in tasks if matches(t)]

# Layout Kanban
st.subheader("Board Kanban")
cols = st.columns(len(STATUS_COLUMNS))

# helper pour afficher une carte
def render_task_card(task):
    st.markdown(f"**{task.get('key','')} — [{task.get('task_type')}] {task.get('title')}**")
    meta = f"Projet : {task.get('project') or '—'} · Priorité : {task.get('priority') or '—'}"
    st.caption(meta)
    owner = task.get("owner") or "—"
    st.caption(f"Owner : {owner}")
    desc = (task.get("description") or "")
    if desc:
        st.write(desc if len(desc) < 240 else desc[:240] + "…")
    if show_screenshots and task.get("screenshot_url"):
        try:
            st.image(task["screenshot_url"], use_column_width=True)
        except Exception:
            st.caption("Screenshot non disponible.")
    # actions: changer statut via selectbox
    statuses_available = []
    # rassembler toutes valeurs uniques connues dans le mapping (utile si l'API a d'autres valeurs)
    for _, vals in STATUS_COLUMNS:
        statuses_available.extend(vals)
    statuses_available = sorted(set(statuses_available))
    new_status = st.selectbox("Changer de statut", options=[""] + statuses_available, index=0, key=f"status_{task['id']}")
    if st.button("Enregistrer", key=f"save_{task['id']}"):
        if not new_status:
            st.warning("Choisir un statut avant d'enregistrer.")
        else:
            try:
                patch_task_status(task["id"], new_status)
                st.success("Statut mis à jour.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Échec mise à jour : {e}")

# Pour chaque colonne, afficher les tâches correspondantes
for col_idx, (col_title, status_values) in enumerate(STATUS_COLUMNS):
    with cols[col_idx]:
        st.markdown(f"### {col_title}")
        column_tasks = [t for t in filtered_tasks if (t.get("status") or "") in status_values]
        if not column_tasks:
            st.caption("Aucune tâche")
        for task in column_tasks:
            with st.container():
                render_task_card(task)
                st.markdown("---")

# Footer / debug
st.sidebar.markdown("---")
st.sidebar.write("API_BASE =", API_BASE)
st.sidebar.write("DEMO mode =", USE_DEMO)
