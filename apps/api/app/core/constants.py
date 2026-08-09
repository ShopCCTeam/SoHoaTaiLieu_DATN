"""Static configuration values."""

# OAuth-style reserved byte for stable error code prefixes.
PROBLEM_TYPE_BASE = "https://api.example.edu.vn/problems"

# Header used for request_id propagation.
REQUEST_ID_HEADER = "X-Request-ID"

# Cookie attrs for refresh token (cf. docs/api/auth-cookie.md).
REFRESH_COOKIE_SAMESITE = "lax"
