import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

from base64 import urlsafe_b64encode
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

with open("private_key.pem", "rb") as f:
    PRIVATE_KEY = load_pem_private_key(f.read(), password=None)

with open("public_key.pem", "rb") as f:
    PUBLIC_KEY = load_pem_public_key(f.read())

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

db = {
    "user1": {
        "username": "user1",
        "hashed_password": "$2b$12$3bD6Mdnnou0KEqQ5CdCse.vbLwswrjHcdSTPjAhXD97pKJbwltCZ6", 
    },
    "user2": {
        "username": "user2",
        "hashed_password": "$2b$12$3bD6Mdnnou0KEqQ5CdCse.vbLwswrjHcdSTPjAhXD97pKJbwltCZ6",  # "password2"
    },
}

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str


class UserInDB(User):
    hashed_password: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm="RS256")


def verify_token(token):
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'], 
            options={
                "verify_signature": True, 
                "verify_exp": True, 
                "verify_aud": False, 
                "verify_iss": False
            }
        )
        return payload 
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré"
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur signature"
        )
    except jwt.InvalidAlgorithmError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NOT RS256"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=User)
async def read_users_me(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return {"username": username}


def get_jwk(public_key):
    numbers = public_key.public_numbers()
    e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "n": urlsafe_b64encode(n).decode("utf-8").rstrip("="),
        "e": urlsafe_b64encode(e).decode("utf-8").rstrip("="),
    }

@app.get("/oauth/.well-known/jwks.json")
async def get_jwks():
    return {"keys": [get_jwk(PUBLIC_KEY)]}

import uvicorn
if __name__ == '__main__':
    # uvicorn.run(app, host='localhost', port=5009)
    # code pour lancer depuis un notebook Jupyter
    import nest_asyncio
    nest_asyncio.apply()
    uvicorn.run(app, host='0.0.0.0', port=5008)