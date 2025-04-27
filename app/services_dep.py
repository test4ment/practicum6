from user_service_pb2_grpc import UserServiceStub
from user_service_pb2 import RegisterRequest, AuthRequest, GetUserInfoRequest
from transaction_service_pb2_grpc import TransactionServiceStub
from transaction_service_pb2 import AddTransactionRequest, GetTransactionsRequest
from report_service_pb2_grpc import ReportServiceStub
from report_service_pb2 import MonthlyReportRequest, ExportReportRequest
import grpc

services = {
    "userservice": ("localhost:50051", UserServiceStub),
    "transactionservice": ("localhost:50052", TransactionServiceStub),
    "reportservice": ("localhost:50053", ReportServiceStub),
}

for name, (addr, cls) in services.items():
    channel = grpc.insecure_channel(addr)
    services[name] = cls(channel)