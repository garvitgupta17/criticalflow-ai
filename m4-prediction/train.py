import os
import pandas as pd
import numpy as np
import joblib

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, mean_squared_error

# 1. Path set karein
csv_path = os.path.join(os.path.dirname(__file__), '..', 'training_data.csv')
print(f"Loading data from: {csv_path}")
df = pd.read_csv(csv_path)

# Boolean column ko float me convert karein
df['recent_deployment_flag'] = df['recent_deployment_flag'].astype(float)

# 2. Splits
train_df = df[df['split'] == 'train'].copy()
val_df = df[df['split'] == 'val'].copy()
test_df = df[df['split'] == 'test'].copy()

# 3. Features define karein
num_cols = ['return_code', 'cpu_utilization_pct', 'error_rate_pct', 'transaction_volume_per_hr', 'recent_deployment_flag']
cat_cols = ['system_id', 'subsystem', 'completion_status', 'abend_code', 'primary_message_id']

# 4. Preprocessor pipeline
num_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median', add_indicator=True)),
    ('scaler', StandardScaler())
])

cat_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant', fill_value='UNKNOWN')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

preprocessor = ColumnTransformer(transformers=[
    ('num', num_transformer, num_cols),
    ('cat', cat_transformer, cat_cols)
])

feature_columns = num_cols + cat_cols
X_train = train_df[feature_columns]
X_val = val_df[feature_columns]

# A) Risk Score Model (Regression)
print("Training Risk Score Regressor...")
y_risk_train = train_df['risk_score']
y_risk_val = val_df['risk_score']

risk_model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
])
risk_model.fit(X_train, y_risk_train)
risk_val_preds = risk_model.predict(X_val)
print("Validation Risk Score MSE:", mean_squared_error(y_risk_val, risk_val_preds))

# B) Severity Model (Classification)
print("\nTraining Severity Classifier...")
y_sev_train = train_df['risk_label']
y_sev_val = val_df['risk_label']

sev_model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
])
sev_model.fit(X_train, y_sev_train)
sev_val_preds = sev_model.predict(X_val)
print("\n--- Severity Classification Report ---")
print(classification_report(y_sev_val, sev_val_preds))

# C) Incident Type Model (Classification)
print("\nTraining Incident Type Classifier...")
y_type_train = train_df['scenario_type']
y_type_val = val_df['scenario_type']

type_model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
])
type_model.fit(X_train, y_type_train)
type_val_preds = type_model.predict(X_val)
print("\n--- Incident Type Classification Report ---")
print(classification_report(y_type_val, type_val_preds))

# 5. Model save karein
models_dir = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(models_dir, exist_ok=True)
output_path = os.path.join(models_dir, 'm4_pipeline.joblib')

joblib.dump({
    'risk_model': risk_model,
    'sev_model': sev_model,
    'type_model': type_model,
    'features': feature_columns
}, output_path)

print(f"\nModel pipeline successfully saved to: {output_path}")