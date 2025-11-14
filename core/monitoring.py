def log_kpi(request, response):
    method = request.method
    endpoint = request.path
    status_code = response.status_code
    duration = response.get('X-Process-Time', '0s')
    with open('kpi_logs.log', 'a') as f:
        f.write(f"{method} {endpoint} {status_code} {duration}\n")