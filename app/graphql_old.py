from collections import defaultdict
import datetime
import graphene
from flask import Flask
from flask_graphql import GraphQLView
import asyncio
from app import services_dep
from flask_socketio import SocketIO
from transaction_service_pb2 import AddTransactionRequest, GetTransactionsRequest
from google.protobuf.json_format import MessageToDict
from user_service_pb2 import RegisterRequest, AuthRequest, GetUserInfoRequest, GetUserInfoResponse

pending_transactions = defaultdict(list)

class Transaction(graphene.ObjectType):
    username = graphene.String()
    amount = graphene.Float()
    category = graphene.String()
    is_income = graphene.Boolean()
    date = graphene.String()


class User(graphene.ObjectType):
    username = graphene.String()
    role = graphene.String()
    transactions = graphene.List(Transaction)

    def resolve_transactions(self, info):
        resp = MessageToDict(services_dep.services["transactionservice"].GetTransactions(
            GetTransactionsRequest(
                user_id=self["username"], 
                start_date="2024-01-01", 
                end_date=(datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
            ))["transactions"]
        return [
            Transaction(
                username=self["username"],
                amount=t.get("amount"),
                category=t.get("category"),
                is_income=t.get("isIncome"),
                date=t.get("date")
            )
            for t in resp
        ]

class Query(graphene.ObjectType):
    get_user = graphene.Field(User, username=graphene.String(required=True))

    def resolve_get_user(self, info, username):
        response = services_dep.services["userservice"].GetUserInfo(GetUserInfoRequest(username=username))
        return MessageToDict(response)

class RegisterUser(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        pw = graphene.String(required=True)
        role = graphene.String(required=True)

    user = graphene.Field(User)

    def mutate(self, info, username, pw, role):
        resp = services_dep.services["userservice"].Register(RegisterRequest(username=username, password=pw, role=role))
        return MessageToDict(resp)

class TransactionOutput(graphene.ObjectType):
    success = graphene.Boolean()
    
class AddTransaction(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        amount = graphene.Float(required=True)
        category = graphene.String(required=True)
        is_income = graphene.Boolean(required=True)
    
    Output = TransactionOutput
    
    def mutate(self, info, username, amount, category, is_income):
        resp = services_dep.services["transactionservice"].AddTransaction(
            AddTransactionRequest(user_id=username, amount=amount, category=category, is_income=is_income))
        
        resp_dict = MessageToDict(resp)
        
        if resp_dict.get("success", False):
            new_transaction = {
                "username": username,
                "amount": amount,
                "category": category,
                "is_income": is_income,
                "date": datetime.datetime.now().isoformat()
            }
            pending_transactions[username].append(new_transaction)

        return TransactionOutput(success = resp_dict.get("success", False))
        
class Mutation(graphene.ObjectType):
    register_user = RegisterUser.Field()
    add_transaction = AddTransaction.Field()

class Subscription(graphene.ObjectType):
    transaction_added = graphene.Field(
        Transaction,
        username=graphene.String(required=True)
    )

    async def resolve_transaction_added(self, info, username):
        while True:
            if pending_transactions.get(username):
                transaction = pending_transactions[username].pop()
                yield transaction
            else:
                await asyncio.sleep(1)

schema = graphene.Schema(query=Query, mutation=Mutation, subscription=Subscription)

app = Flask(__name__)

app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', 
                                                           schema=schema, 
                                                           graphiql=True))

if __name__ == '__main__':
    app.run(port=5000)