from kafka import KafkaConsumer
import json
import requests
import os
from dotenv import load_dotenv
import logging
from typing import List, Optional
import time
import random

from backend.src.util.kafka_consumer_client import KafkaConsumerClient

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RequestWorker:
    def __init__(self, worker_id: str, consumer: KafkaConsumerClient, topics: List[str]):
        self.worker_id = worker_id
        self.consumer = consumer
        self.topics = topics

    def process_request(self, request_data: dict) -> dict:
        """Process a single HTTP request"""
        try:
            response = requests.request(
                method=request_data['method'],
                url=request_data['url'],
                headers=request_data['headers'],
                data=request_data.get('body'),
                timeout=30
            )
            
            return {
                "status_code": response.status_code,
                "headers": response.headers,
                "body": response.text,
                "worker_id": self.worker_id
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {
                "error": str(e),
                "worker_id": self.worker_id
            }
            
    def run(self, test_mode=False):
        """Main worker loop"""
        logger.info(f"Worker {self.worker_id} started")
      
        # TODO: add these to a config file
        timeout_ms = 10000
        page_size = 100
        
        with self.consumer as consumer:
            consumer.subscribe(self.topics)
            while True:
                messages = consumer._consumer.poll(timeout_ms=timeout_ms, max_records=page_size)
                for _, partition_messages in messages.items():
                    for message in partition_messages:
                        http_request = message.value["http_request"]
                        logger.info(f"Processing request for URL: {http_request['url']}")
                        result = self.process_request(http_request)
                        logger.info(f"Request processed: {result}")
                        # In test mode, return after processing one message
                        if test_mode:
                            return result
                        
                        # Add some delay to avoid overwhelming the proxies
                        time.sleep(random.uniform(0.1, 0.5))

def main():
    worker_id = os.getenv('WORKER_ID', f'worker_{random.randint(1000, 9999)}')

    consumer = KafkaConsumerClient(
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        group_id=f'http_worker_group_{worker_id}',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest'
    )
    
    worker = RequestWorker(
        worker_id=worker_id,
        consumer=consumer,
        topics=[os.getenv('KAFKA_TOPIC')]
    )
    worker.run()

if __name__ == "__main__":
    main() 