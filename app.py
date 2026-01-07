import streamlit as st
import requests

API_BASE = "https://api.reverb.com/api"

st.set_page_config(page_title="Reverb Messages", layout="wide")
st.title("📬 Reverb Messages")

# ---------------- TOKEN ----------------
api_token = st.text_input("Enter your Reverb API Token", type="password")
if not api_token:
    st.stop()

headers = {
    "Authorization": f"Bearer {api_token}",
    "Accept": "application/hal+json",
    "Accept-Version": "3.0"
}

# ---------------- API HELPERS ----------------
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
        or c.get("_links", {})
             .get("self", {})
             .get("href", "")
             .split("/")[-1]
    )

def extract_listing_title(c):
    listing = c.get("listing")
    if isinstance(listing, dict):
        return listing.get("title", "General conversation")
    return "General conversation"

def extract_sender_name(c):
    # 1️⃣ Best case
    if c.get("last_message_sender_name"):
        return c["last_message_sender_name"]

    # 2️⃣ Reverb-standard: other participant
    other = c.get("other_user")
    if isinstance(other, dict):
        return other.get("username", "Unknown user")

    # 3️⃣ Fallbacks
    buyer = c.get("buyer")
    if isinstance(buyer, dict):
        return buyer.get("username", "Unknown user")

    seller = c.get("seller")
    if isinstance(seller, dict):
        return seller.get("username", "Unknown user")

    return "Unknown user"

def get_last_message_preview(c):
    return c.get("last_message_preview") or ""

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
search = st.sidebar.text_input("Search")

# ---------------- LOAD ----------------
if st.button("Load Inbox"):
    st.session_state["conversations"] = get_conversations(unread_only)

conversations = st.session_state.get("conversations", [])

# ---------------- INBOX ----------------
if conversations:
    st.subheader("Conversations")

    options = []
    conv_lookup = {}

    for c in conversations:
        if not isinstance(c, dict):
            continue

        conv_id = extract_conversation_id(c)
        if not conv_id:
            continue

        sender = extract_sender_name(c)
        preview = get_last_message_preview(c)[:120]
        listing = extract_listing_title(c)
        unread = c.get("unread", False)

        display = (
            f"{'🔵' if unread else '⚪'} "
            f"{sender} — {preview}\n"
            f"{listing}"
        )

        unique_option = f"[{conv_id}] {display}"

        if search.lower() in unique_option.lower():
            options.append(unique_option)
            conv_lookup[unique_option] = conv_id

    if not options:
        st.info("No conversations found.")
        st.stop()

    selected = st.selectbox("Inbox", options=options)
    selected_conv_id = conv_lookup[selected]

    # ---------------- THREAD ----------------
    thread = get_conversation(selected_conv_id)
    messages = thread.get("messages", [])

    st.divider()
    st.subheader("Conversation")

    if isinstance(messages, list) and messages:
        for m in messages:
            if not isinstance(m, dict):
                continue
            st.markdown(
                f"""
                **{m.get('sender_name', 'Unknown')}**  
                {m.get('body', '')}  
                🕒 {m.get('created_at', '')}
                """
            )
            st.markdown("---")
    else:
        st.info("No messages in this conversation.")

    # ---------------- REPLY ----------------
    reply = st.text_area("Reply")

    if st.button("Send"):
        if not reply.strip():
            st.warning("Message cannot be empty")
        else:
            if send_reply(selected_conv_id, reply):
                st.success("Message sent")
            else:
                st.error("Failed to send message")

else:
    st.info("Click **Load Inbox** to fetch your messages.")
