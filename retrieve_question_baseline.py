import json
import os
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


print(
    f"Loaded {len(data)} records."
)


# =======================================
# Extract questions
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
# Load / create QUESTION embeddings
# =======================================

if os.path.exists(
    EMBEDDINGS_FILE
):

    print(
        "Loading saved question embeddings..."
    )

    question_embeddings = np.load(
        EMBEDDINGS_FILE
    )

else:

    print(
        "Creating question embeddings..."
    )

    print(
        "This will take a few minutes..."
    )

    question_embeddings = model.encode(
        questions,
        show_progress_bar=True,
        batch_size=32
    )

    np.save(
        EMBEDDINGS_FILE,
        question_embeddings
    )

    print(
        "Question embeddings saved!"
    )


print("Retriever ready!")


# =======================================
# Retrieval function
# =======================================

def retrieve(question, top_k=3):

    # -----------------------------------
    # Embed user question
    # -----------------------------------

    question_embedding = model.encode(
        [question]
    )


    # -----------------------------------
    # Compare with SQuAD QUESTIONS
    # -----------------------------------

    similarities = cosine_similarity(
        question_embedding,
        question_embeddings
    )[0]


    # -----------------------------------
    # Get best matches
    # -----------------------------------

    top_indices = np.argsort(
        similarities
    )[-top_k:][::-1]


    results = []


    for index in top_indices:

        results.append({

            "question": questions[index],

            "context": contexts[index],

            "similarity": float(
                similarities[index]
            ),

            "title": titles[index],

            "answer": answers[index]

        })


    return results