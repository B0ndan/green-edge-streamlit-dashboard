import streamlit as st
import json
import os
import glob
import time
import pandas as pd
from datetime import datetime
from PIL import Image, ImageFile
import base64
import struct
import pickle
import threading
import paho.mqtt.client as mqtt

ImageFile.LOAD_TRUNCATED_IMAGES = True

# ==========================================
# ⚙️ 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Sustained Remote Telemetry Dashboard",
    page_icon="📡",
    layout="wide"
)

# ==========================================
# 🔐 2. TTN CONFIGURATION & SECRETS
# ==========================================
# Reads secrets from Streamlit Cloud Secrets (or fallback to local test values)
THE_THINGS_NETWORK_SERVER = st.secrets.get("TTN_SERVER", "au1.cloud.thethings.network")
APPLICATION_ID = st.secrets.get("TTN_APP_ID", "transmission-using-ttgo-new")
API_KEY = st.secrets.get("TTN_API_KEY", "YOUR_NEW_REGENERATED_API_KEY")
DEVICE_ID = st.secrets.get("TTN_DEVICE_ID", "ttgo-03-new")

TARGET_FOLDER = "image_received"
os.makedirs(TARGET_FOLDER, exist_ok=True)

PROGRESS_FILE = os.path.join(TARGET_FOLDER, "RARoom_lorawan_transfer_progress.pkl")
STREAMLIT_LIVE_IMAGE = os.path.join(TARGET_FOLDER, "RARoom_live_progressive.jpg") 
STREAMLIT_TEMP_IMAGE = os.path.join(TARGET_FOLDER, "RARoom_live_progressive.tmp")
FEED_FILE = "live_feed.json"

# Global memory states for MQTT receiver
current_target_label = "Unknown Spontaneous Matrix"
current_target_confidence = "100%"

if os.path.exists(PROGRESS_FILE):
    try:
        with open(PROGRESS_FILE, 'rb') as f:
            chunks = pickle.load(f)
    except Exception:
        chunks = {}
else:
    chunks = {}

# ==========================================
# 📡 3. MQTT RECEIVER LOGIC & HELPER FUNCTIONS
# ==========================================
def load_existing_dashboard_data():
    if os.path.exists(FEED_FILE):
        try:
            with open(FEED_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "target": "Standby Status",
        "confidence": "0%",
        "chunks_received": 0,
        "total_chunks": 1,
        "type": "Idle",
        "live_image_path": "",
        "last_archived_image": "",
        "last_updated": "N/A",
        "history": [],
        "packet_timestamps": []
    }

def log_classification_to_history(target, confidence, trigger_type):
    data = load_existing_dashboard_data()
    history_item = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target": target,
        "confidence": confidence,
        "type": trigger_type
    }
    if "history" not in data:
        data["history"] = []
    data["history"].insert(0, history_item)
    with open(FEED_FILE, "w") as f:
        json.dump(data, f, indent=4)

def update_dashboard_json(target, confidence, chunks_num, total_num, trigger_type, final_archive_path=""):
    data = load_existing_dashboard_data()
    data["target"] = target
    data["confidence"] = confidence
    data["chunks_received"] = chunks_num
    data["total_chunks"] = total_num
    data["type"] = trigger_type
    data["live_image_path"] = STREAMLIT_LIVE_IMAGE
    data["last_archived_image"] = final_archive_path if final_archive_path else data.get("last_archived_image", "")
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    now_ts = time.time()
    if chunks_num <= 1 or len(data.get("packet_timestamps", [])) == 0:
        data["packet_timestamps"] = [{"packet": max(1, chunks_num), "time_elapsed": 0.0, "epoch": now_ts}]
    else:
        timestamps = data.get("packet_timestamps", [])
        if len(timestamps) > 0:
            start_epoch = timestamps[0]["epoch"]
            elapsed = round(now_ts - start_epoch, 2)
            if not any(t["packet"] == chunks_num for t in timestamps):
                timestamps.append({"packet": chunks_num, "time_elapsed": elapsed, "epoch": now_ts})
        data["packet_timestamps"] = timestamps

    if chunks_num == total_num and total_num > 1:
        data["packet_timestamps"] = []

    with open(FEED_FILE, "w") as f:
        json.dump(data, f, indent=4)

