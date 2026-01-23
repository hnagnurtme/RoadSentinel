"""
Request/Response logging middleware.
"""
import logging
import json
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class LoggingMiddleware(MiddlewareMixin):
    """Middleware to log incoming requests and outgoing responses."""
    
    def process_request(self, request):
        """Log incoming request details."""
        log_data = {
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET),
            'user': str(request.user) if request.user.is_authenticated else 'Anonymous',
        }
        
        # Log request body for POST/PUT/PATCH
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.body:
                    log_data['body'] = json.loads(request.body)
            except:
                pass
        
        logger.info(f"Request: {json.dumps(log_data)}")
        return None
    
    def process_response(self, request, response):
        """Log outgoing response details."""
        log_data = {
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
        }
        
        logger.info(f"Response: {json.dumps(log_data)}")
        return response
