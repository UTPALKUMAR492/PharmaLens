"""
PharmaLens LLM Integration Test Suite
======================================
Tests LLM integration across all agents in both cloud and local modes.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.privacy_toggle import PrivacyManager
from app.agents.iqvia_agent import IQVIAInsightsAgent
from app.agents.clinical_agent import ClinicalAgent
from app.services.llm_service import get_llm_service
import structlog

logger = structlog.get_logger(__name__)

# Test drugs with known profiles
TEST_DRUGS = [
    {"name": "Aspirin", "expected_therapy": "cardiology", "description": "Classic NSAID for cardiovascular protection"},
    {"name": "Metformin", "expected_therapy": "metabolic", "description": "First-line diabetes medication"},
    {"name": "Keytruda", "expected_therapy": "oncology", "description": "PD-1 inhibitor for cancer immunotherapy"},
    {"name": "Humira", "expected_therapy": "immunology", "description": "TNF inhibitor for autoimmune diseases"}
]


async def test_llm_service():
    """Test basic LLM service functionality"""
    print("\n" + "="*60)
    print("TEST 1: LLM Service Basic Functionality")
    print("="*60)
    
    llm_service = get_llm_service()
    privacy_manager = PrivacyManager()
    
    # Test cloud mode
    try:
        print("\n[Cloud Mode Test]")
        cloud_config = privacy_manager.get_llm_config("cloud")
        
        if not cloud_config.get("api_key"):
            print("⚠️  OpenAI API key not configured - skipping cloud test")
            print("   Set OPENAI_API_KEY in .env to test cloud mode")
        else:
            response = await llm_service.generate_completion(
                prompt="What is aspirin used for in pharmaceutical medicine? Answer in one sentence.",
                llm_config=cloud_config,
                temperature=0.3,
                max_tokens=100
            )
            print(f"✓ Cloud LLM Response: {response[:150]}...")
    except Exception as e:
        print(f"✗ Cloud mode failed: {e}")
    
    # Test local mode (will fail without model file)
    try:
        print("\n[Local Mode Test]")
        local_config = privacy_manager.get_llm_config("secure")
        
        if not local_config.get("model_path"):
            print("⚠️  Local model path not configured - skipping local test")
            print("   Set LOCAL_MODEL_PATH in .env to test local mode")
        else:
            response = await llm_service.generate_completion(
                prompt="What is metformin used for? Answer in one sentence.",
                llm_config=local_config,
                temperature=0.3,
                max_tokens=100
            )
            print(f"✓ Local LLM Response: {response[:150]}...")
    except Exception as e:
        print(f"⚠️  Local mode not available: {e}")
        print("   This is expected if llama model is not downloaded")


async def test_iqvia_agent(drug_info: dict, mode: str):
    """Test IQVIA agent with LLM integration"""
    print(f"\n[IQVIA Agent - {drug_info['name']} - {mode.upper()} mode]")
    
    agent = IQVIAInsightsAgent()
    privacy_manager = PrivacyManager()
    llm_config = privacy_manager.get_llm_config(mode)
    
    try:
        result = await agent.analyze(drug_info['name'], llm_config)
        
        # Verify LLM-specific fields exist
        has_llm_insights = "market_intelligence_summary" in result
        has_competitive_intel = "competitive_intelligence" in result
        has_strategic_insights = "strategic_insights" in result
        
        print(f"  Therapy Area: {result.get('therapy_area', 'N/A')}")
        print(f"  Market Size: ${result.get('global_market_size_usd_bn', 'N/A')}B")
        print(f"  CAGR: {result.get('five_year_cagr', 'N/A')}")
        print(f"  LLM Summary Present: {'✓' if has_llm_insights else '✗'}")
        print(f"  Strategic Insights: {'✓' if has_strategic_insights else '✗'}")
        print(f"  Model Used: {result.get('model_used', 'N/A')}")
        print(f"  Provider: {result.get('llm_provider', 'N/A')}")
        
        if has_llm_insights:
            summary = result.get('market_intelligence_summary', '')
            print(f"  Summary Preview: {summary[:100]}...")
        
        return result
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


async def test_clinical_agent(drug_info: dict, mode: str):
    """Test Clinical agent with LLM integration"""
    print(f"\n[Clinical Agent - {drug_info['name']} - {mode.upper()} mode]")
    
    agent = ClinicalAgent()
    privacy_manager = PrivacyManager()
    llm_config = privacy_manager.get_llm_config(mode)
    
    try:
        result = await agent.analyze(drug_info['name'], llm_config)
        
        # Verify LLM-specific fields exist
        has_clinical_summary = "clinical_summary" in result
        has_safety_interp = "safety_interpretation" in result
        has_recommendations = "development_recommendations" in result
        
        print(f"  Total Trials: {result.get('total_trials_found', 'N/A')}")
        print(f"  Safety Score: {result.get('safety_score', 'N/A')}/10")
        print(f"  Efficacy: {result.get('efficacy_rating', 'N/A')}")
        print(f"  LLM Clinical Summary: {'✓' if has_clinical_summary else '✗'}")
        print(f"  Safety Interpretation: {'✓' if has_safety_interp else '✗'}")
        print(f"  Recommendations: {'✓' if has_recommendations else '✗'}")
        print(f"  Model Used: {result.get('model_used', 'N/A')}")
        
        if has_clinical_summary:
            summary = result.get('clinical_summary', '')
            print(f"  Summary Preview: {summary[:100]}...")
        
        return result
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


async def test_drug_specificity():
    """Test that different drugs produce different, specific results"""
    print("\n" + "="*60)
    print("TEST 2: Drug-Specific Response Verification")
    print("="*60)
    
    privacy_manager = PrivacyManager()
    cloud_config = privacy_manager.get_llm_config("cloud")
    
    if not cloud_config.get("api_key"):
        print("\n⚠️  Skipping drug specificity test - OpenAI API key not configured")
        return
    
    agent = IQVIAInsightsAgent()
    
    results = {}
    for drug in TEST_DRUGS[:2]:  # Test first 2 drugs
        try:
            result = await agent.analyze(drug['name'], cloud_config)
            therapy_area = result.get('therapy_area', 'Unknown')
            summary = result.get('market_intelligence_summary', '')
            
            results[drug['name']] = {
                "therapy_area": therapy_area,
                "summary": summary,
                "expected": drug['expected_therapy']
            }
            
            print(f"\n{drug['name']}:")
            print(f"  Expected Therapy: {drug['expected_therapy']}")
            print(f"  Detected Therapy: {therapy_area}")
            print(f"  Match: {'✓' if drug['expected_therapy'] in therapy_area.lower() else '⚠️'}")
            print(f"  Summary Length: {len(summary)} chars")
            
        except Exception as e:
            print(f"  ✗ Error analyzing {drug['name']}: {e}")
    
    # Check uniqueness
    if len(results) >= 2:
        drug_names = list(results.keys())
        summary1 = results[drug_names[0]]['summary']
        summary2 = results[drug_names[1]]['summary']
        
        # Simple uniqueness check
        similarity = len(set(summary1.split()) & set(summary2.split())) / max(len(summary1.split()), len(summary2.split()))
        print(f"\nSummary Uniqueness Test:")
        print(f"  Word Overlap: {similarity*100:.1f}%")
        print(f"  Unique Responses: {'✓' if similarity < 0.7 else '⚠️  (Too similar!)'}")


async def main():
    """Run complete test suite"""
    print("\n" + "="*60)
    print("PharmaLens LLM Integration Test Suite")
    print("="*60)
    print("\nThis test suite verifies:")
    print("1. LLM service works in both cloud and local modes")
    print("2. Agents produce LLM-enhanced insights")
    print("3. Drug-specific results are generated (not generic)")
    print("4. Both OpenAI and Llama configurations are valid")
    
    # Test 1: Basic LLM service
    await test_llm_service()
    
    # Test 2: IQVIA agent with one drug (cloud mode)
    print("\n" + "="*60)
    print("TEST 2: IQVIA Agent Integration")
    print("="*60)
    await test_iqvia_agent(TEST_DRUGS[0], "cloud")
    
    # Test 3: Clinical agent with one drug (cloud mode)
    print("\n" + "="*60)
    print("TEST 3: Clinical Agent Integration")
    print("="*60)
    await test_clinical_agent(TEST_DRUGS[1], "cloud")
    
    # Test 4: Drug specificity
    await test_drug_specificity()
    
    print("\n" + "="*60)
    print("Test Suite Complete")
    print("="*60)
    print("\nNext Steps:")
    print("1. If cloud tests passed: LLM integration is working!")
    print("2. If local tests failed: Download Llama model and set LOCAL_MODEL_PATH")
    print("3. Update remaining agents (Web Intelligence, Regulatory, etc.)")
    print("4. Test full orchestrator with all agents")
    print("\nTo run full system test:")
    print("  python -m pytest tests/ -v")


if __name__ == "__main__":
    asyncio.run(main())
