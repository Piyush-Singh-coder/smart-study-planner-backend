import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import json

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request details
        print(f"\n{'='*50}")
        print(f"Request: {request.method} {request.url}")
        print(f"Headers: {dict(request.headers)}")
        
        # Try to log request body if it exists
        try:
            body = await request.body()
            if body:
                print(f"Body: {body.decode()}")
        except:
            pass
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        print(f"Response: {response.status_code} - Processed in {process_time:.2f}s")
        print(f"{'='*50}\n")
        
        return response 