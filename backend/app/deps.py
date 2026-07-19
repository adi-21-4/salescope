import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_token
from app.db.session import get_db
from app.models.shop import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return decode_token(token, expected_type="access")
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_shop_id(payload: dict = Depends(get_current_token_payload)) -> uuid.UUID:
    """The tenant-scoping dependency. Every router touching shop-owned data must
    depend on this and filter every query by it — never trust a shop_id sourced
    from a client-supplied path/query param."""
    return uuid.UUID(payload["shop_id"])


def get_current_user_id(payload: dict = Depends(get_current_token_payload)) -> uuid.UUID:
    return uuid.UUID(payload["sub"])


def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
