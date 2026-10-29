"""
Reassure or Guide? - data-collection app for the 2x2 study
(support style x memory), run locally with Ollama.

Run:  streamlit run app.py
Needs Ollama running locally with a model pulled (see README).
"""

import os
import csv
import json
import random
import datetime as dt

import requests
import streamlit as st

from prompts import REASSURE_PROMPT, GUIDE_PROMPT, CRISIS_MESSAGE

# ---------------------------------------------------------------- CONFIG
MODEL = "llama3.1:8b"          # change to a bigger model if your VRAM allows (see README)
OLLAMA_URL = "http://localhost:11434/api/chat"
STUDY_CODE = "dreamteam2026"   # shared code all participants type to get in. CHANGE THIS.
RESEARCHER_KEY = "letmein"     # open the researcher sidebar with ?researcher=letmein in the URL
WORD_CAP = 80                  # bot reply cap (also enforced in the prompt)
N_CHAT_DAYS = 3                # days 1-3 are chat days; day 4 is the no-AI test
MIN_MINUTES = 5                # minimum chat time asked of participants per day
RANDOM_SEED = 42               # makes block randomization reproducible

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
LOGS = os.path.join(DATA, "logs")
PARTICIPANTS = os.path.join(DATA, "participants.csv")
os.makedirs(LOGS, exist_ok=True)

CONDITIONS = [
    ("reassure", "persistent"),
    ("reassure", "fresh"),
    ("guide", "persistent"),
    ("guide", "fresh"),
]

CRISIS_WORDS = [
    "suicide", "kill myself", "end my life", "want to die", "self harm",
    "self-harm", "hurt myself", "no reason to live", "better off dead",
]

PANAS_ITEMS = ["Upset", "Hostile", "Alert", "Ashamed", "Inspired",
               "Nervous", "Determined", "Attentive", "Afraid", "Active"]

# A new, matched scenario for the Day-4 no-AI transfer test.
DAY4_SCENARIO = (
    "Imagine this new situation. You texted a close friend about something "
    "that mattered to you, and they left you on read for two days with no "
    "reply, even though you can see they have been online.\n\n"
    "In a few sentences: How do you make sense of what happened, and what "
    "would you actually do next?"
)

