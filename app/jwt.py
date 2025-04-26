from fastapi import APIRouter, Depends, HTTPException, Request, status
from datetime import datetime, timedelta
from typing import Optional
import requests
from jose import JWTError, jwt
from user_service_pb2 import AuthRequest, GetUserInfoRequest, GetUserInfoResponse
from google.protobuf.json_format import MessageToDict
from app import app
import os
import dotenv

dotenv.load_dotenv()

router = APIRouter(prefix="/public")

SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

def get_user(username: str):
    stub = app.services["userservice"]
    return MessageToDict(stub.GetUserInfo(GetUserInfoRequest(username=username)))

def auth(username: str, password: str):
    stub = app.services["userservice"]
    return MessageToDict(stub.Auth(AuthRequest(username=username, password=password)))


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(days=7)
    to_encode.update({"exp": expire, "refresh": True})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.get("/login")
async def login_for_access_token(username: str, pw: str):
    user = auth(username, pw)
    if not user.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    userdata = get_user(username)

    access_token = create_access_token(
        data={"sub": userdata["username"], "role": userdata["role"]},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": userdata["username"]},
        expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }

@router.get("/resfresh_access_token")
async def refresh_access_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("refresh"):
            raise HTTPException(status_code=400, detail="Invalid refresh token")
        
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=400, detail="Invalid refresh token")
        
        try:
            user = get_user(username)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        
        new_access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {"access_token": new_access_token, "token_type": "bearer"}
    
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid refresh token")

async def get_current_user(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("refresh"):
            raise credentials_exception
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=username)
    user["role"] = payload.get("role")

    return user


class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user = Depends(get_current_user)):
        if not(user["role"] in self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource"
            )
        return user


@router.get("/users/me/")
async def read_users_me(token: str):
    return get_current_user(token)

@router.get("/admin/", dependencies=[Depends(RoleChecker(["admin"]))])
async def admin_only():
    return {"message": "Welcome admin!"}

@router.get("/user/", dependencies=[Depends(RoleChecker(["user", "admin"]))])
async def user_only():
    return {"message": "Welcome regular user!"}

from fastapi.responses import RedirectResponse, JSONResponse

@router.get("/auth/github")
async def login_github():
    if not all([GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, REDIRECT_URI]):
        return JSONResponse({"response": "Missing GitHub OAuth credentials in .env file"}, status_code=status.HTTP_418_IM_A_TEAPOT)
    
    auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=user:email"
    )
    return RedirectResponse(auth_url, headers={"Access-Control-Allow-Origin": "*"})

@router.get("/auth/github/callback")
async def github_callback(code: str):
    token_url = "https://github.com/login/oauth/access_token"
    token_data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Accept": "application/json"}

    token_response = requests.post(token_url, data=token_data, headers=headers)
    token_json = token_response.json()

    if "details" in token_json:
        raise HTTPException(status_code=400, detail=token_json["error_description"])

    access_token = token_json.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get access token")

    user_data = await get_github_user_data(access_token)

    return {"user": user_data}


async def get_github_user_data(access_token: str):
    api_url = "https://api.github.com/user"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.get(api_url, headers=headers)
    data = response.json()

    if "message" in data and data["message"] == "Bad credentials":
        raise HTTPException(status_code=401, detail="Invalid access token")

    return data
