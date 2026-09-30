import os
import joblib
import pandas as pd
from sentence_transformers import SentenceTransformer

from generator import generate_answer
from verifier import verify_answer

# =======================================
# Load XGBoost V2 & Encoder
# =======================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_V2_PATH = os.path.join(BASE_DIR, "hallucination_model_v2.pkl")

print("Loading hallucination detector V2...")
detector = joblib.load(MODEL_V2_PATH)
encoder = SentenceTransformer("all-MiniLM-L6-v2")
print("Hallucination detector V2 loaded!")

FEATURE_NAMES = [
    "knowledge_answer_similarity",
    "question_answer_similarity",
    "knowledge_question_similarity",
    "word_overlap"
]


# =======================================
# Cosine similarity
# =======================================

def cosine_similarity(a, b):
    denom = ((a * a).sum() ** 0.5) * ((b * b).sum() ** 0.5)
    if denom == 0:
        return 0.0
    return float((a * b).sum() / denom)


# =======================================
# XGBoost V2 verification
# =======================================

def detect_hallucination(
    knowledge,
    question,
    answer,
    custom_detector=None,
    custom_encoder=None
):
    model_detector = custom_detector or detector
    model_encoder = custom_encoder or encoder

    # Create embeddings
    knowledge_embedding = model_encoder.encode([knowledge])[0]
    question_embedding = model_encoder.encode([question])[0]
    answer_embedding = model_encoder.encode([answer])[0]

    # Relationship features
    knowledge_answer_similarity = cosine_similarity(
        knowledge_embedding,
        answer_embedding
    )

    question_answer_similarity = cosine_similarity(
        question_embedding,
        answer_embedding
    )

    knowledge_question_similarity = cosine_similarity(
        knowledge_embedding,
        question_embedding
    )

    # Word overlap
    knowledge_words = set(knowledge.lower().split())
    answer_words = set(answer.lower().split())

    if answer_words:
        word_overlap = (
            len(knowledge_words.intersection(answer_words))
            / len(answer_words)
        )
    else:
        word_overlap = 0.0

    # Feature DataFrame (with names matching train_v2.py)
    features_df = pd.DataFrame([[
        knowledge_answer_similarity,
        question_answer_similarity,
        knowledge_question_similarity,
        word_overlap
    ]], columns=FEATURE_NAMES)

    # Prediction
    prediction = model_detector.predict(features_df)[0]
    probability = model_detector.predict_proba(features_df)[0]

    # prediction 1 = hallucinated; prediction 0 = faithful
    if prediction == 1:
        return False, float(probability[1] * 100)
    else:
        return True, float(probability[0] * 100)


# =======================================
# Unified Local ML Verification
# =======================================

def verify_with_local_ml(
    knowledge,
    question,
    answer,
    contexts=None,
    custom_detector=None,
    custom_encoder=None
):
    """
    Ensemble verification combining:
    1. DeBERTa NLI CrossEncoder (premise vs hypothesis)
    2. XGBoost V2 (cosine similarity + lexical overlap features)
    """
    if contexts is None:
        contexts = [knowledge] if knowledge else []

    # 1. NLI Verification
    nli_result = verify_answer(answer, contexts)
    contradiction = nli_result["contradiction"]
    entailment = nli_result["entailment"]
    neutral = nli_result["neutral"]

    # 2. XGBoost V2 Verification
    xgb_verified, xgb_confidence = detect_hallucination(
        knowledge,
        question,
        answer,
        custom_detector=custom_detector,
        custom_encoder=custom_encoder
    )

    # 3. Ensemble Decision
    nli_says_ok = (entailment >= 50 and entailment > contradiction)
    xgb_says_ok = xgb_verified

    if nli_says_ok and xgb_says_ok:
        verified = True
    elif not nli_says_ok and not xgb_says_ok:
        verified = False
    elif nli_says_ok and not xgb_says_ok:
        # NLI indicates entailment but XGBoost flags: require higher NLI certainty and low contradiction
        verified = (entailment >= 65 and contradiction < 20)
    else:
        # XGBoost confirms faithfulness with high confidence, but NLI scored neutral due to entity/name variations
        verified = (contradiction < 20 and xgb_confidence >= 75)

    return {
        "verified": verified,
        "status": "verified" if verified else "unsupported",
        "entailment": entailment,
        "contradiction": contradiction,
        "neutral": neutral,
        "xgb_verified": xgb_verified,
        "xgb_confidence": xgb_confidence,
        "confidence": entailment if verified else neutral
    }


# =======================================
# Complete pipeline
# =======================================

def run_pipeline(question):
    from retrieve import retrieve
    print("\n" + "=" * 70)
    print("🔎 SEARCHING KNOWLEDGE SOURCES...")
    print("=" * 70)

    # Retrieval
    results = retrieve(question, top_k=3)

    if not results:
        return {
            "status": "no_data",
            "answer": "No reliable data found."
        }

    print("\n📚 FOUND RELEVANT EVIDENCE")
    contexts = []

    for i, result in enumerate(results, 1):
        print(f"\nSource {i}: {result['title']}")
        print(f"Similarity: {result['similarity']:.4f}")
        print(f"Hybrid Score: {result.get('score', 0):.4f}")
        print(f"SQuAD Question: {result['question']}")
        print(f"SQuAD Answer: {result['answer']}")
        print("\nEvidence:")
        print(result["context"])
        print("-" * 70)
        contexts.append(result["context"])

    # Generate answer
    print("\n" + "=" * 70)
    print("🤖 GENERATING ANSWER...")
    print("=" * 70)

    answer = generate_answer(question, contexts)

    print("\nGenerated Answer:")
    print(answer)

    # Verification
    print("\n" + "=" * 70)
    print("🛡️ RUNNING ENSEMBLE VERIFICATION (NLI + XGBOOST V2)...")
    print("=" * 70)

    knowledge = "\n\n".join(contexts)
    decision = verify_with_local_ml(knowledge, question, answer, contexts=contexts)

    print(f"\nNLI Scores -> Entailment: {decision['entailment']:.2f}% | Contradiction: {decision['contradiction']:.2f}% | Neutral: {decision['neutral']:.2f}%")
    print(f"XGBoost V2 -> {'✅ NOT HALLUCINATED' if decision['xgb_verified'] else '❌ HALLUCINATED'} (Confidence: {decision['xgb_confidence']:.2f}%)")
    print(f"Ensemble Verdict -> {'✅ ANSWER VERIFIED' if decision['verified'] else '❌ ANSWER NOT SUPPORTED'}")

    return {
        "status": decision["status"],
        "answer": answer,
        "confidence": decision["confidence"],
        "entailment": decision["entailment"],
        "contradiction": decision["contradiction"],
        "neutral": decision["neutral"],
        "xgb_verified": decision["xgb_verified"],
        "xgb_confidence": decision["xgb_confidence"],
        "sources": results
    }


# =======================================
# Test
# =======================================

if __name__ == "__main__":
    question = input("\nEnter your question: ")
    result = run_pipeline(question)

    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)
    print("\nStatus:", result["status"])
    print("Answer:", result["answer"])
    if "confidence" in result:
        print(f"Confidence: {result['confidence']:.2f}%")
    if "xgb_confidence" in result:
        print(f"XGBoost confidence: {result['xgb_confidence']:.2f}%")