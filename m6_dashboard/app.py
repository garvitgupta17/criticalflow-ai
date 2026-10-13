import pandas as pd
import streamlit as st

from db import load_incidents


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="CriticalFlow AI",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* Main background */
    .stApp {
        background-color: #0b0f14;
    }

    /* Main content */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111720;
        border-right: 1px solid #27303a;
    }

    /* Headings */
    h1, h2, h3 {
        letter-spacing: -0.5px;
    }

    /* PostgreSQL mode banner */
    .mock-banner {
        background: linear-gradient(
            90deg,
            rgba(34, 197, 94, 0.15),
            rgba(34, 197, 94, 0.05)
        );
        border: 1px solid rgba(34, 197, 94, 0.35);
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 20px;
        color: #86efac;
        font-size: 14px;
    }

    /* Dashboard section */
    .section-title {
        font-size: 20px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #111720;
        border: 1px solid #27303a;
        padding: 18px;
        border-radius: 14px;
    }

    div[data-testid="stMetricLabel"] {
        color: #9ca8b5;
    }

    /* Tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid #27303a;
        border-radius: 12px;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
    }

    /* Status pills */
    .status-pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
    }

    .live-pill {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }

    .mock-pill {
        background: rgba(250, 204, 21, 0.15);
        color: #facc15;
        border: 1px solid rgba(250, 204, 21, 0.3);
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# LOAD DATA FROM POSTGRESQL
# ============================================================

@st.cache_data(ttl=30)
def get_incidents():
    return load_incidents()


df = get_incidents()


if df.empty:
    st.warning("No incidents are currently available.")
    st.stop()


# Convert DataFrame to list of dictionaries.
# Existing dashboard logic can continue using `incidents`.

incidents = df.to_dict("records")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def risk_count(label):
    return int((df["risk_label"] == label).sum())


def format_value(value):
    if pd.isna(value):
        return "Not available"

    return value


def get_selected_incident(incident_id):
    rows = df[df["incident_id"] == incident_id]

    if rows.empty:
        return None

    return rows.iloc[0]


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <h1 style="margin-bottom:0;">CriticalFlow AI</h1>
        <p style="color:#9ca8b5; margin-top:5px;">
            Incident Intelligence Platform
        </p>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Incidents",
            "Incident Detail",
            "System Health",
            "Demo Scenarios"
        ]
    )

    st.markdown("---")

    st.markdown(
        """
        <div class="status-pill live-pill">
            ● POSTGRESQL
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("Data source: PostgreSQL")


# ============================================================
# OVERVIEW PAGE
# ============================================================

if page == "Overview":

    st.title("CriticalFlow AI")

    st.markdown(
        """
        <p style="color:#9ca8b5; font-size:16px;">
            AI-powered incident intelligence and operational risk monitoring.
        </p>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="mock-banner">
            🟢 <b>POSTGRESQL DATA MODE</b> — Dashboard is reading incident
            data directly from the PostgreSQL database.
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------

    total_incidents = len(df)
    high_risk = int(df["risk_label"].isin(["HIGH", "CRITICAL"]).sum())
    critical = risk_count("CRITICAL")
    normal = int((df["incident_type"] == "NORMAL").sum())

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Incidents",
            total_incidents
        )

    with col2:
        st.metric(
            "High Risk",
            high_risk
        )

    with col3:
        st.metric(
            "Critical",
            critical
        )

    with col4:
        st.metric(
            "Normal Execution",
            normal
        )

    # --------------------------------------------------------
    # RISK DISTRIBUTION
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Risk Distribution</div>',
        unsafe_allow_html=True
    )

    risk_distribution = (
        df["risk_label"]
        .value_counts()
        .reindex(
            ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            fill_value=0
        )
    )

    st.bar_chart(risk_distribution)

    # --------------------------------------------------------
    # INCIDENT TYPES
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Incident Types</div>',
        unsafe_allow_html=True
    )

    incident_types = df["incident_type"].value_counts()

    st.bar_chart(incident_types)

    # --------------------------------------------------------
    # RECENT INCIDENTS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Recent Incidents</div>',
        unsafe_allow_html=True
    )

    recent_columns = [
        "incident_id",
        "timestamp",
        "system_id",
        "job_name",
        "completion_status",
        "risk_label",
        "risk_score"
    ]

    available_columns = [
        column
        for column in recent_columns
        if column in df.columns
    ]

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# INCIDENTS PAGE
# ============================================================

