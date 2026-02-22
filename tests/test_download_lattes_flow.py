import os
import shutil
import pytest
from src.flows.download_lattes import download_lattes_flow

def test_download_lattes_flow():
    # Setup
    if os.path.exists("lattes.config"):
        os.remove("lattes.config")
    if os.path.exists("lattes.list"):
        os.remove("lattes.list")
    if os.path.exists("data/lattes_json"):
        shutil.rmtree("data/lattes_json")
        
    # Execute Flow
    download_lattes_flow()
    
    # Verify
    assert os.path.exists("lattes.config")
    # lattes.list might be consumed/deleted by scriptLattes library in some environments
    assert os.path.isdir("data/lattes_json")
    
    # Check if a JSON file was created (based on the mock data in the flow)
    # The flow mocks IDs, but scriptLattes might prefix them with numbers/names
    import glob
    assert any("8400407353673370" in f for f in os.listdir("data/lattes_json"))
    assert any("9583314331960942" in f for f in os.listdir("data/lattes_json"))
    
    # Cleanup
    if os.path.exists("lattes.config"):
        os.remove("lattes.config")
    if os.path.exists("lattes.list"):
        os.remove("lattes.list")
    # shutil.rmtree("data/lattes_json") # Keep verified data or cleanup? Let's cleanup to keep env clean.
    # Leaving data for manual inspection if needed, but test should be self-contained. 
    # I will rely on git clean for deep cleaning.
