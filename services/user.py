from concurrent import futures
import grpc
import hashlib
from user_service_pb2_grpc import UserServiceServicer, add_UserServiceServicer_to_server
from user_service_pb2 import RegisterResponse, AuthResponse, GetUserInfoResponse

class UserDataProvider:
    def __init__(self):
        self.users = {}

    def get_user(self, username: str):
        return self.users.get(username)

    def add_user(self, username: str, password: str, role: str):
        assert not username in self.users, "Username has taken"

        self.users[username] = {
            "username": username,
            "role": role,
            "pwhash": hashlib.md5(password.encode()).hexdigest()
        }


class UserService(UserServiceServicer):
    def __init__(self, userdata_provider: UserDataProvider):
        self.userdata_provider = userdata_provider

    def Register(self, request, context):
        self.userdata_provider.add_user(request.username, request.password, request.role)
        return RegisterResponse(success=True, response_success=True)

    def Auth(self, request, context):
        user = self.userdata_provider.get_user(request.username)
        success = bool(user) and user["pwhash"] == hashlib.md5(request.password.encode()).hexdigest()
        return AuthResponse(success=success, response_success=True)

    def GetUserInfo(self, request, context):
        user = self.userdata_provider.get_user(request.username)
        return GetUserInfoResponse(username=user["username"], role=user["role"])

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    add_UserServiceServicer_to_server(
        UserService(UserDataProvider()), 
        server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    print("User Service running on port 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()