def save_progressive_preview(chunks_dict, total):
    with open(STREAMLIT_TEMP_IMAGE, "wb") as f:
        for i in range(total):
            if i in chunks_dict:
                f.write(chunks_dict[i])
            else:
                break
        f.flush()
        os.fsync(f.fileno())

    if os.path.exists(STREAMLIT_TEMP_IMAGE):
        os.replace(STREAMLIT_TEMP_IMAGE, STREAMLIT_LIVE_IMAGE)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Connected to TTN Broker!")
        topic = f"v3/{APPLICATION_ID}@ttn/devices/{DEVICE_ID}/up"
        client.subscribe(topic)
    else:
        print(f"❌ Connection failed: {rc}")

def on_message(client, userdata, msg):
    global chunks, current_target_label, current_target_confidence
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        uplink_message = payload.get("uplink_message")
        if not uplink_message: return
            
        frm_payload = uplink_message.get("frm_payload")
        if not frm_payload: return
            
        raw_bytes = base64.b64decode(frm_payload)
        if len(raw_bytes) == 0: return

        # --- 🎯 1. IMMEDIATE TEXT METADATA LAYER ---
        if b"TEXT:" in raw_bytes:
            try:
                text_data = raw_bytes.decode('utf-8', errors='ignore').strip()
                ai_result = text_data.replace("TEXT:", "")
                
                if "," in ai_result:
                    current_target_label = ai_result.split(",")[0].strip()
                    current_target_confidence = f"{ai_result.split(',')[1].strip()}%"
                else:
                    current_target_label = ai_result.strip()
                    current_target_confidence = "100%"

                trigger_label = "Background Trigger" if "(BG Trigger)" in ai_result else "Primary Target"
                
                log_classification_to_history(current_target_label, current_target_confidence, trigger_label)

                # Reset image buffer
                chunks = {}
                if os.path.exists(PROGRESS_FILE):
                    os.remove(PROGRESS_FILE)
                if os.path.exists(STREAMLIT_LIVE_IMAGE):
                    try:
                        os.remove(STREAMLIT_LIVE_IMAGE)
                    except OSError:
                        pass

                update_dashboard_json(
                    target=current_target_label,
                    confidence=current_target_confidence,
                    chunks_num=0,
                    total_num=1,
                    trigger_type=trigger_label
                )
                return 
            except Exception as e:
                print(f"Failed parsing instant text metadata: {e}")
                return

        # --- 🖼️ 2. IMAGE PACKET PROCESSING ---
        if len(raw_bytes) < 4: return

        chunk_id, total = struct.unpack('>HH', raw_bytes[:4])
        img_payload = raw_bytes[4:]

        # 🚨 CRITICAL FIX 1: New Image Detection
        # If chunk_id is 0, a NEW image transfer is beginning! Wipe previous memory immediately.
        if chunk_id == 0:
            chunks = {}
            if os.path.exists(PROGRESS_FILE):
                os.remove(PROGRESS_FILE)
            
            # Wipe old plot chart latency data for the new stream
            data = load_existing_dashboard_data()
            data["packet_timestamps"] = []
            with open(FEED_FILE, "w") as f:
                json.dump(data, f, indent=4)

        # 🚨 CRITICAL FIX 2: Prevent index overflow
        if chunk_id >= total:
            return  # Ignore malformed/corrupted packet IDs

        if chunk_id not in chunks:
            chunks[chunk_id] = img_payload
            
            with open(PROGRESS_FILE, 'wb') as f:
                pickle.dump(chunks, f)
            
            save_progressive_preview(chunks, total)
            
            update_dashboard_json(
                target=current_target_label,
                confidence=current_target_confidence,
                chunks_num=len(chunks),
                total_num=total,
                trigger_type="Primary Packet Stream"
            )
            
            # --- 🎉 3. IMAGE COMPLETION ARCHIVE ---
            if len(chunks) == total:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_label = current_target_label.replace(' ', '_').replace('/', '_')
                archive_filename = f"reconstructed_{timestamp}_{clean_label}.jpg"
                final_archive_path = os.path.join(TARGET_FOLDER, archive_filename)
                
                if os.path.exists(STREAMLIT_LIVE_IMAGE):
                    with open(STREAMLIT_LIVE_IMAGE, "rb") as src, open(final_archive_path, "wb") as dst:
                        dst.write(src.read())
                
                print(f"🎉 Complete Image Archive Saved: {final_archive_path}")
                
                update_dashboard_json(
                    target=current_target_label,
                    confidence=current_target_confidence,
                    chunks_num=total,
                    total_num=total,
                    trigger_type="Idle",
                    final_archive_path=final_archive_path
                )
                 
                if os.path.exists(PROGRESS_FILE):
                    os.remove(PROGRESS_FILE)  
                chunks = {}
    
    except Exception as e:
        print(f"Parsing error: {e}")

