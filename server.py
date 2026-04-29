from flask import Flask, jsonify, send_file, request, render_template
from flask_cors import CORS
import pandas as pd
import os
from google import genai
from dotenv import load_dotenv
from skin_analysis import analyze_skin
import xai_analysis
import shutil
from datetime import datetime, timedelta
from gemini_api_manager import generate_content_with_retry

app = Flask(__name__)
CORS(app)

load_dotenv()


DATA_FILE = 'health_data.csv'
LIME_FILE = 'lime_explanation.html'
SHAP_FILE = 'shap_summary.png'



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/skin_analysis', methods=['POST'])
def run_skin_analysis():
    data = request.form
    symptoms = data.get('symptoms')
    image_file = request.files.get('image')
    
    image_path = None
    if image_file:
        # Save temp file
        image_path = os.path.join('uploads', image_file.filename)
        os.makedirs('uploads', exist_ok=True)
        image_file.save(image_path)
    
    result = analyze_skin(image_path=image_path, symptoms_text=symptoms)
    
    # Cleanup
    if image_path and os.path.exists(image_path):
        os.remove(image_path)
        
    return jsonify({"result": result})




# Global Cache
last_explanation = ""
last_ai_time = datetime.min
frozen_bpm = None

@app.route('/api/data', methods=['GET'])
def get_data():
    global last_explanation, last_ai_time
    
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            if not df.empty:
                # return last row
                last_row = df.iloc[-1].to_dict()
                
                # Check for stale data (Timeout > 10 seconds)
                try:
                    # Timestamp format from logger: "%Y-%m-%d %H:%M:%S"
                    last_time = datetime.strptime(str(last_row.get('Time')), "%Y-%m-%d %H:%M:%S")
                    if datetime.now() - last_time > timedelta(seconds=10):
                        # Data is stale
                        last_row['Temperature'] = 0
                        last_row['BPM'] = 0
                        last_row['Cough'] = 0 
                        last_row['Coughs'] = 0
                        last_row['Label'] = 0
                        last_row['explanation'] = "Sensors Disconnected (Check Hardware)"
                        return jsonify(last_row)
                except Exception as e:
                    print(f"Time check error: {e}")

                # Rate Limit / Cache AI Explanation
                # Only generate if > 60 seconds passed since last call (Increased to save quota)
                if datetime.now() - last_ai_time > timedelta(seconds=60):
                    try:
                        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                        prompt = f"Analyze these health vitals: Temperature {last_row.get('Temperature')}C, Heart Rate {last_row.get('BPM')} BPM, Cough Events {last_row.get('Cough')}. Provide a 1-sentence health assessment for a doctor."
                        response = generate_content_with_retry(
                            model=model_name,
                            contents=prompt
                        )
                        last_explanation = response.text
                        last_ai_time = datetime.now() # Update time
                    except Exception as ai_error:
                        print(f"Gemini API Error (Background): {ai_error}")
                        if "429" in str(ai_error):
                            print("Background AI: Quota Exceeded. Skipping update.")
                        # Keep previous explanation or fallback if empty
                        if not last_explanation:
                            last_explanation = "AI Service Offline (Simulated). Vitals appear stable."
                
                # Use Cached Explanation
                last_row['explanation'] = last_explanation
                
                if not last_row.get('explanation'):
                     # Fallback to rule-based if API fails
                    reasons = []
                    if last_row.get('Temperature', 0) > 37.0:
                        reasons.append("High Temperature")
                    if last_row.get('Temperature', 0) < 35.0 and last_row.get('Temperature', 0) > 0:
                        reasons.append("Low Temperature")
                    if last_row.get('BPM', 0) > 100:
                        reasons.append("Elevated Heart Rate")
                    if last_row.get('Cough', 0) > 3:
                        reasons.append("Frequent Coughing")
                    
                    if reasons:
                        last_row['explanation'] = "Risk Factors (Simulated): " + ", ".join(reasons)
                    else:
                        last_row['explanation'] = "Vitals Normal (Simulated Analysis)."

                # Add Cough Status for Frontend
                cough_val = last_row.get('Cough', 0)
                try:
                    # Ensure it's treated as an int
                    if int(cough_val) > 0:
                        last_row['CoughStatus'] = "DETECTED"
                    else:
                        last_row['CoughStatus'] = "Normal"
                except:
                     last_row['CoughStatus'] = "Normal"

                # --- 30s Average BPM Logic (Stateful Latch) ---
                global frozen_bpm
                try:
                    df['Time'] = pd.to_datetime(df['Time'])
                    now = datetime.now()
                    
                    # 1. Reset Check: If no valid reading in last 8 seconds, RESET
                    recent_data = df[(df['Time'] >= now - timedelta(seconds=8)) & (df['BPM'] > 20)]
                    if recent_data.empty:
                        frozen_bpm = None # Reset
                        
                    if frozen_bpm is not None:
                        last_row['Avg_BPM'] = f"{frozen_bpm}"
                        last_row['Avg_Status'] = "Locked"
                    else:
                        start_window = now - timedelta(seconds=30)
                        mask = (df['Time'] >= start_window) & (df['BPM'] > 20)
                        valid_window = df.loc[mask]
                        
                        if not valid_window.empty:
                            first = valid_window['Time'].min()
                            last = valid_window['Time'].max()
                            duration = (last - first).total_seconds()
                            
                            if duration >= 25: # Slightly easier to hit
                                avg = int(valid_window['BPM'].mean())
                                frozen_bpm = avg 
                                last_row['Avg_BPM'] = f"{avg}"
                                last_row['Avg_Status'] = "Locked"
                            else:
                                last_row['Avg_BPM'] = f"{int(duration)}s"
                                last_row['Avg_Status'] = "Measuring"
                        else:
                            last_row['Avg_BPM'] = "--"
                            last_row['Avg_Status'] = "Ready"
                            
                except Exception as e:
                    print(f"Avg Error: {e}")
                    last_row['Avg_BPM'] = "--"

                return jsonify(last_row)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "No data found"}), 404

