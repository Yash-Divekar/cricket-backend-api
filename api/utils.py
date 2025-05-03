from rest_framework import status

def api_response(data=None, message="Success", code=status.HTTP_200_OK):
    return {
        "code": str(code),
        "data": data or {},
        "message": message
    }
