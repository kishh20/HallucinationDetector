import joblib
from sentence_transformers import SentenceTransformer

from retrieve import retrieve
from generator import generate_answer
from verifier import verify_answer


# ---------------------------------------
# Load hallucination detector V2
# ---------------------------------------

print("Loading hallucination detector V2...")

detector = joblib.load("hallucination_model_v2.pkl")
encoder = SentenceTransformer("all-MiniLM-L6-v2")

print("Hallucination detector V2 loaded!")


# ---------------------------------------
# Complete pipeline
# ---------------------------------------

def run_pipeline(question):

    print("\n" + "=" * 70)
    print("🔎 SEARCHING KNOWLEDGE SOURCES...")
    print("=" * 70)

    results = retrieve(
        question,
        top_k=3
    )

    if not results:

        return {
            "status": "no_data",
            "answer": "No reliable data found."
        }


    # -----------------------------------
    # Display retrieved evidence
    # -----------------------------------

    print("\n📚 FOUND RELEVANT EVIDENCE")

    contexts = []

    for i, result in enumerate(
        results,
        1
    ):

        print(
            f"\nSource {i}: {result['title']}"
        )

        print(
            f"Similarity: "
            f"{result['similarity']:.4f}"
        )

        contexts.append(
            result["context"]
        )


    # -----------------------------------
    # Generate answer
    # -----------------------------------

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


    print("\nGenerated Answer:")
    print(answer)


    # -----------------------------------
    # NLI verification
    # -----------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "🛡️ VERIFYING ANSWER WITH NLI..."
    )

    print(
        "=" * 70
    )


    # Combine retrieved evidence
    knowledge = "\n\n".join(
        contexts
    )


    verified, confidence = verify_answer(
        knowledge,
        answer
    )


    # -----------------------------------
    # Final result
    # -----------------------------------

    if verified:

        print(
            "\n✅ ANSWER VERIFIED"
        )

        print(
            f"NLI confidence: "
            f"{confidence:.2f}%"
        )


        return {
            "status": "verified",
            "answer": answer,
            "confidence": confidence,
            "sources": results
        }


    else:

        print(
            "\n❌ ANSWER NOT SUPPORTED"
        )

        print(
            f"NLI confidence: "
            f"{confidence:.2f}%"
        )


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