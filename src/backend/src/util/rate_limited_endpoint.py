import atexit
from fastapi import Depends
from flask import Flask, request, jsonify
from backend.src.util.rate_limiter import RateLimiter
import os
from dotenv import load_dotenv
import time

load_dotenv()

# Redis configuration
REDIS_HOST=os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT=os.getenv('REDIS_PORT', 6379)


def get_rate_limiter():
    limiter = RateLimiter(
        redis_host=os.getenv('REDIS_HOST', 'localhost'),
        redis_port=int(os.getenv('REDIS_PORT', 6379))
    )
    return limiter 

#Simple echo endpoint to test rate limit
def create_app(endpoint_key="default"):
    app = Flask(__name__)
    rate_limiter = get_rate_limiter()

    @app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE'])
    def echo():
        # Rate limit check
        client_ip = request.remote_addr
        if not rate_limiter.is_allowed(
            key=f"endpoint:{client_ip}",
            tokens_per_second=1.0,  # 1 request per second
            bucket_size=5
        ):
            return jsonify({
                "error": "Rate limit exceeded",
                "retry_after": "1 second",
                "endpoint_key": endpoint_key
            }), 429
        
        # Reflect back request data with endpoint key
        return jsonify({
            "method": request.method,
            "headers": dict(request.headers),
            "data": request.get_json(silent=True),
            "args": request.args,
            "client_ip": client_ip,
            "timestamp": time.time(),
            "endpoint_key": endpoint_key
        })

    @app.route('/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "timestamp": time.time(),
            "endpoint_key": endpoint_key
        })

    return app

if __name__ == '__main__':
    rate_limiter = RateLimiter(REDIS_HOST, REDIS_PORT)
    atexit.register(rate_limiter.close)
    app = create_app(rate_limiter)

    port = int(os.getenv('TEST_ENDPOINT_PORT', 5001))
    app.run(host='0.0.0.0', port=port)
