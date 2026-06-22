import threading
from .config import AppConfig, Suggestion, generate_prefixes, format_count
from .consistent_hash_ring import ConsistentHashRing

class CacheStore:
    def __init__(self, shard_count: int, hash_ring: ConsistentHashRing):
        self.hash_ring = hash_ring
        self.shards = {}  # shard_id -> dict of prefix suggestions {prefix: list[Suggestion]}
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

    def _shard_for(self, prefix: str) -> int:
        return self.hash_ring.get_node(prefix)

    def update_query(self, query: str, score: float, top_k: int):
        with self.topology_mutex:
            for prefix in generate_prefixes(query):
                self._update_prefix_locked(prefix, Suggestion(query=query, score=score), top_k)

    def _update_prefix_locked(self, prefix: str, suggestion: Suggestion, top_k: int):
        shard_id = self._shard_for(prefix)
        with self.shard_mutexes[shard_id]:
            prefixes = self.shards[shard_id]
            if prefix not in prefixes:
                prefixes[prefix] = []
                
            suggestions = prefixes[prefix]
            
            # Find if suggestion.query already exists
            existing_idx = -1
            for idx, curr in enumerate(suggestions):
                if curr.query == suggestion.query:
                    existing_idx = idx
                    break
                    
            if existing_idx != -1:
                suggestions[existing_idx].score = suggestion.score
            else:
                suggestions.append(suggestion)
                
            # Sort: primary descending by score, secondary ascending alphabetically by query
            suggestions.sort(key=lambda s: (-s.score, s.query))
            
            # Keep topK
            if len(suggestions) > top_k:
                del suggestions[top_k:]

    def get_suggestions(self, prefix: str) -> list[Suggestion]:
        with self.topology_mutex:
            shard_id = self._shard_for(prefix)
            with self.shard_mutexes[shard_id]:
                prefixes = self.shards[shard_id]
                if prefix not in prefixes:
                    return []
                # Return a copy of suggestions to avoid thread mutations when iterating/accessing
                return list(prefixes[prefix])

    def add_shard(self):
        with self.topology_mutex:
            shard_id = self.next_shard_id
            self.next_shard_id += 1
            print(f"\nAdding CacheShard {shard_id}")
            self.shards[shard_id] = {}
            self.shard_mutexes[shard_id] = threading.Lock()
            self.hash_ring.add_node(shard_id)
            self._rebalance_locked()

    def remove_shard(self, shard_id: int):
        with self.topology_mutex:
            if shard_id not in self.shards:
                print(f"\nCacheShard {shard_id} does not exist; no rebalance needed.")
                return
                
            if len(self.shards) == 1:
                raise RuntimeError("cannot remove the last cache shard")
                
            print(f"\nRemoving CacheShard {shard_id}")
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
        for current_shard_id, shard_prefixes in self.shards.items():
            with self.shard_mutexes[current_shard_id]:
                # Collect keys that need to move
                keys_to_remove = []
                for prefix, suggestions in shard_prefixes.items():
                    scanned += 1
                    target_shard_id = self.hash_ring.get_node(prefix)
                    if target_shard_id != current_shard_id:
                        migrations.append((current_shard_id, target_shard_id, prefix, suggestions))
                        keys_to_remove.append(prefix)
                        
                # Remove migrated keys from source shard
                for key in keys_to_remove:
                    del shard_prefixes[key]
                    
        # Apply migrations to target shards
        for _, target_shard_id, prefix, suggestions in migrations:
            with self.shard_mutexes[target_shard_id]:
                self.shards[target_shard_id][prefix] = suggestions

        print(f"Prefixes scanned: {format_count(scanned)}")
        print(f"Prefixes migrated: {format_count(len(migrations))}")
        print("Cache rebalancing complete")

    def print_cache_shard_distribution(self):
        with self.topology_mutex:
            print("\nCache Shard Distribution\n")
            for shard_id in sorted(self.shards.keys()):
                shard_prefixes = self.shards[shard_id]
                with self.shard_mutexes[shard_id]:
                    count = len(shard_prefixes)
                print(f"Shard {shard_id} : {format_count(count)} prefixes")
