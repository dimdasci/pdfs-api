"""Authentication service for API handlers."""

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import Logger

from ..middleware.exceptions import UnauthorizedError


class AuthenticationService:
    """Service for authentication and user context handling."""

    def __init__(self, app: APIGatewayHttpResolver, logger: Logger):
        """Initialize authentication service.

        Args:
            app: The API Gateway resolver instance
            logger: Logger instance
        """
        self.app = app
        self.logger = logger

    def get_authenticated_user_id(self) -> str:
        """Get the authenticated user ID from the context.

        Returns:
            User ID

        Raises:
            UnauthorizedError: If no user ID is found in the context
        """
        user_id = self.app.context.get("user_id")
        if not user_id:
            self.logger.error("User ID missing from context after auth")
            raise UnauthorizedError("Authentication context missing")

        self.logger.debug(f"Authenticated as user {user_id}")
        return user_id
