import pandas as pd
import joblib

from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from xgboost import XGBClassifier

print("Loading dataset...")

df = pd.read_csv("clean_dataset.csv")

texts = df["text"].tolist()
labels = df["hallucination"]

print("Loading embedding model...")

embedder = SentenceTransformer("all-MiniLM-L6-v2")

print("Generating embeddings...")

embeddings = embedder.encode(
    texts,
    show_progress_bar=True
)

print("Embedding Shape:", embeddings.shape)

print("\nSplitting dataset...")

X_train, X_test, y_train, y_test = train_test_split(
    embeddings,
    labels,
    test_size=0.2,
    random_state=42,
    stratify=labels
)

print("\nTraining XGBoost...")

model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric="logloss"
)

model.fit(X_train, y_train)

print("\nTraining Completed!")

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\nAccuracy:")
print(accuracy)

print("\nClassification Report:")
print(classification_report(y_test, predictions))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, predictions))

joblib.dump(model, "hallucination_model.pkl")

print("\nModel saved successfully!")