import streamlit as st
import sqlite3
import json
import random
import os
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")

QUESTIONS_DIR = os.path.join(BASE_DIR, "questions")
#QUESTIONS_DIR = "./questions"  # carpeta donde están los archivos JSON

admin_pass = "admin"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
                    user_id INTEGER,
                    question TEXT,
                    correct INTEGER,
                    timestamp TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS question_index (
                    id INTEGER PRIMARY KEY,
                    file_name TEXT
                )''')
    conn.commit()
    conn.close()

def get_users():
    with sqlite3.connect(DB_PATH) as conn:
        return [row[0] for row in conn.execute("SELECT name FROM users")]

def add_user(name):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
        conn.commit()

def get_user_id(name):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT id FROM users WHERE name=?", (name,)).fetchone()
        return row[0] if row else None

def save_result(user_id, question_id, correct):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO stats (user_id, question, correct, timestamp) VALUES (?, ?, ?, datetime('now'))",
                     (user_id, str(question_id), int(correct)))
        conn.commit()

def get_stats(user_id=None):
    with sqlite3.connect(DB_PATH) as conn:
        if user_id:
            return conn.execute(
                "SELECT question, correct FROM stats WHERE user_id=?", (user_id,)
            ).fetchall()
        return conn.execute("SELECT u.name, s.correct FROM stats s JOIN users u ON s.user_id=u.id").fetchall()

def load_questions(files, mode="random"):
    questions = []
    for file in files:
        with open(os.path.join(QUESTIONS_DIR, file), encoding="utf-8") as f:
            questions.extend(json.load(f))
    if mode == "random":
        random.shuffle(questions)
    with sqlite3.connect(DB_PATH) as conn:
        for q in questions:
            conn.execute(
                "INSERT OR IGNORE INTO question_index (id, file_name) VALUES (?, ?)",
                (q["id"], file)
            )
        conn.commit()
    return questions

# ================= Streamlit App =================

st.set_page_config("Test App")
init_db()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("🔐 Master password", type="password")
    if pwd == admin_pass:  
        st.session_state.authenticated = True
    else:
        st.stop()

st.title("🧠 Interactive Test App")

view = st.sidebar.radio("Menu", ["📋 User Selection", "📊 Global Statistics"])

if view == "📋 User Selection":
    with st.sidebar:
        st.markdown("### 👤 User")
        usuarios = get_users()
        selected_user = st.selectbox("Select a user", [""] + usuarios)
        if selected_user:
            st.session_state.selected_user = selected_user
        new_user = st.text_input("New user")
        if st.button("Create user") and new_user:
            add_user(new_user)
            st.rerun()

    selected_user = st.session_state.get("selected_user", selected_user)
    if selected_user:
        user_id = get_user_id(selected_user)

        files = os.listdir(QUESTIONS_DIR)
        selected_files = st.multiselect("📂 Available question files", files, default=files)
        mode = st.radio("Question mode", ["random", "ordered"])

        if st.button("🎯 Start Test"):
            st.session_state.questions = load_questions(selected_files, mode)
            st.session_state.question_index = 0

        if "questions" in st.session_state:
            questions = st.session_state.questions
            idx = st.session_state.question_index

            if idx < len(questions):
                q = questions[idx]
                with st.container():
                    st.markdown(f"**{q['pregunta']}**")
                    if len(q["respuestas_correctas"]) == 1:
                        answer = st.radio("Options", q["respuestas"], key=f"ans_{q['id']}")
                        answer = [answer] if answer else []
                    else:
                        answer = []
                        for i, opt in enumerate(q["respuestas"]):
                            if st.checkbox(opt, key=f"chk_{q['id']}_{i}"):
                                answer.append(opt)

                submit_key = f"submit_{q['id']}"
                # Use session state to control answer submission
                if "answer_submitted" not in st.session_state:
                    st.session_state.answer_submitted = False
                if not st.session_state.get("answer_submitted"):
                    if st.button("Submit Answer", key=submit_key):
                        correct = set(answer) == set(q["respuestas_correctas"])
                        save_result(user_id, q["id"], correct)
                        st.session_state.answer_submitted = True
                        st.session_state.last_answer_correct = correct
                # Show result and explanation if answer was submitted
                if st.session_state.get("answer_submitted"):
                    if st.session_state.last_answer_correct:
                        st.info("✅ Correct")
                    else:
                        st.warning(f"❌ Incorrect: {q['respuestas_correctas']}")
                    if "explicacion" in q:
                        st.markdown(f"💡 **Explanation:** {q['explicacion']}")
                    if st.button("➡️ Next"):
                        st.session_state.question_index += 1
                        st.session_state.answer_submitted = False
                        st.rerun()
            else:
                st.success("🎉 Test completed")
                del st.session_state.questions
                del st.session_state.question_index
                
        st.subheader("📈 User Statistics")
        user_stats = get_stats(user_id)
        correct = sum(x[1] for x in user_stats)
        total = len(user_stats)
        st.text(f"Correct: {correct} / {total} ({correct/total:.1%} accuracy)" if total else "No responses yet.")

elif view == "📊 Global Statistics":
    data = get_stats()
    user_totals = {}
    for name, correct in data:
        user_totals.setdefault(name, [0, 0])
        user_totals[name][0] += correct
        user_totals[name][1] += 1

    for user, (hits, total) in user_totals.items():
        st.write(f"👤 {user}: {hits}/{total} correct answers ({hits/total:.1%})")

    import pandas as pd
    import matplotlib.pyplot as plt

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("""
            SELECT u.name, s.correct, s.timestamp
            FROM stats s
            JOIN users u ON s.user_id = u.id
        """, conn)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df_grouped = df.groupby([df["timestamp"].dt.date, "name"])["correct"].agg(["mean", "count"]).reset_index()
    df_grouped["mean"] = df_grouped["mean"] * 100

    st.line_chart(
        df_grouped.pivot(index="timestamp", columns="name", values="mean"),
        height=300,
        use_container_width=True
    )