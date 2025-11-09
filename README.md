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
# Database
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=books_crawler
MONGODB_MAX_POOL_SIZE=100
MONGODB_MIN_POOL_SIZE=10
MONGODB_SERVER_SELECTION_TIMEOUT_MS=5000
MONGODB_CONNECT_TIMEOUT_MS=2000
MONGODB_SOCKET_TIMEOUT_MS=10000
MONGODB_MAX_IDLE_TIME_MS=300000
MONGODB_TLS=false
MONGODB_TLS_ALLOW_INVALID_CERTIFICATES=false

# API
API_HOST=0.0.0.0
API_PORT=8000
API_API_KEYS=your-api-key-here,another-key
API_RATE_LIMIT=100
API_CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Crawler
CRAWLER_BASE_URL=https://books.toscrape.com
CRAWLER_MAX_CONCURRENT_REQUESTS=10
CRAWLER_REQUEST_TIMEOUT=30
CRAWLER_MAX_RETRIES=3
CRAWLER_RETRY_BACKOFF=2.0
CRAWLER_RECRAWL_INTERVAL_HOURS=12

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/crawler.log

# Scheduler / Alerts
SCHEDULER_ENABLE_EMAIL_ALERTS=false
SCHEDULER_SMTP_HOST=smtp.ethereal.email
SCHEDULER_SMTP_PORT=587
SCHEDULER_SMTP_USER=
SCHEDULER_SMTP_PASSWORD=
SCHEDULER_ALERT_EMAIL_TO=
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
- `MONGODB_MAX_POOL_SIZE`: Maximum connection pool size (default: 100)
- `MONGODB_MIN_POOL_SIZE`: Minimum connection pool size (default: 10)
- `MONGODB_SERVER_SELECTION_TIMEOUT_MS`: Server selection timeout in milliseconds (default: 5000)
- `MONGODB_CONNECT_TIMEOUT_MS`: Connection timeout in milliseconds (default: 2000)
- `MONGODB_SOCKET_TIMEOUT_MS`: Socket timeout in milliseconds (default: 10000)
- `MONGODB_MAX_IDLE_TIME_MS`: Maximum idle time for pooled connections in milliseconds (default: 300000)
- `MONGODB_TLS`: Enable TLS for MongoDB connection (default: false)
- `MONGODB_TLS_ALLOW_INVALID_CERTIFICATES`: Allow invalid TLS certificates (default: false)

### API Configuration
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)
- `API_KEYS`: Comma-separated list of valid API keys
- `API_RATE_LIMIT`: Requests per hour per API key (default: 100)
- `API_CORS_ORIGINS`: Comma-separated list of allowed origins

### Crawler Configuration
- `CRAWLER_BASE_URL`: Target website URL
- `CRAWLER_MAX_CONCURRENT_REQUESTS`: Max concurrent requests (default: 10)
- `CRAWLER_REQUEST_TIMEOUT`: Request timeout in seconds (default: 30)
- `CRAWLER_MAX_RETRIES`: Maximum retry attempts (default: 3)
- `CRAWLER_RETRY_BACKOFF`: Exponential backoff multiplier (default: 2.0)
- `CRAWLER_RECRAWL_INTERVAL_HOURS`: Minimum hours before re-crawling an unchanged book (default: 12)

### Scheduler Configuration
- `SCHEDULER_CRAWL_SCHEDULE_HOUR`: Hour to run daily crawl (0-23, default: 2)
- `SCHEDULER_CRAWL_SCHEDULE_MINUTE`: Minute to run daily crawl (0-59, default: 0)
- `SCHEDULER_TIMEZONE`: Timezone (default: UTC)
- `SCHEDULER_ENABLE_EMAIL_ALERTS`: Enable email alerts (default: false)
- `SCHEDULER_SMTP_HOST`: SMTP host (default: smtp.ethereal.email)
- `SCHEDULER_SMTP_PORT`: SMTP port (default: 587)
- `SCHEDULER_SMTP_USER`: SMTP username (blank by default; provide your own when enabling alerts)
- `SCHEDULER_SMTP_PASSWORD`: SMTP password (blank by default)
- `SCHEDULER_ALERT_EMAIL_TO`: Alert recipient address (blank by default)

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

## Repository Layer

### BookRepository (`database/repositories/book_repository.py`)
- `upsert_book(book: Book) -> str`: Inserts or updates a book and returns the document ID as a string. New/updated status is logged internally.
- `find_books(filters: dict, skip: int = 0, limit: int = 20, sort: Optional[List[tuple]] = None) -> List[Book]`: `sort` should be provided as a list of `(field, direction)` tuples compatible with Motor, e.g. `[("price_incl_tax", 1), ("rating", -1)]`.
- `count_books(filters: dict) -> int`: Returns the number of matching documents.
- Additional helpers such as `get_book_by_url`, `get_book_by_id`, and `update_book` expose common CRUD operations.

### ChangeRepository (`database/repositories/change_repository.py`)
- `log_change(...) -> str`: Records a change event and returns the change document ID.
- `get_recent_changes(since: datetime | None, limit: int) -> List[ChangeDocument]`: Retrieves recent changes sorted by newest first.
- `get_changes_by_book(book_id: str) -> List[ChangeDocument]`: Returns a book-specific change history.

### StateRepository (`database/repositories/state_repository.py`)
- `save_state(state: CrawlerState) -> bool`: Persists the crawler state (upsert).
- `get_last_state() -> Optional[CrawlerState]`: Fetches the latest crawler state snapshot.
- `update_last_page(page: int) -> bool`: Updates the checkpoint page and refreshes the timestamp.

## Testing

### Run Tests

```bash
# Unit tests
pytest tests/unit --cov=crawler --cov=utils --cov-report=term-missing

# Integration tests
pytest tests/integration --cov=database --cov=api --cov-append

# End-to-end tests
pytest tests/e2e --cov=crawler --cov=scheduler --cov-append

# Full suite with HTML coverage report
pytest --cov=. --cov-report=html
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


## Environment Configuration

1. Copy `.env.example` to `.env` and fill in any sensitive values:
   ```bash
   cp .env.example .env
   ```
   - `SCHEDULER_SMTP_*` controls email delivery for report/alert notifications. Leave these blank or point them to your own SMTP provider; Ethereal defaults are included as placeholders only.
   - Set `SCHEDULER_ENABLE_EMAIL_ALERTS=true` if you want emails sent; otherwise keep it `false`.

2. With Docker Compose, `.env` is automatically loaded by the app services, so secrets stay out of version control.