# ---------------------------------------------------------------- HELPERS
def today():
    return dt.date.today().isoformat()


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def load_participants():
    rows = {}
    if os.path.exists(PARTICIPANTS):
        with open(PARTICIPANTS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows[r["participant_id"].strip()] = (r["style"], r["memory"])
    return rows


def assign_condition(pid):
    """Return (style, memory) for pid, block-randomizing new participants."""
    people = load_participants()
    if pid in people:
        return people[pid]
    n = len(people)
    block = n // 4
    rng = random.Random(RANDOM_SEED + block)
    order = CONDITIONS[:]
    rng.shuffle(order)
    style, memory = order[n % 4]
    new = not os.path.exists(PARTICIPANTS)
    with open(PARTICIPANTS, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["participant_id", "style", "memory", "assigned_at"])
        w.writerow([pid, style, memory, now()])
    return style, memory


def msg_path(pid):
    return os.path.join(LOGS, f"{pid}_messages.csv")


def sess_path(pid):
    return os.path.join(LOGS, f"{pid}_sessions.csv")


def final_path(pid):
    return os.path.join(LOGS, f"{pid}_final.csv")


def log_message(pid, session_date, role, content):
    new = not os.path.exists(msg_path(pid))
    with open(msg_path(pid), "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "session_date", "role", "content"])
        w.writerow([now(), session_date, role, content])


def completed_chat_dates(pid):
    """Distinct dates on which this participant finished a chat session."""
    dates = set()
    p = sess_path(pid)
    if os.path.exists(p):
        with open(p, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("session_type") == "chat":
                    dates.add(r["session_date"])
    return sorted(dates)


def save_session_row(pid, row):
    p = sess_path(pid)
    cols = ["session_date", "session_type", "duration_min", "distress_pre",
            "distress_post", "panas_pre", "panas_post", "timestamp"]
    new = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        w.writerow({c: row.get(c, "") for c in cols})


def prior_recap(pid):
    """Condensed recap of earlier conversations, for the Persistent condition."""
    p = msg_path(pid)
    if not os.path.exists(p):
        return ""
    turns = []
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            who = "Them" if r["role"] == "user" else "You"
            turns.append(f"{who}: {r['content']}")
    turns = turns[-16:]  # last ~8 exchanges is plenty of memory
    return "\n".join(turns)


def is_crisis(text):
    t = text.lower()
    return any(w in t for w in CRISIS_WORDS)


def build_system_prompt(style, memory, pid):
    base = REASSURE_PROMPT if style == "reassure" else GUIDE_PROMPT
    if memory == "persistent":
        recap = prior_recap(pid)
        if recap:
            base += (
                "\n\nEARLIER CONVERSATIONS WITH THIS PERSON (you remember these; "
                "refer back to them naturally, like someone who recalls last time):\n"
                + recap
            )
    return base


def ollama_reply(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.8, "num_predict": 160},
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as e:
        return f"[Error reaching the model: {e}. Is Ollama running?]"


# ---------------------------------------------------------------- UI SETUP
st.set_page_config(page_title="Chat study", page_icon="*", layout="centered")

ss = st.session_state
ss.setdefault("pid", None)
ss.setdefault("style", None)
ss.setdefault("memory", None)
ss.setdefault("phase", "login")     # login -> presurvey -> chat -> postsurvey -> done / day4 -> final
ss.setdefault("messages", [])        # visible chat turns for this session
ss.setdefault("start_time", None)
ss.setdefault("stressor", "")

# ---------------------------------------------------------------- LOGIN
if ss.phase == "login":
    st.title("Welcome")
    st.write("Please enter the study code and the participant ID you were given.")
    code = st.text_input("Study code").strip()
    pid = st.text_input("Participant ID").strip()
    if st.button("Start", type="primary") and pid and code:
        if code != STUDY_CODE:
            st.error("That study code is not correct. Please check and try again.")
            st.stop()
        style, memory = assign_condition(pid)
        ss.pid, ss.style, ss.memory = pid, style, memory
        done = completed_chat_dates(pid)
        # Decide today's session type.
        if today() in done:
            ss.phase = "already_today"
        elif len(done) < N_CHAT_DAYS:
            ss.phase = "presurvey"
            ss.day_number = len(done) + 1
        else:
            ss.phase = "day4"
        st.rerun()
    st.stop()

# Researcher panel: only visible when the URL has ?researcher=<RESEARCHER_KEY>.
# Participants never see it.
show_researcher = st.query_params.get("researcher") == RESEARCHER_KEY
if show_researcher:
  with st.sidebar:
    st.caption("Researcher panel")
    if ss.pid:
        st.write(f"ID: `{ss.pid}`")
        st.write(f"Style: `{ss.style}`  Memory: `{ss.memory}`")
        st.write(f"Chat days done: {len(completed_chat_dates(ss.pid))}/{N_CHAT_DAYS}")
    st.caption("Override today's session (piloting only):")
    if st.button("Force a chat day"):
        ss.phase = "presurvey"; ss.day_number = len(completed_chat_dates(ss.pid)) + 1; st.rerun()
    if st.button("Force Day-4 test"):
        ss.phase = "day4"; st.rerun()

# ---------------------------------------------------------------- ALREADY TODAY
if ss.phase == "already_today":
    st.title("All done for today")
    st.success("You have already completed today's session. Please come back tomorrow. Thank you!")
    st.stop()

# ---------------------------------------------------------------- PRE-SURVEY
if ss.phase == "presurvey":
    st.title(f"Day {ss.day_number} - before we chat")
    if ss.day_number == 1:
        st.write("First, tell us briefly about a **mild, recent situation** that left you a bit stressed or upset (a group project, a class, a friend, etc.).")
        ss.stressor = st.text_area("What happened?", height=120, value=ss.stressor)
    st.write("How distressed do you feel **right now**?")
    distress = st.slider("0 = not at all, 10 = extremely", 0, 10, 5, key="distress_pre")
    st.write("To what extent do you feel each of these right now? (1 = very slightly, 5 = extremely)")
    panas = {}
    cols = st.columns(2)
    for i, item in enumerate(PANAS_ITEMS):
        with cols[i % 2]:
            panas[item] = st.slider(item, 1, 5, 3, key=f"pre_{item}")
    ready = (ss.day_number != 1) or ss.stressor.strip()
    if st.button("Start the chat", type="primary", disabled=not ready):
        ss.distress_pre = distress
        ss.panas_pre = panas
        ss.start_time = dt.datetime.now()
        ss.messages = []
        # Seed the conversation with a fixed opening (same for everyone).
        opener = "Hey, thanks for checking in. What's been on your mind today?"
        ss.messages.append({"role": "assistant", "content": opener})
        log_message(ss.pid, today(), "assistant", opener)
        if ss.day_number == 1 and ss.stressor.strip():
            log_message(ss.pid, today(), "user_stressor", ss.stressor.strip())
        ss.phase = "chat"
        st.rerun()
    st.stop()

# ---------------------------------------------------------------- CHAT
if ss.phase == "chat":
    st.title(f"Day {ss.day_number}")
    elapsed = (dt.datetime.now() - ss.start_time).total_seconds() / 60 if ss.start_time else 0
    st.caption(f"Please chat for at least {MIN_MINUTES} minutes. Time so far: {elapsed:.1f} min.")

    for m in ss.messages:
        with st.chat_message("assistant" if m["role"] == "assistant" else "user"):
            st.write(m["content"])

    user_text = st.chat_input("Type your message...")
    if user_text:
        if is_crisis(user_text):
            log_message(ss.pid, today(), "user_flagged", user_text)
            with st.chat_message("user"):
                st.write(user_text)
            st.error(CRISIS_MESSAGE)
            st.stop()
        ss.messages.append({"role": "user", "content": user_text})
        log_message(ss.pid, today(), "user", user_text)
        with st.chat_message("user"):
            st.write(user_text)
        sys = build_system_prompt(ss.style, ss.memory, ss.pid)
        convo = [{"role": "system", "content": sys}] + [
            {"role": m["role"], "content": m["content"]} for m in ss.messages
        ]
        with st.chat_message("assistant"):
            with st.spinner("..."):
                reply = ollama_reply(convo)
            st.write(reply)
        ss.messages.append({"role": "assistant", "content": reply})
        log_message(ss.pid, today(), "assistant", reply)
        st.rerun()

    if elapsed >= MIN_MINUTES:
        if st.button("I'm ready to finish for today", type="primary"):
            ss.phase = "postsurvey"
            st.rerun()
    else:
        st.info(f"The finish button appears after {MIN_MINUTES} minutes.")
    st.stop()

# ---------------------------------------------------------------- POST-SURVEY
if ss.phase == "postsurvey":
    st.title(f"Day {ss.day_number} - after the chat")
    st.write("How distressed do you feel **now**?")
    distress_post = st.slider("0 = not at all, 10 = extremely", 0, 10, 5, key="distress_post")
    st.write("And to what extent do you feel each of these now? (1 = very slightly, 5 = extremely)")
    panas_post = {}
    cols = st.columns(2)
    for i, item in enumerate(PANAS_ITEMS):
        with cols[i % 2]:
            panas_post[item] = st.slider(item, 1, 5, 3, key=f"post_{item}")
    if st.button("Submit and finish", type="primary"):
        dur = (dt.datetime.now() - ss.start_time).total_seconds() / 60 if ss.start_time else 0
        save_session_row(ss.pid, {
            "session_date": today(), "session_type": "chat",
            "duration_min": round(dur, 1),
            "distress_pre": ss.distress_pre, "distress_post": distress_post,
            "panas_pre": json.dumps(ss.panas_pre), "panas_post": json.dumps(panas_post),
            "timestamp": now(),
        })
        ss.phase = "done"
        st.rerun()
    st.stop()

# ---------------------------------------------------------------- DONE (chat day)
if ss.phase == "done":
    st.title("Thank you!")
    done = len(completed_chat_dates(ss.pid))
    if done < N_CHAT_DAYS:
        st.success("That's it for today. Please come back tomorrow for your next chat.")
    else:
        st.success("That's your last chat. Please come back tomorrow morning for a short final task (no chatbot).")
    st.stop()

# ---------------------------------------------------------------- DAY 4: NO-AI TEST
if ss.phase == "day4":
    st.title("Final task")
    st.write("No chatbot today. Please read the situation below and answer in your own words.")
    st.info(DAY4_SCENARIO)
    answer = st.text_area("Your response", height=200, key="day4_answer")
    if st.button("Continue to the last questions", type="primary", disabled=not answer.strip()):
        ss.day4_answer = answer.strip()
        ss.phase = "final"
        st.rerun()
    st.stop()

# ---------------------------------------------------------------- FINAL QUESTIONNAIRES
if ss.phase == "final":
    st.title("A few last questions")
    st.caption("1 = strongly disagree, 7 = strongly agree")

    def scale(label, key):
        return st.slider(label, 1, 7, 4, key=key)

    st.subheader("Coping confidence")
    c1 = scale("I could handle a similar situation on my own.", "c1")
    c2 = scale("I feel capable of working through this kind of problem myself.", "c2")

    st.subheader("Reliance on the AI")
    r1 = scale("Next time, I'd want the AI's help before thinking it through myself.", "r1")
    r2 = scale("It's easier to let the AI figure these things out than to do it myself.", "r2")

    st.subheader("Seeking human support")
    h1 = scale("For something like this, I would reach out to a friend or family member.", "h1")

    st.subheader("How the chatbot felt")
    p1 = scale("The chatbot felt caring.", "p1")
    p2 = scale("I was satisfied with the chatbot.", "p2")
    p3 = scale("I would use this chatbot again.", "p3")

    st.subheader("A couple of checks")
    m1 = scale("The chatbot agreed with my view of the situation.", "m1")
    m2 = scale("The chatbot asked me to think about the situation differently.", "m2")
    m3 = scale("The chatbot remembered things I had told it before.", "m3")
    guess = st.text_input("In one line, what do you think this study was about?")

    if st.button("Submit", type="primary"):
        cols = ["participant_id", "style", "memory", "timestamp",
                "day4_answer", "conf1", "conf2", "reliance1", "reliance2",
                "human_support", "caring", "satisfaction", "use_again",
                "mc_agreed", "mc_reappraise", "mc_remembered", "study_guess"]
        new = not os.path.exists(final_path(ss.pid))
        with open(final_path(ss.pid), "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if new:
                w.writeheader()
            w.writerow({
                "participant_id": ss.pid, "style": ss.style, "memory": ss.memory,
                "timestamp": now(), "day4_answer": ss.day4_answer,
                "conf1": c1, "conf2": c2, "reliance1": r1, "reliance2": r2,
                "human_support": h1, "caring": p1, "satisfaction": p2, "use_again": p3,
                "mc_agreed": m1, "mc_reappraise": m2, "mc_remembered": m3,
                "study_guess": guess,
            })
        save_session_row(ss.pid, {
            "session_date": today(), "session_type": "day4_test",
            "duration_min": "", "distress_pre": "", "distress_post": "",
            "panas_pre": "", "panas_post": "", "timestamp": now(),
        })
        ss.phase = "thanks"
        st.rerun()
    st.stop()

# ---------------------------------------------------------------- THANKS
if ss.phase == "thanks":
    st.title("You're all done")
    st.success("Thank you so much for taking part. This completes the study. "
               "If anything we discussed left you feeling down, please reach out "
               "to someone you trust.")
    st.stop()
