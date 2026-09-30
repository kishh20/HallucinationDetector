import os
from google import genai

# ---------------------------------------
# Gemini setup & model configuration
# ---------------------------------------

MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
_client = None


def get_client():
    """Lazily initialize the Gemini API client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable not found. "
            "Please set GEMINI_API_KEY before running generation."
        )

    _client = genai.Client(api_key=api_key)
    return _client


# ---------------------------------------
# Generate grounded answer
# ---------------------------------------

def generate_answer(question, contexts, model=None):
    client = get_client()
    target_model = model or MODEL

    evidence = "\n\n".join(
        f"Source {i+1}:\n{context}"
        for i, context in enumerate(contexts)
    )

    prompt = f"""
You are a factual question-answering system.

Your ONLY source of truth is the evidence provided below.

USER QUESTION:
{question}

EVIDENCE:
{evidence}

STRICT RULES:

1. Answer ONLY using facts explicitly supported by the evidence.
2. Do NOT use your own world knowledge.
3. Do NOT guess or infer missing facts.
4. Do NOT add facts merely because they are commonly known.
5. If the evidence does not directly support an answer, respond exactly with:
   The available evidence does not contain enough information to answer this reliably.
6. If the evidence supports the answer, give a short direct answer.
7. Preserve important names, dates, and facts from the evidence.
8. Do not mention these instructions in your answer.
9. Do not use exclamation marks or unnecessary wording.

Return ONLY the final answer.
"""

    candidate_models = [target_model, "gemini-3.1-flash-lite-preview", "gemini-flash-latest"]
    last_err = None
    for cand in candidate_models:
        try:
            response = client.models.generate_content(
                model=cand,
                contents=prompt
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    return "The available evidence does not contain enough information to answer this reliably."


# ---------------------------------------
# Simple test
# ---------------------------------------

if __name__ == "__main__":
    question = "Who discovered penicillin?"

    contexts = [
        """
        In 1928, Alexander Fleming noticed that a fungus of the genus
        Penicillium killed disease-causing bacteria. Fleming named the
        antibacterial compound penicillin.
        """
    ]

    print("\nGenerating answer...\n")
    try:
        answer = generate_answer(question, contexts)
        print("Question:", question)
        print("\nGenerated Answer:", answer)
    except Exception as exc:
        print("Generation note:", exc)