import os
import httpx
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
HELIUS_API_BASE_URL = "https://api.helius.xyz/v0" # Verify this base URL

async def get_helius_token_metadata(mint_address: str) -> Optional[Dict[str, Any]]:
    """
    Fetches token metadata from Helius API for a given mint address (Solana).

    Args:
        mint_address: The mint address of the Solana token.

    Returns:
        A dictionary containing the token metadata if successful, None otherwise.
        Raises httpx.HTTPStatusError for API errors (4xx, 5xx).
    """
    if not HELIUS_API_KEY:
        print("Warning: HELIUS_API_KEY not found in environment variables. Skipping Helius fetch.")
        return None

    # Example endpoint: Get token metadata. Adjust endpoint/params as needed.
    api_url = f"{HELIUS_API_BASE_URL}/token-metadata"
    params = {
        "api-key": HELIUS_API_KEY,
        "mintAccounts": [mint_address] # API expects a list
    }

    async with httpx.AsyncClient() as client:
        try:
            # Helius might use POST for this endpoint, check their docs
            response = await client.post(api_url, json=params) # Assuming POST based on common patterns
            # If it's GET: response = await client.get(api_url, params=params)
            response.raise_for_status()

            data = response.json()
            # Helius API might return a list, even for one token
            if isinstance(data, list) and len(data) > 0:
                return data[0] # Return the first result
            elif isinstance(data, dict): # Handle case where it might return a single dict
                 return data
            else:
                print(f"No Helius metadata found for mint address {mint_address}.")
                return None

        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching Helius data for {mint_address}: {e.response.status_code} - {e.response.text}")
            # Handle specific errors (e.g., 401 Unauthorized)
            raise e # Re-raise for now
        except httpx.RequestError as e:
            print(f"Network error fetching Helius data for {mint_address}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred fetching Helius data for {mint_address}: {e}")
            return None

# Example usage (can be removed or moved to CLI/tests)
# import asyncio
# async def main():
#     # Example Solana token mint address (e.g., Bonk) - replace with actual
#     bonk_mint = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
#     metadata = await get_helius_token_metadata(bonk_mint)
#     if metadata:
#         print(f"\n--- Helius Metadata for {bonk_mint} ---")
#         print(metadata)
#     else:
#         print(f"Could not get Helius metadata for {bonk_mint}.")
#
# if __name__ == "__main__":
#     asyncio.run(main())
