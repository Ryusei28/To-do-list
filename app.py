import uuid
from datetime import date, datetime

import streamlit as st
from supabase import create_client
from streamlit_calendar import calendar


st.set_page_config(
    page_title="ToDo + Calendar",
    page_icon="✅",
    layout="wide",
)


# -----------------------------
# Supabase connection
# -----------------------------
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase = init_supabase()


# -----------------------------
# Utility
# -----------------------------
def today_str() -> str:
    return date.today().isoformat()


def safe_parse_date(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    if isinstance(value, datetime):
        return value.date()

    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def generate_id() -> str:
    return str(uuid.uuid4())


def normalize_task(task: dict) -> dict:
    return {
        "id": task.get("id", generate_id()),
        "title": task.get("title", "").strip(),
        "status": task.get("status", "未完了"),
        "priority": task.get("priority", "中"),
        "due_date": str(task["due_date"]) if task.get("due_date") else "",
        "memo": task.get("memo", "") or "",
        "created_at": task.get("created_at", ""),
    }


# -----------------------------
# Database operations
# -----------------------------
def load_tasks():
    response = (
        supabase
        .table("tasks")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    data = response.data if response.data else []
    return [normalize_task(t) for t in data]


def add_task_to_db(task: dict):
    payload = {
        "id": task["id"],
        "title": task["title"],
        "status": task["status"],
        "priority": task["priority"],
        "due_date": task["due_date"] if task["due_date"] else None,
        "memo": task["memo"],
    }
    supabase.table("tasks").insert(payload).execute()


def update_task_in_db(task: dict):
    payload = {
        "title": task["title"],
        "status": task["status"],
        "priority": task["priority"],
        "due_date": task["due_date"] if task["due_date"] else None,
        "memo": task["memo"],
    }
    supabase.table("tasks").update(payload).eq("id", task["id"]).execute()


def delete_task_from_db(task_id: str):
    supabase.table("tasks").delete().eq("id", task_id).execute()


def delete_all_tasks_from_db():
    # 全件削除
    rows = supabase.table("tasks").select("id").execute()
    ids = [row["id"] for row in (rows.data or [])]
    for task_id in ids:
        delete_task_from_db(task_id)


# -----------------------------
# View helpers
# -----------------------------
def get_priority_color(priority: str, status: str) -> str:
    if status == "完了":
        return "#9CA3AF"
    if priority == "高":
        return "#EF4444"
    if priority == "中":
        return "#F59E0B"
    return "#3B82F6"


def tasks_to_calendar_events(tasks):
    events = []
    for task in tasks:
        if not task["due_date"]:
            continue

        color = get_priority_color(task["priority"], task["status"])
        title_prefix = "✓ " if task["status"] == "完了" else ""

        events.append(
            {
                "id": task["id"],
                "title": f"{title_prefix}{task['title']}",
                "start": task["due_date"],
                "allDay": True,
                "color": color,
                "extendedProps": {
                    "priority": task["priority"],
                    "status": task["status"],
                    "memo": task["memo"],
                },
            }
        )
    return events


def calculate_progress(tasks):
    total = len(tasks)
    if total == 0:
        return 0.0
    done = sum(1 for t in tasks if t["status"] == "完了")
    return round(done / total * 100, 1)


def calculate_month_progress(tasks, year: int, month: int):
    month_tasks = []
    for t in tasks:
        d = safe_parse_date(t["due_date"])
        if d and d.year == year and d.month == month:
            month_tasks.append(t)

    if not month_tasks:
        return 0.0, 0

    done = sum(1 for t in month_tasks if t["status"] == "完了")
    return round(done / len(month_tasks) * 100, 1), len(month_tasks)


def filter_tasks(tasks, status_filter, priority_filter, keyword, selected_date_str):
    result = tasks[:]

    if status_filter != "すべて":
        result = [t for t in result if t["status"] == status_filter]

    if priority_filter != "すべて":
        result = [t for t in result if t["priority"] == priority_filter]

    if keyword:
        kw = keyword.lower()
        result = [
            t for t in result
            if kw in t["title"].lower() or kw in t["memo"].lower()
        ]

    if selected_date_str:
        result = [t for t in result if t["due_date"] == selected_date_str]

    return result


def sort_tasks(tasks, sort_option):
    if sort_option == "期限が早い順":
        return sorted(
            tasks,
            key=lambda t: (t["due_date"] == "", t["due_date"], t["created_at"])
        )
    if sort_option == "期限が遅い順":
        return sorted(
            tasks,
            key=lambda t: (t["due_date"] == "", t["due_date"], t["created_at"]),
            reverse=True,
        )
    if sort_option == "優先度順":
        priority_order = {"高": 0, "中": 1, "低": 2}
        return sorted(tasks, key=lambda t: priority_order.get(t["priority"], 99))
    if sort_option == "作成が新しい順":
        return sorted(tasks, key=lambda t: t["created_at"], reverse=True)
    return tasks


def get_selected_date_from_calendar(calendar_value):
    if not calendar_value or not isinstance(calendar_value, dict):
        return None

    callback = calendar_value.get("callback")

    if callback == "dateClick":
        date_click = calendar_value.get("dateClick", {})
        return date_click.get("dateStr")

    if callback == "eventClick":
        event_click = calendar_value.get("eventClick", {})
        event = event_click.get("event", {})
        start_value = event.get("start", "")
        return start_value[:10] if start_value else None

    return None


def is_overdue(task):
    due = safe_parse_date(task["due_date"])
    return (
        due is not None
        and due < date.today()
        and task["status"] != "完了"
    )


# -----------------------------
# Session init
# -----------------------------
if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()

if "selected_date" not in st.session_state:
    st.session_state.selected_date = None


def refresh_tasks():
    st.session_state.tasks = load_tasks()


# -----------------------------
# Header
# -----------------------------
st.title("✅ やることリスト + カレンダー")
st.caption("Supabase 保存版: ページを閉じてもデータが残ります")


# -----------------------------
# Summary
# -----------------------------
all_tasks = st.session_state.tasks
overall_progress = calculate_progress(all_tasks)
today = date.today()
month_progress, month_task_count = calculate_month_progress(
    all_tasks,
    today.year,
    today.month
)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("全タスク数", len(all_tasks))
col_m2.metric("完了率", f"{overall_progress}%")
col_m3.metric("今月タスク数", month_task_count)
col_m4.metric("今月達成率", f"{month_progress}%")

st.progress(min(overall_progress / 100, 1.0))


# -----------------------------
# Add task
# -----------------------------
with st.expander("＋ 新しいタスクを追加", expanded=True):
    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("タスク名")
        col_f1, col_f2 = st.columns(2)
        priority = col_f1.selectbox("優先度", ["高", "中", "低"], index=1)
        due_date = col_f2.date_input("期限", value=None, format="YYYY-MM-DD")
        memo = st.text_area("メモ", placeholder="補足があれば入力")
        submitted = st.form_submit_button("追加")

        if submitted:
            if not title.strip():
                st.warning("タスク名を入力してください。")
            else:
                new_task = {
                    "id": generate_id(),
                    "title": title.strip(),
                    "status": "未完了",
                    "priority": priority,
                    "due_date": due_date.isoformat() if due_date else "",
                    "memo": memo.strip(),
                }
                add_task_to_db(new_task)
                refresh_tasks()
                st.success("タスクを追加しました。")
                st.rerun()


# -----------------------------
# Layout
# -----------------------------
left_col, right_col = st.columns([1.15, 1.0])


# -----------------------------
# Calendar
# -----------------------------
with left_col:
    st.subheader("📅 カレンダー")

    events = tasks_to_calendar_events(st.session_state.tasks)

    calendar_options = {
        "initialView": "dayGridMonth",
        "locale": "ja",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listWeek",
        },
        "height": 650,
        "editable": False,
        "selectable": True,
        "dayMaxEvents": True,
    }

    custom_css = """
    .fc .fc-toolbar-title {
        font-size: 1.2rem;
        font-weight: 700;
    }
    .fc-event {
        border-radius: 6px;
        padding: 2px 4px;
        font-size: 0.82rem;
    }
    """

    calendar_value = calendar(
        events=events,
        options=calendar_options,
        custom_css=custom_css,
        key="todo_calendar",
    )

    clicked_date = get_selected_date_from_calendar(calendar_value)
    if clicked_date:
        st.session_state.selected_date = clicked_date

    c1, c2 = st.columns([1, 1])
    with c1:
        selected = st.session_state.selected_date or "未選択"
        st.info(f"選択中の日付: {selected}")
    with c2:
        if st.button("日付選択を解除"):
            st.session_state.selected_date = None
            st.rerun()


# -----------------------------
# Task list
# -----------------------------
with right_col:
    st.subheader("📝 タスク一覧")

    status_filter = st.selectbox("状態", ["すべて", "未完了", "完了"])
    priority_filter = st.selectbox("優先度", ["すべて", "高", "中", "低"])
    keyword = st.text_input("キーワード検索")
    sort_option = st.selectbox(
        "並び替え",
        ["期限が早い順", "期限が遅い順", "優先度順", "作成が新しい順"]
    )

    filtered = filter_tasks(
        st.session_state.tasks,
        status_filter=status_filter,
        priority_filter=priority_filter,
        keyword=keyword,
        selected_date_str=st.session_state.selected_date,
    )
    filtered = sort_tasks(filtered, sort_option)

    if not filtered:
        st.write("表示するタスクがありません。")
    else:
        for task in filtered:
            due = task["due_date"] if task["due_date"] else "期限なし"
            overdue_text = " ⚠️期限切れ" if is_overdue(task) else ""

            with st.container(border=True):
                top1, top2 = st.columns([0.72, 0.28])

                with top1:
                    new_status = st.checkbox(
                        task["title"],
                        value=(task["status"] == "完了"),
                        key=f"check_{task['id']}"
                    )
                with top2:
                    st.markdown(f"**{task['priority']}** / {due}{overdue_text}")

                if task["memo"]:
                    st.caption(task["memo"])

                if new_status != (task["status"] == "完了"):
                    task["status"] = "完了" if new_status else "未完了"
                    update_task_in_db(task)
                    refresh_tasks()
                    st.rerun()

                with st.expander("編集"):
                    edit_title = st.text_input(
                        "タスク名",
                        value=task["title"],
                        key=f"title_{task['id']}"
                    )
                    edit_priority = st.selectbox(
                        "優先度",
                        ["高", "中", "低"],
                        index=["高", "中", "低"].index(task["priority"]),
                        key=f"priority_{task['id']}"
                    )

                    current_due = safe_parse_date(task["due_date"])
                    edit_due = st.date_input(
                        "期限",
                        value=current_due if current_due else date.today(),
                        key=f"due_{task['id']}",
                        format="YYYY-MM-DD"
                    )

                    no_due = st.checkbox(
                        "期限を設定しない",
                        value=(task["due_date"] == ""),
                        key=f"no_due_{task['id']}"
                    )

                    edit_memo = st.text_area(
                        "メモ",
                        value=task["memo"],
                        key=f"memo_{task['id']}"
                    )

                    btn1, btn2 = st.columns(2)

                    if btn1.button("保存", key=f"save_{task['id']}"):
                        task["title"] = edit_title.strip()
                        task["priority"] = edit_priority
                        task["due_date"] = "" if no_due else edit_due.isoformat()
                        task["memo"] = edit_memo.strip()
                        update_task_in_db(task)
                        refresh_tasks()
                        st.success("更新しました。")
                        st.rerun()

                    if btn2.button("削除", key=f"delete_{task['id']}"):
                        delete_task_from_db(task["id"])
                        refresh_tasks()
                        st.warning("削除しました。")
                        st.rerun()


# -----------------------------
# Utilities
# -----------------------------
st.divider()
st.subheader("⚙️ 便利機能")

u1, u2, u3, u4 = st.columns(4)

with u1:
    if st.button("今日のタスクだけ見る"):
        st.session_state.selected_date = today_str()
        st.rerun()

with u2:
    if st.button("期限切れ未完了タスクを表示"):
        overdue_tasks = [
            t for t in st.session_state.tasks
            if is_overdue(t)
        ]
        if overdue_tasks:
            st.write("### 期限切れタスク")
            for t in overdue_tasks:
                st.write(f"- {t['title']}（期限: {t['due_date']}）")
        else:
            st.success("期限切れタスクはありません。")

with u3:
    if st.button("最新状態に更新"):
        refresh_tasks()
        st.success("再読み込みしました。")
        st.rerun()

with u4:
    if st.button("全データを削除"):
        delete_all_tasks_from_db()
        refresh_tasks()
        st.session_state.selected_date = None
        st.rerun()
