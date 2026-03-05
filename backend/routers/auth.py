import os
import hmac
import logging
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import database
from auth.jwt import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserSyncRequest(BaseModel):
    google_id: str
    email: str
    name: str
    access_token: str
    refresh_token: Optional[str] = None


def _verify_sync_secret(x_sync_secret: Optional[str] = Header(None)) -> None:
    expected = os.getenv("NEXTAUTH_SYNC_SECRET")
    if not expected:
        return
    if not x_sync_secret or not hmac.compare_digest(expected, x_sync_secret):
        raise HTTPException(status_code=403, detail="Invalid sync secret.")


@router.post("/sync")
def sync_user(req: UserSyncRequest, db=Depends(database.get_db), _=Depends(_verify_sync_secret)):
    """NextAuth 로그인 시 유저 DB 동기화 + 백엔드 JWT 발급."""
    cur = db.cursor()

    cur.execute("SELECT id FROM users WHERE google_id = ?", (req.google_id,))
    row = cur.fetchone()

    if row:
        user_id = row[0]
        cur.execute(
            """
            UPDATE users
            SET name = ?, email = ?, access_token = ?,
                refresh_token = COALESCE(?, refresh_token)
            WHERE id = ?
            """,
            (req.name, req.email, req.access_token, req.refresh_token, user_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO users (google_id, email, name, access_token, refresh_token)
            VALUES (?, ?, ?, ?, ?)
            """,
            (req.google_id, req.email, req.name, req.access_token, req.refresh_token),
        )
        cur.execute("SELECT id FROM users WHERE google_id = ?", (req.google_id,))
        user_id = cur.fetchone()[0]

    db.commit()

    token = create_access_token(user_id)
    return {"status": "success", "token": token}
