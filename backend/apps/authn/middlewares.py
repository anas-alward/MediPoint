import jwt
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.models import Session
from django.utils.deprecation import MiddlewareMixin


class JWTSessionMiddleware(MiddlewareMixin):
    """
    Overrides default session lookup to read session_id from JWT payload
    sent in Authorization header.
    """

    def process_request(self, request):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            try:
                payload = jwt.decode(
                    token, settings.SIMPLE_JWT["SIGNING_KEY"], algorithms=["HS256"]
                )
                session_id = payload.get("sessionid")
            except Exception:
                session_id = None
        else:
            session_id = None

        # Fallback to cookie if JWT does not provide session_id
        if session_id:
            request.COOKIES["sessionid"] = session_id
        # SessionMiddleware will pick up session from request.COOKIES as usual
