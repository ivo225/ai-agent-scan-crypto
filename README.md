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

## Running the Interactive CLI Chat

To start the interactive chat interface directly in your terminal:

```bash
# Ensure your virtual environment is active
# source venv/bin/activate  (or .\venv\Scripts\activate on Windows)

python -m app.cli
```

This will launch the chat prompt where you can interact with the analysis bot (e.g., using `/analyze <symbol_or_id>`). Type `/exit` or `/quit` to leave the chat.

## Running the API Server (Optional)

If you want to expose the functionality via an HTTP API (e.g., for integration with other applications or using the Swagger UI), run the FastAPI server using Uvicorn:

```bash
# Ensure your virtual environment is active
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

*   `--reload`: Enables auto-reloading on code changes (useful for development).
*   `--host 0.0.0.0`: Makes the server accessible on your local network.
*   `--port 8000`: Specifies the port.

When the server is running, the API will be available at `http://localhost:8000` or `http://<your-local-ip>:8000`.

## Usage

### Command Line Interface (CLI)

The application provides a command-line interface for direct interaction and management tasks. Ensure your virtual environment is active before running these commands.

*   **Start Interactive Chat (Default):**
    ```bash
    python -m app.cli
    ```
    *   Starts an interactive session.
    *   Use `/analyze <symbol_or_id>` (e.g., `/analyze bitcoin` or `/analyze btc`) to get a detailed analysis of a cryptocurrency.
    *   Use `/exit` or `/quit` to end the session.
    *   Any other input is treated as a chat message for the AI.

*   **Database Setup:**
    ```bash
    python -m app.cli setup-db
    ```
    *   Initializes the database schema. **Warning:** This might drop existing tables if they exist.

*   **Cache Management:**
    *   Show statistics:
        ```bash
        python -m app.cli cache-stats
        ```
    *   Clear all caches:
        ```bash
        python -m app.cli cache-clear
        ```
    *   Clear a specific namespace:
        ```bash
        python -m app.cli cache-clear <namespace>
        ```
        *(Example: `python -m app.cli cache-clear coingecko`)*
    *   Set TTL for a namespace:
        ```bash
        python -m app.cli cache-ttl <namespace> <seconds>
        ```
        *(Example: `python -m app.cli cache-ttl coingecko 3600`)*

*   **Help:**
    ```bash
    python -m app.cli --help
    ```
    *   Displays a summary of all available commands.


### API (When running Uvicorn)

*   **Interactive Documentation (Swagger UI):** Open `http://localhost:8000/docs` in your browser to see all available API endpoints, test them, and view request/response models.
*   **Chat Endpoint (`/api/chat`):** Use this endpoint (via Swagger UI or tools like `curl`/Postman) to interact with the analysis bot. Send a POST request with a JSON body like:
    ```json
    {
      "message": "analyze bitcoin",
      "session_id": "user123" # A unique ID for the chat session
    }
    ```
