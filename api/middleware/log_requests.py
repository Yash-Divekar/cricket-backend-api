import logging
import json

logger = logging.getLogger('django.request')

class APILoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Clone request body (as it can only be read once)
        body = ''
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = request.body.decode('utf-8')
                body = json.loads(body) if body else {}
            except (ValueError, Exception):
                body = '[unreadable]'

        # Get user information
        user = getattr(request, 'user', None)
        
        if user and user.is_authenticated:
            user_info = f"{user.username} ({getattr(user, 'category', 'Unknown')})"
        else:
            user_info = "Anonymous"

        # Log request details
        logger.info(
            f"[REQUEST] {request.method} {request.path} | User: {user_info} | Body: {body}"
        )

        # Process the request
        response = self.get_response(request)

        # Determine error type for non-2xx responses
        error_type = None
        if 400 <= response.status_code < 500:
            error_type = "Client Error"
        elif 500 <= response.status_code < 600:
            error_type = "Server Error"

        # Log response details
        logger.info(
            f"[RESPONSE] {request.method} {request.path} | User: {user_info} | "
            f"Status: {response.status_code} | Error Type: {error_type or 'Success'}\n"
        )

        return response