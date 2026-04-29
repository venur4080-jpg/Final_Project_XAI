import serial
import requests
import csv
import os
from datetime import datetime
import time

# --- CONFIGURATION ---
FIREBASE_URL = "https://xai-healthcare-default-rtdb.firebaseio.com/health_logs.json"
SERIAL_PORT = 'COM3' 
BAUD_RATE = 115200
CSV_FILE = 'health_data.csv'

# --- INITIALIZE CSV ---
file_exists = os.path.isfile(CSV_FILE)

# --- INITIALIZE SERIAL ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to hardware on {SERIAL_PORT}")
except Exception as e:
    print(f"Error: {e}")
    exit()

print(f"Logging to {CSV_FILE} and Firebase ({FIREBASE_URL}) with LIVE cough values.")

# Open file in 'append' mode
with open(CSV_FILE, 'a', newline='') as f:
    writer = csv.writer(f)
    
    # Write header only if the file is new
    if not file_exists:
        writer.writerow(["Time", "Temperature", "BPM", "Cough", "Label"])

    # --- COUGH LATCH STATE ---
    last_raw_coughs = -1 # Initialize
    last_cough_time = 0
    display_coughs = 0

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if "TEMP" in line:
                    # Parsing: TEMP:24.8C | BPM:74 | COUGHS:2
                    clean_data = line.replace("TEMP:", "").replace("C | BPM:", ",").replace(" | COUGHS:", ",")
                    parts = clean_data.split(",")
                    
                    temp = float(parts[0])
                    bpm = int(parts[1])
                    raw_coughs = int(parts[2]) # Using the REAL value from hardware
                    
                    # --- SOFTWARE LATCH LOGIC ---
                    if last_raw_coughs == -1:
                        last_raw_coughs = raw_coughs # Sync start
                        
                    # If hardware count INCREASES (new cough detected)
                    if raw_coughs > last_raw_coughs:
                        display_coughs = 1
                        last_cough_time = time.time()
                        last_raw_coughs = raw_coughs # Update reference
                    
                    # Check reset timer
                    if display_coughs == 1:
                        if (time.time() - last_cough_time) > 10:
                            display_coughs = 0 # Reset after 10s silence

                    # --- MANUAL OVERRIDE ---
                    # Check for cough_status.txt to force state
                    if os.path.exists("cough_status.txt"):
                        with open("cough_status.txt", "r") as cf:
                           status_content = cf.read().strip()
                           if status_content == "1":
                               display_coughs = 1
                           elif status_content == "0":
                               display_coughs = 0
                    # -----------------------
                    
                    # ----------------------------

                    # AI Label Logic: High Risk (1) if fever, low temp, high heart rate, or coughing
                    label = 1 if (temp > 37.0 or (temp < 35.0 and temp > 0) or bpm > 100 or display_coughs > 3) else 0
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 1. SAVE TO LOCAL CSV
                    writer.writerow([timestamp, temp, bpm, display_coughs, label])
                    f.flush() 
                    
                    # 2. PUSH TO CLOUD
                    payload = {
                        "timestamp": timestamp,
                        "temperature": temp,
                        "bpm": bpm,
                        "coughs": display_coughs,
                        "label": label
                    }
                    response = requests.post(FIREBASE_URL, json=payload)
                    
                    if response.status_code == 200:
                        print(f"Sync Success (200 OK) -> Temp: {temp}C | Cough Status: {display_coughs}")
                    else:
                        print(f"Sync FAILED ({response.status_code}) -> {response.text}")
                        
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(0.1)