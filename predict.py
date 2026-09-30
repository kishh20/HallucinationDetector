import os
import joblib
import pandas as pd
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_V2_PATH = os.path.join(BASE_DIR, "hallucination_model_v2.pkl")

print("Loading XGBoost V2 model...")
model = joblib.load(MODEL_V2_PATH)

print("Loading SentenceTransformer (all-MiniLM-L6-v2)...")
encoder = SentenceTransformer("all-MiniLM-L6-v2")
print("Model loaded successfully!\n")


def cosine_similarity(a, b):
    denom = ((a * a).sum() ** 0.5) * ((b * b).sum() ** 0.5)
    if denom == 0:
        return 0.0
    return float((a * b).sum() / denom)


def predict_hallucination(knowledge, question, answer):
    # Separate embeddings
    knowledge_emb = encoder.encode([knowledge])[0]
    question_emb = encoder.encode([question])[0]
    answer_emb = encoder.encode([answer])[0]

    # Relational features
    k_a_sim = cosine_similarity(knowledge_emb, answer_emb)
    q_a_sim = cosine_similarity(question_emb, answer_emb)
    k_q_sim = cosine_similarity(knowledge_emb, question_emb)

    # Lexical overlap
    k_words = set(knowledge.lower().split())
    a_words = set(answer.lower().split())
    word_overlap = (
        len(k_words.intersection(a_words)) / len(a_words)
        if a_words else 0.0
    )

    feature_names = [
        "knowledge_answer_similarity",
        "question_answer_similarity",
        "knowledge_question_similarity",
        "word_overlap"
    ]

    features_df = pd.DataFrame(
        [[k_a_sim, q_a_sim, k_q_sim, word_overlap]],
        columns=feature_names
    )

    prediction = model.predict(features_df)[0]
    probability = model.predict_proba(features_df)[0]

    # In dataset: 1 = hallucinated ('yes'), 0 = faithful ('no')
    is_hallucinated = (prediction == 1)
    confidence = float(probability[1 if is_hallucinated else 0] * 100)

    return {
        "is_hallucinated": is_hallucinated,
        "confidence": confidence,
        "features": {
            "knowledge_answer_similarity": k_a_sim,
            "question_answer_similarity": q_a_sim,
            "knowledge_question_similarity": k_q_sim,
            "word_overlap": word_overlap
        }
    }


if __name__ == "__main__":
    print("=" * 50)
    print("   HALLUCINATION DETECTOR (XGBoost V2)")
    print("=" * 50)

    knowledge = input("Enter Knowledge: ")
    question = input("Enter Question: ")
    answer = input("Enter Answer: ")

    result = predict_hallucination(knowledge, question, answer)

    print("\n" + "=" * 50)
    print("   DETECTION RESULT")
    print("=" * 50)
    if result["is_hallucinated"]:
        print("Prediction: ❌ HALLUCINATED")
    else:
        print("Prediction: ✅ NOT HALLUCINATED (FAITHFUL)")

    print(f"Confidence: {result['confidence']:.2f}%")
    print("\nFeature Details:")
    for k, v in result["features"].items():
        print(f"  - {k}: {v:.4f}")
    print("=" * 50)