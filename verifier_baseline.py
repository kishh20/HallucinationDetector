import numpy as np
from sentence_transformers import CrossEncoder


# ---------------------------------------
# Load NLI model
# ---------------------------------------

print("Loading NLI verifier...")

verifier = CrossEncoder(
    "cross-encoder/nli-deberta-v3-base"
)

print("NLI verifier loaded!")


# ---------------------------------------
# Split knowledge into chunks
# ---------------------------------------

def split_into_chunks(text, max_words=100):

    words = text.split()

    chunks = []

    for i in range(0, len(words), max_words):

        chunk = " ".join(
            words[i:i + max_words]
        )

        chunks.append(chunk)

    return chunks


# ---------------------------------------
# Verify answer
# ---------------------------------------

def verify_answer(knowledge, answer):

    # Split retrieved knowledge
    chunks = split_into_chunks(
        knowledge,
        max_words=100
    )

    if not chunks:

        return False, 0.0


    # Create premise-hypothesis pairs
    pairs = []

    for chunk in chunks:

        pairs.append(
            (chunk, answer)
        )


    # Run NLI on every chunk
    scores = verifier.predict(
        pairs
    )


    best_entailment = 0.0
    best_contradiction = 0.0
    best_neutral = 0.0


    # -----------------------------------
    # Find strongest supporting evidence
    # -----------------------------------

    for score in scores:

        # Convert logits to probabilities
        exp_score = np.exp(
            score - np.max(score)
        )

        probabilities = (
            exp_score / exp_score.sum()
        )

        contradiction = probabilities[0]
        entailment = probabilities[1]
        neutral = probabilities[2]


        # Keep the chunk with highest entailment
        if entailment > best_entailment:

            best_entailment = entailment
            best_contradiction = contradiction
            best_neutral = neutral


    # -----------------------------------
    # Display strongest evidence score
    # -----------------------------------

    print("\nNLI Best Evidence Scores:")

    print(
        f"Contradiction: "
        f"{best_contradiction * 100:.2f}%"
    )

    print(
        f"Entailment:    "
        f"{best_entailment * 100:.2f}%"
    )

    print(
        f"Neutral:       "
        f"{best_neutral * 100:.2f}%"
    )


    # -----------------------------------
    # Final decision
    # -----------------------------------

    # Require entailment to be the strongest
    # and reasonably confident.

    if (
        best_entailment > best_contradiction
        and best_entailment > best_neutral
        and best_entailment >= 0.50
    ):

        return (
            True,
            best_entailment * 100
        )


    return (
        False,
        max(
            best_contradiction,
            best_neutral
        ) * 100
    )