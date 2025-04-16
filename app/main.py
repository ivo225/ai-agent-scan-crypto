from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.db.database import init_db
# Import routers
from app.routers import chat_router # Import the new chat router
# from app.routers import coin_routes, analysis_routes, report_routes # Keep others commented for now

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle application startup and shutdown events.
    Initializes the database on startup.
    """
    print("Application startup: Initializing database...")
    # You might want to make DB initialization optional or controlled via CLI/env var
    # await init_db()
    print("Database initialization skipped on startup (use CLI 'setup-db' command).")
    yield
    # Clean up resources on shutdown if needed
    print("Application shutdown.")

app = FastAPI(
    title="Crypto Analyzer API",
    description="API for analyzing cryptocurrency data using various sources.",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint providing basic API information.
    """
    return {"message": "Welcome to the Crypto Analyzer API!"}

# Include routers (uncomment when created)
# Include the chat router
app.include_router(chat_router.router, prefix="/api", tags=["Chat"])

# Include other routers (uncomment when created)
# app.include_router(coin_routes.router, prefix="/coins", tags=["Coins"])
# app.include_router(analysis_routes.router, prefix="/analysis", tags=["Analysis"])
# app.include_router(report_routes.router, prefix="/reports", tags=["Reports"])

# Add middleware later if needed (e.g., for logging, CORS)
