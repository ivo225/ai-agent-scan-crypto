# Crypto Analyzer API

This project provides a FastAPI-based API for analyzing cryptocurrency data using various sources like CoinGecko, CryptoPanic, DeepSeek AI, Perplexity AI, Binance (for market data), Helius (for Solana data), and technical indicators. It includes a chat interface for interacting with the analysis features.

## Prerequisites

*   Python 3.10+
*   pip (Python package installer)
*   Git

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ivo225/ai-agent-scan-crypto.git
    cd ai-agent-scan-crypto
    ```

2.  **Create and activate a virtual environment:**
    *   On macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Create a `.env` file:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Open the `.env` file in a text editor and add your API keys. You **must** provide keys for:
    *   `CRYPTO_PANIC_API_KEY`: Get from [CryptoPanic API](https://cryptopanic.com/developers/api/) (for news sentiment)
    *   `DEEPSEEK_API_KEY`: Get from [DeepSeek Platform](https://platform.deepseek.com/) (for AI-driven analysis/chat)
    *   `PERPLEXITY_API_KEY`: Get from [Perplexity Labs](https://docs.perplexity.ai/docs/getting-started) (for alternative AI analysis/chat)
    *   `BINANCE_API_KEY` & `BINANCE_SECRET_KEY`: Get from your [Binance Account](https://www.binance.com/en/my/settings/api-management) (for market data like price, volume, klines)
    *   `HELIUS_API_KEY`: Get from [Helius](https://helius.dev/) (for Solana-specific on-chain data)

    *Note: CoinGecko API is used for general coin information and market data and does not require an API key for the free tier.*

    The `DATABASE_URL` defaults to a local SQLite file (`sqlite+aiosqlite:///./crypto_analysis.db`) and usually doesn't need changing for local use.

## Database Setup

Before running the application for the first time, initialize the database schema:

```bash
python -m app.cli setup-db
```
This command creates the `crypto_analysis.db` file (if it doesn't exist) and sets up the necessary tables (e.g., `coin_reports`).

## Running the Application

To start the FastAPI server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

*   `--reload`: Enables auto-reloading on code changes (useful for development).
*   `--host 0.0.0.0`: Makes the server accessible on your local network.
*   `--port 8000`: Specifies the port.

The API will be available at `http://localhost:8000` or `http://<your-local-ip>:8000`.

## Usage

### API

*   **Interactive Documentation (Swagger UI):** Open `http://localhost:8000/docs` in your browser to see all available API endpoints, test them, and view request/response models.
*   **Chat Endpoint (`/api/chat`):** Use this endpoint (via Swagger UI or tools like `curl`/Postman) to interact with the analysis bot. Send a POST request with a JSON body like:
    ```json
    {
      "message": "analyze bitcoin",
      "session_id": "user123"
    }
    ```

### Command Line Interface (CLI)

The project also includes a basic CLI for certain actions (like database setup). You can explore available commands:

```bash
python -m app.cli --help
