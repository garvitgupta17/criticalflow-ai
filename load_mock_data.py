import json
import getpass
import psycopg

# --------------------------------------------------
# 1. Load mock JSON data
# --------------------------------------------------

json_file = r"m6_dashboard\mock_data\incidents.json"

with open(json_file, "r", encoding="utf-8") as file:
    incidents = json.load(file)

print(f"Loaded {len(incidents)} incidents from JSON.")


# --------------------------------------------------
# 2. Ask for PostgreSQL password
# --------------------------------------------------

password = getpass.getpass("Enter PostgreSQL password: ")


# --------------------------------------------------
# 3. Connect to PostgreSQL
# --------------------------------------------------

connection = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="criticalflow_ai",
    user="postgres",
    password=password
)


# --------------------------------------------------
# 4. Insert incidents into PostgreSQL
# --------------------------------------------------

insert_query = """
INSERT INTO incidents (
    schema_version,
    incident_id,
    timestamp,
    system_id,
    subsystem,
    job_name,
    job_id,
    step_name,
    completion_status,
    return_code,
    abend_code,
    primary_message_id,
    cpu_utilization_pct,
    error_rate_pct,
    transaction_volume_per_hr,
    recent_deployment_flag,
    raw_log_snippet,
    risk_score,
    risk_label,
    anomaly_score,
    incident_type,
    model_version,
    root_cause,
    explanation,
    evidence,
    remediation
)
VALUES (
    %(schema_version)s,
    %(incident_id)s,
    %(timestamp)s,
    %(system_id)s,
    %(subsystem)s,
    %(job_name)s,
    %(job_id)s,
    %(step_name)s,
    %(completion_status)s,
    %(return_code)s,
    %(abend_code)s,
    %(primary_message_id)s,
    %(cpu_utilization_pct)s,
    %(error_rate_pct)s,
    %(transaction_volume_per_hr)s,
    %(recent_deployment_flag)s,
    %(raw_log_snippet)s,
    %(risk_score)s,
    %(risk_label)s,
    %(anomaly_score)s,
    %(incident_type)s,
    %(model_version)s,
    %(root_cause)s,
    %(explanation)s,
    %(evidence)s,
    %(remediation)s
)
ON CONFLICT (incident_id) DO NOTHING;
"""


# --------------------------------------------------
# 5. Insert all incidents
# --------------------------------------------------

with connection.cursor() as cursor:
    cursor.executemany(insert_query, incidents)

connection.commit()


# --------------------------------------------------
# 6. Close connection
# --------------------------------------------------

connection.close()

print("Mock data successfully inserted into PostgreSQL.")
