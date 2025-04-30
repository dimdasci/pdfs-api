from functools import wraps
from typing import Any, Callable

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import Logger


def create_inject_user_context_decorator(
    app: APIGatewayHttpResolver, logger: Logger
) -> Callable:
    """Factory function that creates the user context injection decorator."""

    def inject_user_context(func: Callable) -> Callable:
        """Decorator to extract user_id from Lambda authorizer context and add to Powertools context."""

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            user_id = None
            try:
                # Extract userId from the Lambda authorizer's context output
                # Accessing via app instance passed to the factory
                auth_context = app.current_event.request_context.authorizer
                lambda_context = auth_context.get_context()
                user_id = lambda_context.get("userId")

                if user_id:
                    app.append_context(user_id=user_id)
                    logger.debug(
                        "User context injected from Lambda authorizer",
                        extra={"user_id": user_id},
                    )
                else:
                    logger.warning(
                        "'userId' missing in Lambda authorizer context.",
                        extra={"lambda_context": lambda_context},
                    )

            except (AttributeError, KeyError):
                logger.exception(
                    "Could not retrieve Lambda authorizer context or userId. Check authorizer configuration and response format."
                )

            # Execute the original handler function
            return func(*args, **kwargs)

        return wrapper

    return inject_user_context
