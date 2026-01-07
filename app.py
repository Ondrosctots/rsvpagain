import streamlit as st
import requests
import time
from streamlit_autorefresh import st_autorefresh
from typing import Dict, List, Optional

API_BASE = "https://api.reverb.com/api"

st.set_page_config(page_title="Reverb Inbox & Listings", layout="wide")

# ---------------- SESSION STATE ----------------
if "token" not in st.session_state:
    st.session_state.token = ""
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "sending" not in st.session_state:
    st.session_state.sending = False
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = 0
if "reply_text" not in st.session_state:
    st.session_state.reply_text = ""

# ---------------- AUTO REFRESH ----------------
if st.session_state.auto_refresh and not st.session_state.sending:
    st_autorefresh(interval=30000, key="reverb_refresh")  # Reduced to 30s for efficiency

# ---------------- HELPERS ----------------
def get_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/hal+json",
        "Accept-Version": "3.0"
    }

def validate_token(token: str) -> bool:
    if not token.strip():
        return False
    try:
        # Test with a lightweight API call (e.g., fetch one conversation)
        headers = get_headers(token)
        r = requests.get(f"{API_BASE}/my/conversations?per_page=1", headers=headers, timeout=10)
        return r.ok
    except:
        return False

@st.cache_data(ttl=300)  # Cache for 5 minutes
def api_call(url: str, headers: Dict[str, str], method: str = "GET", data: Optional[Dict] = None, retries: int = 3) -> Optional[Dict]:
    for attempt in range(retries):
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                r = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                r = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                r = requests.delete(url, headers=headers, timeout=10)
            if r.ok:
                return r.json() if r.content else {}
            elif r.status_code == 429:  # Rate limit
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                st.error(f"API Error: {r.status_code} - {r.text}")
                return None
        except Exception as e:
            st.error(f"Request failed: {e}")
            time.sleep(1)
    return None

def extract_conversation_id(c: Dict) -> Optional[str]:
    return c.get("id") or c.get("conversation_id") or (c.get("_links", {}).get("self", {}).get("href", "").split("/")[-1] if c.get("_links") else None)

def get_conversations(token: str, page: int = 1, per_page: int = 20) -> List[Dict]:
    data = api_call(f"{API_BASE}/my/conversations?page={page}&per_page={per_page}", get_headers(token))
    return data.get("conversations", []) if data else []

def get_conversation(token: str, cid: str) -> Dict:
    return api_call(f"{API_BASE}/my/conversations/{cid}", get_headers(token)) or {}

def send_message(token: str, cid: str, body: str, attachments: Optional[List] = None) -> bool:
    data = {"body": body}
    if attachments:
        data["attachments"] = attachments  # Placeholder for image uploads
    result = api_call(f"{API_BASE}/my/conversations/{cid}/messages", get_headers(token), "POST", data)
    return result is not None

def mark_conversation_read(token: str, cid: str) -> bool:
    return api_call(f"{API_BASE}/my/conversations/{cid}/read", get_headers(token), "POST") is not None

def get_notifications(token: str) -> List[Dict]:
    data = api_call(f"{API_BASE}/my/notifications", get_headers(token))
    return data.get("notifications", []) if data else []

def get_listings(token: str, page: int = 1, per_page: int = 20) -> List[Dict]:
    data = api_call(f"{API_BASE}/my/listings?page={page}&per_page={per_page}", get_headers(token))
    return data.get("listings", []) if data else []

def get_listing_details(token: str, listing_id: str) -> Dict:
    return api_call(f"{API_BASE}/listings/{listing_id}", get_headers(token)) or {}

def update_listing(token: str, listing_id: str, data: Dict) -> bool:
    return api_call(f"{API_BASE}/listings/{listing_id}", get_headers(token), "PUT", data) is not None

def delete_listing(token: str, listing_id: str) -> bool:
    return api_call(f"{API_BASE}/listings/{listing_id}", get_headers(token), "DELETE") is not None

