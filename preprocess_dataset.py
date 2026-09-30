import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset.csv")
CLEAN_DATASET_PATH = os.path.join(BASE_DIR, "clean_dataset.csv")

print("Loading raw dataset from:", DATASET_PATH)
df = pd.read_csv(DATASET_PATH)

print("Original Shape:", df.shape)

# Convert labels ('yes' -> 1, 'no' -> 0)
df["hallucination"] = df["hallucination"].map({
    "yes": 1,
    "no": 0
})

# Remove missing values
df = df.dropna()

# Remove duplicate rows
df = df.drop_duplicates()

# Create combined text column for V1 model compatibility
df["text"] = (
    "Knowledge: " + df["knowledge"] +
    " Question: " + df["question"] +
    " Answer: " + df["answer"]
)

# Save cleaned dataset
df_clean = df[["text", "hallucination"]]
df_clean.to_csv(CLEAN_DATASET_PATH, index=False)

print("Clean Dataset Shape:", df_clean.shape)
print("\nFirst 3 rows:\n", df_clean.head(3))
print(f"\nDataset cleaned successfully and saved to {CLEAN_DATASET_PATH}!")
