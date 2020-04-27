import logging
import json
import os
import sys
import signal

from argparse import ArgumentParser, Namespace
from typing import Iterator

from sseclient import SSEClient as EventSource
from kafka import KafkaProducer

WIKIPEDIA_CHANGES: str = "https://stream.wikimedia.org/v2/stream/recentchange"

BOOTSTRAP_ENV_VAR: str = "KAFKA_BOOTSTRAP_SERVERS"
TOPIC_ENV_VAR: str = "KAFKA_TOPIC"

LOG: logging.Logger = logging.getLogger("streamingSQL.generator")

def wikipedia_changes() -> Iterator[dict]:

    for event in EventSource(WIKIPEDIA_CHANGES):
        if event.event == 'message':
            try:
                change = json.loads(event.data)
            except json.JSONDecodeError:
                LOG.error("JSON Decode failed on message: %s", event.data)
                pass
            else:
                yield change

def setup_logging(logger: logging.Logger, debug: bool = False) -> None:

    style = "{"

    if debug:
        level: int = logging.DEBUG
        console_fmt: str = "{asctime} | {levelname} | {name} | F:{funcName} | L:{lineno} | {message}"

    else:
        level = logging.INFO
        console_fmt = "{asctime} | {levelname} | {name} | {message}"

    console_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(fmt=console_fmt, style=style))
    logger.addHandler(console_handler)

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

    parser.add_argument(
        "-t",
        "--topic",
        required=False,
        help="The topic which messages will be sent to",
    )

    return parser


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
            TOP_LOG.info("Using Kafka bootstrap {%s} defined in %s environment variable",
                    BOOTSTRAP, BOOTSTRAP_ENV_VAR)
        else:
            TOP_LOG.error(
                "Kafka boostrap servers string was not supplied via the command line "
                "argument or the environment variable (%s). Exiting.", BOOTSTRAP_ENV_VAR)
            sys.exit(1)
    else:
        BOOTSTRAP = ARGS.bootstrap_servers

    if not ARGS.topic:
        if TOPIC_ENV_VAR in os.environ:
            TOPIC: str = os.environ[TOPIC_ENV_VAR]
            TOP_LOG.info("Using topic {%s} defined in %s environment variable", TOPIC,
                    TOPIC_ENV_VAR)
        else:
            TOP_LOG.error(
                "Kafka topic was not specified via the command line "
                "argument or the environment variable (%s). Exiting.", TOPIC_ENV_VAR)
            sys.exit(1)
    else:
        TOPIC = ARGS.topic


    PRODUCER: KafkaProducer = KafkaProducer(bootstrap_servers=BOOTSTRAP)

    def terminate_handler(sigterm, frame):
        TOP_LOG.warning("SIGTERM signal received, closing Kafka Producer")
        PRODUCER.close()

    #Intercept SIGTERM and close PRODUCER gracefully
    signal.signal(signal.SIGTERM, terminate_handler)

    WIKI_CHANGES: Iterator[dict] = wikipedia_changes()

    try:
        TOP_LOG.info("Starting stream generation to %s topic", TOPIC)
        while True:

            change: dict = next(WIKI_CHANGES)

            try:
                payload_str: str = json.dumps(change)
            except Exception as json_error:
                TOP_LOG.error("Error encoding change message to JSON: %s", str(json_error))
                continue

            try:
                payload: bytes = payload_str.encode("UTF-8")
            except UnicodeError as serialise_error:
                TOP_LOG.error("Error encoding change message to bytes: %s", str(serialise_error))
                continue

            try:
                PRODUCER.send(TOPIC, value=payload)
            except Exception as kafka_error:
                TOP_LOG.error("Error when sending to Kafka: %s", str(kafka_error))
                continue

    except KeyboardInterrupt:
         TOP_LOG.info("Closing Kafka producer...")
         PRODUCER.close()
         TOP_LOG.info("Kafka producer closed. Exiting.")

