import json
import uuid
from datetime import date, datetime, timedelta

import streamlit as st
from streamlit_calendar import calendar
from streamlit_local_storage import LocalStorage


st.set_page_config(
    page_title="ToDo + Calendar",
    page_icon="✅",
    layout="wide",
)

local_storage = LocalStorage()
STORAGE_KEY = "todo_calendar_app_tasks_v1"


# -----------------------------
# Utility
# -----------------------------
def today_str() -> str:
    return date.today().isoformat()


def safe_parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def generate_id() -> str:
    return str(uuid.uuid4())


def load_tasks():
    """
    local storage からタスク一覧を読む。
    初回や空の場合は [] を返す。
    """
    stored = local_storage.getItem(STORAGE_KEY, key="load_tasks")
    if stored is None or stored == "":
        return []

    if isinstance(stored, list):
        return stored

    if isinstance(stored, str):
        try:
            data = json.loads(stored)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            return []

    return []


def save_tasks(tasks):
    """
    local storage に JSON 文字列として保存。
    """
    local_storage.setItem(STORAGE_KEY, json.dumps(tasks), key="save_tasks")


def normalize_tasks(tasks):
    """
    旧データが混じっていても最低限動くように整形。
    """
    normalized = []
    for task in tasks:
        normalized.append(
            {
                "id": task.get("id", generate_id()),
                "title": task.get("title", "").strip(),
                "status": task.get("status", "未完了"),
                "priority": task.get("priority", "中"),
                "due_date": task.get("due_date", ""),
                "memo": task.get("memo", ""),
                "created_at": task.get("created_at", datetime.now().isoformat()),
            }
        )
    return normalized


def get_priority_color(priority: str, status: str) -> str:
    if status == "完了":
        return "#9CA3AF"  # gray
    if priority == "高":
        return "#EF4444"  # red
    if priority == "中":
        return "#F59E0B"  # amber
    return "#3B82F6"      # blue


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
                "end": task["due_date"],
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
    """
    calendar の戻り値から選択日を取り出す。
    日付クリック、イベントクリックの両方に対応。
    """
    if not calendar_value or not isinstance(calendar_value, dict):
        return None

    callback = calendar_value.get("callback")

    if callback == "dateClick":
        date_click = calendar_value.get("dateClick", {})
        return date_click.get("dateStr")

    if callback == "eventClick":
        event_click = calendar_value.get("eventClick", {})
        event = event_click.get("event", {})
        return event.get("start", "")[:10]

    return None


def is_overdue(task):
    due = safe_parse_date(task["due_date"])
    return (
        due is not None
        and due < date.today()
        and task["status"] != "完了"
    )


# -----------------------------
# Init state
# -----------------------------
if "tasks" not in st.session_state:
    loaded = normalize_tasks(load_tasks())
    st.session_state.tasks = loaded

if "selected_date" not in st.session_state:
    st.session_state.selected_date = None

if "last_saved_json" not in st.session_state:
    st.session_state.last_saved_json = json.dumps(st.session_state.tasks, ensure_ascii=False)


# -----------------------------
# Sync save when tasks changed
# -----------------------------
current_json = json.dumps(st.session_state.tasks, ensure_ascii=False)
if current_json != st.session_state.last_saved_json:
    save_tasks(st.session_state.tasks)
    st.session_state.last_saved_json = current_json


# -----------------------------
# Header
# -----------------------------
st.title("✅ やることリスト + カレンダー")
st.caption("同じブラウザなら、ページを閉じてもタスクが残る版")


# -----------------------------
# Top summary
# -----------------------------
all_tasks = st.session_state.tasks
overall_progress = calculate_progress(all_tasks)
today = date.today()
month_progress, month_task_count = calculate_month_progress(all_tasks, today.year, today.month)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("全タスク数", len(all_tasks))
col_m2.metric("完了率", f"{overall_progress}%")
col_m3.metric("今月タスク数", month_task_count)
col_m4.metric("今月達成率", f"{month_progress}%")

st.progress(min(overall_progress / 100, 1.0))


# -----------------------------
# Add task form
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
                    "created_at": datetime.now().isoformat(),
                }
                st.session_state.tasks.append(new_task)
                save_tasks(st.session_state.tasks)
                st.session_state.last_saved_json = json.dumps(
                    st.session_state.tasks, ensure_ascii=False
                )
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
# Filters + task list
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
                    st.markdown(
                        f"**{task['priority']}** / {due}{overdue_text}"
                    )

                if task["memo"]:
                    st.caption(task["memo"])

                if new_status != (task["status"] == "完了"):
                    task["status"] = "完了" if new_status else "未完了"
                    save_tasks(st.session_state.tasks)
                    st.session_state.last_saved_json = json.dumps(
                        st.session_state.tasks, ensure_ascii=False
                    )
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
                    edit_due = st.date_input(
                        "期限",
                        value=safe_parse_date(task["due_date"]),
                        key=f"due_{task['id']}",
                        format="YYYY-MM-DD"
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
                        task["due_date"] = edit_due.isoformat() if edit_due else ""
                        task["memo"] = edit_memo.strip()
                        save_tasks(st.session_state.tasks)
                        st.session_state.last_saved_json = json.dumps(
                            st.session_state.tasks, ensure_ascii=False
                        )
                        st.success("更新しました。")
                        st.rerun()

                    if btn2.button("削除", key=f"delete_{task['id']}"):
                        st.session_state.tasks = [
                            t for t in st.session_state.tasks
                            if t["id"] != task["id"]
                        ]
                        save_tasks(st.session_state.tasks)
                        st.session_state.last_saved_json = json.dumps(
                            st.session_state.tasks, ensure_ascii=False
                        )
                        st.warning("削除しました。")
                        st.rerun()


# -----------------------------
# Bottom utilities
# -----------------------------
st.divider()
st.subheader("⚙️ 便利機能")

u1, u2, u3 = st.columns(3)

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
    if st.button("全データを削除"):
        st.session_state.tasks = []
        save_tasks([])
        st.session_state.last_saved_json = json.dumps([], ensure_ascii=False)
        st.session_state.selected_date = None
        st.rerun()


# -----------------------------
# Debug / export
# -----------------------------
with st.expander("データ確認 / バックアップ"):
    st.download_button(
        label="JSONをダウンロード",
        data=json.dumps(st.session_state.tasks, ensure_ascii=False, indent=2),
        file_name="tasks_backup.json",
        mime="application/json",
    )
    st.code(json.dumps(st.session_state.tasks, ensure_ascii=False, indent=2), language="json")
