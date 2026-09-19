import os
import json
import numpy as np
import joblib

def generate_synthetic_dataset(num_samples=4000, seed=42):
    np.random.seed(seed)
    
    # 1. Max Pressure Deviation (0.0 to 70.0 kPa above baseline)
    max_p_dev = np.random.uniform(0.0, 65.0, num_samples)
    
    # 2. Avg Pressure Deviation
    avg_p_dev = max_p_dev * np.random.uniform(0.15, 0.55, num_samples)
    
    # 3. Temperature Asymmetry Difference (0.0 to 4.5 °C)
    temp_diff = np.random.uniform(0.0, 4.0, num_samples)
    
    # 4. Gait Asymmetry (0.0 to 30.0 %)
    gait_asym = np.random.uniform(0.0, 28.0, num_samples)
    
    # 5. Cadence (70 to 130 steps/min)
    cadence = np.random.uniform(70.0, 130.0, num_samples)
    
    # 6. Impact Force (0.9 to 2.2 G)
    impact_g = 1.0 + (gait_asym / 30.0) * 0.8 + np.random.normal(0, 0.05, num_samples)
    
    # 7. Patient Age (35 to 85)
    patient_age = np.random.randint(35, 85, num_samples)

    labels = []
    for i in range(num_samples):
        p_score = min(100.0, (max_p_dev[i] / 45.0) * 70.0 + (avg_p_dev[i] / 20.0) * 30.0)
        t_score = min(100.0, (temp_diff[i] / 3.0) * 100.0)
        g_score = min(100.0, (gait_asym[i] / 25.0) * 100.0)
        
        # Clinical composite risk calculation + small stochastic noise
        composite = 0.40 * p_score + 0.30 * t_score + 0.30 * g_score + np.random.normal(0, 2.0)
        
        if composite < 30.0:
            labels.append(0)  # LOW
        elif composite <= 60.0:
            labels.append(1)  # MODERATE
        else:
            labels.append(2)  # HIGH

    X = np.column_stack([
        max_p_dev,
        avg_p_dev,
        temp_diff,
        gait_asym,
        cadence,
        impact_g,
        patient_age
    ])
    y = np.array(labels)
    
    return X, y

def train_and_save_model():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score

    print("Generating synthetic clinical dataset...")
    X, y = generate_synthetic_dataset(num_samples=5000, seed=42)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print("Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("Training RandomForestClassifier model...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model Training Complete! Test Accuracy: {acc * 100:.2f}%")
    print("\nClassification Report:\n", classification_report(y_test, y_pred, target_names=['LOW', 'MODERATE', 'HIGH']))

    feature_names = [
        'max_p_dev',
        'avg_p_dev',
        'temp_diff',
        'gait_asym',
        'cadence',
        'impact_g',
        'patient_age'
    ]
    
    importances = dict(zip(feature_names, [round(float(imp), 4) for imp in model.feature_importances_]))
    print("Feature Importances:", importances)

    output_dir = os.path.join(os.path.dirname(__file__), 'models_ml')
    os.makedirs(output_dir, exist_ok=True)
    
    model_path = os.path.join(output_dir, 'smartfoot_ml_model.joblib')
    metadata_path = os.path.join(output_dir, 'model_metadata.json')

    pipeline_data = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_names,
        'label_mapping': {0: 'LOW', 1: 'MODERATE', 2: 'HIGH'},
        'accuracy': acc,
        'feature_importances': importances
    }
    
    joblib.dump(pipeline_data, model_path)
    print(f"Saved trained ML model to: {model_path}")

    metadata = {
        'trained_at_version': '1.0-ML',
        'algorithm': 'RandomForestClassifier',
        'n_estimators': 100,
        'accuracy': acc,
        'labels': ['LOW', 'MODERATE', 'HIGH'],
        'feature_names': feature_names,
        'feature_importances': importances
    }
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print("Metadata written successfully!")

if __name__ == '__main__':
    train_and_save_model()
