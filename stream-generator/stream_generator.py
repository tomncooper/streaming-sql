import logging
import json

from argparse import ArgumentParser, Namespace
from typing import Iterator

from sseclient import SSEClient as EventSource
from kafka import KafkaProducer

WIKIPEDIA_CHANGES = "https://stream.wikimedia.org/v2/stream/recentchange"

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

def setup_logging(logger: logging.Logger, debug: bool = False) -> logging.Logger:

    style = "{"

    if debug:
        level: int = logging.DEBUG
        console_fmt: str = "{levelname} | {name} | F:{funcName} | L:{lineno} | {message}"
        file_fmt: str = (
            "{asctime} | {levelname} | {name} | F:{funcName} | L:{lineno} | {message}"
        )

    else:
        level = logging.INFO
        console_fmt = "{levelname} | {name} | {message}"
        file_fmt = "{asctime} | {name} | {levelname} | {message}"

    console_handler: logging.StreamHandler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt=console_fmt, style=style))
    logger.addHandler(console_handler)

    return logger

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
        required=True,
        help="The server boostrap string for the Kafka cluster",
    )

    parser.add_argument(
        "-t",
        "--topic",
        required=True,
        help="The topic which messages will be sent to",
    )

    return parser


if __name__ == "__main__":

    PARSER: ArgumentParser = create_parser()
    ARGS: Namespace = PARSER.parse_args()

    TOP_LOG: logging.Logger = setup_logging(logging.getLogger("streamingSQL"), ARGS.debug)

    TOP_LOG.info("Starting stream generation program")

    TOP_LOG.info(
        "Creating Kafka Producer for Kafka Cluster at: %s",
        ARGS.bootstrap_servers,
    )

    PRODUCER: KafkaProducer = KafkaProducer(bootstrap_servers=ARGS.bootstrap_servers)

    WIKI_CHANGES: Iterator = wikipedia_changes()

    try:
        while True:

            change: dict = next(WIKI_CHANGES)

            try:
                payload_str: str = json.dumps(change)
            except Exception as json_error:
                LOG.error("Error encoding change message to JSON: %s", str(json_error))
                continue

            try:
                payload: bytes = payload_str.encode("UTF-8")
            except UnicodeError as serialise_error:
                LOG.error("Error encoding change message to bytes: %s", str(serialise_error))
                continue

            try:
                PRODUCER.send(ARGS.topic, value=payload)
            except Exception as kafka_error:
                LOG.error("Error sending to Kafka: %s", str(kafka_error))
                continue

    except KeyboardInterrupt:
         LOG.info("Closing Kafka producer...")
         PRODUCER.close()
         LOG.info("Kafka producer closed. Exiting.")

