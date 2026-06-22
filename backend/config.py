from dataclasses import dataclass

@dataclass
class AppConfig:
    top_k: int = 10
    query_shard_count: int = 3
    cache_shard_count: int = 3
    virtual_nodes: int = 100
    update_threshold: float = 100.0
    decay_factor: float = 0.99

@dataclass
class QueryInfo:
    total_count: int = 0
    recent_score: float = 0.0
    last_published_score: float = 0.0
    last_updated_timestamp: int = 0

@dataclass
class Suggestion:
    query: str
    score: float

def trim(value: str) -> str:
    return value.strip()

def normalize_query(value: str) -> str:
    return trim(value).lower()

def generate_prefixes(query: str) -> list[str]:
    return [query[:i] for i in range(1, len(query) + 1)]

def format_count(value: int) -> str:
    return f"{value:,}"
