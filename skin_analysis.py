from google import genai
import os
from dotenv import load_dotenv
from PIL import Image
import sys
from gemini_api_manager import generate_content_with_retry

# Load environment variables
load_dotenv()


def analyze_skin(image_path=None, symptoms_text=None):
    """
    Analyzes skin conditions using Gemini Vision (if image provided) or Text.
    """
    print("\n--- AI Skin Allergy Assistant ---")

    prompt_parts = [
        "You are an AI Medical Assistant specializing in dermatology.",
        "Analyze the provided input (image or text description) for potential skin allergies or conditions.",
        "Provide a structured response:",
        "1. Observation: What do you see or understand from the symptoms?",
        "2. Potential Causes: What could be causing this (e.g., eczema, contact dermatitis, hives)?",

        "3. Management: General home remedies or over-the-counter suggestions.",
        "4. Disclaimer: ONLY 'Consult a doctor if symptoms persist'. Do NOT prescribe medication.",
        "IMPORTANT: Use simple formatting. Use **Part Name** for headers. Do NOT use markdown tables or complex code blocks."
    ]
    
    if symptoms_text:
        prompt_parts.append(f"\nPatient Symptoms: {symptoms_text}")

    try:
        # Update model from env
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        print(f"Using model: {model_name}")

        normalized_prompt = "\n".join(prompt_parts)

        if image_path:
            if not os.path.exists(image_path):
                return "Error: Image file not found."
            
            print(f"Loading image: {image_path}...")
            img = Image.open(image_path)
            response = generate_content_with_retry(
                model=model_name,
                contents=[img, normalized_prompt]
            )
        else:
            if not symptoms_text:
                return "Error: Please provide either an image path or symptom text."
            response = generate_content_with_retry(
                model=model_name,
                contents=normalized_prompt
            )

        return response.text

    except Exception as e:
        print(f"AI Analysis Failed: {e}")
        if "429" in str(e):
             print("Quota Exceeded. Using Fallback.")
        
        # Fallback Simulation
        simulated_response = """
1. Observation (Simulated): Analysis unavailable due to high server load (Quota Exceeded). Based on typical cases: Redness or texture change detected.
2. Potential Causes: Could be simple contact dermatitis or heat rash.
3. Management: Keep area clean and dry. Apply aloe vera or calamine lotion.
4. Disclaimer: AI Service Unreachable. Rule-based fallback. Consult a doctor.
"""
        return simulated_response

if __name__ == "__main__":
    # Simple CLI for testing
    print("Select Mode:")
    print("1. Text Description")
    print("2. Image Analysis")
    
    choice = input("Enter choice (1/2): ").strip()
    
    if choice == '1':
        symptoms = input("Describe your symptoms (e.g., 'Red itchy rash on arm'): ")
        analyze_skin(symptoms_text=symptoms)
    elif choice == '2':
        img_path = input("Enter path to image file: ").strip()
        # Remove quotes if user dragged and dropped file
        img_path = img_path.strip('"').strip("'") 
        # Optional: Ask for extra text
        symptoms = input("Any additional symptoms? (Optional, press Enter to skip): ")
        analyze_skin(image_path=img_path, symptoms_text=symptoms)
    else:
        print("Invalid choice.")
