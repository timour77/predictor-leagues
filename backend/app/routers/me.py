from fastapi import APIRouter, Depends

from app.auth import get_current_user

router = APIRouter()


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "telegram_id": user["telegram_id"],
        "username": user["username"],
        "first_name": user["first_name"],
        "photo_url": user["photo_url"],
    }
