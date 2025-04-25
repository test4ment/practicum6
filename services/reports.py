from concurrent import futures
import grpc
import json
from report_service_pb2_grpc import ReportServiceServicer, add_ReportServiceServicer_to_server
from report_service_pb2 import MonthlyReportResponse, ExportReportResponse
from transaction_service_pb2_grpc import TransactionServiceStub
from transaction_service_pb2 import GetTransactionsRequest
from datetime import datetime
import calendar

class ReportService(ReportServiceServicer):
    month_format = r"%Y-%m"
    date_format = r"%Y-%m-%d"
    def __init__(self):
        channel = grpc.insecure_channel("localhost:50052") # make dependency
        self.transactionservice = TransactionServiceStub(channel)

    def GenerateMonthlyReport(self, request, context):
        dt = datetime.strptime(request.month, self.month_format)
        
        transactions = self.transactionservice.GetTransactions(
            GetTransactionsRequest(user_id=request.user_id, 
                                   start_date=dt.replace(day = 1).strftime(self.date_format),
                                   end_date=dt.replace(
                                            day = calendar.monthrange(dt.year, dt.month)[1]
                                        ).strftime(self.date_format),
                                    )
        ).transactions
        total_income = sum(t.amount for t in transactions if t.is_income)
        total_expenses = sum(t.amount for t in transactions if not t.is_income)
        return MonthlyReportResponse(
            total_income=total_income,
            total_expenses=total_expenses,
            transactions=transactions
        )

    def ExportReport(self, request, context):
        monthly_report = self.GenerateMonthlyReport(request=request, context=context)
        report_data = {"month": request.month, "total_income": monthly_report.total_income, "total_expenses": monthly_report.total_expenses}
        file_content = json.dumps(report_data).encode()
        return ExportReportResponse(file_content=file_content)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_ReportServiceServicer_to_server(ReportService(), server)
    server.add_insecure_port("[::]:50053")
    server.start()
    print("Report Service running on port 50053")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
