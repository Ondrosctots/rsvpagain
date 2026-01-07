import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh
import hashlib

API = "https://api.reverb.com/api"

st.set_page_config(page_title="Reverb Inbox", layout="wide")

# ---------------- SESSION STATE ----------------
if "sending" not in st.session_state:
    st.session_state.sending = False

if "last_seen_msg" not in st.session_state:
    st.session_state.last_seen_msg = {}

# ---------------- AUTO REFRESH ----------------
if not st.session_state.sending:
    st_autorefresh(interval=2000, key="reverb_refresh")

# ---------------- UI ----------------
st.title("📬 Reverb Messages")

token = st.text_input("Reverb API Token", type="password")
if not token:
    st.stop()

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/hal+json",
    "Accept-Version": "3.0"
}

# ---------------- HELPERS ----------------
def extract_conversation_id(c):
    if c.get("id"):
        return c["id"]
    if c.get("conversation_id"):
        return c["conversation_id"]
    href = c.get("_links", {}).get("self", {}).get("href")
    if href:
        return href.split("/")[-1]
    return None

def get_conversations():
    r = requests.get(f"{API}/my/conversations", headers=HEADERS)
    return r.json().get("conversations", []) if r.ok else []

def get_conversation(cid):
    r = requests.get(f"{API}/my/conversations/{cid}", headers=HEADERS)
    return r.json() if r.ok else {}

def send_message(cid, body):
    r = requests.post(
        f"{API}/my/conversations/{cid}/messages",
        headers=HEADERS,
        json={"body": body}
    )
    return r.ok

def get_notifications():
    r = requests.get(f"{API}/my/notifications", headers=HEADERS)
    return r.json().get("notifications", []) if r.ok else []

def get_sender_name(c):
    if c.get("last_message_sender_name"):
        return c["last_message_sender_name"]
    other = c.get("other_user")
    if isinstance(other, dict):
        return other.get("username", "Unknown")
    return "Unknown"

def message_fingerprint(m):
    base = (
        (m.get("created_at") or "") +
        (m.get("sender_name") or "") +
        (m.get("body") or "")
    )
    return hashlib.md5(base.encode()).hexdigest()

# ---------------- SIDEBAR ----------------
st.sidebar.header("🔔 Notifications")
for n in get_notifications():
    st.sidebar.info(f"{n.get('type', '').upper()}: {n.get('message', '')}")

# ---------------- INBOX ----------------
convs = get_conversations()
if not convs:
    st.info("No conversations found.")
    st.stop()

labels = {}
for c in convs:
    if not isinstance(c, dict):
        continue

    cid = extract_conversation_id(c)
    if not cid:
        continue

    sender = get_sender_name(c)
    listing = c.get("listing", {}).get("title", "General")
    unread = "🔵" if c.get("unread") else "⚪"
    preview = (c.get("last_message_preview") or "")[:80]

    labels[f"{unread} {sender} — {preview}\n{listing}"] = cid

if not labels:
    st.warning("No usable conversations.")
    st.stop()

# Preserve selection
if "selected" not in st.session_state:
    st.session_state.selected = list(labels.keys())[0]

selected = st.selectbox(
    "Inbox",
    labels.keys(),
    index=list(labels.keys()).index(st.session_state.selected)
    if st.session_state.selected in labels else 0
)

st.session_state.selected = selected
cid = labels[selected]

# ---------------- THREAD ----------------
thread = get_conversation(cid)
messages = thread.get("messages", [])

# ---------------- NEW MESSAGE SOUND ----------------
if messages:
    last_fp = message_fingerprint(messages[-1])
    if st.session_state.last_seen_msg.get(cid) != last_fp:
        st.session_state.last_seen_msg[cid] = last_fp
        st.markdown(
            """
            <audio autoplay>
            <source src="https://actions.google.com/sounds/v1/cartoon/clang_and_wobble.ogg">
            </audio>
            """,
            unsafe_allow_html=True
        )

# ---------------- LISTING IMAGE ----------------
listing = thread.get("listing", {})
photos = listing.get("photos", [])
if photos:
    st.image(photos[0]["_links"]["full"]["href"], width=220)

# ---------------- BADGES ----------------
if thread.get("order_id"):
    st.success("📦 Order conversation")
if thread.get("offer"):
    st.warning("💰 Offer conversation")

# ---------------- MESSAGES ----------------
st.divider()
for m in messages:
    st.markdown(
        f"""
        **{m.get('sender_name', 'User')}**  
        {m.get('body', '')}  
        🕒 {m.get('created_at')}
        """
    )
    st.markdown("---")

# ---------------- REPLY ----------------
reply = st.text_area("Reply", key="reply")

if st.button("Send", disabled=st.session_state.sending):
    if reply.strip():
        st.session_state.sending = True
        if send_message(cid, reply):
            st.session_state.reply = ""
            st.success("Message sent")
        else:
            st.error("Failed to send")
        st.session_state.sending = False
    else:
        st.warning("Message cannot be empty")
