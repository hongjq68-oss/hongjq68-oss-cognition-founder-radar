"""Lightweight role-based access. Demo login issues an HMAC-signed bearer token; swap for SSO/OIDC in production."""
import hashlib
import hmac
import os
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .db import DATA_DIR, get_db
from .models import User

ROLES = ["viewer", "researcher", "recruiter", "admin"]
PERMISSIONS = {
    "read": {"viewer", "researcher", "recruiter", "admin"},
    "research": {"researcher", "recruiter", "admin"},     # create/edit people, evidence, imports, research runs, notes
    "verify": {"recruiter", "admin"},                     # workflow status, checklist, outreach approval, exports, ownership
    "audit": {"recruiter", "admin"},
    "admin": {"admin"},                                   # sources, users, roles config
}


def _secret() -> bytes:
    env = os.environ.get("RADAR_SECRET")
    if env:
        return env.encode()
    f = DATA_DIR / ".secret"
    if not f.exists():
        f.write_text(secrets.token_hex(32))
        f.chmod(0o600)
    return f.read_text().strip().encode()


def issue_token(user: User) -> str:
    sig = hmac.new(_secret(), str(user.id).encode(), hashlib.sha256).hexdigest()
    return f"{user.id}.{sig}"


def current_user(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not signed in")
    try:
        uid, sig = authorization[7:].split(".", 1)
    except ValueError:
        raise HTTPException(401, "Invalid token")
    expected = hmac.new(_secret(), uid.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(401, "Invalid token")
    user = db.get(User, int(uid))
    if not user or not user.active:
        raise HTTPException(401, "User disabled")
    return user


def require(permission: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in PERMISSIONS[permission]:
            raise HTTPException(403, f"Your role ({user.role}) cannot perform this action ({permission})")
        return user
    return dep
