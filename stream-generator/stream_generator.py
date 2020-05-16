import logging
import json
import os
import sys
import signal

from argparse import ArgumentParser, Namespace
from typing import Iterator, Optional

from sseclient import SSEClient as EventSource
from kafka import KafkaProducer

WIKIPEDIA_CHANGES: str = "https://stream.wikimedia.org/v2/stream/recentchange"

BOOTSTRAP_ENV_VAR: str = "KAFKA_BOOTSTRAP_SERVERS"

LOG: logging.Logger = logging.getLogger("streamingSQL.generator")

def wikipedia_changes() -> Iterator[Optional[dict]]:

    for event in EventSource(WIKIPEDIA_CHANGES):
        if event.event == 'message':
            LOG.debug("Processing new message")
            try:
                change = json.loads(event.data)
            except json.JSONDecodeError:
                LOG.warning("JSON Decode failed on message: %s", event.data)
                yield None
            else:
                LOG.debug("Yielding message")
                yield change

def setup_logging(logger: logging.Logger, debug: bool = False) -> None:

    style = "{"

    if debug:
        level: int = logging.DEBUG
        console_fmt: str = "{asctime} | {levelname} | {name} | F:{funcName} | L:{lineno} | {message}"

    else:
        level = logging.INFO
        console_fmt = "{asctime} | {levelname} | {name} | {message}"

    console_handler: logging.StreamHandler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt=console_fmt, style=style))
    logger.addHandler(console_handler)
    logger.setLevel(level)

def create_parser() -> ArgumentParser:

    parser: ArgumentParser = ArgumentParser("Source stream generation program")

    parser.add_argument(
        "--debug",
        required=False,
        action="store_true",
        help="Flag indicating if debug information should be logged.",
    )

    parser.add_argument(
        "-bs",
        "--bootstrap_servers",
        required=False,
        help="The server boostrap string for the Kafka cluster",
    )

    return parser

def send_to_kafka(producer: KafkaProducer, topic: str, payload_str: str, key_str: Optional[str] = None):

    try:
        payload: bytes = payload_str.encode("UTF-8")
    except UnicodeError as serialise_error:
        LOG.warning("Error encoding message payload to bytes: %s", str(serialise_error))
        return None

    key: Optional[bytes]
    if key_str:
        try:
            key = key_str.encode("UTF-8")
        except UnicodeError as serialise_error:
            LOG.warning("Error encoding message key to bytes: %s", str(serialise_error))
            return None
    else:
        key = None

    try:
        if key:
            producer.send(topic, key=key, value=payload)
        else:
            producer.send(topic, value=payload)
    except Exception as kafka_error:
        LOG.warning("Error when sending to Kafka: %s", str(kafka_error))


if __name__ == "__main__":

    PARSER: ArgumentParser = create_parser()
    ARGS: Namespace = PARSER.parse_args()

    TOP_LOG: logging.Logger = logging.getLogger("streamingSQL")

    setup_logging(TOP_LOG, ARGS.debug)

    TOP_LOG.info("Starting stream generation program")

    TOP_LOG.info(
        "Creating Kafka Producer for Kafka Cluster at: %s",
        ARGS.bootstrap_servers,
    )

    # If the command line args are specified then use them. If not then look for env vars
    # and if they aren't present exit.
    if not ARGS.bootstrap_servers:
        if BOOTSTRAP_ENV_VAR in os.environ:
            BOOTSTRAP: str = os.environ[BOOTSTRAP_ENV_VAR]
            TOP_LOG.info("Using Kafka bootstrap address (%s) defined in %s environment variable",
                    BOOTSTRAP, BOOTSTRAP_ENV_VAR)
        else:
            TOP_LOG.error(
                "Kafka boostrap servers string was not supplied via the command line "
                "argument or the environment variable (%s). Exiting.", BOOTSTRAP_ENV_VAR)
            sys.exit(1)
    else:
        BOOTSTRAP = ARGS.bootstrap_servers

    TOP_LOG.info(
        "Creating Kafka Producer for Kafka Cluster at: %s", BOOTSTRAP,
    )

    PRODUCER: KafkaProducer = KafkaProducer(bootstrap_servers=BOOTSTRAP)

    def terminate_handler(sigterm, frame):
        TOP_LOG.warning("SIGTERM signal received, closing Kafka Producer")
        PRODUCER.close()

    #Intercept SIGTERM and close PRODUCER gracefully
    signal.signal(signal.SIGTERM, terminate_handler)

    WIKI_CHANGES: Iterator[Optional[dict]] = wikipedia_changes()

    try:
        TOP_LOG.info("Starting stream generation")
        while True:

            try:
                change: Optional[dict] = next(WIKI_CHANGES)
            except Exception as read_err:
                TOP_LOG.warning("Error fetching Wikipedia change message: %s", str(read_err))
                continue

            if not change:
                TOP_LOG.warning("Returned wiki change was empty")
                continue

            try:
                payload_str: str = json.dumps(change)
            except Exception as json_error:
                TOP_LOG.warning("Error encoding change message to JSON: %s", str(json_error))
                continue

            # Send raw wiki change to wiki-changes
            send_to_kafka(PRODUCER, "wiki-changes", payload_str=payload_str)

            # Send user and title to user-titles topic for simple example.
            try:
                send_to_kafka(PRODUCER, "user-titles", key_str=change["user"], payload_str=change["title"])
            except KeyError as key_error:
                TOP_LOG.error("Wiki change dictionary did not contain expected keys")
                continue

    except KeyboardInterrupt:
         TOP_LOG.info("Closing Kafka producer...")
         PRODUCER.close()
         TOP_LOG.info("Kafka producer closed. Exiting.")

