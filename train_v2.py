import pandas as pd
import joblib

from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from xgboost import XGBClassifier


print("Loading dataset...")

df = pd.read_csv("dataset.csv")

# Keep only valid rows
df = df.dropna(
    subset=["knowledge", "question", "answer", "hallucination"]
)

# Convert labels
df["hallucination"] = df["hallucination"].map({
    "yes": 1,
    "no": 0
})

print("Dataset shape:", df.shape)


# ------------------------------------------------
# Load embedding model
# ------------------------------------------------

print("\nLoading embedding model...")

encoder = SentenceTransformer("all-MiniLM-L6-v2")


# ------------------------------------------------
# Create separate embeddings
# ------------------------------------------------

print("\nCreating knowledge embeddings...")

knowledge_embeddings = encoder.encode(
    df["knowledge"].tolist(),
    show_progress_bar=True
)

print("\nCreating question embeddings...")

question_embeddings = encoder.encode(
    df["question"].tolist(),
    show_progress_bar=True
)

print("\nCreating answer embeddings...")

answer_embeddings = encoder.encode(
    df["answer"].tolist(),
    show_progress_bar=True
)


# ------------------------------------------------
# Create relationship features
# ------------------------------------------------

print("\nCreating relationship features...")


def cosine_similarity(a, b):
    return (a * b).sum(axis=1) / (
        ((a * a).sum(axis=1) ** 0.5) *
        ((b * b).sum(axis=1) ** 0.5)
    )


knowledge_answer_similarity = cosine_similarity(
    knowledge_embeddings,
    answer_embeddings
)

question_answer_similarity = cosine_similarity(
    question_embeddings,
    answer_embeddings
)

knowledge_question_similarity = cosine_similarity(
    knowledge_embeddings,
    question_embeddings
)


# ------------------------------------------------
# Additional simple lexical feature
# ------------------------------------------------

def word_overlap(knowledge, answer):

    knowledge_words = set(knowledge.lower().split())
    answer_words = set(answer.lower().split())

    if not answer_words:
        return 0

    return len(
        knowledge_words.intersection(answer_words)
    ) / len(answer_words)


overlap_features = []

for knowledge, answer in zip(
    df["knowledge"],
    df["answer"]
):

    overlap_features.append(
        word_overlap(knowledge, answer)
    )


# ------------------------------------------------
# Combine features
# ------------------------------------------------

features = pd.DataFrame({
    "knowledge_answer_similarity":
        knowledge_answer_similarity,

    "question_answer_similarity":
        question_answer_similarity,

    "knowledge_question_similarity":
        knowledge_question_similarity,

    "word_overlap":
        overlap_features
})

labels = df["hallucination"]


print("\nFeature shape:", features.shape)

print("\nFeature preview:")
print(features.head())


# ------------------------------------------------
# Train/test split
# ------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    features,
    labels,
    test_size=0.2,
    random_state=42,
    stratify=labels
)


# ------------------------------------------------
# Train XGBoost
# ------------------------------------------------

print("\nTraining XGBoost V2...")

model = XGBClassifier(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric="logloss"
)

model.fit(X_train, y_train)


# ------------------------------------------------
# Evaluate
# ------------------------------------------------

predictions = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

print("\n==============================")
print("       V2 RESULTS")
print("==============================")

print("\nAccuracy:")
print(accuracy)

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions
    )
)

print("\nConfusion Matrix:")
print(
    confusion_matrix(
        y_test,
        predictions
    )
)


# ------------------------------------------------
# Save model
# ------------------------------------------------

joblib.dump(
    model,
    "hallucination_model_v2.pkl"
)

print(
    "\nV2 model saved as "
    "hallucination_model_v2.pkl"
)