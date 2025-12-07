"""
Quick test to verify all agents return complete data
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.privacy_toggle import PrivacyManager
from app.agents.iqvia_agent import IQVIAInsightsAgent
from app.agents.clinical_agent import ClinicalAgent
from app.agents.patent_agent import PatentAgent
from app.agents.regulatory_agent import RegulatoryComplianceAgent
from app.agents.patient_sentiment_agent import PatientSentimentAgent
from app.agents.esg_agent import ESGSustainabilityAgent
from app.agents.exim_agent import EXIMAgent
from app.agents.web_intelligence_agent import WebIntelligenceAgent
from app.agents.validation_agent import ValidationAgent

async def test_agent_completeness():
    print("=" * 60)
    print("Testing Agent Data Completeness")
    print("=" * 60)
    
    privacy_manager = PrivacyManager()
    llm_config = privacy_manager.get_llm_config("cloud")
    
    test_drug = "Aspirin"
    
    # Test each agent
    agents = [
        ("IQVIA Agent", IQVIAInsightsAgent()),
        ("Clinical Agent", ClinicalAgent()),
        ("Patent Agent", PatentAgent()),
        ("Regulatory Agent", RegulatoryComplianceAgent()),
        ("Patient Sentiment Agent", PatientSentimentAgent()),
        ("ESG Agent", ESGSustainabilityAgent()),
        ("EXIM Agent", EXIMAgent()),
        ("Web Intelligence Agent", WebIntelligenceAgent()),
    ]
    
    all_results = {}
    
    for agent_name, agent in agents:
        print(f"\n[{agent_name}]")
        try:
            result = await agent.analyze(test_drug, llm_config)
            all_results[agent_name.lower().replace(" ", "_")] = result
            
            # Check for key fields
            has_molecule = "molecule" in result
            has_date = "analysis_date" in result
            has_processing = "processing_time_ms" in result
            has_llm_fields = any("llm" in key.lower() for key in result.keys())
            
            print(f"  Molecule field: {'OK' if has_molecule else 'MISSING'}")
            print(f"  Date field: {'OK' if has_date else 'MISSING'}")
            print(f"  Processing time: {'OK' if has_processing else 'MISSING'}")
            print(f"  LLM fields: {'OK' if has_llm_fields else 'MISSING'}")
            print(f"  Total fields: {len(result)}")
            print(f"  Status: SUCCESS")
        except Exception as e:
            print(f"  Status: ERROR - {e}")
    
    # Test Validation Agent with collected results
    print(f"\n[Validation Agent]")
    try:
        validation_agent = ValidationAgent()
        validation_result = await validation_agent.analyze(test_drug, all_results, llm_config)
        
        has_risks = "risk_flags" in validation_result
        has_confidence = "overall_confidence" in validation_result
        has_llm_summary = "validation_summary_llm" in validation_result
        
        print(f"  Risk flags: {'OK' if has_risks else 'MISSING'}")
        print(f"  Confidence score: {'OK' if has_confidence else 'MISSING'}")
        print(f"  LLM summary: {'OK' if has_llm_summary else 'MISSING'}")
        print(f"  Total fields: {len(validation_result)}")
        print(f"  Status: SUCCESS")
    except Exception as e:
        print(f"  Status: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_agent_completeness())
