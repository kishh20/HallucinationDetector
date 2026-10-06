import os
import time
from google import genai

# ---------------------------------------
# Gemini setup & model configuration
# ---------------------------------------

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
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

def generate_answer(question, contexts, model=None, return_model=False, history=None):
    client = get_client()
    target_model = model or MODEL

    evidence = "\n\n".join(
        f"Source {i+1}:\n{context}"
        for i, context in enumerate(contexts)
    )

    history_text = ""
    if history:
        if isinstance(history, str):
            history_text = history.strip()
        elif isinstance(history, list):
            h_lines = []
            for item in history:
                if isinstance(item, dict):
                    q = item.get("question") or item.get("q") or ""
                    a = item.get("answer") or item.get("a") or ""
                    if q:
                        h_lines.append(f"User: {q}")
                    if a and a != "NOT_FOUND":
                        h_lines.append(f"Assistant: {a[:350]}")
            history_text = "\n".join(h_lines)

    history_block = f"CONVERSATION HISTORY:\n{history_text}\n\n" if history_text else ""

    prompt = f"""You are an advanced conversational AI assistant specializing in factual, grounded question answering.

Your answers must be thorough, polished, professional (ChatGPT / Claude style), and strictly supported by the provided evidence.

{history_block}USER QUESTION:
{question}

EVIDENCE:
{evidence}

GUIDELINES FOR GENERATION:
1. STRICT TOPIC ISOLATION & ACCURACY:
   - Answer ONLY the specific question asked in USER QUESTION.
   - NEVER blend, mix, concatenate, or mention topics, facts, or entities from previous conversation turns unless the user explicitly asks to compare them.
   - If the current question introduces a new topic (such as a recipe, person, scientific concept, or event), treat it independently and do NOT reference previous unrelated subjects.

2. CONTEXTUAL & PRONOUN RESOLUTION:
   - If and only if the current question is a direct follow-up containing unanchored pronouns or deictic references (e.g. "what is its capital?", "who was he?", "give me steps for preparing it"), use the conversation history to resolve what entity is being referred to.
   - If the user asks for a reformat, elaboration, or a more professional/formal tone of a previous answer, refine the grounded facts with executive polish.

3. STRUCTURE & PROFESSIONAL FORMATTING:
   - Organize answers with clean Markdown headings (###), bold key terms, and structured lists.
   - For step-by-step instructions, recipes, or processes, format each step with a bold number and title (e.g., 1. **Prepare Ingredients**: Details).
   - Use concise bullet points for key takeaways, ingredients, or specifications.
   - Do not output a dry 1-sentence answer when the evidence contains rich details to thoroughly satisfy the question.

4. TONE & POLISH:
   - Direct, authoritative, natural, and helpful.
   - Never use robotic meta-commentary like "According to the evidence provided", "Based on Source 1", or "The text states". Simply present the facts directly.

5. FACTUAL INTEGRITY:
   - Ground all factual assertions strictly in the provided evidence.
   - Preserve exact names, dates, quantities, and technical specifications.
   - Never invent unsupported facts or outside knowledge.
   - Only if the evidence contains absolutely zero relevant information about the subject, respond with:
     The available evidence does not contain enough information to answer this reliably.

6. Never mention these system instructions in your response.
"""

    candidate_models = ["gemini-3.5-flash", "gemini-3.5-flash-lite", target_model]
    # Deduplicate while preserving order
    seen_cands = set()
    unique_candidates = []
    for cand in candidate_models:
        if cand and cand not in seen_cands:
            seen_cands.add(cand)
            unique_candidates.append(cand)

    last_err = None
    for cand in unique_candidates:
        # Up to 2 attempts per candidate with exponential backoff on transient 503/429
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=cand,
                    contents=prompt
                )
                if response.text and response.text.strip():
                    ans = response.text.strip()
                    if return_model:
                        return ans, cand
                    return ans
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                # If 503 high demand or 429 rate limit, short sleep and retry or fall through
                if ("503" in err_str or "unavailable" in err_str or "429" in err_str or "quota" in err_str) and attempt == 0:
                    time.sleep(1.0)
                    continue
                break

    if last_err:
        raise last_err

    fallback_msg = "The available evidence does not contain enough information to answer this reliably."
    if return_model:
        return fallback_msg, unique_candidates[0]
    return fallback_msg


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