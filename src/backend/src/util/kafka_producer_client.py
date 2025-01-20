from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class KafkaProducerClient:
    def __init__(
        self,
        bootstrap_servers: str,
        retries: int = 5,
        acks: str = 'all',
        topic: str = 'default',
        **additional_config: Dict[str, Any]
    ):
        """
        Initialize the Kafka producer client.
        
        Args:
            bootstrap_servers: Kafka broker address
            retries: Number of retries for failed publishes
            acks: Acknowledgment level ('all', '1', or '0')
            additional_config: Additional Kafka producer configuration options
            topic: Kafka topic to publish to
        """
        self.config = {
            'bootstrap_servers': bootstrap_servers,
            'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
            'retries': retries,
            'acks': acks,
            **additional_config
        }
        self.topic = topic
        self._producer: Optional[KafkaProducer] = None

    def connect(self) -> None:
        """Establish connection to Kafka broker."""
        try:
            self._producer = KafkaProducer(**self.config)
            logger.info("Successfully connected to Kafka broker")
        except KafkaError as e:
            logger.error(f"Failed to connect to Kafka broker: {str(e)}")
            raise

    def publish(self, message: dict, timeout: int = 10) -> None:
        """
        Publish a message to specified Kafka topic.
        
        Args:
            message: Dictionary containing the message data
            timeout: Maximum time to wait for acknowledgment in seconds
        """
        if not self._producer:
            raise RuntimeError("Producer not connected. Call connect() first")
        
        try:
            future = self._producer.send(self.topic, message)
            future.get(timeout=timeout)
        except Exception as e:
            logger.error(f"Failed to publish message to topic {self.topic}: {str(e)}")
            raise

    def close(self) -> None:
        """Close the Kafka producer connection."""
        if self._producer:
            try:
                self._producer.close()
                self._producer = None
                logger.info("Kafka producer connection closed")
            except KafkaError as e:
                logger.error(f"Error closing Kafka producer: {str(e)}")
                raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await app.state.kafka_producer.close()

def init(
    app: FastAPI,
    bootstrap_servers: str,
    retries: int = 5,
    acks: str = 'all',
    topic: str = 'default',
    **additional_config: Dict[str, Any]
) -> None:
    """Initialize kafka producer"""
    app.state.kafka_producer = KafkaProducerClient(
        bootstrap_servers=bootstrap_servers,
        retries=retries,
        acks=acks,
        topic=topic,
        **additional_config
    )

async def get_kafka_producer(request: Request) -> KafkaProducerClient:
    """Dependency to get kafka producer"""
    if not hasattr(request.app.state, "kafka_producer"):
        raise RuntimeError("Kafka producer not initialized. Ensure init() is called during app startup.")
    return request.app.state.kafka_producer

