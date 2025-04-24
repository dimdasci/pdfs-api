import os
import threading
import psutil
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.middleware_factory import lambda_handler_decorator

# Initialize logger outside the handler for performance
logger = Logger(service="auth-api")


@lambda_handler_decorator
def logging_middleware(handler, event, context):
    """Middleware to automatically handle structured logging."""
    # Inject context into the logger
    logger.inject_lambda_context(handler.__name__)

    # Log system details at the start
    vm_start = psutil.virtual_memory()
    system_info_start = {
        "cpu_cores": os.cpu_count(),
        "memory_limit_mb": context.memory_limit_in_mb,
        "memory_available_mb": vm_start.available // (1024 * 1024),
        "memory_percent_used": vm_start.percent,
        "active_threads": threading.active_count(),
    }
    logger.info("System details at start", extra={"system_info": system_info_start})

    # Log the incoming event (optional, can be verbose)
    logger.info("Received event", extra={"event": event})

    try:
        response = handler(event, context)
        logger.info("Handler executed successfully", extra={"response": response})

        # Log system details at the end
        vm_end = psutil.virtual_memory()
        system_info_end = {
            "memory_available_mb": vm_end.available // (1024 * 1024),
            "memory_percent_used": vm_end.percent,
        }
        logger.info("System details at end", extra={"system_info": system_info_end})

        return response
    except Exception as e:
        logger.exception("Error processing request")
        # Re-raise the exception to be handled by the error handler middleware
        raise
