import pandas as pd
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parent
SOURCE_FILE = DATASET_DIR / "user-ct-test-collection-02.txt"
OUTPUT_FILE = DATASET_DIR / "query_counts.csv"

df = pd.read_csv(
    SOURCE_FILE,
    sep="\t",
    names=[
        "AnonID",
        "Query",
        "QueryTime",
        "ItemRank",
        "ClickURL"
    ],
    low_memory=False
)

query_counts = (
    df["Query"]
    .dropna()
    .astype(str)
    .str.strip()
    .value_counts()
    .reset_index()
)

query_counts.columns = ["query", "count"]

query_counts = query_counts[
    query_counts["query"].str.len() > 1
]

query_counts = query_counts[
    query_counts["query"] != "-"
]

query_counts = query_counts[
    query_counts["count"] >= 5
]

query_counts.to_csv(
    OUTPUT_FILE,
    index=False
)

print(query_counts.head(20))
print(f"Unique queries: {len(query_counts)}")
