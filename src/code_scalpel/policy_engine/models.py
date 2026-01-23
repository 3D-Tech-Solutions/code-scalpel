from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class HumanResponse:
    """Represents a human's response to an override challenge."""

    code: str
    justification: str
    human_id: str
    timestamp: datetime = field(default_factory=datetime.now)
