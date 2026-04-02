import json
from datetime import date
import streamlit as st

try:
    from streamlit_local_storage import LocalStorage
except Exception:
    LocalStorage = None

st.set_page_config(page_title="やることリスト", page_icon="✅", layout="wide")

STORAGE_KEY = "todo_progress_tasks_v2"

def get_local_storage():
    if LocalStorage is None:
        return None
    try:
        return LocalStorage()
    except Exception:
        return None

def parse_tasks(raw):
    if raw in (None, "", "null"):
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def normalize_tasks(tasks):
    normalized = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            continue
        normalized.append({
            "id": t.get("id", i + 1),
            "title": str(t.get("title", "")).strip(),
            "done": bool(t.get("done", False)),
            "priority": t.get("priority", "中"),
            "due_date": t.get("due_date", ""),
            "notes": t.get("notes", ""),
            "created_at": t.get("created_at", ""),
        })
    return normalized

localS = get_local_storage()

if "tasks" not in st.session_state:
    initial_raw = None
    if localS is not None:
        try:
            initial_raw = localS.getItem(STORAGE_KEY, key="initial_load")
        except Exception:
            initial_raw = None
    st.session_state.tasks = normalize_tasks(parse_tasks(initial_raw))
    st.session_state.storage_ready = localS is not None

def save_tasks():
    if localS is not None:
        try:
            localS.setItem(STORAGE_KEY, json.dumps(st.session_state.tasks, ensure_ascii=False), key="save_tasks")
            st.session_state.storage_ready = True
        except Exception:
            st.session_state.storage_ready = False
    else:
        st.session_state.storage_ready = False

def add_task(title, priority, due_date, notes):
    if not title.strip():
        return
    next_id = max([t["id"] for t in st.session_state.tasks], default=0) + 1
    st.session_state.tasks.append({
        "id": next_id,
        "title": title.strip(),
        "done": False,
        "priority": priority,
        "due_date": due_date.isoformat() if due_date else "",
        "notes": notes.strip(),
        "created_at": date.today().isoformat(),
    })
    save_tasks()

def delete_task(task_id):
    st.session_state.tasks = [t for t in st.session_state.tasks if t["id"] != task_id]
    save_tasks()

def update_task(task_id, field, value):
    for task in st.session_state.tasks:
        if task["id"] == task_id:
            if field == "title":
                task[field] = str(value).strip()
            elif field == "notes":
                task[field] = str(value)
            elif field == "due_date":
                task[field] = value.isoformat() if value else ""
            else:
                task[field] = value
            break
    save_tasks()

def clear_completed():
    st.session_state.tasks = [t for t in st.session_state.tasks if not t["done"]]
    save_tasks()

def reset_all():
    st.session_state.tasks = []
    save_tasks()

tasks = st.session_state.tasks
total = len(tasks)
completed = sum(1 for t in tasks if t["done"])
progress = completed / total if total else 0.0

st.title("✅ やることリスト")
st.caption("この版はブラウザのローカル保存を使います。同じブラウザなら、ページを閉じても内容が残ります。")

if st.session_state.get("storage_ready"):
    st.success("保存方式: ブラウザのローカル保存")
else:
    st.warning("ローカル保存コンポーネントを読み込めていません。requirements.txt の再デプロイ後に改善することがあります。")

col1, col2, col3 = st.columns([1.2, 1, 1])
with col1:
    st.metric("達成率", f"{progress * 100:.0f}%")
with col2:
    st.metric("完了", f"{completed} / {total}")
with col3:
    st.progress(progress)

with st.expander("新しいタスクを追加", expanded=True):
    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("タスク名")
        c1, c2 = st.columns(2)
        with c1:
            priority = st.selectbox("優先度", ["高", "中", "低"], index=1)
        with c2:
            due_date = st.date_input("期限", value=None)
        notes = st.text_area("メモ", placeholder="任意")
        submitted = st.form_submit_button("追加")
        if submitted:
            add_task(title, priority, due_date, notes)
            st.rerun()

st.subheader("表示設定")
fc1, fc2, fc3 = st.columns(3)
with fc1:
    status_filter = st.selectbox("状態", ["すべて", "未完了", "完了のみ"])
with fc2:
    priority_filter = st.selectbox("優先度", ["すべて", "高", "中", "低"])
with fc3:
    sort_key = st.selectbox("並び順", ["作成順", "期限順", "優先度順"])

filtered = tasks[:]
if status_filter == "未完了":
    filtered = [t for t in filtered if not t["done"]]
elif status_filter == "完了のみ":
    filtered = [t for t in filtered if t["done"]]

if priority_filter != "すべて":
    filtered = [t for t in filtered if t["priority"] == priority_filter]

priority_order = {"高": 0, "中": 1, "低": 2}
if sort_key == "期限順":
    filtered.sort(key=lambda x: (x["due_date"] == "", x["due_date"]))
elif sort_key == "優先度順":
    filtered.sort(key=lambda x: (priority_order.get(x["priority"], 99), x["due_date"]))
else:
    filtered.sort(key=lambda x: x["id"])

st.subheader("タスク一覧")

if not filtered:
    st.info("表示するタスクがありません。")
else:
    for task in filtered:
        with st.container(border=True):
            top1, top2, top3 = st.columns([0.8, 4, 1])
            with top1:
                done_val = st.checkbox(
                    "完了",
                    value=task["done"],
                    key=f"done_{task['id']}",
                    label_visibility="collapsed",
                )
                if done_val != task["done"]:
                    update_task(task["id"], "done", done_val)
                    st.rerun()

            with top2:
                title_val = st.text_input("タスク名", value=task["title"], key=f"title_{task['id']}")
                if title_val != task["title"]:
                    update_task(task["id"], "title", title_val)

                m1, m2 = st.columns(2)
                with m1:
                    pr_val = st.selectbox(
                        "優先度",
                        ["高", "中", "低"],
                        index=["高", "中", "低"].index(task["priority"]) if task["priority"] in ["高", "中", "低"] else 1,
                        key=f"priority_{task['id']}",
                    )
                    if pr_val != task["priority"]:
                        update_task(task["id"], "priority", pr_val)

                with m2:
                    due_default = None
                    if task["due_date"]:
                        try:
                            due_default = date.fromisoformat(task["due_date"])
                        except Exception:
                            due_default = None
                    due_val = st.date_input("期限", value=due_default, key=f"due_{task['id']}")
                    due_str = due_val.isoformat() if due_val else ""
                    if due_str != task["due_date"]:
                        update_task(task["id"], "due_date", due_val)

                notes_val = st.text_area("メモ", value=task["notes"], key=f"notes_{task['id']}")
                if notes_val != task["notes"]:
                    update_task(task["id"], "notes", notes_val)

            with top3:
                st.write("")
                st.write("")
                if st.button("削除", key=f"delete_{task['id']}"):
                    delete_task(task["id"])
                    st.rerun()

st.divider()
b1, b2 = st.columns(2)
with b1:
    if st.button("完了済みを削除"):
        clear_completed()
        st.rerun()
with b2:
    if st.button("全タスクを初期化"):
        reset_all()
        st.rerun()
