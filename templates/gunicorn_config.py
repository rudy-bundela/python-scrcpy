# optimized for long-lived SSE with threaded workers
bind = "0.0.0.0:5000"
workers = 4                 # fewer workers when threads are high
# worker_class = "gthread"
# threads = 50                # allow many concurrent SSE connections
worker_connections = 1000
timeout = 120               # allow long-running requests
graceful_timeout = 30
keepalive = 2
reload = True
reload_extra_files = "./templates/index.html"
loglevel = "info"
errorlog = "-"
accesslog = "-"