def create_listing(token: str, data: Dict) -> bool:
    return api_call(f"{API_BASE}/listings", get_headers(token), "POST", data) is not None

def get_orders(token: str) -> List[Dict]:
    data = api_call(f"{API_BASE}/my/orders", get_headers(token))
    return data.get("orders", []) if data else []

def get_offers(token: str) -> List[Dict]:
    data = api_call(f"{API_BASE}/my/offers", get_headers(token))
    return data.get("offers", []) if data else []

def get_sender_name(c: Dict) -> str:
    return c.get("last_message_sender_name") or (c.get("other_user", {}).get("username", "Unknown") if isinstance(c.get("other_user"), dict) else "Unknown")

# ---------------- UI ----------------
st.title("📬 Reverb Messages, Listings & More")

# Global search
search_query = st.text_input("🔍 Global Search (e.g., sender, listing title)", key="global_search")

# Refresh button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.session_state.last_refresh = time.time()
    st.rerun()

# ---------------- SETTINGS TAB FIRST ----------------
tab_settings, tab_inbox, tab_listings, tab_orders, tab_offers, tab_notifications = st.tabs(["⚙️ Settings", "📬 Inbox", "📊 Listings", "📦 Orders", "💰 Offers", "🔔 Notifications"])

with tab_settings:
    st.header("Settings")
    token_input = st.text_input("Reverb API Token", value=st.session_state.token, type="password")
    if st.button("Validate & Save Token"):
        if validate_token(token_input):
            st.session_state.token = token_input
            st.success("Token validated and saved!")
        else:
            st.error("Invalid token. Please check and try again.")
    st.checkbox("Enable Auto-Refresh (every 30s)", value=st.session_state.auto_refresh, key="auto_refresh_toggle")
    if st.button("Logout"):
        st.session_state.token = ""
        st.cache_data.clear()
        st.success("Logged out!")

token = st.session_state.token
if not token:
    st.warning("Please enter and validate your API token in Settings.")
    st.stop()

HEADERS = get_headers(token)

# ===================== INBOX TAB =====================
with tab_inbox:
    st.header("📬 Inbox")
    page = st.number_input("Page", min_value=1, value=1, key="inbox_page")
    convs = get_conversations(token, page)
    
    if not convs:
        st.info("No conversations found.")
    else:
        # Filter by search
        filtered_convs = [c for c in convs if search_query.lower() in (get_sender_name(c) + c.get("listing", {}).get("title", "") + (c.get("last_message_preview") or "")).lower()]
        
        options = []
        conv_lookup = {}
        for c in filtered_convs:
            cid = extract_conversation_id(c)
            if not cid:
                continue
            sender = get_sender_name(c)
            listing = c.get("listing", {}).get("title", "General")
            unread = "🔵" if c.get("unread") else "⚪"
            preview = (c.get("last_message_preview") or "")[:80]
            label = f"[{cid}] {unread} {sender} — {preview}\n{listing}"
            options.append(label)
            conv_lookup[label] = cid
        
        selected = st.selectbox("Select Conversation", options)
        if selected:
            cid = conv_lookup[selected]
            thread = get_conversation(token, cid)
            messages = thread.get("messages", [])
            
            photos = thread.get("listing", {}).get("photos", [])
            if photos:
                st.image(photos[0]["_links"]["full"]["href"], width=220)
            
            if thread.get("order_id"):
                st.success("📦 Order conversation")
            if thread.get("offer"):
                st.warning("💰 Offer conversation")
            
            st.divider()
            for m in messages:
                with st.expander(f"**{m.get('sender_name', 'User')}** - {m.get('created_at')}"):
                    st.write(m.get('body', ''))
            
            col1, col2 = st.columns([3, 1])
            with col1:
                reply = st.text_area("Reply", value=st.session_state.reply_text, key="reply")
            with col2:
                if st.button("Send", disabled=st.session_state.sending):
                    if reply.strip():
                        st.session_state.sending = True
                        if send_message(token, cid, reply):
                            st.session_state.reply_text = ""
                            st.success("Message sent!")
                            st.cache_data.clear()
                        else:
                            st.error("Failed to send.")
                        st.session_state.sending = False
                if st.button("Mark as Read"):
                    if mark_conversation_read(token, cid):
                        st.success("Marked as read!")
                        st.cache_data.clear()

