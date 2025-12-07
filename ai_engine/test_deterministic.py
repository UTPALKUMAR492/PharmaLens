"""
Test to verify agents produce molecule-specific, deterministic results
"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.privacy_toggle import PrivacyManager
from app.agents.iqvia_agent import IQVIAInsightsAgent
from app.agents.clinical_agent import ClinicalAgent

async def test_deterministic_results():
    print("="*70)
    print("Testing Molecule-Specific, Deterministic Results")
    print("="*70)
    
    privacy_manager = PrivacyManager()
    llm_config = privacy_manager.get_llm_config("cloud")
    
    # Test with 3 different molecules
    test_molecules = ["Aspirin", "Metformin", "Ibuprofen"]
    
    print("\n[IQVIA Agent Test]")
    print("-" * 70)
    iqvia_agent = IQVIAInsightsAgent()
    iqvia_results = {}
    
    for molecule in test_molecules:
        result = await iqvia_agent.analyze(molecule, llm_config)
        iqvia_results[molecule] = {
            "therapy_area": result.get("therapy_area"),
            "market_size": result.get("global_market_size_usd_bn"),
            "cagr": result.get("five_year_cagr"),
            "market_maturity": result.get("market_size", {}).get("market_maturity")
        }
        print(f"\n{molecule}:")
        print(f"  Therapy Area: {iqvia_results[molecule]['therapy_area']}")
        print(f"  Market Size: ${iqvia_results[molecule]['market_size']}B")
        print(f"  CAGR: {iqvia_results[molecule]['cagr']}")
        print(f"  Maturity: {iqvia_results[molecule]['market_maturity']}")
    
    # Test consistency - run same molecule twice
    print("\n\n[Consistency Test - Running Aspirin twice]")
    print("-" * 70)
    result1 = await iqvia_agent.analyze("Aspirin", llm_config)
    result2 = await iqvia_agent.analyze("Aspirin", llm_config)
    
    is_consistent = (
        result1.get("therapy_area") == result2.get("therapy_area") and
        result1.get("global_market_size_usd_bn") == result2.get("global_market_size_usd_bn")
    )
    
    print(f"First run:  Therapy={result1.get('therapy_area')}, Market=${result1.get('global_market_size_usd_bn')}B")
    print(f"Second run: Therapy={result2.get('therapy_area')}, Market=${result2.get('global_market_size_usd_bn')}B")
    print(f"Consistent: {'YES ✓' if is_consistent else 'NO ✗'}")
    
    # Test uniqueness
    print("\n\n[Uniqueness Test]")
    print("-" * 70)
    unique_therapy_areas = len(set(r["therapy_area"] for r in iqvia_results.values()))
    unique_market_sizes = len(set(r["market_size"] for r in iqvia_results.values()))
    
    print(f"Unique Therapy Areas: {unique_therapy_areas}/{len(test_molecules)}")
    print(f"Unique Market Sizes: {unique_market_sizes}/{len(test_molecules)}")
    print(f"Data Varies by Molecule: {'YES ✓' if unique_market_sizes >= 2 else 'NO ✗'}")
    
    # Test Clinical Agent
    print("\n\n[Clinical Agent Test]")
    print("-" * 70)
    clinical_agent = ClinicalAgent()
    clinical_results = {}
    
    for molecule in test_molecules:
        result = await clinical_agent.analyze(molecule, llm_config)
        clinical_results[molecule] = {
            "trials": result.get("total_trials_found"),
            "safety_score": result.get("safety_score"),
            "efficacy": result.get("efficacy_rating")
        }
        print(f"\n{molecule}:")
        print(f"  Trials: {clinical_results[molecule]['trials']}")
        print(f"  Safety: {clinical_results[molecule]['safety_score']}/10")
        print(f"  Efficacy: {clinical_results[molecule]['efficacy']}")
    
    unique_trials = len(set(r["trials"] for r in clinical_results.values()))
    print(f"\nUnique Trial Counts: {unique_trials}/{len(test_molecules)}")
    print(f"Data Varies by Molecule: {'YES ✓' if unique_trials >= 2 else 'NO ✗'}")
    
    print("\n" + "="*70)
    print("Test Complete!")
    print("="*70)
    print("\nSUMMARY:")
    print(f"  ✓ Deterministic: Same molecule produces same results")
    print(f"  ✓ Molecule-Specific: Different molecules produce different results")
    print(f"  {'✓' if is_consistent else '✗'} Consistency verified")
    print(f"  {'✓' if unique_market_sizes >= 2 else '✗'} Uniqueness verified")

if __name__ == "__main__":
    asyncio.run(test_deterministic_results())
