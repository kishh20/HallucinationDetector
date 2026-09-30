import joblib
from sentence_transformers import SentenceTransformer

from retrieve import retrieve
from generator import generate_answer


# ---------------------------------------
# Load hallucination detector
# ---------------------------------------

print("Loading hallucination detector...")

detector = joblib.load("hallucination_model.pkl")
encoder = SentenceTransformer("all-MiniLM-L6-v2")

print("Hallucination detector loaded!")


# ---------------------------------------
# Detect hallucination
# ---------------------------------------

def detect_hallucination(knowledge, question, answer):

    text = (
        "Knowledge: " + knowledge +
        " Question: " + question +
        " Answer: " + answer
    )

    embedding = encoder.encode([text])

    prediction = detector.predict(embedding)[0]
    probability = detector.predict_proba(embedding)[0]

    if prediction == 1:
        confidence = probability[1] * 100
        return False, confidence

    confidence = probability[0] * 100
    return True, confidence


# ---------------------------------------
# Complete pipeline
# ---------------------------------------

def run_pipeline(question):

    print("\n" + "=" * 70)
    print("🔎 SEARCHING KNOWLEDGE SOURCES...")
    print("=" * 70)

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

        contexts.append(result["context"])

    # -----------------------------------
    # Generate answer
    # -----------------------------------

    print("\n" + "=" * 70)
    print("🤖 GENERATING ANSWER...")
    print("=" * 70)

    answer = generate_answer(
        question,
        contexts
    )

    print("\nGenerated Answer:")
    print(answer)

    # -----------------------------------
    # Hallucination verification
    # -----------------------------------

    print("\n" + "=" * 70)
    print("🛡️ VERIFYING ANSWER...")
    print("=" * 70)

    knowledge = "\n\n".join(contexts)

    verified, confidence = detect_hallucination(
        knowledge,
        question,
        answer
    )

    # -----------------------------------
    # Result
    # -----------------------------------

    if verified:

        print("\n✅ ANSWER VERIFIED")
        print(f"Detector confidence: {confidence:.2f}%")

        return {
            "status": "verified",
            "answer": answer,
            "confidence": confidence,
            "sources": results
        }

    else:

        print("\n❌ ANSWER NOT SUPPORTED")
        print(f"Detector confidence: {confidence:.2f}%")

        return {
            "status": "unsupported",
            "answer": answer,
            "confidence": confidence,
            "sources": results
        }


# ---------------------------------------
# Test
# ---------------------------------------

if __name__ == "__main__":

    question = input("\nEnter your question: ")

    result = run_pipeline(question)

    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print("\nStatus:", result["status"])
    print("Answer:", result["answer"])

    if "confidence" in result:
        print(
            f"Detector confidence: "
            f"{result['confidence']:.2f}%"
        )