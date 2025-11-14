import logging
import time

logger = logging.getLogger('taskflow')
from core.monitoring import log_kpi

class PerformanceLoggingMiddleware:
    def __init__(self, get_response):  
        self.get_response = get_response 

    def __call__(self, request):  
        request.start_time = time.time() 
        response = self.get_response(request)
        duration = time.time() - request.start_time
        response['X-Process-Time'] = f"{duration:.3f}s"
        logger.info(f"X-Process-Time: {duration:.3f}s")  
        return response
    def process_response(self, request, response):
        duration = time.time() - getattr(request, 'start_time', time.time())
        response['X-Process-Time'] = f"{duration:.3f}s"
        log_kpi(request, response)
        return response