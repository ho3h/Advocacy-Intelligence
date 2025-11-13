"""Classifier for customer references using Google Gemini API."""

import google.generativeai as genai
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()


class ReferenceClassifier:
    """Classify customer references using Google Gemini."""
    
    def __init__(self):
        """Initialize Gemini client."""
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("Missing GOOGLE_API_KEY in environment")
        
        genai.configure(api_key=api_key)
        # List available models and use the first one that supports generateContent
        # Prefer flash models for speed/cost, fallback to pro models
        available_models = [m.name for m in genai.list_models() 
                           if 'generateContent' in m.supported_generation_methods]
        
        # Prefer flash models, then pro models
        preferred_models = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.5-flash-lite']
        model_name = None
        
        for preferred in preferred_models:
            full_name = f'models/{preferred}'
            if full_name in available_models:
                model_name = preferred
                break
        
        # Fallback to first available if none match
        if not model_name and available_models:
            # Extract model name from full path (e.g., "models/gemini-2.5-flash" -> "gemini-2.5-flash")
            model_name = available_models[0].split('/')[-1]
        
        if not model_name:
            raise ValueError("No available Gemini models found. Check your API key and region.")
        
        self.model = genai.GenerativeModel(model_name)
        print(f"Using Gemini model: {model_name}")
        
        # Load taxonomies
        self.taxonomies = self._load_taxonomies()
    
    def _load_taxonomies(self):
        """Load predefined taxonomies from JSON files."""
        taxonomies = {}
        
        taxonomy_files = ['industries', 'use_cases', 'company_sizes']
        for taxonomy in taxonomy_files:
            path = f'data/taxonomies/{taxonomy}.json'
            if os.path.exists(path):
                with open(path) as f:
                    taxonomies[taxonomy] = json.load(f)
        
        return taxonomies
    
    def classify(self, reference_text, reference_url="", max_retries=3):
        """
        Classify a customer reference.
        
        Args:
            reference_text: Full text of the reference
            reference_url: URL of the reference (for context)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict with classification results
        """
        industries_list = ', '.join(self.taxonomies.get('industries', {}).get('industries', []))
        company_sizes_list = ', '.join(self.taxonomies.get('company_sizes', {}).get('company_sizes', []))
        use_cases_list = ', '.join(self.taxonomies.get('use_cases', {}).get('use_cases', []))
        
        prompt = f"""You are analyzing a customer reference/case study. Extract structured information from the text below to support sales teams, marketing, and customer advocacy workflows.

Think about:
- Which account (customer) the story is about and how to profile them.
- Which personas or champions are quoted and what roles they play in the deal.
- What challenge, solution, and impact are highlighted.
- What supporting materials/assets exist that enable go-to-market teams.

REFERENCE URL: {reference_url}

REFERENCE TEXT:
{reference_text}

---

Extract the following information and return ONLY valid JSON (no markdown, no explanations). Use null for unknown scalar values and [] for unknown lists.

{{
  "customer_name": "Name of the customer company",
  "industry": "Select ONE from: {industries_list}",
  "company_size": "Select ONE from: {company_sizes_list}",
  "region": "Select ONE: North America, EMEA, APAC, LATAM, or Unknown",
  "country": "Specific country if mentioned, otherwise null",
  "account_details": {{
    "logo_url": "Official logo URL if mentioned, else null",
    "website": "Primary website URL for the account if mentioned, else null",
    "summary": "One sentence summary of the account if available, else null",
    "tagline": "Short tagline or descriptor if provided, else null"
  }},
  "use_cases": ["Select 1-3 relevant from: {use_cases_list}"],
  "outcomes": [
    {{
      "type": "performance | cost_savings | revenue_impact | efficiency | other",
      "description": "Brief description of outcome",
      "metric": "Specific metric if mentioned (e.g., '10x faster', '40% reduction')"
    }}
  ],
  "personas": [
    {{
      "title": "Job title of person quoted or featured",
      "name": "Person's name if mentioned",
      "seniority": "C-Level | VP | Director | Manager | Individual Contributor"
    }}
  ],
  "tech_stack": ["List of other technologies mentioned (AWS, Azure, dbt, etc.)"],
  "quoted_text": "Most compelling customer quote from the reference (if any)",
  "champions": [
    {{
      "champion_id": "Create a slug using account name + champion name + title (lowercase, hyphen-separated)",
      "name": "Champion full name if available, else descriptive placeholder (e.g., 'Data Engineering VP')",
      "title": "Exact job title if available",
      "role": "Commercial role this person plays in the story (e.g., Economic Buyer, Technical Champion, Executive Sponsor)",
      "seniority": "C-Level | VP | Director | Manager | Individual Contributor | Unknown",
      "quotes": ["Up to 3 direct quotes attributable to this champion"]
    }}
  ],
  "materials": [
    {{
      "material_id": "Unique ID or slug for this asset. Use reference URL if nothing else is available.",
      "title": "Title of the asset if available, otherwise null",
      "content_type": "Select ONE: case_study | blog | video | press_release | webinar | whitepaper | datasheet | infographic | podcast | other",
      "publish_date": "ISO 8601 date (YYYY-MM-DD) if available, else null",
      "url": "Canonical URL for the asset. If missing, reuse the reference URL.",
      "raw_text_excerpt": "Most relevant 1-2 sentence excerpt (<=500 chars) that captures the story",
      "country": "Country highlighted in the asset if different from account country, else null",
      "region": "Region highlighted in the asset (North America, EMEA, APAC, LATAM, Unknown)",
      "language": "Language of the asset (e.g., English, German). Use 'Unknown' if not clear.",
      "product": "Primary product or solution focus (e.g., 'Snowflake Data Cloud')",
      "challenge": "1-2 sentence summary of the challenge",
      "solution": "1-2 sentence summary of the solution",
      "impact": "1-2 sentence summary of the quantifiable/qualitative impact",
      "elevator_pitch": "Concise 1 sentence pitch summarizing the story",
      "proof_points": ["List up to 5 key metrics or qualitative proof statements"],
      "quotes": ["Key quotes drawn from the asset"],
      "champion_role": "Role of the champion within this material (e.g., quote source, narrator, featured exec)",
      "embedding": null
    }}
  ]
}}

IMPORTANT EXTRACTION GUIDELINES:

1. COMPANY SIZE: Look for explicit mentions like:
   - "Fortune 500", "enterprise", "large company", "thousands of employees" → Enterprise (>5000 employees)
   - "mid-size", "hundreds of employees", "500-5000" → Mid-Market (500-5000 employees)
   - "small business", "startup", "SMB", "under 500 employees" → SMB (<500 employees) or Startup
   - If no clear indication, use "Unknown"

2. REGION: Look for:
   - Country names: USA, Canada, Mexico → North America
   - UK, Germany, France, Netherlands, etc. → EMEA
   - China, Japan, India, Australia, Singapore, etc. → APAC
   - Brazil, Argentina, etc. → LATAM
   - If no geographic info, use "Unknown"

3. COUNTRY: Extract specific country name if mentioned (e.g., "United States", "United Kingdom", "Germany")

4. Use ONLY values from the predefined lists for industry, company_size, use_cases
5. If information is not in the text, use "Unknown" or empty array as appropriate
6. Keep descriptions concise (1-2 sentences)
7. Limit champions to those explicitly named or clearly described spokespeople (max 3)
8. For materials, if you only have the current reference, output a single material that summarizes it
9. Return ONLY the JSON object, no other text
"""
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Remove markdown code blocks if present
                if response_text.startswith('```'):
                    # Find the JSON content between ```json and ```
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    if start >= 0 and end > start:
                        response_text = response_text[start:end]
                
                classification = json.loads(response_text)
                return classification
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse Gemini response as JSON (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"Response was: {response_text[:500]}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    print(f"Final response was: {response_text[:500]}")
                    return None
                    
            except Exception as e:
                error_str = str(e).lower()
                # Check for rate limit or quota errors
                if 'quota' in error_str or 'rate limit' in error_str or '429' in error_str:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Rate limit/quota error (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Rate limit/quota error after {max_retries} attempts")
                        raise
                else:
                    print(f"Classification error: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None
        
        return None


if __name__ == '__main__':
    # Test classifier
    classifier = ReferenceClassifier()
    
    test_text = """
    Capital One Uses Snowflake for Real-Time Fraud Detection
    
    Capital One, one of the largest banks in the United States, implemented Snowflake's
    Data Cloud to power their fraud detection systems. The solution processes millions
    of transactions per day in real-time.
    
    "Snowflake enabled us to analyze transaction patterns 10x faster than our previous
    system," said Sarah Johnson, VP of Data Engineering at Capital One. "We've reduced
    false positives by 40% while catching 25% more fraudulent transactions."
    
    The bank also uses AWS, dbt, and Fivetran alongside Snowflake to build a modern
    data stack that serves 100+ million customers.
    """
    
    result = classifier.classify(test_text, "https://snowflake.com/customers/capital-one")
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Classification failed")

