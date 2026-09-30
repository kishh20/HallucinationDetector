from datasets import load_dataset

print("Downloading SQuAD...")

dataset = load_dataset("rajpurkar/squad")

print("\nDataset downloaded successfully!")

print("\nTrain:")
print(dataset["train"])

print("\nValidation:")
print(dataset["validation"])

# Save locally
dataset["train"].to_json("squad_train.json")
dataset["validation"].to_json("squad_validation.json")

print("\nSaved:")
print("squad_train.json")
print("squad_validation.json")