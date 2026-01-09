import jwt
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware

class JWTSessionMiddleware(SessionMiddleware):
    def process_request(self, request):
        # 1. Try to get session_id from JWT in Authorization header
        auth_header = request.headers.get("Authorization", "")
        session_id = None

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Use Simple JWT's key or Django's SECRET_KEY
                key = settings.SIMPLE_JWT.get("SIGNING_KEY", settings.SECRET_KEY)
                payload = jwt.decode(token, key, algorithms=["HS256"])
                session_id = payload.get("sessionid")
            except Exception:
                session_id = None

        # 2. If we found a session_id in the JWT, use it
        if session_id:
            request.session = self.SessionStore(session_id)
        else:
            # 3. Otherwise, fall back to standard cookie-based session logic
            super().process_request(request)