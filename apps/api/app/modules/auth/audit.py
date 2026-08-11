"""Structured auth security audit logging.

Sử dụng structlog JSON — 1 event/line.
Trong Phase 2 sẽ ghi vào `audit_logs` table.
"""

from __future__ import annotations

from structlog import get_logger

_audit = get_logger("auth.audit")


def audit_log(
    event: str,
    *,
    user_id: str | None = None,
    family_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    email_hash: str | None = None,
    reason: str | None = None,
) -> None:
    """Ghi security event vào audit log (structured JSON).

    KHÔNG log: password, JWT token, email thật, PII.
    """
    _audit.info(
        event,
        user_id=user_id,
        family_id=str(family_id) if family_id else None,
        ip=ip,
        user_agent=user_agent,
        email_hash=email_hash,
        reason=reason,
    )
