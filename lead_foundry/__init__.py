"""lead-foundry: normalize, dedupe, score, export lead lists."""

from .models import Lead, ScoredLead
from .pipeline import Pipeline

__version__ = "0.1.0"
__all__ = ["Lead", "ScoredLead", "Pipeline"]
