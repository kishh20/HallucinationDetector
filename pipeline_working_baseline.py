import joblib
from sentence_transformers import SentenceTransformer

from retrieve import retrieve
from generator import generate_answer
from verifier import verify_answer


# =======================================
# Load NLI verifier
# =======================================

print("Loading NLI verifier...")

nli_model = SentenceTransformer(
    "cross-encoder/nli-deberta-v3-base"
)

print("NLI verifier loaded!")


# =======================================
# Load XGBoost V2
# =======================================

print("Loading hallucination detector V2...")

detector = joblib.load(
    "hallucination_model_v2.pkl"
)

encoder = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Hallucination detector V2 loaded!")


# =======================================
# Cosine similarity
# =======================================

def cosine_similarity(a, b):

    return (a * b).sum() / (
        ((a * a).sum() ** 0.5) *
        ((b * b).sum() ** 0.5)
    )


# =======================================
# XGBoost V2 verification
# =======================================

def detect_hallucination(
    knowledge,
    question,
    answer
):

    # Create embeddings

    knowledge_embedding = encoder.encode(
        [knowledge]
    )[0]

    question_embedding = encoder.encode(
        [question]
    )[0]

    answer_embedding = encoder.encode(
        [answer]
    )[0]


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

    knowledge_words = set(
        knowledge.lower().split()
    )

    answer_words = set(
        answer.lower().split()
    )

    if answer_words:

        word_overlap = (
            len(
                knowledge_words.intersection(
                    answer_words
                )
            )
            /
            len(answer_words)
        )

    else:

        word_overlap = 0


    # Feature vector

    features = [[
        knowledge_answer_similarity,
        question_answer_similarity,
        knowledge_question_similarity,
        word_overlap
    ]]


    # Prediction

    prediction = detector.predict(
        features
    )[0]

    probability = detector.predict_proba(
        features
    )[0]


    if prediction == 1:

        return (
            False,
            probability[1] * 100
        )

    else:

        return (
            True,
            probability[0] * 100
        )


# =======================================
# Complete pipeline
# =======================================

def run_pipeline(question):

    print(
        "\n" + "=" * 70
    )

    print(
        "🔎 SEARCHING KNOWLEDGE SOURCES..."
    )

    print(
        "=" * 70
    )


    # ===================================
    # Retrieval
    # ===================================

    results = retrieve(
        question,
        top_k=3
    )


    if not results:

        return {
            "status": "no_data",
            "answer": (
                "No reliable data found."
            )
        }


    print(
        "\n📚 FOUND RELEVANT EVIDENCE"
    )


    contexts = []


    # ===================================
    # Show retrieved evidence
    # ===================================

    for i, result in enumerate(
        results,
        1
    ):

        print(
            f"\nSource {i}: "
            f"{result['title']}"
        )

        print(
            f"Similarity: "
            f"{result['similarity']:.4f}"
        )

        print(
            f"Hybrid Score: "
            f"{result.get('score', 0):.4f}"
        )

        print(
            f"SQuAD Question: "
            f"{result['question']}"
        )

        print(
            f"SQuAD Answer: "
            f"{result['answer']}"
        )

        print(
            "\nEvidence:"
        )

        print(
            result["context"]
        )

        print(
            "-" * 70
        )


        contexts.append(
            result["context"]
        )


    # ===================================
    # Generate answer
    # ===================================

    print(
        "\n" + "=" * 70
    )

    print(
        "🤖 GENERATING ANSWER..."
    )

    print(
        "=" * 70
    )


    answer = generate_answer(
        question,
        contexts
    )


    print(
        "\nGenerated Answer:"
    )

    print(answer)


    # ===================================
    # NLI Verification
    # ===================================

    print(
        "\n" + "=" * 70
    )

    print(
        "🛡️ NLI VERIFICATION..."
    )

    print(
        "=" * 70
    )


    # Use the verifier module

    nli_result = verify_answer(
        answer,
        contexts
    )


    contradiction = (
        nli_result["contradiction"]
    )

    entailment = (
        nli_result["entailment"]
    )

    neutral = (
        nli_result["neutral"]
    )


    print(
        "\nNLI Best Evidence Scores:"
    )

    print(
        f"Contradiction: "
        f"{contradiction:.2f}%"
    )

    print(
        f"Entailment:    "
        f"{entailment:.2f}%"
    )

    print(
        f"Neutral:       "
        f"{neutral:.2f}%"
    )


    # ===================================
    # XGBoost Verification
    # ===================================

    print(
        "\n" + "=" * 70
    )

    print(
        "📊 XGBOOST V2 VERIFICATION..."
    )

    print(
        "=" * 70
    )


    knowledge = "\n\n".join(
        contexts
    )


    xgb_verified, xgb_confidence = (
        detect_hallucination(
            knowledge,
            question,
            answer
        )
    )


    if xgb_verified:

        print(
            "\n✅ XGBoost: "
            "NOT HALLUCINATED"
        )

    else:

        print(
            "\n❌ XGBoost: "
            "HALLUCINATED"
        )


    print(
        f"XGBoost confidence: "
        f"{xgb_confidence:.2f}%"
    )


    # ===================================
    # Final verification
    # ===================================

    print(
        "\n" + "=" * 70
    )

    print(
        "⚖️ FINAL VERIFICATION"
    )

    print(
        "=" * 70
    )


    print(
        f"NLI confidence: "
        f"{max(entailment, neutral, contradiction):.2f}%"
    )

    print(
        f"XGBoost confidence: "
        f"{xgb_confidence:.2f}%"
    )


    # ===================================
    # Current decision
    # ===================================

    if entailment >= 50:

        verified = True

    else:

        verified = False


    if verified:

        print(
            "\n✅ ANSWER VERIFIED"
        )

        return {

            "status": "verified",

            "answer": answer,

            "confidence": entailment,

            "xgb_confidence": xgb_confidence,

            "sources": results

        }

    else:

        print(
            "\n❌ ANSWER NOT SUPPORTED"
        )

        return {

            "status": "unsupported",

            "answer": answer,

            "confidence": neutral,

            "xgb_confidence": xgb_confidence,

            "sources": results

        }


# =======================================
# Test
# =======================================

if __name__ == "__main__":

    question = input(
        "\nEnter your question: "
    )


    result = run_pipeline(
        question
    )


    print(
        "\n" + "=" * 70
    )

    print(
        "FINAL RESULT"
    )

    print(
        "=" * 70
    )


    print(
        "\nStatus:",
        result["status"]
    )

    print(
        "Answer:",
        result["answer"]
    )


    if "confidence" in result:

        print(
            f"NLI confidence: "
            f"{result['confidence']:.2f}%"
        )

    if "xgb_confidence" in result:

        print(
            f"XGBoost confidence: "
            f"{result['xgb_confidence']:.2f}%"
        )