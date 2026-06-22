import time
import math
from .config import QueryInfo

class RankingEngine:
    def current_timestamp(self) -> int:
        return int(time.time())

    def compute_score(self, info: QueryInfo) -> float:
        return 0.8 * info.recent_score + 0.2 * float(info.total_count)

    def apply_search_update(self, info: QueryInfo, decay_factor: float) -> float:
        now = self.current_timestamp()
        
        if info.last_updated_timestamp == 0 or now < info.last_updated_timestamp:
            elapsed_seconds = 0
        else:
            elapsed_seconds = now - info.last_updated_timestamp
            
        # FIX: Use fractional hours to prevent frequent searches from resetting decay intervals
        elapsed_hours = elapsed_seconds / 3600.0
        
        info.recent_score *= math.pow(decay_factor, elapsed_hours)
        info.recent_score += 1.0
        info.total_count += 1
        info.last_updated_timestamp = now
        
        return self.compute_score(info)
