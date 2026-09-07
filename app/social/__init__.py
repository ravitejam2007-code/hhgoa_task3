"""
app.social — social & web candidate validation and scoring.
"""

from app.social.validator import (
    RECOGNIZED_SOCIAL_DOMAINS,
    SelectedEvidence,
    SocialValidator,
    extract_registered_domain,
    is_recognized_social,
)

__all__ = [
    "RECOGNIZED_SOCIAL_DOMAINS",
    "SelectedEvidence",
    "SocialValidator",
    "extract_registered_domain",
    "is_recognized_social",
]
