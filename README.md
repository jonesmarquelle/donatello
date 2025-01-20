[Sonnet kinda snapped on the readme, god bless her]

# Donatello 🧂🌶️

A scalable HTTP request queueing and processing system built with Python, FastAPI, Kafka, and PostgreSQL.

## Features

- Asynchronous HTTP request processing
- Request queueing with Kafka
- Job status tracking and management
- Response handling and storage
- Scalable worker architecture
- Docker containerization
- Comprehensive test suite

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Kafka
- PostgreSQL

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/jonesmarquelle/donatello.git
cd donatello
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start the services using Docker Compose:
```bash
docker-compose up -d
```

4. The service will be available at:
- API Server: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run tests:
```bash
.\run_tests.bat  # On Windows
```

## Project Structure

```
http_queue/
├── config/              # Configuration files
├── src/
│   └── backend/
│       ├── src/
│       │   ├── db/     # Database models and sessions
│       │   ├── server/ # API endpoints
│       │   ├── util/   # Utility functions
│       │   └── worker/ # Worker implementation
│       └── test/       # Test suite
└── docker-compose.yml  # Docker composition
```

## API Documentation

The API documentation is available at `/docs` when the server is running. It provides detailed information about all available endpoints and their usage.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 
