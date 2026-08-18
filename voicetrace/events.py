from dataclasses import dataclass, field
from time import monotonic_ns
from typing import Any


@dataclass
class VoiceEvent:
    session_id: str
    event_type: str
    timestamp_ns: int = field(default_factory=monotonic_ns)
    turn_id: str | None = None
    call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)



    