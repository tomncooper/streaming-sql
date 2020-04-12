import logging
import json

from sseclient import SSEClient as EventSource

WIKIPEDIA_CHANGES = "https://stream.wikimedia.org/v2/stream/recentchange"

LOG: logging.Logger = logging.getLogger("stream_generator")

def wikipedia_changes():

    for event in EventSource(WIKIPEDIA_CHANGES):
        if event.event == 'message':
            try:
                change = json.loads(event.data)
            except json.JSONDecodeError:
                LOG.error("JSON Decode failed on message: %s", event.data)
                pass
            else:
                yield change
        else:
            LOG.debug("Event was not a message, it was a %s", event.event)


