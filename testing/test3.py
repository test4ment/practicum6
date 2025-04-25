import grpc
from transaction_service_pb2_grpc import TransactionServiceStub
from transaction_service_pb2 import AddTransactionRequest
from report_service_pb2_grpc import ReportServiceStub
from report_service_pb2 import MonthlyReportRequest, ExportReportRequest

channel1 = grpc.insecure_channel("localhost:50052")
stub_transaction = TransactionServiceStub(channel1)

print(stub_transaction.AddTransaction(AddTransactionRequest(user_id="1", amount=200.0, category="Salary", is_income=True)))

channel2 = grpc.insecure_channel("localhost:50053")
stub_report = ReportServiceStub(channel2)

print(stub_report.GenerateMonthlyReport(MonthlyReportRequest(user_id="1", month="2025-04")))

print(stub_report.ExportReport(ExportReportRequest(user_id="1", month="2025-04")))
