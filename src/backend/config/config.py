import os
from typing import List, Dict, Any
import yaml
from dotenv import load_dotenv

load_dotenv()

def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    # Default to environment variable if no path provided
    if not config_path:
        config_path = os.getenv('CONFIG_PATH', 'config/config.yaml')
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Return default configuration if file doesn't exist
        return {
            'worker': {
                'kafka_topic': 'http_requests',
                'request_timeout': 30,
                'retry_attempts': 3
            },
            'proxies': [
                "proxy1.example.com:8080",
                "proxy2.example.com:8080",
                "proxy3.example.com:8080"
            ]
        }
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in configuration file: {e}")

def get_worker_config() -> Dict[str, Any]:
    """Get worker configuration including proxy list"""
    config = load_config()
    return {
        'worker_id': os.getenv('WORKER_ID', f'worker_{os.getpid()}'),
        'proxy_ips': config.get('proxies', []),
        'kafka_topic': config['worker'].get('kafka_topic', 'http_requests'),
        'kafka_bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'request_timeout': config['worker'].get('request_timeout', 30),
        'retry_attempts': config['worker'].get('retry_attempts', 3)
    } 