@app.route('/api/xai/lime', methods=['GET'])
def get_lime():
    if os.path.exists(LIME_FILE):
        return send_file(LIME_FILE)
    return "LIME explanation not found", 404

@app.route('/api/xai/shap', methods=['GET'])
def get_shap():
    if os.path.exists(SHAP_FILE):
        return send_file(SHAP_FILE, mimetype='image/png')
    return "SHAP summary not found", 404

@app.route('/api/xai/lime_plot', methods=['GET'])
def get_lime_plot():
    if os.path.exists('lime_plot.png'):
        return send_file('lime_plot.png', mimetype='image/png')
    return "LIME plot not found", 404

@app.route('/api/xai/shap_plot', methods=['GET'])
def get_shap_plot():
    if os.path.exists('shap_plot.png'):
        return send_file('shap_plot.png', mimetype='image/png')
    return "SHAP plot not found", 404

@app.route('/api/xai/explanation', methods=['GET'])
def get_xai_text():
    if os.path.exists('xai_explanation.txt'):
        try:
            with open('xai_explanation.txt', 'r') as f:
                return jsonify({"text": f.read()})
        except:
            pass
    return jsonify({"text": "Explanation loading..."})

@app.route('/api/xai/regenerate', methods=['POST'])
def regenerate_xai():
    try:
        success = xai_analysis.generate_now()
        if success:
            return jsonify({"status": "success", "message": "XAI Analysis Regenerated"})
        else:
            return jsonify({"status": "error", "message": "Generation failed inside script"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_msg = data.get('message', '')
    context = data.get('context', {})
    
    # Construct prompt with context
    system_prompt = f"""You are a helpful AI Medical Assistant for a patient monitoring dashboard.
    Current Vitals:
    - Temperature: {context.get('Temperature', 'N/A')} C
    - Heart Rate: {context.get('BPM', 'N/A')} BPM
    - Cough Count: {context.get('Cough', 'N/A')}
    
    User Question: {user_msg}
    
    Provide a concise, helpful, and safe medical answer based on these vitals. 
    If values are high, warn the user sensibly. Keep answers short (under 50 words)."""
    
    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = generate_content_with_retry(
            model=model_name,
            contents=system_prompt
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        print(f"Gemini Chat Error: {e}")
        # Fallback for chat
        fallback_msg = f"I'm currently offline (Quota Exceeded). Based on your vitals (Temp: {context.get('Temperature', 'N/A')}C, BPM: {context.get('BPM', 'N/A')}), please rest and monitor for changes."
        return jsonify({"reply": fallback_msg})

@app.route('/api/analyze_vital', methods=['POST'])
def analyze_vital():
    data = request.json
    vital_name = data.get('vital')
    value = data.get('value')
    
    prompt = f"""
    Act as a professional doctor. The patient has a {vital_name} of {value}.
    Provide a structured response in plain text (no markdown):
    
    1. Status: [Normal / At Risk / High / Low]
    2. Explanation: [Why it is in this status]
    3. Actionable Cure/Advice: [What steps to take immediately]
    
    Keep it concise and helpful.
    """
    
    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = generate_content_with_retry(
            model=model_name,
            contents=prompt
        )
        return jsonify({"analysis": response.text})
    except Exception as e:
        print(f"Analyze Vital Error: {e}, type: {type(e)}")
        
        # Fallback Simulation
        advice = "Monitor closely."
        status = "Unknown"
        
        try:
            # Parse value if possible (handle "75 (Locked)", "37.5°C" etc)
            clean_val = str(value).split(' ')[0] # Take first part "75" from "75 (Locked)"
            val = float(clean_val.replace('°C', '').replace('BPM', '').replace('s', '').strip())
            
            if "Temperature" in vital_name:
                if val > 37.0: status, advice = "High (Fever)", "Hydrate and rest."
                elif val < 35.0 and val > 0: status, advice = "Low (Cold)", "Warm up immediately."
                else: status, advice = "Normal", "Maintain routine."
            elif "Heart" in vital_name:
                if val > 100: status, advice = "High", "Relax and breathe."
                else: status, advice = "Normal", "Good condition."
            elif "Cough" in vital_name:
                if val > 3: status, advice = "High", "Consult doctor."
                else: status, advice = "Normal", "Monitor."
        except:
            pass

        fallback_text = f"1. Status: {status} (Simulated)\n2. Explanation: AI Service unavailable (Quota). Rule-based check applied.\n3. Actionable Cure/Advice: {advice}"
        return jsonify({"analysis": fallback_text})

if __name__ == '__main__':
    print("Starting Flask server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
