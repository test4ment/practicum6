import grpc
from user_service_pb2 import RegisterRequest, AuthRequest, GetUserInfoRequest, GetUserInfoResponse
from user_service_pb2_grpc import UserServiceStub

channel = grpc.insecure_channel("localhost:50051")
stub = UserServiceStub(channel)

print(stub.Register(RegisterRequest(username="alice", password="pass123", role="user")))

print(stub.Auth(AuthRequest(username="alice", password="pass123")))

print(stub.GetUserInfo(GetUserInfoRequest(username="alice")))