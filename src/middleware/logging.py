from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.middleware_factory import lambda_handler_decorator

# Initialize logger outside the handler for performance
logger = Logger(service="auth-api")


@lambda_handler_decorator
def logging_middleware(handler, event, context):
    """Middleware to automatically handle structured logging."""
    # Inject context into the logger
    logger.inject_lambda_context(handler.__name__)

    # Log the incoming event (optional, can be verbose)
    logger.info("Received event", extra={"event": event})

    try:
        response = handler(event, context)
        logger.info("Handler executed successfully", extra={"response": response})
        return response
    except Exception as e:
        logger.exception("Error processing request")
        # Re-raise the exception to be handled by the error handler middleware
        raise
