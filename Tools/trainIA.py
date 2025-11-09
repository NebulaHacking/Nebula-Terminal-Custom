

import os
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.datasets import make_classification



# Création du dossier Tools s'il n'existe pas
os.makedirs("Tools", exist_ok=True)

# Générer des données factices pour entraîner le modèle
X, y = make_classification(n_samples=500, n_features=15, random_state=42)

# Séparer en train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)

# Créer et appliquer scaler
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

# Entraîner le modèle
model = RandomForestClassifier(random_state=42)
model.fit(X_train_scaled, y_train)

# Sauvegarder scaler et modèle dans le dossier Tools
with open('Tools/scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

with open('Tools/model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Modèle et scaler entraînés et sauvegardés dans le dossier Tools.")
