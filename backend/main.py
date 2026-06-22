import os
import sys
import csv
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import AppConfig, QueryInfo, normalize_query
from .consistent_hash_ring import ConsistentHashRing
from .ranking_engine import RankingEngine
from .query_store import QueryStore
from .cache_store import CacheStore

app = FastAPI(title="Distributed Typeahead API")

# Enable CORS for local testing if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances initialized at startup
config = AppConfig()
query_hash_ring = ConsistentHashRing(config.virtual_nodes, "query")
cache_hash_ring = ConsistentHashRing(config.virtual_nodes, "cache")
query_store = QueryStore(config.query_shard_count, query_hash_ring)
cache_store = CacheStore(config.cache_shard_count, cache_hash_ring)
ranking_engine = RankingEngine()

def resolve_dataset_path() -> str:
    candidates = []
    
    # 1. Configured path from env
    env_path = os.getenv("TYPEAHEAD_DATASET_PATH")
    if env_path:
        candidates.append(Path(env_path))
        
    # 2. Path relative to main.py
    script_dir = Path(__file__).resolve().parent
    candidates.append(script_dir / "../dataset/query_counts.csv")
    candidates.append(script_dir / "../../dataset/query_counts.csv")
    
    # 3. Path relative to current working directory
    candidates.append(Path("dataset/query_counts.csv"))
    candidates.append(Path("../dataset/query_counts.csv"))
    candidates.append(Path("../../dataset/query_counts.csv"))
    
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
            
    msg = "failed to locate dataset/query_counts.csv; checked:\n"
    for candidate in candidates:
        msg += f"  - {candidate}\n"
    msg += "Set TYPEAHEAD_DATASET_PATH to override the dataset location."
    raise RuntimeError(msg)

def load_dataset(path: str):
    loaded_rows = 0
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            next(reader, None)  # Skip header
        except StopIteration:
            return
            
        for row in reader:
            if not row or len(row) < 2:
                continue
                
            query_raw = row[0]
            count_raw = row[1]
            
            query = normalize_query(query_raw)
            if not query:
                continue
                
            try:
                count = int(count_raw)
            except ValueError:
                continue
                
            info = QueryInfo(
                total_count=count,
                recent_score=float(count),
                last_updated_timestamp=ranking_engine.current_timestamp()
            )
            info.last_published_score = ranking_engine.compute_score(info)
            
            query_store.put(query, info)
            cache_store.update_query(query, info.last_published_score, config.top_k)
            loaded_rows += 1
            
    print(f"Loaded {loaded_rows} queries into the sharded query store.")
    print("Prepopulated cache prefixes before accepting traffic.")

@app.post("/search")
async def search_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"status": "error", "message": "invalid JSON body"})
        
    if not isinstance(body, dict) or "query" not in body or not isinstance(body["query"], str):
        return JSONResponse(status_code=400, content={"status": "error", "message": "request body must contain a string field named query"})
        
    query = normalize_query(body["query"])
    if not query:
        return JSONResponse(status_code=400, content={"status": "error", "message": "query must not be empty"})
        
    update_result = query_store.record_search(query, ranking_engine, config)
    
    if update_result.should_publish_to_cache:
        cache_store.update_query(query, update_result.score, config.top_k)
        query_store.mark_published(query, update_result.score)
        
    return {"status": "success"}

@app.get("/suggest")
async def suggest_endpoint(q: str = ""):
    prefix = normalize_query(q)
    
    suggestions = []
    if prefix:
        suggestions = [s.query for s in cache_store.get_suggestions(prefix)]
        
    return {
        "prefix": prefix,
        "suggestions": suggestions
    }

def main():
    try:
        dataset_path = resolve_dataset_path()
        print(f"Loading dataset from {dataset_path}")
        load_dataset(dataset_path)
    except Exception as e:
        print(f"Error loading dataset: {e}", file=sys.stderr)
        sys.exit(1)
        
    run_scaling_demo = os.getenv("TYPEAHEAD_SCALING_DEMO") is not None
    if run_scaling_demo:
        query_store.print_query_shard_distribution()
        cache_store.print_cache_shard_distribution()
        
        query_store.add_shard()
        cache_store.add_shard()
        
        query_store.print_query_shard_distribution()
        cache_store.print_cache_shard_distribution()
        
    print("Typeahead backend listening on http://localhost:18080")
    uvicorn.run(app, host="0.0.0.0", port=18080, log_level="info")

if __name__ == "__main__":
    main()
