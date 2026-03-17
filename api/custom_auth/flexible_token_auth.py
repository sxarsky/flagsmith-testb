"""
Flexible Token Authentication for Flagsmith
Accepts both "Token" (Django REST Framework default) and "Bearer" (OAuth2 standard) prefixes.
This enables compatibility with testbot-generated tests while maintaining backward compatibility.
"""
from rest_framework.authentication import TokenAuthentication


class FlexibleTokenAuthentication(TokenAuthentication):
    """
    Token authentication that accepts both 'Token' and 'Bearer' prefixes.

    Examples:
        Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
        Authorization: Bearer 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
    """
    keyword = ["Token", "Bearer"]

    def authenticate(self, request):
        """
        Override to check for both Token and Bearer keywords.
        """
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()

        if not auth or len(auth) != 2:
            return None

        # Check if the prefix is either 'Token' or 'Bearer'
        if auth[0] not in self.keyword:
            return None

        # Use the parent class logic with the token value
        try:
            return self.authenticate_credentials(auth[1])
        except Exception:
            return None
