import asyncio
from app.cli import run_analysis

async def main():
    print("Testing CLI analysis...")

    # Test with Solana
    coin_id = "solana"
    print(f"Analyzing {coin_id}...")

    # Run the analysis
    await run_analysis(coin_id)

if __name__ == "__main__":
    asyncio.run(main())
