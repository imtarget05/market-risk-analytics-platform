from app.auth import create_access_token
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.account import Account
from app.schemas import AuthLoginRequest, AuthRegisterRequest, Token
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(tags=["auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/login", response_model=Token)
def login(req: AuthLoginRequest, db: Session = Depends(get_db)):
    user = db.query(Account).filter(Account.account_number == req.account_number).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid account number")
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: AuthRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Account).filter(Account.account_number == req.account_number).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account already exists")
    user = Account(
        account_number=req.account_number,
        account_holder_name=req.account_holder_name,
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "account_number": user.account_number, "role": user.role}
