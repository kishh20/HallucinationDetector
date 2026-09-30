import json
import os
import re
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# =======================================
# Configuration
# =======================================

DATA_FILE = "squad_train.json"
EMBEDDINGS_FILE = "squad_question_embeddings.npy"


# =======================================
# Load SQuAD database
# =======================================

print("Loading SQuAD database...")

with open(DATA_FILE, "r", encoding="utf-8") as f:

    data = [
        json.loads(line)
        for line in f
    ]

print(f"Loaded {len(data)} records.")


# =======================================
# Extract data
# =======================================

questions = [
    item["question"]
    for item in data
]

contexts = [
    item["context"]
    for item in data
]

titles = [
    item["title"]
    for item in data
]

answers = [
    item["answers"]["text"]
    for item in data
]


# =======================================
# Load embedding model
# =======================================

print("Loading embedding model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# =======================================
# Load / create question embeddings
# =======================================

if os.path.exists(EMBEDDINGS_FILE):

    print("Loading saved question embeddings...")

    question_embeddings = np.load(
        EMBEDDINGS_FILE
    )

else:

    print("Creating question embeddings...")
    print("This will take a few minutes...")

    question_embeddings = model.encode(
        questions,
        show_progress_bar=True,
        batch_size=32
    )

    np.save(
        EMBEDDINGS_FILE,
        question_embeddings
    )

    print("Question embeddings saved!")


print("Retriever ready!")


# =======================================
# Text normalization
# =======================================

def normalize_text(text):

    text = text.lower()

    # Keep only words
    words = re.findall(
        r"\b[a-z0-9]+\b",
        text
    )

    return set(words)


# =======================================
# Keyword overlap
# =======================================

def keyword_overlap(query, candidate):

    query_words = normalize_text(query)
    candidate_words = normalize_text(candidate)

    if not query_words:
        return 0.0

    common_words = (
        query_words.intersection(
            candidate_words
        )
    )

    return len(common_words) / len(query_words)


# =======================================
# Retrieval function
# =======================================

def retrieve(question, top_k=3):

    # -----------------------------------
    # Semantic similarity
    # -----------------------------------

    question_embedding = model.encode(
        [question]
    )

    similarities = cosine_similarity(
        question_embedding,
        question_embeddings
    )[0]


    # -----------------------------------
    # Calculate hybrid scores
    # -----------------------------------

    scores = []

    for index, semantic_score in enumerate(
        similarities
    ):

        lexical_score = keyword_overlap(
            question,
            questions[index]
        )

        # Hybrid score
        #
        # Semantic similarity is still
        # the main signal.
        #
        # Keyword overlap helps when
        # important words match exactly.

        hybrid_score = (
            0.75 * semantic_score
            +
            0.25 * lexical_score
        )

        scores.append(
            hybrid_score
        )


    scores = np.array(scores)


    # ===================================
    # Sort candidates
    # ===================================

    sorted_indices = np.argsort(
        scores
    )[::-1]


    # ===================================
    # Select diverse results
    # ===================================

    results = []

    used_contexts = set()

    for index in sorted_indices:

        context = contexts[index]

        # Avoid returning the exact same
        # context multiple times.

        if context in used_contexts:
            continue

        used_contexts.add(context)

        results.append({

            "question": questions[index],

            "context": context,

            "similarity": float(
                similarities[index]
            ),

            "score": float(
                scores[index]
            ),

            "title": titles[index],

            "answer": answers[index]

        })

        if len(results) >= top_k:
            break


    return results