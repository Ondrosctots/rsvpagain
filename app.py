# file: reverb_messenger.py
import streamlit as st
import requests
import time

st.set_page_config(page_title="Reverb Messaging Tool", layout="wide")
st.title("📬 Reverb Messaging Tool")

# -----------------------------
# User Inputs
# -----------------------------
api_token = st.text_input("Reverb API Token", type="password")
st.write("Enter your Reverb API token above to access messages.")

# -----------------------------
# Functions
# -----------------------------
def fetch_messages():
    """Fetch messages from Reverb API."""
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        response = requests.get("https://api.reverb.com/api/messages", headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch messages: {e}")
        return []

def send_message(recipient_id, body, uploaded_files):
    """Send a message with optional images."""
    headers = {"Authorization": f"Bearer {api_token}"}

    files = []
    for f in uploaded_files:
        files.append(("files[]", (f.name, f.getvalue(), f.type)))

    data = {"body": body, "recipient_id": recipient_id}

    try:
        response = requests.post(
            "https://api.reverb.com/api/messages",
            headers=headers,
            data=data,
            files=files
        )
        if response.status_code == 201:
            st.success("✅ Message sent successfully!")
        else:
            st.error(f"Failed to send message: {response.text}")
    except Exception as e:
        st.error(f"Error sending message: {e}")

# -----------------------------
# Auto-refresh messages every second
# -----------------------------
placeholder = st.empty()

if api_token:
    while True:
        with placeholder.container():
            messages = fetch_messages()
            if not messages:
                st.info("No messages found.")
            else:
                for msg in messages:
                    sender = msg.get("from", {}).get("name", "Unknown")
                    subject = msg.get("subject", "No Subject")
                    body = msg.get("body", "")
                    category = msg.get("category", {}).get("description", "Unknown")
                    msg_id = msg.get("id")

                    with st.expander(f"From: {sender} | Subject: {subject} | Category: {category}"):
                        st.write(body)

                        # Reply section
                        reply_text = st.text_area(f"Reply to {sender}", key=f"reply_{msg_id}")
                        uploaded_files = st.file_uploader(
                            "Upload images to send",
                            type=["png", "jpg", "jpeg"],
                            accept_multiple_files=True,
                            key=f"upload_{msg_id}"
                        )

                        if st.button(f"Send Reply to {sender}", key=f"send_{msg_id}"):
                            if reply_text.strip() == "":
                                st.warning("Please enter a message before sending.")
                            else:
                                send_message(msg.get("from", {}).get("id"), reply_text, uploaded_files)
                                st.experimental_rerun()  # Refresh the messages

        time.sleep(1)  # Refresh every second
