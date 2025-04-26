from concurrent import futures
import grpc
from datetime import datetime
from transaction_service_pb2_grpc import TransactionServiceServicer, add_TransactionServiceServicer_to_server
from transaction_service_pb2 import AddTransactionResponse, GetTransactionsResponse, Transaction

class TransactionDataProvider:
    dateformat = r"%Y-%m-%d"
    
    def __init__(self):
        self.transactions = []

    def add_transaction(self, user_id, amount, category, is_income):
        self.transactions.append({
            "user_id": user_id,
            "amount": amount,
            "category": category,
            "is_income": is_income,
            "date": datetime.now()
        })

    def get_transactions(self, user_id, start_date, end_date):
        start_date = datetime.strptime(start_date, self.dateformat)
        end_date = datetime.strptime(end_date, self.dateformat)
        return [t for t in self.transactions if t["user_id"] == user_id and start_date <= t["date"] <= end_date]


class TransactionService(TransactionServiceServicer):
    def __init__(self, transaction_provider: TransactionDataProvider):
        self.transaction_provider = transaction_provider

    def AddTransaction(self, request, context):
        self.transaction_provider.add_transaction(request.user_id, request.amount, request.category, request.is_income)
        return AddTransactionResponse(success=True, response_success=True)

    def GetTransactions(self, request, context):
        transactions = self.transaction_provider.get_transactions(request.user_id, request.start_date, request.end_date)
        return GetTransactionsResponse(transactions=[
            Transaction(
                id=str(i),
                amount=t["amount"],
                category=t["category"],
                is_income=t["is_income"],
                date=t["date"].strftime(self.transaction_provider.dateformat)
            ) for i, t in enumerate(transactions)
        ])

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_TransactionServiceServicer_to_server(
        TransactionService(TransactionDataProvider()), 
        server)
    server.add_insecure_port("[::]:50052")
    server.start()
    print("Transaction Service running on port 50052")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
