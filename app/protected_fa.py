from fastapi import FastAPI, HTTPException, status
from app import jwt_worker
import datetime
from jose import JWTError, jwt

app = FastAPI()

@app.get("/")
async def hello():
    return {"message": "Hello from protected service!"}

@app.get("/generate_token")
async def generate_token(service_name: str):
    payload = {
        "sub": service_name
    }
    token = jwt_worker.create_access_token(
        payload, datetime.timedelta(hours=1)
    )
    return {"access_token": token}

@app.get("/auth_service")
async def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, jwt_worker.SECRET_KEY, algorithms=["HS256"])
        return {"response": f"Hello, {payload['sub']}!"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


if __name__ == "__main__":
    import ssl
    import uvicorn
    import os
    path = os.getcwd() + "/certs/"

    uvicorn.run(
        "app.protected_fa:app",
        host="127.0.0.1",
        port=8000,
        ssl_keyfile=path + "server.key",
        ssl_certfile=path + "server.crt",
        ssl_ca_certs=path + "ca.crt",
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        reload=True
    )
