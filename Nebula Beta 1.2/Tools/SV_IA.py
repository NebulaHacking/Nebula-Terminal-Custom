
import os
import json
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

MODEL_PATH = "Tools/shadowviper_rf_model.pkl"
SCALER_PATH = "Tools/shadowviper_scaler.pkl"
FEATURES_PATH = "Tools/shadowviper_features.json"


def extract_features(data_dict):
    """
    Extrait un vecteur de features numériques à partir du dict résultat de collecte.
    """
    features = []
    features.append(len(data_dict.get("domain", "")))
    features.append(data_dict.get("avg_ttl", 0))
    features.append(len(data_dict.get("open_ports", [])))
    features.append(data_dict.get("latitude", 0))
    features.append(data_dict.get("longitude", 0))
    features.append(int(data_dict.get("proxy", False)))
    features.append(int(data_dict.get("hosting", False)))
    features.append(int(data_dict.get("mobile", False)))
    features.append(len(data_dict.get("country", "")))
    features.append(len(data_dict.get("region", "")))
    features.append(len(data_dict.get("city", "")))
    features.append(len(data_dict.get("isp", "")))
    features.append(len(data_dict.get("org", "")))
    features.append(len(data_dict.get("asn", "")))
    features.append(len(data_dict.get("timezone", "")))

    # Sauvegarde optionnelle du nombre de features (debug)
    with open(FEATURES_PATH, "w") as f:
        json.dump({"features_count": len(features)}, f)

    return features


def train_shadowviper_ai(dataset_path="Tools/dataset.json"):
    if not os.path.exists(dataset_path):
        print("[ERREUR] Aucun dataset trouvé pour l’entraînement.")
        return False

    with open(dataset_path, "r") as f:
        data = json.load(f)

    # Extraction des features
    X = np.array([item["features"] for item in data])
    y = np.array([item["label"] for item in data])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Sauvegarde du scaler
    joblib.dump(scaler, SCALER_PATH)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"[INFO] Modèle entraîné - Précision : {acc:.2f}")

    # Sauvegarde du modèle
    joblib.dump(model, MODEL_PATH)
    print(f"[INFO] Modèle sauvegardé dans {MODEL_PATH}")

    return True


def start_phase_2(result_dict):
    """
    Lance l'inférence avec le modèle entraîné, en utilisant le dict d'infos collectées.
    """
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        print("[ERREUR] Modèle ou scaler non trouvés, entraîne-le d’abord.")
        return

    scaler = joblib.load(SCALER_PATH)
    model = joblib.load(MODEL_PATH)

    features = extract_features(result_dict)  # dict avec une seule collecte
    X = np.array([features])
    X_scaled = scaler.transform(X)

    prediction = model.predict(X_scaled)[0]
    prediction_prob = model.predict_proba(X_scaled)[0][1]  # probabilité classe 1 (suspect)

    if prediction == 1:
        print("Alerte : élément suspect détecté.")
    else:
        print("Analyse OK : pas de suspicion détectée.")

    print(f"[IA] Probabilité suspicion : {prediction_prob*100:.1f}%")


if __name__ == "__main__":
    print("ShadowViper IA - Options:")
    print("1 - Entraîner le modèle")
    print("2 - Tester une analyse avec un fichier JSON de données collectées")
    choix = input("Choix (1 ou 2) : ").strip()

    if choix == "1":
        success = train_shadowviper_ai()
        if not success:
            print("Échec de l'entraînement.")

    elif choix == "2":
        json_path = "Tools/dataset.json"

        if not os.path.exists(json_path):
            print(f"Fichier {json_path} non trouvé, collecte des données nécessaire.")
        else:
            with open(json_path, "r") as f:
                data = json.load(f)

            # data est une liste de dicts, on en teste un seul (ex: le premier)
            exemple_unique = data[0]

            # IMPORTANT : le dict doit contenir les clés nécessaires pour extract_features
            start_phase_2(exemple_unique)

    else:
        print("Choix invalide.")
