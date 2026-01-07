import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

API = "https://api.reverb.com/api"

st.set_page_config(page_title="Reverb Inbox", layout="wide")

# ---------- SESSION FLAGS ----------
if "sending" not in st.session_state:
    st.session_state.sending = False
if "last_seen" not in st.session_state:
    st.session_state.last_seen = {}

# ---------- AUTO REFRESH ----------
if not st.session_state.sending:
    st_autorefresh(interval=2000, key="refresh")  # safer than 1s

# ---------- UI ----------
st.title("📬 Reverb Messages")

token = st.text_input("Reverb API Token", type="password")
if not token:
    st.stop()

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/hal+json",
    "Accept-Version": "3.0"
}

# ---------- API ----------
def get_conversations():
    r = requests.get(f"{API}/my/conversations", headers=HEADERS)
    return r.json().get("conversations", []) if r.ok else []

def get_thread(cid):
    r = requests.get(f"{API}/my/conversations/{cid}", headers=HEADERS)
    return r.json() if r.ok else {}

def send_message(cid, body):
    return requests.post(
        f"{API}/my/conversations/{cid}/messages",
        headers=HEADERS,
        json={"body": body}
    ).ok

def get_notifications():
    r = requests.get(f"{API}/my/notifications", headers=HEADERS)
    return r.json().get("notifications", []) if r.ok else []

# ---------- SIDEBAR ----------
st.sidebar.header("🔔 Notifications")

for n in get_notifications():
    st.sidebar.info(f"{n.get('type', '').upper()}: {n.get('message', '')}")

# ---------- INBOX ----------
convs = get_conversations()
if not convs:
    st.info("No conversations")
    st.stop()

labels = {}
for c in convs:
    cid = c["id"]
    user = c.get("other_user", {}).get("username", "Unknown")
    title = c.get("listing", {}).get("title", "General")
    unread = "🔵" if c.get("unread") else "⚪"
    labels[f"{unread} {user} — {title}"] = cid

selected = st.selectbox("Inbox", labels.keys())
cid = labels[selected]

# ---------- THREAD ----------
thread = get_thread(cid)
messages = thread.get("messages", [])

# ---------- NEW MESSAGE SOUND ----------
last_id = messages[-1]["id"] if messages else None
if st.session_state.last_seen.get(cid) != last_id:
    st.session_state.last_seen[cid] = last_id
    st.markdown(
        """
        <audio autoplay>
        <source src="https://actions.google.com/sounds/v1/cartoon/clang_and_wobble.ogg">
        </audio>
        """,
        unsafe_allow_html=True
    )

# ---------- LISTING IMAGE ----------
listing = thread.get("listing", {})
photos = listing.get("photos", [])
if photos:
    st.image(photos[0]["_links"]["full"]["href"], width=200)

# ---------- ORDER / OFFER BADGE ----------
if thread.get("order_id"):
    st.success("📦 Order conversation")
if thread.get("offer"):
    st.warning("💰 Offer conversation")

# ---------- MESSAGES ----------
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

# ---------- TYPING INDICATOR ----------
st.caption("🟢 User may be typing..." if messages else "")

# ---------- REPLY ----------
reply = st.text_area("Reply", key="reply")

if st.button("Send", disabled=st.session_state.sending):
    if reply.strip():
        st.session_state.sending = True
        if send_message(cid, reply):
            st.session_state.reply = ""
            st.success("Sent")
        else:
            st.error("Failed")
        st.session_state.sending = False
