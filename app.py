from fastapi import FastAPI
import grpc
from user_service_pb2_grpc import UserServiceStub
from user_service_pb2 import RegisterRequest, AuthRequest, GetUserInfoRequest
from transaction_service_pb2_grpc import TransactionServiceStub
from transaction_service_pb2 import AddTransactionRequest, GetTransactionsRequest
from report_service_pb2_grpc import ReportServiceStub
from report_service_pb2 import MonthlyReportRequest, ExportReportRequest
from google.protobuf.json_format import MessageToDict

app = FastAPI()

types = {
    8: "bool",  
    12: "bytes",  
    1: "float",  
    14: "int",  
    7: "int",  
    6: "int",  
    2: "float",  
    10: "object",  
    5: "int",  
    3: "int",  
    11: "object",  
    15: "int",  
    16: "int",  
    17: "int",  
    18: "int",  
    9: "str",  
    13: "int",  
    4: "int"  
}

services = {
    "userservice": ("localhost:50051", UserServiceStub),
    "transactionservice": ("localhost:50052", TransactionServiceStub),
    "reportservice": ("localhost:50053", ReportServiceStub),
}

for name, (addr, cls) in services.items():
    channel = grpc.insecure_channel(addr)
    services[name] = cls(channel)

for name, cls in services.items():
    for method in cls.__dict__:
        fields_str = ", ".join([f"{f.name}: {types[f.type]}" for f in eval(f"{method}Request.DESCRIPTOR.fields")])
        fields_fillup = ", ".join([f"{f.name}={f.name}" for f in eval(f"{method}Request.DESCRIPTOR.fields")])

        exec(f"""
@app.get('/{name}/{method}')
async def {name}_{method}({fields_str}):
    req = {method}Request({fields_fillup})
    resp = services['{name}'].{method}(req)
    return MessageToDict(resp)
            """)
