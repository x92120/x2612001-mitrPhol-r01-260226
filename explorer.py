import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def get_gemini_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Warning: GOOGLE_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    return genai

def chat_with_thinking(prompt, thinking_level="MEDIUM"):
    """
    Interact with Gemini 3.1 Pro using reasoning/thinking levels.
    Levels: LOW, MEDIUM, HIGH
    """
    try:
        model = genai.GenerativeModel(
            model_name="gemini-3.1-pro",
            thinking_config={
                "include_thoughts": True, 
                "thinking_level": thinking_level
            }
        )
        
        response = model.generate_content(prompt)
        
        return {
            "thought": getattr(response.candidates[0], 'thought', 'No thought process returned.'),
            "text": response.text
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    client = get_gemini_client()
    print("--- Gemini 3.1 Pro Explorer ---")
    print("Type 'quit' to exit. Multi-line inputs are supported (end with CTRL+D).")
    
    while True:
        try:
            print("\nEnter prompt: (LOW/MEDIUM/HIGH reasoning)")
            prompt = input("> ")
            if prompt.lower() in ['quit', 'exit']:
                break
                
            # For now, default to MEDIUM reasoning
            result = chat_with_thinking(prompt, thinking_level="MEDIUM")
            
            if "error" in result:
                print(f"Error: {result['error']}")
                continue
                
            print("\n--- THOUGHT PROCESS ---")
            print(result["thought"])
            print("\n--- RESPONSE ---")
            print(result["text"])
            
        except EOFError:
            break
        except KeyboardInterrupt:
            break

    print("\nGoodbye!")
