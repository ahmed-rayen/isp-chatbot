from slowapi import Limiter
from slowapi.util import get_remote_address

def rate_limit_key(request):
    # Use user ID if authenticated, otherwise use IP
    user = getattr(request.state, "user", None)
    if user:
        return str(user.id)
    return get_remote_address(request)

limiter = Limiter(key_func=rate_limit_key)