import logging

logger = logging.getLogger(__name__)


class DebugRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # #region debug-point A:log-request
        logger.info(
            "[DEBUG] %s %s | Content-Type: %s | Accept: %s",
            request.method,
            request.path,
            request.headers.get("Content-Type", "-"),
            request.headers.get("Accept", "-"),
        )
        # #endregion debug-point A:log-request

        response = self.get_response(request)

        # #region debug-point A:log-response
        content_type = response.headers.get("Content-Type", "-")
        preview = b""
        if hasattr(response, "content"):
            preview = response.content[:200]
        logger.info(
            "[DEBUG] Response %s %s | Content-Type: %s | Preview: %s",
            response.status_code,
            request.path,
            content_type,
            preview,
        )
        # #endregion debug-point A:log-response

        return response
