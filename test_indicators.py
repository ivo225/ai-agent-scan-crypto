import asyncio
from app.services.technical_analysis_service import get_technical_analysis
from app.utils.confidence import calculate_confidence_score

async def main():
    print("Testing enhanced technical analysis...")
    
    # Test with Bitcoin
    coin_id = "bitcoin"
    print(f"Analyzing {coin_id}...")
    
    # Get technical analysis
    ta_results = await get_technical_analysis(coin_id, days=90)
    
    if ta_results:
        # Extract indicators and confidence data
        indicators = {k: v for k, v in ta_results.items() if k != 'confidence'}
        confidence = ta_results.get('confidence', {})
        
        # Print all indicators
        print("\nTechnical Indicators:")
        for key, value in indicators.items():
            print(f"{key}: {value}")
        
        # Print confidence data
        print("\nConfidence Analysis:")
        print(f"Overall Score: {confidence.get('overall_score')}")
        print(f"Direction: {confidence.get('direction')}")
        print(f"Signal: {confidence.get('signal')}")
        
        # Print supporting and conflicting indicators
        print("\nSupporting Indicators:")
        for indicator in confidence.get('supporting_indicators', []):
            print(f"- {indicator}")
        
        print("\nConflicting Indicators:")
        for indicator in confidence.get('conflicting_indicators', []):
            print(f"- {indicator}")
        
        # Print factor scores
        print("\nFactor Scores:")
        for factor, score in confidence.get('factor_scores', {}).items():
            print(f"{factor}: {score}")
    else:
        print("Failed to get technical analysis results")

if __name__ == "__main__":
    asyncio.run(main())
