import grpc
from transaction_service_pb2_grpc import TransactionServiceStub
from transaction_service_pb2 import AddTransactionRequest, GetTransactionsRequest

channel = grpc.insecure_channel("localhost:50052")
stub = TransactionServiceStub(channel)

print(stub.AddTransaction(AddTransactionRequest(user_id="1", amount=200.0, category="Salary", is_income=True)))

print(stub.GetTransactions(GetTransactionsRequest(user_id="1", start_date="2025-04-01", end_date="2025-05-01")).transactions)
