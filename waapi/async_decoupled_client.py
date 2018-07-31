import logging
from pprint import pformat

from autobahn.wamp import ApplicationError

from waapi.interface import WampRequestType, WampRequest
from waapi.libs.ak_autobahn import AkComponent
from waapi.libs.async_compatibility import asyncio, yield_from

_logger = logging.getLogger("WaapiClientAutobahn")
_logger.setLevel(logging.DEBUG)
_logger.hasHandlers()


class WaapiClientAutobahn(AkComponent):
    """
    Implementation class of a Waapi client using the autobahn library
    """
    def __init__(self, config, request_queue, connected_event):
        """
        :param config: Autobahn configuration
        :type queue_size: int
        """
        super(WaapiClientAutobahn, self).__init__(config)
        self._request_queue = request_queue
        self._connected_event = connected_event

    def _log(self, msg):
        _logger.debug("WaapiClientAutobahn: %s", msg)

    @asyncio.coroutine
    def stop_handler(self, request):
        """
        :param request: WampRequest
        """
        self._log("Received STOP, stopping and setting the result")
        self.disconnect()
        self._log("Disconnected")
        request.future.set_result(True)

    @asyncio.coroutine
    def call_handler(self, request):
        self._log("Received CALL, calling " + request.uri)
        res = yield from (self.call(request.uri, **request.kwargs))
        self._log("Received response for call")
        result = res.kwresults if res else {}
        callback = _WampCallbackHandler(request.callback)
        callback(result)
        request.future.set_result(result)

    @asyncio.coroutine
    def subscribe_handler(self, request):
        self._log("Received SUBSCRIBE, subscribing to " + request.uri)
        callback = _WampCallbackHandler(request.callback)
        subscription = yield from (self.subscribe(
            callback,
            topic=request.uri,
            options=request.kwargs)
        )
        request.future.set_result(subscription)

    @asyncio.coroutine
    def unsubscribe_handler(self, request):
        self._log("Received UNSUBSCRIBE, unsubscribing from " + str(request.subscription))
        try:
            # Successful unsubscribe returns nothing
            yield from request.subscription.unsubscribe()
            request.future.set_result(True)
        except ApplicationError:
            request.future.set_result(False)
        except Exception as e:
            self._log(str(e))
            request.future.set_result(False)

    @asyncio.coroutine
    def onJoin(self, details):
        self._log("Joined!")
        self._connected_event.set()

        try:
            while True:
                self._log("About to wait on the queue")
                request = yield from self._request_queue.get()
                """:type: WampRequest"""
                self._log("Received something!")

                try:
                    handler = {
                        WampRequestType.STOP: lambda request: self.stop_handler(request),
                        WampRequestType.CALL: lambda request: self.call_handler(request),
                        WampRequestType.SUBSCRIBE: lambda request: self.subscribe_handler(request),
                        WampRequestType.UNSUBSCRIBE: lambda request: self.unsubscribe_handler(request)
                    }.get(request.request_type)

                    if handler:
                        yield from handler(request)
                    else:
                        self._log("Undefined WampRequestType")

                except Exception as e:
                    self._log(pformat(str(e)))
                    request.future.set_result(None)

                self._log("Done treating request")
        except RuntimeError:
            # The loop has been shut down by a disconnect
            pass

    def onDisconnect(self):
        self._log("The client was disconnected.")

        # Stop the asyncio loop, ultimately stopping the runner thread
        asyncio.get_event_loop().stop()


class _WampCallbackHandler:
    """
    Wrapper for a callback that unwraps a WAMP response
    """
    def __init__(self, callback=None):
        assert callable(callback)
        self._callback = callback

    def __call__(self, *args, **kwargs):
        if self._callback and callable(self._callback):
            self._callback(**kwargs)