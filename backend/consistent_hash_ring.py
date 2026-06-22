import hashlib
import bisect

class ConsistentHashRing:
    def __init__(self, virtual_nodes: int, node_prefix: str):
        self.virtual_nodes = virtual_nodes
        self.node_prefix = node_prefix
        self.ring = {}  # hash_val -> nodeId
        self.sorted_hashes = []

    def _hash(self, key: str) -> int:
        # Use stable MD5 hash converted to an integer
        return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16)

    def add_node(self, node_id: int):
        for replica in range(self.virtual_nodes):
            virtual_node_key = f"{self.node_prefix}-node-{node_id}-vn-{replica}"
            h = self._hash(virtual_node_key)
            self.ring[h] = node_id
        self.sorted_hashes = sorted(self.ring.keys())

    def remove_node(self, node_id: int):
        # Remove all hashes mapped to this node_id
        self.ring = {h: nid for h, nid in self.ring.items() if nid != node_id}
        self.sorted_hashes = sorted(self.ring.keys())

    def get_node(self, key: str) -> int:
        if not self.ring:
            raise RuntimeError(f"{self.node_prefix} hash ring has no nodes")
        
        hashed_key = self._hash(key)
        index = bisect.bisect_left(self.sorted_hashes, hashed_key)
        if index == len(self.sorted_hashes):
            index = 0
            
        return self.ring[self.sorted_hashes[index]]
