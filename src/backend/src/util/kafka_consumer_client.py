from typing import Optional, List, Dict, Any
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import logging

logger = logging.getLogger(__name__)

class KafkaConsumerClient:
    def __init__(
        self,
        bootstrap_servers: List[str],
        group_id: str,
        auto_offset_reset: str = 'earliest',
        enable_auto_commit: bool = True,
        **additional_config: Dict[str, Any]
    ):
        """
        Initialize the Kafka consumer client.
        
        Args:
            bootstrap_servers: List of Kafka broker addresses
            group_id: Consumer group identifier
            auto_offset_reset: Where to start reading messages ('earliest' or 'latest')
            enable_auto_commit: Whether to auto-commit offsets
            additional_config: Additional Kafka consumer configuration options
        """
        self.config = {
            'bootstrap_servers': bootstrap_servers,
            'group_id': group_id,
            'auto_offset_reset': auto_offset_reset,
            'enable_auto_commit': enable_auto_commit,
            **additional_config
        }
        self._consumer: Optional[KafkaConsumer] = None

    def connect(self) -> None:
        """Establish connection to Kafka brokers."""
        try:
            self._consumer = KafkaConsumer(**self.config)
            logger.info("Successfully connected to Kafka brokers")
        except KafkaError as e:
            logger.error(f"Failed to connect to Kafka brokers: {str(e)}")
            raise

    def subscribe(self, topics: List[str]) -> None:
        """
        Subscribe to the specified topics.
        
        Args:
            topics: List of topic names to subscribe to
        """
        if not self._consumer:
            raise RuntimeError("Consumer not connected. Call connect() first")
        
        try:
            self._consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
        except KafkaError as e:
            logger.error(f"Failed to subscribe to topics: {str(e)}")
            raise

    def close(self) -> None:
        """Close the Kafka consumer connection."""
        if self._consumer:
            try:
                self._consumer.close()
                self._consumer = None
                logger.info("Kafka consumer connection closed")
            except KafkaError as e:
                logger.error(f"Error closing Kafka consumer: {str(e)}")
                raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __iter__(self):
        """Make the client iterable to consume messages."""
        if not self._consumer:
            raise RuntimeError("Consumer not connected. Call connect() first")
        return self._consumer
