import threading
from .config import AppConfig, QueryInfo, format_count
from .consistent_hash_ring import ConsistentHashRing
from .ranking_engine import RankingEngine

class SearchUpdateResult:
    def __init__(self, score: float, should_publish_to_cache: bool):
        self.score = score
        self.should_publish_to_cache = should_publish_to_cache

class QueryStore:
    def __init__(self, shard_count: int, hash_ring: ConsistentHashRing):
        self.hash_ring = hash_ring
        self.shards = {}  # shard_id -> dict of query records {query: QueryInfo}
        self.next_shard_id = 0
        self.topology_mutex = threading.Lock()
        self.shard_mutexes = {}  # shard_id -> Lock
        
        for _ in range(shard_count):
            self._add_shard_no_rebalance()

    def _add_shard_no_rebalance(self):
        shard_id = self.next_shard_id
        self.next_shard_id += 1
        self.shards[shard_id] = {}
        self.shard_mutexes[shard_id] = threading.Lock()
        self.hash_ring.add_node(shard_id)

    def _shard_for(self, query: str) -> int:
        return self.hash_ring.get_node(query)

    def put(self, query: str, info: QueryInfo):
        with self.topology_mutex:
            shard_id = self._shard_for(query)
            with self.shard_mutexes[shard_id]:
                self.shards[shard_id][query] = info

    def record_search(self, query: str, ranking_engine: RankingEngine, config: AppConfig) -> SearchUpdateResult:
        with self.topology_mutex:
            shard_id = self._shard_for(query)
            with self.shard_mutexes[shard_id]:
                records = self.shards[shard_id]
                if query not in records:
                    info = QueryInfo(
                        total_count=0,
                        recent_score=0.0,
                        last_published_score=0.0,
                        last_updated_timestamp=ranking_engine.current_timestamp()
                    )
                    records[query] = info
                else:
                    info = records[query]

                score = ranking_engine.apply_search_update(info, config.decay_factor)
                difference = abs(score - info.last_published_score)
                
                return SearchUpdateResult(
                    score=score,
                    should_publish_to_cache=difference > config.update_threshold
                )

    def mark_published(self, query: str, score: float):
        with self.topology_mutex:
            shard_id = self._shard_for(query)
            with self.shard_mutexes[shard_id]:
                records = self.shards[shard_id]
                if query in records:
                    records[query].last_published_score = score

    def size(self) -> int:
        with self.topology_mutex:
            total = 0
            for shard_id, shard_records in self.shards.items():
                with self.shard_mutexes[shard_id]:
                    total += len(shard_records)
            return total

    def add_shard(self):
        with self.topology_mutex:
            shard_id = self.next_shard_id
            self.next_shard_id += 1
            print(f"\nAdding QueryShard {shard_id}")
            self.shards[shard_id] = {}
            self.shard_mutexes[shard_id] = threading.Lock()
            self.hash_ring.add_node(shard_id)
            self._rebalance_locked()

    def remove_shard(self, shard_id: int):
        with self.topology_mutex:
            if shard_id not in self.shards:
                print(f"\nQueryShard {shard_id} does not exist; no rebalance needed.")
                return
            
            if len(self.shards) == 1:
                raise RuntimeError("cannot remove the last query shard")
                
            print(f"\nRemoving QueryShard {shard_id}")
            self.hash_ring.remove_node(shard_id)
            self._rebalance_locked()
            del self.shards[shard_id]
            del self.shard_mutexes[shard_id]

    def rebalance(self):
        with self.topology_mutex:
            self._rebalance_locked()

    def _rebalance_locked(self):
        migrations = []
        scanned = 0
        
        # Determine migrations by scanning all shards
        for current_shard_id, shard_records in self.shards.items():
            with self.shard_mutexes[current_shard_id]:
                # Collect keys that need to move
                keys_to_remove = []
                for query, info in shard_records.items():
                    scanned += 1
                    target_shard_id = self.hash_ring.get_node(query)
                    if target_shard_id != current_shard_id:
                        migrations.append((current_shard_id, target_shard_id, query, info))
                        keys_to_remove.append(query)
                
                # Remove migrated keys from source shard
                for key in keys_to_remove:
                    del shard_records[key]
                    
        # Apply migrations to target shards
        for _, target_shard_id, query, info in migrations:
            with self.shard_mutexes[target_shard_id]:
                self.shards[target_shard_id][query] = info

        print(f"Queries scanned: {format_count(scanned)}")
        print(f"Queries migrated: {format_count(len(migrations))}")
        print("Query rebalancing complete")

    def print_query_shard_distribution(self):
        with self.topology_mutex:
            print("\nQuery Shard Distribution\n")
            for shard_id in sorted(self.shards.keys()):
                shard_records = self.shards[shard_id]
                with self.shard_mutexes[shard_id]:
                    count = len(shard_records)
                print(f"Shard {shard_id} : {format_count(count)} queries")
