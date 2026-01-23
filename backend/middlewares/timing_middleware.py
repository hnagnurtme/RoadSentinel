"""
Request performance tracking middleware.
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class TimingMiddleware(MiddlewareMixin):
    """Middleware to track request processing time."""
    
    def process_request(self, request):
        """Store request start time."""
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Calculate and log request processing time."""
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            
            # Add custom header
            response['X-Request-Duration'] = f"{duration:.3f}s"
            
            # Log slow requests (> 1 second)
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.3f}s"
                )
            else:
                logger.debug(
                    f"Request timing: {request.method} {request.path} "
                    f"took {duration:.3f}s"
                )
        
        return response