elif page == "Incidents":

    st.title("Incidents")

    st.markdown(
        """
        <p style="color:#9ca8b5;">
            All incidents currently available in PostgreSQL.
        </p>
        """,
        unsafe_allow_html=True
    )

    # Filters

    col1, col2, col3 = st.columns(3)

    with col1:

        risk_options = [
            "ALL",
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL"
        ]

        selected_risk = st.selectbox(
            "Risk Level",
            risk_options
        )

    with col2:

        systems = ["ALL"] + sorted(
            df["system_id"].dropna().unique().tolist()
        )

        selected_system = st.selectbox(
            "System",
            systems
        )

    with col3:

        incident_type_options = (
            ["ALL"]
            + sorted(
                df["incident_type"]
                .dropna()
                .unique()
                .tolist()
            )
        )

        selected_type = st.selectbox(
            "Incident Type",
            incident_type_options
        )

    filtered_df = df.copy()

    if selected_risk != "ALL":
        filtered_df = filtered_df[
            filtered_df["risk_label"] == selected_risk
        ]

    if selected_system != "ALL":
        filtered_df = filtered_df[
            filtered_df["system_id"] == selected_system
        ]

    if selected_type != "ALL":
        filtered_df = filtered_df[
            filtered_df["incident_type"] == selected_type
        ]

    st.markdown(
        f"**Showing {len(filtered_df)} incident(s)**"
    )

    display_columns = [
        "incident_id",
        "timestamp",
        "system_id",
        "subsystem",
        "job_name",
        "completion_status",
        "return_code",
        "abend_code",
        "risk_label",
        "risk_score",
        "incident_type"
    ]

    available_columns = [
        column
        for column in display_columns
        if column in filtered_df.columns
    ]

    st.dataframe(
        filtered_df[available_columns],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# INCIDENT DETAIL PAGE
# ============================================================

elif page == "Incident Detail":

    st.title("Incident Detail")

    incident_ids = df["incident_id"].tolist()

    selected_incident_id = st.selectbox(
        "Select Incident",
        incident_ids
    )

    incident = get_selected_incident(
        selected_incident_id
    )

    if incident is not None:

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        st.subheader(
            f"{incident['incident_id']} — "
            f"{incident['job_name']}"
        )

        st.caption(
            f"System: {format_value(incident['system_id'])} | "
            f"Subsystem: {format_value(incident['subsystem'])}"
        )

        # ----------------------------------------------------
        # Risk / Execution
        # ----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Risk Label",
                format_value(incident["risk_label"])
            )

        with col2:
            st.metric(
                "Risk Score",
                format_value(incident["risk_score"])
            )

        with col3:
            st.metric(
                "Execution Status",
                format_value(incident["completion_status"])
            )

        with col4:
            st.metric(
                "Incident Type",
                format_value(incident["incident_type"])
            )

        # ----------------------------------------------------
        # Operational Metrics
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Operational Metrics</div>',
            unsafe_allow_html=True
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "CPU Utilization",
                (
                    f"{incident['cpu_utilization_pct']}%"
                    if pd.notna(incident["cpu_utilization_pct"])
                    else "Not available"
                )
            )

        with col2:
            st.metric(
                "Error Rate",
                (
                    f"{incident['error_rate_pct']}%"
                    if pd.notna(incident["error_rate_pct"])
                    else "Not available"
                )
            )

        with col3:
            st.metric(
                "Transactions / Hr",
                format_value(
                    incident["transaction_volume_per_hr"]
                )
            )

        with col4:
            st.metric(
                "Return Code",
                format_value(incident["return_code"])
            )

        # ----------------------------------------------------
        # Execution Information
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Execution Information</div>',
            unsafe_allow_html=True
        )

        execution_data = {
            "Incident ID": incident["incident_id"],
            "Timestamp": incident["timestamp"],
            "System ID": incident["system_id"],
            "Subsystem": incident["subsystem"],
            "Job Name": incident["job_name"],
            "Job ID": incident["job_id"],
            "Step Name": incident["step_name"],
            "Completion Status": incident["completion_status"],
            "Return Code": incident["return_code"],
            "ABEND Code": incident["abend_code"],
            "Primary Message ID": incident["primary_message_id"],
        }

        execution_df = pd.DataFrame(
            execution_data.items(),
            columns=["Field", "Value"]
        )

        execution_df["Value"] = execution_df["Value"].apply(
            format_value
        )

        st.dataframe(
            execution_df,
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # Model / Investigation Information
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">AI Investigation</div>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)

        with col1:

            st.markdown("### Risk Assessment")

            st.write(
                f"**Risk Score:** "
                f"{format_value(incident['risk_score'])}"
            )

            st.write(
                f"**Risk Label:** "
                f"{format_value(incident['risk_label'])}"
            )

            st.write(
                f"**Anomaly Score:** "
                f"{format_value(incident['anomaly_score'])}"
            )

            st.write(
                f"**Model Version:** "
                f"{format_value(incident['model_version'])}"
            )

        with col2:

            st.markdown("### Investigation")

            st.write(
                f"**Incident Type:** "
                f"{format_value(incident['incident_type'])}"
            )

            st.write(
                f"**Recent Deployment:** "
                f"{format_value(incident['recent_deployment_flag'])}"
            )

        # ----------------------------------------------------
        # Root Cause
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Root Cause</div>',
            unsafe_allow_html=True
        )

        st.info(
            format_value(incident["root_cause"])
        )

        # ----------------------------------------------------
        # Explanation
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Explanation</div>',
            unsafe_allow_html=True
        )

        st.write(
            format_value(incident["explanation"])
        )

        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Evidence</div>',
            unsafe_allow_html=True
        )

        st.write(
            format_value(incident["evidence"])
        )

        # ----------------------------------------------------
        # Raw Log
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Raw Log Snippet</div>',
            unsafe_allow_html=True
        )

        st.code(
            format_value(incident["raw_log_snippet"]),
            language="text"
        )

        # ----------------------------------------------------
        # Remediation
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">Recommended Remediation</div>',
            unsafe_allow_html=True
        )

        st.success(
            format_value(incident["remediation"])
        )


