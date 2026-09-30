from sentence_transformers import CrossEncoder
import numpy as np
import re


# =======================================
# Load NLI model
# =======================================

print("Loading NLI verifier...")

verifier = CrossEncoder(
    "cross-encoder/nli-deberta-v3-base",
    max_length=512
)

print("NLI verifier loaded!")


# =======================================
# Split context into sentences
# =======================================

def split_into_sentences(text):

    sentences = re.split(
        r'(?<=[.!?])\s+',
        text.strip()
    )

    # Remove very short pieces
    sentences = [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip()) > 20
    ]

    return sentences


# =======================================
# Verify answer against evidence
# =======================================

def verify_answer(answer, contexts):

    if not contexts:

        return {
            "supported": False,
            "entailment": 0.0,
            "contradiction": 0.0,
            "neutral": 100.0
        }


    # -----------------------------------
    # Create small evidence chunks
    # -----------------------------------

    evidence_chunks = []

    for context in contexts:

        sentences = split_into_sentences(
            context
        )

        evidence_chunks.extend(
            sentences
        )


    if not evidence_chunks:

        return {
            "supported": False,
            "entailment": 0.0,
            "contradiction": 0.0,
            "neutral": 100.0
        }


    # -----------------------------------
    # Create NLI pairs
    #
    # premise    = evidence
    # hypothesis = generated answer
    # -----------------------------------

    pairs = [
        (chunk, answer)
        for chunk in evidence_chunks
    ]


    # -----------------------------------
    # Run NLI
    # -----------------------------------

    scores = verifier.predict(
        pairs,
        apply_softmax=True
    )

    scores = np.asarray(
        scores
    )


    # ===================================
    # Find strongest ENTAILMENT evidence
    # ===================================

    best_index = np.argmax(
        scores[:, 1]
    )

    best_scores = scores[
        best_index
    ]


    contradiction = (
        float(best_scores[0]) * 100
    )

    entailment = (
        float(best_scores[1]) * 100
    )

    neutral = (
        float(best_scores[2]) * 100
    )


    # -----------------------------------
    # Print strongest evidence
    # -----------------------------------

    print(
        "\nBest NLI Evidence:"
    )

    print(
        evidence_chunks[best_index]
    )


    # ===================================
    # Determine support
    # ===================================

    supported = (
        entailment >= 50
        and
        entailment > contradiction
        and
        entailment > neutral
    )


    return {

        "supported": supported,

        "entailment": entailment,

        "contradiction": contradiction,

        "neutral": neutral
    }