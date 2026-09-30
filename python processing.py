import pandas as pd

# Load dataset
df = pd.read_csv("dataset.csv")

print("Original Shape:", df.shape)

# Convert labels
df["hallucination"] = df["hallucination"].map({
    "yes": 1,
    "no": 0
})

# Remove missing values
df = df.dropna()

# Remove duplicate rows
df = df.drop_duplicates()

# Create one input column
df["text"] = (
    "Knowledge: " + df["knowledge"] +
    " Question: " + df["question"] +
    " Answer: " + df["answer"]
)

# Keep only required columns
df = df[["text", "hallucination"]]

# Save cleaned dataset
df.to_csv("clean_dataset.csv", index=False)

print("Clean Dataset Shape:", df.shape)
print(df.head())

print("\nDataset cleaned successfully!")