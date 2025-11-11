"""Quick test script to verify environment setup and connections."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_env_vars():
    """Check that required environment variables are set."""
    print("=" * 60)
    print("ENVIRONMENT VARIABLES CHECK")
    print("=" * 60)
    
    required_vars = {
        'NEO4J_URI': 'Neo4j AuraDB connection URI',
        'NEO4J_USERNAME': 'Neo4j username',
        'NEO4J_PASSWORD': 'Neo4j password',
        'GOOGLE_API_KEY': 'Google Gemini API key',
    }
    
    optional_vars = {
        'HYPERBROWSER_API_KEY': 'HyperBrowser.ai API key (optional)',
    }
    
    all_good = True
    
    print("\nRequired variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            masked = value[:10] + '...' if len(value) > 10 else '***'
            print(f"  ✓ {var}: {masked} ({description})")
        else:
            print(f"  ✗ {var}: NOT SET ({description})")
            all_good = False
    
    print("\nOptional variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:10] + '...' if len(value) > 10 else '***'
            print(f"  ✓ {var}: {masked} ({description})")
        else:
            print(f"  ⚠ {var}: NOT SET ({description} - fallback disabled)")
    
    return all_good


def test_neo4j_connection():
    """Test Neo4j connection."""
    print("\n" + "=" * 60)
    print("NEO4J CONNECTION TEST")
    print("=" * 60)
    
    try:
        sys.path.insert(0, 'src')
        from graph.neo4j_client import Neo4jClient
        
        client = Neo4jClient()
        if client.verify_connection():
            print("  ✓ Successfully connected to Neo4j")
            try:
                stats = client.get_stats()
                print(f"  Current database stats:")
                for key, value in stats.items():
                    print(f"    - {key.replace('_', ' ').title()}: {value}")
            except Exception as e:
                print(f"  ⚠ Could not get stats (database may be empty): {e}")
            client.close()
            return True
        else:
            print("  ✗ Failed to connect to Neo4j")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_gemini_api():
    """Test Gemini API connection."""
    print("\n" + "=" * 60)
    print("GEMINI API TEST")
    print("=" * 60)
    
    try:
        sys.path.insert(0, 'src')
        from classifiers.gemini_classifier import ReferenceClassifier
        
        classifier = ReferenceClassifier()
        print("  ✓ Gemini classifier initialized successfully")
        
        # Test with a simple classification
        test_text = "Capital One is a financial services company using Snowflake for fraud detection."
        print("  Testing classification...")
        result = classifier.classify(test_text, "https://test.com")
        
        if result:
            print("  ✓ Classification successful")
            print(f"    Customer: {result.get('customer_name', 'N/A')}")
            print(f"    Industry: {result.get('industry', 'N/A')}")
            return True
        else:
            print("  ✗ Classification returned None")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_hyperbrowser():
    """Test HyperBrowser.ai (if configured)."""
    print("\n" + "=" * 60)
    print("HYPERBROWSER.AI TEST")
    print("=" * 60)
    
    api_key = os.getenv('HYPERBROWSER_API_KEY')
    if not api_key:
        print("  ⚠ HYPERBROWSER_API_KEY not set - skipping test")
        print("  (This is optional - scraper will work without it)")
        return None
    
    try:
        from hyperbrowser import Hyperbrowser
        client = Hyperbrowser(api_key=api_key)
        print("  ✓ HyperBrowser.ai client initialized successfully")
        print("  (Full test requires API call - skipping to save credits)")
        return True
    except ImportError:
        print("  ✗ hyperbrowser package not installed")
        print("  Run: pip install hyperbrowser")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ADVOCACY INTELLIGENCE - SETUP VERIFICATION")
    print("=" * 60)
    
    results = {}
    
    # Test environment variables
    results['env'] = test_env_vars()
    
    if not results['env']:
        print("\n⚠ Some required environment variables are missing!")
        print("  Please check your .env file and try again.")
        return
    
    # Test Neo4j
    results['neo4j'] = test_neo4j_connection()
    
    # Test Gemini
    results['gemini'] = test_gemini_api()
    
    # Test HyperBrowser (optional)
    results['hyperbrowser'] = test_hyperbrowser()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    required_tests = ['env', 'neo4j', 'gemini']
    passed = sum(1 for test in required_tests if results.get(test))
    
    print(f"\nRequired tests: {passed}/{len(required_tests)} passed")
    
    if passed == len(required_tests):
        print("\n✓ All required components are working!")
        print("  You're ready to run the pipeline:")
        print("  python scripts/test_pipeline.py")
    else:
        print("\n✗ Some required components failed")
        print("  Please fix the issues above before running the pipeline")
    
    if results.get('hyperbrowser'):
        print("\n✓ HyperBrowser.ai fallback is available")
    elif results.get('hyperbrowser') is False:
        print("\n⚠ HyperBrowser.ai fallback is not available")
        print("  Scraper will still work, but won't have fallback for blocked pages")


if __name__ == '__main__':
    main()

