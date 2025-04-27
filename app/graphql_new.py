from collections import defaultdict
import datetime
from typing import List, Optional, AsyncGenerator
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from app import services_dep
from transaction_service_pb2 import AddTransactionRequest, GetTransactionsRequest
from google.protobuf.json_format import MessageToDict
from user_service_pb2 import RegisterRequest, GetUserInfoRequest
import asyncio

pending_transactions = defaultdict(list)

@strawberry.type
class Transaction:
    username: str
    amount: float
    category: str
    is_income: bool
    date: str

@strawberry.type
class User:
    username: str
    role: str
    
    @strawberry.field
    async def transactions(self) -> List[Transaction]:
        resp = MessageToDict(services_dep.services["transactionservice"].GetTransactions(
            GetTransactionsRequest(
                user_id=self.username, 
                start_date="2024-01-01", 
                end_date=(datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
            ))["transactions"]
        
        return [
            Transaction(
                username=self.username,
                amount=t.get("amount"),
                category=t.get("category"),
                is_income=t.get("isIncome"),
                date=t.get("date")
            )
            for t in resp
        ]

@strawberry.type
class TransactionOutput:
    success: bool

@strawberry.type
class Query:
    @strawberry.field
    async def get_user(self, username: str) -> User:
        response = services_dep.services["userservice"].GetUserInfo(GetUserInfoRequest(username=username))
        user_data = MessageToDict(response)
        return User(username=user_data["username"], role=user_data["role"])

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def register_user(self, username: str, pw: str, role: str) -> User:
        resp = services_dep.services["userservice"].Register(
            RegisterRequest(username=username, password=pw, role=role)
        )
        user_data = MessageToDict(resp)
        return User(username=user_data["username"], role=user_data["role"])

    @strawberry.mutation
    async def add_transaction(
        self, 
        username: str, 
        amount: float, 
        category: str, 
        is_income: bool
    ) -> TransactionOutput:
        resp = services_dep.services["transactionservice"].AddTransaction(
            AddTransactionRequest(
                user_id=username, 
                amount=amount, 
                category=category, 
                is_income=is_income
            )
        )
        
        resp_dict = MessageToDict(resp)
        
        if resp_dict.get("success", False):
            new_transaction = Transaction(
                username=username,
                amount=amount,
                category=category,
                is_income=is_income,
                date=datetime.datetime.now().isoformat()
            )
            pending_transactions[username].append(new_transaction)

        return TransactionOutput(success=resp_dict.get("success", False))

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def transaction_added(self, username: str) -> AsyncGenerator[Transaction, None]:
        while True:
            if pending_transactions.get(username):
                transaction = pending_transactions[username].pop()
                yield transaction
            await asyncio.sleep(1)

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)

app = FastAPI()
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)