# ===================== LISTINGS TAB =====================
with tab_listings:
    st.header("📊 My Listings")
    page = st.number_input("Page", min_value=1, value=1, key="listings_page")
    listings = get_listings(token, page)
    
    if not listings:
        st.info("No listings found.")
    else:
        # Filter by search
        filtered_listings = [l for l in listings if search_query.lower() in l.get("title", "").lower()]
        
        for l in filtered_listings:
            with st.expander(f"{l.get('title')} - {l.get('state')}"):
                listing_id = l.get("id")
                details = get_listing_details(token, listing_id) if listing_id else {}
                st.write(f"**Price:** {l.get('price', {}).get('amount', '')} {l.get('price', {}).get('currency', '')}")
                st.write(f"**Views:** {details.get('views', 0)} | **Watchers:** {details.get('watchers_count', 0)} | **In Cart:** {details.get('in_cart_count', 0)}")
                st.write(f"**Condition:** {details.get('condition', {}).get('display_name', 'N/A')}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"Edit {listing_id}", key=f"edit_{listing_id}"):
                        # Simple edit form (expand as needed)
                        new_title = st.text_input("New Title", value=l.get("title"))
                        new_price = st.number_input("New Price", value=l.get("price", {}).get("amount", 0.0))
                        if st.button("Save Changes"):
                            if update_listing(token, listing_id, {"title": new_title, "price": {"amount": new_price}}):
                                st.success("Updated!")
                                st.cache_data.clear()
                with col2:
                    if st.button(f"Delete {listing_id}", key=f"delete_{listing_id}"):
                        if delete_listing(token, listing_id):
                            st.success("Deleted!")
                            st.cache_data.clear()
                with col3:
                    photos = details.get("photos", [])
                    if photos:
                        photo_urls = [p.get("_links", {}).get("full", {}).get("href", "N/A") for p in photos]
                        st.write("Photos:", photo_urls)
                        # Optionally display first image
                        if photo_urls[0] != "N/A":
                            st.image(photo_urls[0], width=220)
                    else:
                        st.write("No photos available.")
        
        # Create new listing
        with st.expander("➕ Create New Listing"):
            title = st.text_input("Title")
            description = st.text_area("Description")
            price = st.number_input("Price", min_value=0.0)
            if st.button("Create"):
                if create_listing(token, {"title": title, "description": description, "price": {"amount": price}}):
                    st.success("Created!")
                    st.cache_data.clear()

# ===================== ORDERS TAB =====================
with tab_orders:
    st.header("📦 My Orders")
    orders = get_orders(token)
    if not orders:
        st.info("No orders found.")
    else:
        for o in orders:
            st.write(f"**Order ID:** {o.get('id')} | **Status:** {o.get('status')} | **Buyer:** {o.get('buyer', {}).get('username', 'N/A')}")

# ===================== OFFERS TAB =====================
with tab_offers:
    st.header("💰 My Offers")
    offers = get_offers(token)
    if not offers:
        st.info("No offers found.")
    else:
        for o in offers:
            st.write(f"**Offer ID:** {o.get('id')} | **Amount:** {o.get('amount')} | **Listing:** {o.get('listing', {}).get('title', 'N/A')}")
            # Add accept/reject buttons if API supports

# ===================== NOTIFICATIONS TAB =====================
with tab_notifications:
    st.header("🔔 Notifications")
    notifs = get_notifications(token)
    if not notifs:
        st.info("No notifications.")
    else:
        for n in notifs:
            st.info(f"{n.get('type', '').upper()}: {n.get('message', '')}")
            if st.button(f"Mark Read {n.get('id')}", key=f"mark_{n.get('id')}"):
                # Assume API has a mark read endpoint
                pass
