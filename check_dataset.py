import pandas as pd

# Read the parquet file
df = pd.read_parquet("samples-00000-of-00001.parquet")

print("Dataset Shape:")
print(df.shape)

print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 Rows:")
print(df.head())

# Save as CSV (optional)
df.to_csv("dataset.csv", index=False)
print("\nCSV file saved as dataset.csv")