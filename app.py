import streamlit as st
import requests
import time

# ---------------- CONFIG ----------------
API_BASE = "https://api.reverb.com/api"

st.set_page_config(
    page_title="Reverb Messages Inbox",
    layout="wide"
)

st.title("📬 Reverb Messages Inbox")

# ---------------- TOKEN INPUT ----------------
api_token = st.text_input(
    "Enter your Reverb API Token",
    type="password",
    help="Required every session. Token is never saved."
)

if not api_token:
    st.info("Please enter your API token to continue.")
    st.stop()

headers = {
    "Authorization": f"Bearer {api_token}",
    "Accept": "application/hal+json",
    "Content-Type": "application/hal+json",
    "Accept-Version": "3.0"
}

# ---------------- API HELPERS ----------------
def extract_conversation_id(c):
    return (
        c.get("id")
        or c.get("conversation_id")
        or c.get("_links", {})
             .get("self", {})
             .get("href", "")
             .split("/")[-1]
    )

def get_all_conversations(unread_only=False):
    url = f"{API_BASE}/my/conversations"
    params = {"unread_only": "true"} if unread_only else {}

    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        st.error("Failed to load conversations.")
        return []

    return r.json().get("conversations", [])

def get_conversation(conv_id):
    r = requests.get(
        f"{API_BASE}/my/conversations/{conv_id}",
        headers=headers
    )
    if r.status_code != 200:
        st.error("Failed to load conversation.")
        return {}
    return r.json()

def send_reply(conv_id, body):
    r = requests.post(
        f"{API_BASE}/my/conversations/{conv_id}/messages",
        headers=headers,
        json={"body": body}
    )
    return r.status_code in [200, 201]

# ---------------- SIDEBAR CONTROLS ----------------
st.sidebar.header("⚙️ Inbox Settings")

unread_only = st.sidebar.checkbox("Show unread only", value=False)
auto_refresh = st.sidebar.checkbox("Auto refresh (30s)", value=False)
search_query = st.sidebar.text_input("Search conversations")

if auto_refresh:
    time.sleep(30)
    st.experimental_rerun()

# ---------------- LOAD CONVERSATIONS ----------------
if st.button("📥 Load Conversations"):
    st.session_state["conversations"] = get_all_conversations(unread_only)

conversations = st.session_state.get("conversations", [])

# ---------------- DISPLAY CONVERSATION LIST ----------------
if conversations:
    st.subheader("📂 Conversations")

    conv_map = {}

    for c in conversations:
        conv_id = extract_conversation_id(c)
        if not conv_id:
            continue

        sender = c.get("last_message_sender_name", "Unknown sender")
        preview = c.get("last_message_preview", "")
        unread = "🔔" if c.get("unread", False) else ""
        listing = (
            c.get("listing", {})
             .get("title", "General conversation")
        )

        label = f"{unread} {sender} — {listing}\n{preview}"

        if search_query.lower() in label.lower():
            conv_map[label] = conv_id

    if not conv_map:
        st.warning("No conversations match your filters.")
        st.stop()

    selected_label = st.selectbox(
        "Select a conversation",
        options=list(conv_map.keys())
    )

    selected_conv_id = conv_map[selected_label]

    # ---------------- LOAD MESSAGES ----------------
    data = get_conversation(selected_conv_id)
    messages = data.get("messages", [])

    st.divider()
    st.subheader("💬 Messages")

    if not messages:
        st.info("No messages yet.")
    else:
        for msg in messages:
            sender = msg.get("sender_name", "Unknown")
            body = msg.get("body", "")
            created = msg.get("created_at", "")

            st.markdown(
                f"""
                **{sender}**  
                {body}  
                🕒 {created}
                """
            )
            st.markdown("---")

    # ---------------- REPLY ----------------
    st.subheader("✉️ Reply")

    reply_text = st.text_area(
        "Write your reply",
        height=120,
        placeholder="Type your message here..."
    )

    col1, col2 = st.columns([1, 3])

    with col1:
        send = st.button("Send Reply")

    with col2:
        st.caption("Tip: Keep replies professional and concise.")

    if send:
        if not reply_text.strip():
            st.warning("Reply cannot be empty.")
        else:
            if send_reply(selected_conv_id, reply_text):
                st.success("Message sent successfully.")
            else:
                st.error("Failed to send message.")

else:
    st.info("Click **Load Conversations** to fetch your inbox.")
