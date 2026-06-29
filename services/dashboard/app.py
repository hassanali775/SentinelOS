import streamlit as st
import requests
import json
import sseclient
import time

st.set_page_config(
    page_title="SentinelOS Kernel Operator Canvas",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Crucial styling: Transforming the UI from an analytics platform to a bare-metal shell
st.markdown("""
<style>
    .reportview-container { background: #07090e; }
    .stApp { background-color: #07090e; }
    
    /* Process Grid Elements */
    .os-process-card {
        border-left: 3px solid #3b82f6;
        background-color: #0d1117;
        border-top: 1px solid #21262d;
        border-right: 1px solid #21262d;
        border-bottom: 1px solid #21262d;
        padding: 12px;
        border-radius: 2px;
        margin-bottom: 8px;
        font-family: 'SF Mono', Consolas, 'Courier New', monospace;
    }
    .os-process-card.executing { border-left-color: #23a55a; }
    .os-process-card.failed { border-left-color: #f23f43; }
    
    .process-meta {
        font-size: 0.75rem;
        color: #8b949e;
        display: flex;
        justify-content: space-between;
        margin-bottom: 6px;
    }
    .process-title {
        font-size: 0.95rem;
        color: #c9d1d9;
        font-weight: bold;
    }
    .process-payload {
        font-size: 0.85rem;
        color: #58a6ff;
        background: #161b22;
        padding: 6px;
        border-radius: 3px;
        margin-top: 6px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📟 SentinelOS Kernel Operator Console")
st.caption("Distributed AI Infrastructure Matrix // Node: Local Cluster Core")

# Persistent State Management
if "event_history" not in st.session_state:
    st.session_state.event_history = []
if "seen_event_ids" not in st.session_state:
    st.session_state.seen_event_ids = set()

# Initialize dynamic operational frames
if "agent_fleet_state" not in st.session_state:
    st.session_state.agent_fleet_state = {
        "Orchestrator": "IDLE", "Planner": "IDLE", "Executor": "IDLE", "Validator": "IDLE"
    }
if "tool_bus_state" not in st.session_state:
    st.session_state.tool_bus_state = {
        "directory_scanner": "STANDBY", "file_writer": "STANDBY", "network_resolver": "STANDBY"
    }

# --- SYSTEM TOPOLOGY BAR (EXPOSING RUNTIME INFRASTRUCTURE) ---
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
with metric_col1:
    st.metric(label="Broker Pipe Latency", value="42 ms", delta="-3ms (Stable)")
with metric_col2:
    st.metric(label="Context Window Load", value="14.2%", delta="Llama 3 Local")
with metric_col3:
    st.metric(label="Active Pipelines", value=len(st.session_state.event_history), delta="Event Ledger Frame")
with metric_col4:
    st.metric(label="Kernel System State", value="OPERATIONAL")

st.divider()

# Left Panel: Kernel Intent Injection & Fleet Monitor
with st.sidebar:
    st.markdown("### 🖥️ Mission Objectives Injection")
    objective = st.text_area(
        "Define High-Level Autonomous Intent:", 
        placeholder="Input target objective for the agent fleet...", 
        height=100
    )
    launch_btn = st.button("Initialize Kernel Execution Pool", use_container_width=True)
    
    st.divider()
    
    # --- COGNITIVE AGENT FLEET STATES (Screams 'Operating System') ---
    st.markdown("### 🤖 Managed Agent Fleet Matrix")
    for agent, state in st.session_state.agent_fleet_state.items():
        color = "🟢" if state == "ACTIVE" else "🟡" if state == "THINKING" else "⚪"
        st.markdown(f"{color} **{agent} Subsystem:** `{state}`")
        
    st.divider()
    
    # --- ACTIVE TOOL PERIPHERAL BUS ---
    st.markdown("### 🔌 Active Peripheral Tool Bus")
    for tool, status in st.session_state.tool_bus_state.items():
        t_color = "⚡" if status == "ATTACHED" else "💤"
        st.markdown(f"{t_color} `tool_io://{tool}` → **{status}**")

# Main Interface Layout Splitting
col_main, col_telemetry = st.columns([2, 1])

with col_main:
    st.markdown("### 📜 Kernel Process Thread Ledger")
    timeline_placeholder = st.empty()

with col_telemetry:
    st.markdown("### 📡 Stream State Telemetry Matrix")
    status_box = st.code("SYSTEM_STATUS: KERNEL_IDLE")
    raw_debug_placeholder = st.empty()

# --- RUNTIME PIPELINE ORCHESTRATION ENGINE ---
if launch_btn and objective:
    # Clear cache pools for fresh execution instance
    st.session_state.event_history = []
    st.session_state.seen_event_ids = set()
    status_box.code("SYSTEM_STATUS: DISPATCHING_RUN_TX_TO_CONTROL_PLANE")
    
    try:
        res = requests.post(
            "http://localhost:8000/api/v1/runs", 
            json={
                "objective": objective,
                "agent_id": "00000000-0000-0000-0000-000000000000"
            }
        )
        run_data = res.json()
        run_id = run_data.get("id") or run_data.get("run_id") or run_data.get("uuid")
        
        if not run_id:
            st.error(f"Kernel Configuration Rejection: {run_data}")
    except Exception as e:
        st.error(f"Inference Initialization Vector Failure: {str(e)}")
        run_id = None

    if run_id:
        status_box.code(f"SYSTEM_STATUS: STREAMING_LEDGER_OFFSETS\nINSTANCE_UUID: {run_id}")
        stream_url = f"http://localhost:8000/api/v1/runs/{run_id}/stream"
        
        try:
            response = requests.get(stream_url, stream=True)
            client = sseclient.SSEClient(response)
            
            for event in client.events():
                if event.data:
                    data = json.loads(event.data)
                    
                    if data.get("status") == "STREAM_COMPLETE":
                        status_box.code("SYSTEM_STATUS: KERNEL_EXECUTION_TERMINATED_SUCCESS")
                        # Reset all fleet modules to IDLE state upon completion
                        for a in st.session_state.agent_fleet_state: st.session_state.agent_fleet_state[a] = "IDLE"
                        for t in st.session_state.tool_bus_state: st.session_state.tool_bus_state[t] = "STANDBY"
                        break
                    
                    # Deduplicate frame allocations
                    event_key = data.get("id") or data.get("uuid") or str(data.get("sequence_number")) or str(data)
                    
                    if event_key not in st.session_state.seen_event_ids:
                        st.session_state.event_history.append(data)
                        st.session_state.seen_event_ids.add(event_key)
                    
                    # --- DYNAMIC MATRIX STATE MUTATION ENGINE ---
                    ev_type = data.get("event_type", data.get("type", "EVENT_UNSPECIFIED"))
                    
                    # Update fleet and tool state boards based on real event streams
                    if ev_type == "RUN_STARTED":
                        st.session_state.agent_fleet_state["Orchestrator"] = "ACTIVE"
                    elif ev_type == "PLAN_GENERATED":
                        st.session_state.agent_fleet_state["Planner"] = "THINKING"
                        st.session_state.agent_fleet_state["Executor"] = "IDLE"
                    elif ev_type == "TOOL_CALLED":
                        st.session_state.agent_fleet_state["Planner"] = "IDLE"
                        st.session_state.agent_fleet_state["Executor"] = "ACTIVE"
                        target_tool = data.get("tool_name", "directory_scanner")
                        if target_tool in st.session_state.tool_bus_state:
                            st.session_state.tool_bus_state[target_tool] = "ATTACHED"
                    elif ev_type == "TOOL_OUTPUT_RECEIVED":
                        target_tool = data.get("tool_name", "directory_scanner")
                        if target_tool in st.session_state.tool_bus_state:
                            st.session_state.tool_bus_state[target_tool] = "STANDBY"
                    
                    # Force update on sidebar updates inside the streaming loop
                    st.sidebar.empty()
                    
                    # Render telemetry matrix overview data
                    with raw_debug_placeholder.container():
                        st.caption("Live Pipeline Frame Block:")
                        st.json(data)
                    
                    # --- CONSOLE PROCESS THREAD RENDERER ---
                    with timeline_placeholder.container():
                        for ev in reversed(st.session_state.event_history):
                            e_type = ev.get("event_type", ev.get("type", "EVENT_UNSPECIFIED"))
                            content = ev.get("content", ev.get("payload", ""))
                            seq = ev.get("sequence_number", ev.get("offset", 0))
                            t_name = ev.get("tool_name", "")
                            
                            # Determine visual theme profile based on OS event type
                            card_class = "os-process-card"
                            if e_type in ["TOOL_CALLED", "RUN_STARTED"]: card_class += " executing"
                            if "FAIL" in e_type or "ERR" in e_type: card_class += " failed"
                            
                            label_str = f"PID_{seq:03d} // EXPORT_TYPE: {e_type}"
                            if t_name: label_str += f" // ATTACHED_BUS: {t_name}"
                            
                            st.markdown(f"""
                            <div class="{card_class}">
                                <div class="process-meta">
                                    <span>{label_str}</span>
                                    <span>SYS_CLOCK: {time.strftime('%H:%M:%S')}</span>
                                </div>
                                <div class="process-title">⚡ Thread Activity Log Frame</div>
                                <div class="process-payload">{content}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
        except Exception as e:
            st.error(f"Kernel Broker Telemetry Loss: {str(e)}")