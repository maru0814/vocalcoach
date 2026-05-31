"""
シンプルなインメモリ・レート制限（単一コンテナ前提）。
CPU負荷の高い音声解析の悪用を防ぐ。
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, max_calls: int, window_sec: int) -> bool:
    """key に対して window_sec 秒で max_calls まで許可。超過なら False。"""
    now = time.time()
    with _lock:
        dq = _hits[key]
        while dq and now - dq[0] > window_sec:
            dq.popleft()
        if len(dq) >= max_calls:
            return False
        dq.append(now)
        return True
