import os
from google import genai
from dotenv import load_dotenv

def test_call():
    """Minimal test to confirm Gemini API connectivity."""
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY missing from environment variables.")
        return None
        
    client = genai.Client(api_key=api_key)
    
    print("Pinging Gemini API with 'say hello'...")
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="say hello"
    )
    
    print("\n--- Response ---")
    print(response.text)
    print("----------------")
    
    return response.text