# ============================================================
# SYSTEM HEALTH PAGE
# ============================================================

elif page == "System Health":

    st.title("System Health")

    st.markdown(
        """
        <p style="color:#9ca8b5;">
            Operational health overview based on incident data.
        </p>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # System Summary
    # --------------------------------------------------------

    system_summary = (
        df.groupby("system_id")
        .agg(
            incidents=("incident_id", "count"),
            high_risk=(
                "risk_label",
                lambda x: x.isin(["HIGH", "CRITICAL"]).sum()
            ),
            avg_risk_score=("risk_score", "mean")
        )
        .reset_index()
    )

    system_summary["avg_risk_score"] = (
        system_summary["avg_risk_score"]
        .round(2)
    )

    st.dataframe(
        system_summary,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # CPU Utilization
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">CPU Utilization</div>',
        unsafe_allow_html=True
    )

    cpu_df = df[
        ["incident_id", "cpu_utilization_pct"]
    ].dropna()

    if not cpu_df.empty:

        cpu_df = cpu_df.set_index("incident_id")

        st.bar_chart(
            cpu_df
        )

    else:

        st.info(
            "CPU utilization data is not available."
        )

    # --------------------------------------------------------
    # Error Rate
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Error Rate</div>',
        unsafe_allow_html=True
    )

    error_df = df[
        ["incident_id", "error_rate_pct"]
    ].dropna()

    if not error_df.empty:

        error_df = error_df.set_index("incident_id")

        st.bar_chart(
            error_df
        )

    else:

        st.info(
            "Error rate data is not available."
        )


# ============================================================
# DEMO SCENARIOS PAGE
# ============================================================

elif page == "Demo Scenarios":

    st.title("Demo Scenarios")

    st.markdown(
        """
        <p style="color:#9ca8b5;">
            Golden test scenarios available in the current dataset.
        </p>
        """,
        unsafe_allow_html=True
    )

    scenario_columns = [
        "incident_id",
        "incident_type",
        "completion_status",
        "abend_code",
        "risk_label",
        "risk_score",
        "root_cause"
    ]

    available_columns = [
        column
        for column in scenario_columns
        if column in df.columns
    ]

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True
    )

    st.markdown(
        '<div class="section-title">Scenario Summary</div>',
        unsafe_allow_html=True
    )

    for _, row in df.iterrows():

        with st.expander(
            f"{row['incident_id']} — "
            f"{row['incident_type']} — "
            f"{row['risk_label']}"
        ):

            st.write(
                f"**Job:** {row['job_name']}"
            )

            st.write(
                f"**System:** {row['system_id']}"
            )

            st.write(
                f"**Completion Status:** "
                f"{format_value(row['completion_status'])}"
            )

            st.write(
                f"**ABEND Code:** "
                f"{format_value(row['abend_code'])}"
            )

            st.write(
                f"**Risk Score:** "
                f"{format_value(row['risk_score'])}"
            )

            st.write(
                f"**Root Cause:** "
                f"{format_value(row['root_cause'])}"
            )

            st.write(
                f"**Remediation:** "
                f"{format_value(row['remediation'])}"
            )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "CriticalFlow AI • PostgreSQL-backed M6 Dashboard • "
    "Data source: PostgreSQL"
)