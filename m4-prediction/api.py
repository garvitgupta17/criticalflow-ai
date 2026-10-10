import os
import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

# 1. FastAPI app setup
app = FastAPI(title="CriticalFlow M4 Risk Engine", version="1.0.0")

# 2. Trained model pipeline load karein
model_path = os.path.join(os.path.dirname(__file__), 'models', 'm4_pipeline.joblib')
artifacts = joblib.load(model_path)

risk_model = artifacts['risk_model']
sev_model = artifacts['sev_model']
type_model = artifacts['type_model']

# 3. Input JSON Schema (Jo M2/M3 se aayega)
class IncidentRequest(BaseModel):
    incident_id: str
    system_id: Optional[str] = None
    subsystem: Optional[str] = None
    completion_status: Optional[str] = None
    return_code: Optional[float] = None
    abend_code: Optional[str] = None
    primary_message_id: Optional[str] = None
    cpu_utilization_pct: Optional[float] = None
    error_rate_pct: Optional[float] = None
    transaction_volume_per_hr: Optional[float] = None
    recent_deployment_flag: Optional[bool] = False

# 4. Prediction Logic
def run_prediction(data: dict):
    row = {
        'system_id': data.get('system_id'),
        'subsystem': data.get('subsystem'),
        'completion_status': data.get('completion_status'),
        'return_code': data.get('return_code'),
        'abend_code': data.get('abend_code'),
        'primary_message_id': data.get('primary_message_id'),
        'cpu_utilization_pct': data.get('cpu_utilization_pct'),
        'error_rate_pct': data.get('error_rate_pct'),
        'transaction_volume_per_hr': data.get('transaction_volume_per_hr'),
        'recent_deployment_flag': 1.0 if data.get('recent_deployment_flag') else 0.0
    }
    df_single = pd.DataFrame([row])
    
    risk_pred = float(risk_model.predict(df_single)[0])
    sev_pred = str(sev_model.predict(df_single)[0])
    type_pred = str(type_model.predict(df_single)[0])
    
    anomaly_score = round(min(max(risk_pred * 0.95, 0.0), 1.0), 3)

    return {
        "incident_id": data.get("incident_id", "UNKNOWN"),
        "anomaly_score": anomaly_score,
        "risk_score": round(risk_pred, 3),
        "severity": sev_pred,
        "incident_type": type_pred,
        "model_version": "v1.0"
    }

# 5. Routes
@app.get("/health")
def health():
    return {"status": "healthy", "module": "M4"}

@app.post("/predict")
def predict_incident_post(payload: IncidentRequest):
    return run_prediction(payload.model_dump())

@app.get("/predict")
def predict_incident_get(incident_id: str,
                         system_id: Optional[str] = None,
                         subsystem: Optional[str] = None,
                         completion_status: Optional[str] = None,
                         return_code: Optional[float] = None,
                         abend_code: Optional[str] = None,
                         primary_message_id: Optional[str] = None,
                         cpu_utilization_pct: Optional[float] = None,
                         error_rate_pct: Optional[float] = None,
                         transaction_volume_per_hr: Optional[float] = None,
                         recent_deployment_flag: Optional[bool] = False):
    query_data = {
        "incident_id": incident_id,
        "system_id": system_id,
        "subsystem": subsystem,
        "completion_status": completion_status,
        "return_code": return_code,
        "abend_code": abend_code,
        "primary_message_id": primary_message_id,
        "cpu_utilization_pct": cpu_utilization_pct,
        "error_rate_pct": error_rate_pct,
        "transaction_volume_per_hr": transaction_volume_per_hr,
        "recent_deployment_flag": recent_deployment_flag
    }
    return run_prediction(query_data)