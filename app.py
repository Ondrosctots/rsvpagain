import streamlit as st
import requests
import time

API_BASE = "https://api.reverb.com/api"

st.set_page_config(page_title="Reverb Inbox", layout="wide")
st.title("📬 Reverb Messages")

# ---------------- TOKEN ----------------
api_token = st.text_input(
    "Enter your Reverb API Token",
    type="password"
)

if not api_token:
    st.stop()

headers = {
    "Authorization": f"Bearer {api_token}",
    "Accept": "application/hal+json",
    "Accept-Version": "3.0"
}

# ---------------- HELPERS ----------------
def get_conversations(unread_only=False):
    params = {"unread_only": "true"} if unread_only else {}
    r = requests.get(f"{API_BASE}/my/conversations", headers=headers, params=params)
    if r.status_code != 200:
        st.error("Failed to load conversations")
        return []
    return r.json().get("conversations", [])

def extract_conversation_id(c):
    return (
        c.get("id")
        or c.get("conversation_id")
        or c.get("_links", {}).get("self", {}).get("href", "").split("/")[-1]
    )

def get_last_message(c):
    messages = c.get("messages")
    if isinstance(messages, list) and messages:
        return messages[-1]
    return None

def get_conversation(conv_id):
    r = requests.get(f"{API_BASE}/my/conversations/{conv_id}", headers=headers)
    if r.status_code != 200:
        return {}
    return r.json()

def send_reply(conv_id, body):
    r = requests.post(
        f"{API_BASE}/my/conversations/{conv_id}/messages",
        headers=headers,
        json={"body": body}
    )
    return r.status_code in (200, 201)

# ---------------- SIDEBAR ----------------
st.sidebar.header("Inbox")
unread_only = st.sidebar.checkbox("Unread only")
search = st.sidebar.text_input("Search messages")

# ---------------- LOAD ----------------
if st.button("Load Inbox"):
    st.session_state["conversations"] = get_conversations(unread_only)

conversations = st.session_state.get("conversations", [])

# ---------------- INBOX LIST ----------------
if conversations:
    st.subheader("Conversations")

    inbox = []

    for c in conversations:
        conv_id = extract_conversation_id(c)
        if not conv_id:
            continue

        last_msg = get_last_message(c)
        sender = last_msg.get("sender_name", "Unknown") if last_msg else "Unknown"
        preview = last_msg.get("body", "")[:120] if last_msg else ""
        created = last_msg.get("created_at", "")
        unread = c.get("unread", False)

        listing_title = "General conversation"
        listing = c.get("listing")
        if isinstance(listing, dict):
            listing_title = listing.get("title", listing_title)

        label = (
            f"{'🔵' if unread else '⚪'} "
            f"{sender} — {preview}\n"
            f"{listing_title} • {created}"
        )

        if search.lower() in label.lower():
            inbox.append((label, conv_id))

    if not inbox:
        st.info("No conversations found.")
        st.stop()

    selected_label = st.selectbox(
        "Inbox",
        options=[x[0] for x in inbox]
    )

    selected_conv_id = dict(inbox)[selected_label]

    # ---------------- THREAD ----------------
    thread = get_conversation(selected_conv_id)
    messages = thread.get("messages", [])

    st.divider()
    st.subheader("Conversation")

    for m in messages:
        st.markdown(
            f"""
            **{m.get('sender_name', 'Unknown')}**  
            {m.get('body', '')}  
            🕒 {m.get('created_at', '')}
            """
        )
        st.markdown("---")

    # ---------------- REPLY ----------------
    reply = st.text_area("Reply")

    if st.button("Send"):
        if reply.strip():
            if send_reply(selected_conv_id, reply):
                st.success("Message sent")
            else:
                st.error("Failed to send")
        else:
            st.warning("Message cannot be empty")

else:
    st.info("Click **Load Inbox** to fetch messages.")
