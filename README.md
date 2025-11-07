# Books Crawler - Production-Grade Web Crawling System

A production-ready web crawling system for monitoring and serving data from books.toscrape.com. Built with Python, MongoDB, FastAPI, and async/await patterns.

## Features

- **Robust Web Crawling**: Async crawling with retry logic, rate limiting, and error handling
- **Change Detection**: Automatic detection of new books and price/availability changes
- **Scheduled Updates**: Daily automated crawls with APScheduler
- **RESTful API**: FastAPI-based API with authentication and rate limiting
- **MongoDB Storage**: Efficient NoSQL storage with proper indexing
- **Production Ready**: Comprehensive logging, error handling, and Docker support

## Tech Stack

- **Python 3.11+**: Modern Python with async/await
- **MongoDB**: NoSQL database with Motor (async driver)
- **FastAPI**: Modern async REST API framework
- **APScheduler**: Task scheduling for automated crawls
- **Pydantic v2**: Data validation and settings management
- **httpx**: Async HTTP client
- **BeautifulSoup4**: HTML parsing

## Prerequisites

- Python 3.11 or higher
- MongoDB 7.0 or higher (or Docker)
- Docker and Docker Compose (optional, for containerized deployment)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Web_Crawler
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For development:

```bash
pip install -r requirements-dev.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=books_crawler
API_KEYS=your-api-key-here,another-key
# ... other settings
```

## Running the Application

### Option 1: Docker Compose (Recommended)

```bash
docker-compose up -d
```

This starts:
- MongoDB on port 27017
- API server on port 8000
- Scheduler service (runs daily at 2 AM)
- One-time crawler run

### Option 2: Manual Execution

#### Start MongoDB

```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:7

# Or install MongoDB locally and start the service
```

#### Run Crawler

```bash
python -m crawler.main
```

#### Run Scheduler

```bash
python -m scheduler.main
```

#### Run API Server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the API is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication

All API endpoints require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/books
```

### Endpoints

#### GET /books

Get paginated list of books with filtering and sorting.

**Query Parameters:**
- `category` (optional): Filter by category
- `min_price` (optional): Minimum price filter
- `max_price` (optional): Maximum price filter
- `rating` (optional): Filter by rating (One, Two, Three, Four, Five)
- `sort_by` (optional): Sort field (name, price, rating, reviews)
- `page` (default: 1): Page number
- `limit` (default: 20, max: 100): Items per page

**Example:**

```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8000/books?category=Fiction&min_price=10&max_price=50&sort_by=price&page=1&limit=20"
```

#### GET /books/{book_id}

Get detailed information about a specific book.

**Example:**

```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8000/books/507f1f77bcf86cd799439011"
```

#### GET /changes

Get recent changes (new books, price changes, etc.).

**Query Parameters:**
- `since` (optional): ISO datetime to filter changes
- `change_type` (optional): Filter by change type (new, price_change, availability_change)
- `limit` (default: 50): Items per page
- `page` (default: 1): Page number

**Example:**

```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8000/changes?since=2024-01-01T00:00:00Z&change_type=price_change"
```

#### GET /health

Health check endpoint (no authentication required).

```bash
curl http://localhost:8000/health
```

## Configuration

All configuration is done via environment variables (see `.env.example`):

### MongoDB Configuration
- `MONGODB_URL`: MongoDB connection URL
- `MONGODB_DB_NAME`: Database name

### API Configuration
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)
- `API_KEYS`: Comma-separated list of valid API keys
- `API_RATE_LIMIT`: Requests per hour per API key (default: 100)

### Crawler Configuration
- `CRAWLER_BASE_URL`: Target website URL
- `CRAWLER_MAX_CONCURRENT_REQUESTS`: Max concurrent requests (default: 10)
- `CRAWLER_REQUEST_TIMEOUT`: Request timeout in seconds (default: 30)
- `CRAWLER_MAX_RETRIES`: Maximum retry attempts (default: 3)

### Scheduler Configuration
- `SCHEDULER_CRAWL_SCHEDULE_HOUR`: Hour to run daily crawl (0-23, default: 2)
- `SCHEDULER_CRAWL_SCHEDULE_MINUTE`: Minute to run daily crawl (0-59, default: 0)
- `SCHEDULER_TIMEZONE`: Timezone (default: UTC)

## Database Schema

### Books Collection

```javascript
{
  "_id": ObjectId,
  "name": "Book Title",
  "description": "Book description...",
  "category": "Fiction",
  "price_excl_tax": 45.17,
  "price_incl_tax": 51.77,
  "availability": "In stock (22 available)",
  "num_reviews": 0,
  "image_url": "https://books.toscrape.com/media/cache/...",
  "rating": "Five",
  "source_url": "https://books.toscrape.com/catalogue/...",
  "crawl_timestamp": ISODate("2024-01-01T00:00:00Z"),
  "status": "active",
  "content_hash": "sha256_hash_string",
  "raw_html": "<html>...</html>"
}
```

### Changes Collection

```javascript
{
  "_id": ObjectId,
  "book_id": ObjectId,
  "book_name": "Book Title",
  "change_type": "price_change",
  "field_name": "price_incl_tax",
  "old_value": "50.00",
  "new_value": "51.77",
  "detected_at": ISODate("2024-01-01T00:00:00Z")
}
```

### Crawler State Collection

```javascript
{
  "_id": "crawler_state",
  "last_page": 50,
  "last_run": ISODate("2024-01-01T00:00:00Z"),
  "status": "idle",
  "total_books_crawled": 1000
}
```

## Testing

### Run Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/
```

## Project Structure

```
book-crawler/
├── config/           # Configuration management
├── crawler/          # Web crawler implementation
├── scheduler/        # Scheduled tasks and change detection
├── api/              # FastAPI REST API
├── database/         # MongoDB layer and repositories
├── utils/            # Utility functions
├── tests/            # Test suite
├── logs/             # Log files
└── reports/          # Daily reports
```

## Troubleshooting

### MongoDB Connection Issues

- Ensure MongoDB is running: `docker ps` or check MongoDB service
- Verify connection URL in `.env`
- Check MongoDB logs: `docker logs mongodb`

### API Authentication Errors

- Verify API key is set in `.env` (`API_KEYS`)
- Check API key header name matches (`X-API-Key` by default)
- Ensure API key is included in request headers

### Crawler Not Starting

- Check MongoDB connection
- Verify base URL is accessible
- Review logs in `logs/crawler.log`

### Rate Limiting

- Default limit is 100 requests/hour per API key
- Adjust `API_RATE_LIMIT` in `.env` if needed
- Check rate limit headers in API responses

## Development

### Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Type checking
mypy .

# Linting
flake8 .
pylint .
```

### Pre-commit Hooks

Install pre-commit hooks:

```bash
pre-commit install
```

## Deployment

### Production Considerations

1. **Security**:
   - Use strong API keys
   - Enable HTTPS
   - Restrict CORS origins
   - Use environment variables for secrets

2. **Performance**:
   - Adjust MongoDB connection pool size
   - Configure appropriate concurrent request limits
   - Monitor database indexes

3. **Monitoring**:
   - Set up log aggregation
   - Monitor API response times
   - Track crawler success rates
   - Alert on errors

## License

MIT License

## Contact

For questions or issues, contact: sudipto@filerskeepers.co