# ==========================================
# 🚀 4. START MQTT IN BACKGROUND THREAD
# ==========================================
@st.cache_resource
def start_ttn_mqtt_listener():
    def run_mqtt():
        client = mqtt.Client() 
        client.username_pw_set(APPLICATION_ID, API_KEY)
        client.on_connect = on_connect
        client.on_message = on_message
        try:
            client.connect(THE_THINGS_NETWORK_SERVER, 1883, 60)
            client.loop_forever()
        except Exception as e:
            print(f"MQTT Connection Error: {e}")

    thread = threading.Thread(target=run_mqtt, daemon=True)
    thread.start()
    return thread

# Initialize background listener
start_ttn_mqtt_listener()

# ==========================================
# 🎨 5. STREAMLIT UI DASHBOARD
# ==========================================
st.markdown("""
    <style>
    .metric-alert {
        background-color: #ff4b4b;
        color: white;
        padding: 22px;
        border-radius: 12px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.45);
    }
    .metric-warning {
        background-color: #ffa500;
        color: white;
        padding: 22px;
        border-radius: 12px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(255, 165, 0, 0.45);
    }
    .metric-safe {
        background-color: #2e7d32;
        color: white;
        padding: 22px;
        border-radius: 12px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(46, 125, 50, 0.45);
    }
    .metric-alert h1, .metric-warning h1, .metric-safe h1 {
        margin: 0;
        font-size: 2.8rem;
        letter-spacing: 1px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Sustained 24/7 Remote Telemetry Dashboard")
st.markdown("---")

def get_image_bytes(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception:
            return None
    return None

if os.path.exists(FEED_FILE):
    try:
        with open(FEED_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        data = {}
else:
    data = {}

target_label = data.get("target", "Standby Status").upper()
confidence_val = data.get("confidence", "0%")
sys_type = data.get("type", "Idle")
chunks_rx = data.get("chunks_received", 0)
total_cx = max(1, data.get("total_chunks", 1))
history = data.get("history", [])
packet_timestamps = data.get("packet_timestamps", [])

if "Primary" in sys_type or chunks_rx > 0:
    st.markdown(f"""
        <div class="metric-alert">
            <p style="margin:0; font-size: 1.15rem; text-transform: uppercase; letter-spacing: 2px;">⚠️ ACTIVE EVENT REGISTERED</p>
            <h1>🚨 {target_label} ({confidence_val})</h1>
        </div>
    """, unsafe_allow_html=True)
elif "Background" in sys_type:
    st.markdown(f"""
        <div class="metric-warning">
            <p style="margin:0; font-size: 1.15rem; text-transform: uppercase; letter-spacing: 2px;">⚠️ BACKGROUND ENVIRONMENT EVENT</p>
            <h1>🔍 {target_label} ({confidence_val})</h1>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
        <div class="metric-safe">
            <p style="margin:0; font-size: 1.15rem; text-transform: uppercase; letter-spacing: 2px;">🟢 FIELD SYSTEM SECURE</p>
            <h1>MONITORING ACTIVE</h1>
        </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Active Streaming Metrics")
    st.metric(label="Data Packets Reassembled", value=f"{chunks_rx} / {total_cx}")
    
    progress_percent = min(1.0, float(chunks_rx) / float(total_cx))
    st.progress(progress_percent)
    
    st.markdown("---")
    
    st.subheader("📈 Packet Reception Latency (Current Stream)")
    if len(packet_timestamps) > 1:
        df_chart = pd.DataFrame(packet_timestamps)
        st.line_chart(
            data=df_chart, 
            x="packet", 
            y="time_elapsed", 
            x_label="Chunk Index", 
            y_label="Elapsed Transmission Time (Seconds)"
        )
    else:
        st.info("No active packet transit. Stream latency metrics will plot dynamically when next image begins transferring.")

with col2:
    st.subheader("🖼️ Live Progressive Canvas")
    live_img = "image_received/RARoom_live_progressive.jpg"
    last_archived = data.get("last_archived_image", "")

    image_placeholder = st.empty()

    try:
        if chunks_rx > 0 and chunks_rx < total_cx:
            img_bytes = get_image_bytes(live_img)
            if img_bytes and len(img_bytes) > 400:
                image_placeholder.image(img_bytes, caption=f"📥 RECONSTRUCTING INCOMING STREAM... ({chunks_rx}/{total_cx})", use_container_width=True)
            else:
                image_placeholder.warning("Awaiting initial sequence packets to compile file headers...")
                
        elif last_archived and os.path.exists(last_archived):
            img_bytes = get_image_bytes(last_archived)
            if img_bytes:
                image_placeholder.image(img_bytes, caption=f"✅ Current Secure Snapshot: {target_label}", use_container_width=True)
            else:
                image_placeholder.info("Standby Mode: Awaiting hardware wake event...")
            
        elif os.path.exists(live_img):
            img_bytes = get_image_bytes(live_img)
            if img_bytes and len(img_bytes) > 400:
                image_placeholder.image(img_bytes, caption="Standby Feed Canvas", use_container_width=True)
            else:
                image_placeholder.info("Standby Mode: Awaiting hardware wake event...")
        else:
            image_placeholder.info("Standby Mode: Awaiting hardware wake event...")
            
    except (OSError, SyntaxError):
        image_placeholder.warning("⚡ Thread locking protection active... Repainting canvas.")

st.markdown("---")
col_chart, col_log = st.columns([1.1, 0.9])

with col_chart:
    st.subheader("📊 Classification Distribution Analysis")
    if len(history) > 0:
        df_hist = pd.DataFrame(history)
        df_hist["target_clean"] = df_hist["target"].str.upper().str.strip()
        
        class_counts = df_hist["target_clean"].value_counts().reset_index()
        class_counts.columns = ["Classification Event", "Occurrences"]
        
        try:
            import plotly.express as px
            fig = px.pie(
                class_counts, 
                values="Occurrences", 
                names="Classification Event", 
                color_discrete_sequence=px.colors.sequential.YlOrRd[::-1],
                hole=0.4
            )
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.bar_chart(class_counts, x="Classification Event", y="Occurrences")
    else:
        st.info("No classification event history captured yet.")

with col_log:
    st.subheader("📜 Historical Classification Records (Real-time)")
    if len(history) > 0:
        df_clean = pd.DataFrame(history)[["timestamp", "target", "confidence", "type"]]
        df_clean.columns = ["Timestamp", "Target Match", "Confidence", "Trigger Source"]
        st.dataframe(df_clean, use_container_width=True, hide_index=True)
    else:
        st.info("Waiting for first sensor classification capture log...")

st.markdown("---")
st.subheader("📚 Historical Field Captures Archive Gallery")

archive_pattern = os.path.join(TARGET_FOLDER, "reconstructed_*.jpg")
archived_files = glob.glob(archive_pattern)
archived_files.sort(key=os.path.getmtime, reverse=True)

if archived_files:
    grid_cols = st.columns(4)
    for idx, img_path in enumerate(archived_files):
        col_selector = idx % 4
        filename = os.path.basename(img_path)
        try:
            parts = filename.replace(".jpg", "").split("_")
            detected_tag = parts[-1].upper()
            time_stamp_str = f"{parts[1]} - {parts[2][:2]}:{parts[2][2:4]}:{parts[2][4:6]}"
        except Exception:
            detected_tag = "UNKNOWN TARGET"
            time_stamp_str = "Archived Record"

        historical_bytes = get_image_bytes(img_path)
        if historical_bytes:
            with grid_cols[col_selector]:
                st.image(historical_bytes, caption=f"🏷️ {detected_tag} ({time_stamp_str})", use_container_width=True)
else:
    st.info("Archive store empty.")

time.sleep(2)
st.rerun()
