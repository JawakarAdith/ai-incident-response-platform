import streamlit as st
import requests

API_URL = "http://localhost:8000/api/v1"

# ── Page config ────────────────────────────────────────────
st.set_page_config(
    page_title="Workflow Automation Platform",
    page_icon="🤖",
    layout="wide"
)

# ── Session state ──────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None


# ── Helper functions ───────────────────────────────────────

def login(email: str, password: str) -> bool:
    response = requests.post(
        f"{API_URL}/auth/login",
        data={"username": email, "password": password}
    )
    if response.status_code == 200:
        st.session_state.token = response.json()["access_token"]
        st.session_state.user_email = email
        return True
    return False


def get_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"}


def run_workflow(task: str, logs: str) -> dict:
    response = requests.post(
        f"{API_URL}/workflow/run",
        json={"task": task, "logs": logs},
        headers=get_headers()
    )
    return response.json()


def get_history() -> list:
    response = requests.get(
        f"{API_URL}/workflow/history",
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return []


def get_workflow_detail(workflow_id: str) -> dict:
    response = requests.get(
        f"{API_URL}/workflow/{workflow_id}",
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return {}


def get_workflow_steps(workflow_id: str) -> list:
    response = requests.get(
        f"{API_URL}/workflow/{workflow_id}/steps",
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return []


def feed_rag_memory(problem: str, solution: str, tags: str) -> dict:
    response = requests.post(
        f"{API_URL}/memory/feed",
        json={"problem": problem, "solution": solution, "tags": tags},
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return {"error": response.text}


def search_rag_memory(query: str) -> dict:
    response = requests.post(
        f"{API_URL}/memory/search",
        json={"query": query},
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return {"error": response.text}


# ── Login page ─────────────────────────────────────────────

def show_login():
    st.title("🤖 Workflow Automation Platform")
    st.subheader("Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if login(email, password):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid email or password!")


# ── Main dashboard ─────────────────────────────────────────

def show_dashboard():
    st.title("🤖 Workflow Automation Platform")

    # Top bar
    col1, col2 = st.columns([6, 1])
    with col1:
        st.write(f"Welcome, **{st.session_state.user_email}**!")
    with col2:
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.user_email = None
            st.rerun()

    st.divider()

    # ── Quick stats bar ────────────────────────────────────
    history = get_history()
    total      = len(history)
    completed  = sum(1 for w in history if w["status"] == "COMPLETED")
    low_conf   = sum(1 for w in history if w["status"] == "COMPLETED_LOW_CONFIDENCE")
    failed     = sum(1 for w in history if w["status"] == "FAILED")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Workflows", total)
    c2.metric("✅ Completed",    completed)
    c3.metric("⚠️ Low Confidence", low_conf)
    c4.metric("❌ Failed",       failed)

    st.divider()

    # ── Tabs ───────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "▶️ Run Workflow",
        "📋 History",
        "🧠 RAG Memory",
        "🔍 Workflow Details"
    ])


    # ══════════════════════════════════════════════════════
    # TAB 1 — Run Workflow
    # ══════════════════════════════════════════════════════
    with tab1:
        st.subheader("Run New Workflow")

        task = st.text_area(
            "Task Description",
            value="Analyze failed deployment logs, create Jira ticket and notify Slack",
            height=100
        )

        logs = st.text_area(
            "Paste Logs Here",
            value=(
                "[02:28:41] ERROR Connection timeout after 30s\n"
                "[02:28:41] ERROR Pool size: 100/100 exhausted\n"
                "[02:28:42] FATAL Payment service crashed"
            ),
            height=200
        )

        if st.button("🚀 Run Workflow", type="primary"):
            with st.spinner("Running workflow... all agents working..."):
                result = run_workflow(task, logs)

            if "detail" in result:
                st.error(f"Error: {result['detail']}")
            else:
                status = result.get("status", "")
                confidence = result.get("confidence_score", 0)

                # Status banner
                if status == "COMPLETED":
                    st.success("✅ Workflow completed with high confidence!")
                elif status == "COMPLETED_LOW_CONFIDENCE":
                    st.warning(
                        f"⚠️ Workflow completed but confidence is low "
                        f"({confidence:.0%}). Jira ticket flagged for review."
                    )
                else:
                    st.error(f"Workflow ended with status: {status}")

                # Metrics row
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Jira Ticket", result.get("jira_ticket_id", "N/A"))
                with col2:
                    st.metric(
                        "Slack Notified",
                        "✅ Yes" if result.get("slack_sent") else "❌ No"
                    )
                with col3:
                    color = "normal" if confidence >= 0.75 else "inverse"
                    st.metric(
                        "Confidence Score",
                        f"{confidence:.0%}",
                        delta="High" if confidence >= 0.75 else "Low — verify ticket",
                        delta_color=color
                    )

                st.divider()

                # Results
                st.subheader("🔍 Root Cause")
                st.info(result.get("root_cause", "N/A"))

                st.subheader("💡 Recommendation")
                st.success(result.get("recommendation", "N/A"))

                # Agent pipeline flow
                st.subheader("🔀 Agent Pipeline")
                agents = [
                    "🧠 Planner",
                    "🔍 RAG Search",
                    "📋 Log Analysis",
                    "💡 Recommendation",
                    "✅ Validation",
                    "🔧 Tool Execution"
                ]
                cols = st.columns(len(agents))
                for col, agent in zip(cols, agents):
                    col.success(agent)


    # ══════════════════════════════════════════════════════
    # TAB 2 — History
    # ══════════════════════════════════════════════════════
    with tab2:
        st.subheader("Workflow History")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col3:
            if st.button("🔄 Refresh", key="refresh_history"):
                st.rerun()

        # Filter bar
        with col1:
            filter_status = st.selectbox(
                "Filter by status",
                ["All", "COMPLETED", "COMPLETED_LOW_CONFIDENCE", "FAILED"]
            )
        with col2:
            search_term = st.text_input("Search by title", placeholder="e.g. payment")

        # Apply filters
        filtered = history
        if filter_status != "All":
            filtered = [w for w in filtered if w["status"] == filter_status]
        if search_term:
            filtered = [
                w for w in filtered
                if search_term.lower() in w["title"].lower()
            ]

        if not filtered:
            st.info("No workflows match your filters.")
        else:
            for wf in filtered:
                status = wf["status"]
                if status == "COMPLETED":
                    icon = "✅"
                elif status == "COMPLETED_LOW_CONFIDENCE":
                    icon = "⚠️"
                else:
                    icon = "❌"

                with st.expander(
                    f"{icon} {wf['title'][:60]} — {wf['created_at'][:19]}"
                ):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.write(f"**Status:** {status}")
                    with col2:
                        st.write(f"**Created by:** {wf['created_by']}")
                    with col3:
                        score = wf.get("confidence_score") or 0
                        st.write(f"**Confidence:** {score:.0%}")
                    with col4:
                        # Button to jump to details tab
                        if st.button(
                            "🔍 View Details",
                            key=f"view_{wf['id']}"
                        ):
                            st.session_state["selected_workflow_id"] = wf["id"]
                            st.rerun()


    # ══════════════════════════════════════════════════════
    # TAB 3 — RAG Memory
    # ══════════════════════════════════════════════════════
    with tab3:
        st.subheader("🧠 RAG Memory — Feed Past Incidents")
        st.write(
            "Teach the AI from past incidents. "
            "Next time a similar problem occurs, it will use this knowledge."
        )

        subtab1, subtab2 = st.tabs(["➕ Feed New Memory", "🔎 Search Memory"])

        # ── Feed new memory ────────────────────────────────
        with subtab1:
            st.markdown("#### Add a past incident to memory")

            problem = st.text_area(
                "Problem / Error Description",
                placeholder=(
                    "e.g. Database connection pool exhausted during peak traffic. "
                    "Payment service crashed with FATAL error."
                ),
                height=120
            )

            solution = st.text_area(
                "Solution / Fix Applied",
                placeholder=(
                    "e.g. Increased connection pool size from 100 to 300. "
                    "Added connection timeout retry logic. Restarted payment service."
                ),
                height=120
            )

            tags = st.text_input(
                "Tags (comma separated)",
                placeholder="e.g. database, connection-pool, payment-service"
            )

            if st.button("💾 Save to Memory", type="primary"):
                if not problem or not solution:
                    st.warning("Please fill in both Problem and Solution fields.")
                else:
                    with st.spinner("Saving to RAG memory..."):
                        result = feed_rag_memory(problem, solution, tags)

                    if "error" in result:
                        st.error(f"Failed to save: {result['error']}")
                    else:
                        st.success(
                            "✅ Saved to memory! The AI will use this "
                            "for similar incidents in future."
                        )

        # ── Search memory ──────────────────────────────────
        with subtab2:
            st.markdown("#### Search past incidents in memory")

            query = st.text_input(
                "Describe the problem",
                placeholder="e.g. database timeout connection pool"
            )

            if st.button("🔎 Search", type="primary"):
                if not query:
                    st.warning("Please enter a search query.")
                else:
                    with st.spinner("Searching memory..."):
                        result = search_rag_memory(query)

                    if "error" in result:
                        st.error(f"Search failed: {result['error']}")
                    elif not result.get("results"):
                        st.info("No similar incidents found in memory.")
                    else:
                        st.success(
                            f"Found {len(result['results'])} similar incident(s):"
                        )
                        for i, item in enumerate(result["results"], 1):
                            with st.expander(f"Incident #{i} — similarity: {item.get('score', 'N/A')}"):
                                st.markdown("**Problem:**")
                                st.write(item.get("problem", "N/A"))
                                st.markdown("**Solution:**")
                                st.write(item.get("solution", "N/A"))
                                if item.get("tags"):
                                    st.markdown(
                                        f"**Tags:** `{'` `'.join(item['tags'].split(','))}`"
                                    )


    # ══════════════════════════════════════════════════════
    # TAB 4 — Workflow Details
    # ══════════════════════════════════════════════════════
    with tab4:
        st.subheader("🔍 Workflow Details")

        # Pre-fill if coming from history tab
        default_id = st.session_state.get("selected_workflow_id", "")

        workflow_id = st.text_input(
            "Enter Workflow ID",
            value=default_id,
            placeholder="e.g. 3f2a1b..."
        )

        # Quick select from recent history
        if history:
            recent_options = {
                f"{w['title'][:40]} ({w['created_at'][:10]})": w["id"]
                for w in history[:10]
            }
            selected_label = st.selectbox(
                "Or pick from recent workflows",
                options=["— select —"] + list(recent_options.keys())
            )
            if selected_label != "— select —":
                workflow_id = recent_options[selected_label]

        if st.button("🔍 Load Details", type="primary") and workflow_id:
            with st.spinner("Loading workflow details..."):
                detail = get_workflow_detail(workflow_id)
                steps  = get_workflow_steps(workflow_id)

            if not detail:
                st.error("Workflow not found.")
            else:
                output = detail.get("output_data", {}) or {}
                confidence = output.get("confidence_score", 0)
                status = detail.get("status", "")

                # Header
                if status == "COMPLETED":
                    st.success(f"✅ {detail['title']}")
                elif status == "COMPLETED_LOW_CONFIDENCE":
                    st.warning(f"⚠️ {detail['title']} — Low Confidence")
                else:
                    st.error(f"❌ {detail['title']}")

                # Overview metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Status", status)
                col2.metric("Confidence", f"{confidence:.0%}")
                col3.metric("Jira Ticket",  output.get("jira_ticket_id", "N/A"))
                col4.metric(
                    "Slack",
                    "✅ Sent" if output.get("slack_sent") else "❌ Not sent"
                )

                st.divider()

                # Root cause + recommendation
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("🔍 Root Cause")
                    st.info(output.get("root_cause", "N/A"))
                with col_b:
                    st.subheader("💡 Recommendation")
                    st.success(output.get("recommendation", "N/A"))

                st.divider()

                # Agent steps timeline
                st.subheader("🔀 Agent Steps Timeline")

                if not steps:
                    st.info(
                        "Step details not available. "
                        "The /steps endpoint may need to be added — see note below."
                    )
                else:
                    for step in sorted(steps, key=lambda x: x.get("step_order", 0)):
                        agent_icons = {
                            "PlannerAgent":       "🧠",
                            "RAGSearchAgent":     "🔍",
                            "LogAnalysisAgent":   "📋",
                            "RecommendationAgent":"💡",
                            "ValidationAgent":    "✅",
                            "ToolExecutionAgent": "🔧"
                        }
                        icon = agent_icons.get(step.get("agent_name", ""), "⚙️")

                        with st.expander(
                            f"{icon} Step {step.get('step_order')} — "
                            f"{step.get('step_name')} [{step.get('status')}]"
                        ):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Input:**")
                                st.text(step.get("input_data", "N/A"))
                            with col2:
                                st.markdown("**Output:**")
                                st.text(step.get("output_data", "N/A"))

                # Meta info
                st.divider()
                st.caption(
                    f"Workflow ID: `{detail['id']}` | "
                    f"Created by: {detail['created_by']} | "
                    f"Created at: {detail['created_at'][:19]}"
                )


# ── Main ───────────────────────────────────────────────────

if st.session_state.token is None:
    show_login()
else:
    show_dashboard()