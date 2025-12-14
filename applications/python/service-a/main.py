import os
import time
import random
import asyncio
import requests
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from prometheus_client import (
    Counter,
    Histogram,
    Summary,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST
)

from loguru import logger

# Load env variables
load_dotenv()

app = FastAPI(title="Service A")

PORT = 3001
SERVICE_B_URI = os.getenv("SERVICE_B_URI")

# -------------------------
# Logging
# -------------------------
def logging_example():
    logger.info("Here are the logs")
    logger.info("Please have a look")
    logger.info("This is just for testing")

# -------------------------
# Prometheus Metrics
# -------------------------
http_request_counter = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status_code"]
)

request_duration_histogram = Histogram(
    "http_request_duration_seconds",
    "Duration of HTTP requests in seconds",
    ["method", "path", "status_code"],
    buckets=(0.1, 0.5, 1, 5, 10)
)

request_duration_summary = Summary(
    "http_request_duration_summary_seconds",
    "Summary of HTTP request durations",
    ["method", "path", "status_code"]
)

gauge = Gauge(
    "node_gauge_example",
    "Example gauge tracking async task duration",
    ["method", "status"]
)

# -------------------------
# Middleware (metrics)
# -------------------------
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    method = request.method
    path = request.url.path
    status_code = response.status_code

    http_request_counter.labels(method, path, status_code).inc()
    request_duration_histogram.labels(method, path, status_code).observe(duration)
    request_duration_summary.labels(method, path, status_code).observe(duration)

    return response

# -------------------------
# Routes
# -------------------------
@app.get("/")
async def root():
    return {"status": "🏃- Running"}

@app.get("/healthy")
async def healthy():
    return {
        "name": "👀 - Observability 🔥 - Abhishek Veeramalla",
        "status": "healthy"
    }

@app.get("/serverError")
async def server_error():
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "statusCode": 500}
    )

@app.get("/notFound")
async def not_found():
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "statusCode": 404}
    )

@app.get("/logs")
async def logs():
    logging_example()
    return {"objective": "To generate logs"}

@app.get("/crash")
async def crash():
    logger.error("Intentionally crashing the server...")
    os._exit(1)

# -------------------------
# Async task + Gauge
# -------------------------
async def simulate_async_task():
    await asyncio.sleep(random.uniform(0, 5))

@app.get("/example")
async def example(request: Request):
    with gauge.labels(request.method, "running").time():
        await simulate_async_task()
    return PlainTextResponse("Async task completed")

# -------------------------
# Prometheus Metrics Endpoint
# -------------------------
@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# -------------------------
# Call Service B
# -------------------------
@app.get("/call-service-b")
async def call_service_b():
    try:
        response = requests.get(f"{SERVICE_B_URI}/hello", timeout=5)
        return PlainTextResponse(
            f"Service B says: {response.text}"
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=500,
            content={"error": "Error communicating with Service B"}
        )
