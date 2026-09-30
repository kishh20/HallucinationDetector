import os
from google import genai

# ---------------------------------------
# Gemini setup
# ---------------------------------------

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY not found.")

client = genai.Client(api_key=api_key)

MODEL = "gemini-3.6-flash"


# ---------------------------------------
# Generate grounded answer
# ---------------------------------------

def generate_answer(question, contexts):

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

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    return response.text.strip()


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

    answer = generate_answer(
        question,
        contexts
    )

    print("Question:")
    print(question)

    print("\nGenerated Answer:")
    print(answer)