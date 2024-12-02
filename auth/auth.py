import sqlite3
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from base64 import urlsafe_b64encode
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
import pathlib

with open("private_key.pem", "rb") as f:
    PRIVATE_KEY = load_pem_private_key(f.read(), password=None)

with open("public_key.pem", "rb") as f:
    PUBLIC_KEY = load_pem_public_key(f.read())

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Modèles
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str

class UserInDB(User):
    hashed_password: str


path_to_db = pathlib.Path(__file__).parent.absolute() / "data" / "database.db"


def get_user_from_db(username: str):
    try:
        with sqlite3.connect(path_to_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nom, mot_de_passe FROM utilisateurs WHERE nom = ?", (username,))
            row = cursor.fetchone()
            if row:
                return UserInDB(username=row[0], hashed_password=row[1])
    except sqlite3.Error as e:
        print(f"Erreur SQLite : {e}")
    return None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str):
    user = get_user_from_db(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)


def verify_token(token):
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM], 
            options={"verify_signature": True, "verify_exp": True})
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expiré")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=User)
async def read_users_me(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return {"username": username}


@app.get("/oauth/.well-known/jwks.json")
async def get_jwks():
    numbers = PUBLIC_KEY.public_numbers()
    e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    return {
        "keys": [{
            "kty": "RSA",
            "use": "sig",
            "alg": ALGORITHM,
            "n": urlsafe_b64encode(n).decode("utf-8").rstrip("="),
            "e": urlsafe_b64encode(e).decode("utf-8").rstrip("="),
        }]
    }

# Lancer le serveur FastAPI
if __name__ == "__main__":
    import uvicorn
    import nest_asyncio
    nest_asyncio.apply()
    uvicorn.run(app, host="0.0.0.0", port=5008)
