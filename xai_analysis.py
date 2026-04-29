import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Fix "main thread" error
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import lime
import lime.lime_tabular
import shap
import os
from dotenv import load_dotenv
from datetime import datetime
from gemini_api_manager import generate_content_with_retry

load_dotenv()

# Configuration
DATA_FILE = 'health_data.csv'
LIME_OUTPUT = 'lime_explanation.html'
SHAP_SUMMARY = 'shap_summary.png'
DASHBOARD_IMAGE = 'dashboard.png'
SHAP_FORCE = 'shap_force.html'
XAI_TEXT = 'xai_explanation.txt'

def generate_medical_explanation(risk_score, features):
    """
    Uses Gemini to explain WHY the model predicts risk.
    """
    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        prompt = f"""
        You are an expert cardiologist AI.
        A machine learning model has predicted this patient's health status.
        
        Prediction Confidence (Risk): {risk_score:.2f}%
        Key Risk Factors (sorted by impact):
        {features}
        
        Explain these results to the patient in simple, reassuring language. 
        Focus on the top 2 factors. Limit to 50 words.
        """
        
        response = generate_content_with_retry(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"XAI Gen Error: {e}")
        return "AI Explanation unavailable (Quota Exceeded). Key factors are listed in the chart."


def load_or_generate_data():
    """Load sensor data and apply heuristic labels if missing."""
    df = None
    cols = ['Temperature', 'BPM', 'Coughs', 'Label']
    
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE, on_bad_lines='skip')
            # Standardize column names
            df.columns = [c.strip() for c in df.columns]
            rename_map = {
                'HeartRate': 'BPM', 
                'Heart Rate': 'BPM',
                'Cough': 'Coughs',
                'Coughs': 'Coughs'
            }
            df.rename(columns=rename_map, inplace=True)
            
            # Ensure numeric columns
            for col in ['Temperature', 'BPM', 'Coughs']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Apply heuristic labeling if Label is missing or all zeros
            if 'Label' not in df.columns or df['Label'].sum() == 0:
                # Rules derived from healthcare demo defaults
                df['Label'] = ((df['Temperature'] > 37.5) | (df['BPM'] > 100) | (df['Coughs'] > 3)).astype(int)
            
            df.dropna(subset=['Temperature', 'BPM', 'Coughs'], inplace=True)
            
            # Ensure final column structure
            for col in cols:
                if col not in df.columns:
                    df[col] = 0
            df = df[cols]
            
        except Exception as e:
            print(f"Error reading CSV: {e}")

    # If we have significant real data, use it
    if df is not None and len(df) >= 100:
        return df

    # Otherwise, generate/supplement with synthetic training data
    print("Insufficient or unbalanced data. Supplementing with synthetic data...")
    np.random.seed(42)
    n_synthetic = 500
    
    temps = np.concatenate([
        np.random.uniform(36.0, 37.4, n_synthetic // 2), # Healthy
        np.random.uniform(37.5, 39.5, n_synthetic // 2)  # Unhealthy
    ])
    bpms = np.concatenate([
        np.random.randint(60, 95, n_synthetic // 2),     # Healthy
        np.random.randint(90, 130, n_synthetic // 2)     # Unhealthy
    ])
    coughs = np.concatenate([
        np.random.randint(0, 2, n_synthetic // 2),       # Healthy
        np.random.randint(2, 10, n_synthetic // 2)       # Unhealthy
    ])
    
    # Label based on the same rules
    labels = ((temps > 37.5) | (bpms > 100) | (coughs > 3)).astype(int)
    
    df_synthetic = pd.DataFrame({
        'Temperature': temps, 
        'BPM': bpms, 
        'Coughs': coughs, 
        'Label': labels
    })
    
    if df is not None and not df.empty:
        df = pd.concat([df_synthetic, df], ignore_index=True)
    else:
        df = df_synthetic
            
    return df

def train_model(df):
    feature_names = ['Temperature', 'BPM', 'Coughs']
    X = df[feature_names]
    y = df['Label']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    score = model.score(X_test, y_test)
    print(f"Model Accuracy: {score:.2f}")
    
    return model, X_train, feature_names

def run_lime(model, X_train, feature_names, instance_data):
    print("Generating LIME explanation...")
    explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=np.array(X_train),
        feature_names=feature_names,
        class_names=['Normal', 'Risk'],
        mode='classification'
    )
    
    # Explain the specific instance
    exp = explainer.explain_instance(
        data_row=np.array(instance_data), 
        predict_fn=model.predict_proba
    )
    
    exp.save_to_file(LIME_OUTPUT)
    print(f"LIME explanation saved to {LIME_OUTPUT}")

def run_shap(model, X_train, feature_names, instance_data):
    print("Generating SHAP plots...")
    # TreeExplainer is fast for random forests
    explainer = shap.TreeExplainer(model)
    
    # Calculate shap values for training data (for summary) and instance
    # shap_values returns a list for classification: [class0, class1]
    shap_values = explainer.shap_values(X_train, check_additivity=False)
    
    # We care about Class 1 (Risk)
    # Handle case where shap_values might not be a list (binary vs multiclass variations in some versions)
    if isinstance(shap_values, list):
        shap_vals_risk = shap_values[1]
    else:
        shap_vals_risk = shap_values

    # Summary Plot
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_vals_risk, X_train, show=False, plot_type="bar")
    plt.tight_layout()
    plt.savefig(SHAP_SUMMARY, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"SHAP Summary plot saved to {SHAP_SUMMARY}")
    
    # Force Plot for the specific instance
    feature_names = list(feature_names) # Ensure list
    
    # Get shap values for the single instance
    shap_val_instance = explainer.shap_values(pd.DataFrame([instance_data], columns=feature_names), check_additivity=False)
    
    if isinstance(shap_val_instance, list):
        shap_val_single = shap_val_instance[1][0]
        base_value = explainer.expected_value[1]
    else:
        shap_val_single = shap_val_instance[0]
        base_value = explainer.expected_value
    
    plot = shap.force_plot(
        base_value, 
        shap_val_single, 
        instance_data, 
        feature_names=feature_names,
        show=False
    )
    shap.save_html(SHAP_FORCE, plot)
    print(f"SHAP Force plot saved to {SHAP_FORCE}")

LIME_IMAGE = 'lime_plot.png'
SHAP_IMAGE = 'shap_plot.png'

def generate_shap_plot(model, X_train, instance_data, feature_names):
    plt.style.use('dark_background')
    bg_color = '#000000'  # Absolute Black
    
    # Calculate SHAP values
    explainer = shap.TreeExplainer(model)
    X_sample = X_train.sample(min(100, len(X_train))) if hasattr(X_train, 'sample') else X_train[:100]
    shap_values_global = explainer.shap_values(X_sample, check_additivity=False)
    
    if isinstance(shap_values_global, list):
        sv_global = shap_values_global[1]
    else:
        sv_global = shap_values_global

    # Solid Black Theme for entire figure
    fig = plt.figure(figsize=(10, 10), facecolor=bg_color)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg_color)
    
    # Summary plot
    shap.summary_plot(
        sv_global, 
        X_sample, 
        feature_names=feature_names, 
        show=False,
        plot_type="dot",
        color_bar=False,
        alpha=0.9 # Slightly increased opacity for better visibility
    )
    
    # HIGHLIGHTED Title: Extra Large, Bold, pure White
    plt.title("Global Risk Factors (Feature Impact Distribution)", 
              color='#FFFFFF', fontsize=24, fontweight='extra bold', pad=45, ha='center')
    
    # HIGHLIGHTED Axis Labels
    ax.set_xlabel("SHAP Value (Impact on Prediction)", color='#FFFFFF', fontsize=16, fontweight='bold', labelpad=25)
    
    # HIGHLIGHTED Feature Names and Ticks: Pure White for maximum contrast
    ax.tick_params(axis='both', colors='#FFFFFF', labelsize=15, length=0)
    # Make feature names (y-axis) bold
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')
    
    # Explicit X-Ticks - wide gap to prevent overlap
    ax.set_xticks([-0.5, 0.0, 0.5])
    
    # Horizontal lines (dotted)
    ax.yaxis.grid(True, linestyle=(0, (1, 5)), alpha=0.3, color='white')
    # Central vertical line (solid white)
    ax.axvline(0, color='white', linestyle='-', linewidth=2.0, alpha=0.9)
    
    # Spines - Hide all
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    ax.set_axisbelow(True)
    
    plt.savefig(SHAP_IMAGE, dpi=300, facecolor=bg_color, bbox_inches='tight')
    plt.close()
    print(f"SHAP Plot saved to {SHAP_IMAGE}")

def generate_lime_plot(model, X_train, feature_names, instance_data):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6.5))
    
    # Absolute Black Background
    bg_color = '#000000'
    bar_cyan = '#00D7D7' # Vibrant Cyan
    text_color = '#E2E8F0'
    
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    
    lime_explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=np.array(X_train),
        feature_names=feature_names,
        class_names=['Normal', 'Risk'],
        mode='classification'
    )
    exp = lime_explainer.explain_instance(
        data_row=np.array(instance_data), 
        predict_fn=model.predict_proba
    )
    
    vals = exp.as_list()
    # Sort for horizontal layout as seen in reference
    features = [v[0] for v in vals][::-1]
    weights = [v[1] for v in vals][::-1]
    
    # Plot bars with uniform cyan color as seen in reference
    y_pos = np.arange(len(features))
    ax.barh(y_pos, weights, color=bar_cyan, height=0.7, edgecolor='none', alpha=1.0)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(features, color=text_color, fontsize=12)
    ax.tick_params(axis='x', colors=text_color, labelsize=11)
    
    # Title matching reference
    plt.title("Patient Risk Analysis (Current Status)", 
              color='white', fontsize=20, pad=30, fontweight='normal')
    
    plt.xlabel("Contribution to Risk", color=text_color, fontsize=12, labelpad=10)
    
    # Styling - match reference lines and box
    # Vertical grid lines (x-axis)
    ax.xaxis.grid(True, linestyle='-', alpha=0.3, color='white')
    ax.yaxis.grid(False) # No horizontal lines for LIME
    
    # Visible spines (border)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('#475569') # Slate gray border
        spine.set_linewidth(1.5)
        
    ax.set_axisbelow(True)
        
    plt.tight_layout()
    plt.savefig(LIME_IMAGE, dpi=300, facecolor=bg_color, bbox_inches='tight')
    plt.close()
    print(f"LIME Plot saved to {LIME_IMAGE}")

def generate_now():
    df = load_or_generate_data()
    model, X_train, feature_names = train_model(df)
    
    latest_row = df.iloc[-1]
    instance_vals = latest_row[feature_names]
    
    try:
        generate_shap_plot(model, X_train, instance_vals, feature_names)
    except Exception as e: print(f"SHAP Plot Error: {e}")
    try:
        generate_lime_plot(model, X_train, feature_names, instance_vals)
    except Exception as e: print(f"LIME Plot Error: {e}")
    try:
        run_shap(model, X_train, feature_names, instance_vals)
    except Exception as e: print(f"run_shap Error: {e}")
    try:
        run_lime(model, X_train, feature_names, instance_vals)
    except Exception as e: print(f"run_lime Error: {e}")
    
    try:
        risk_prob = model.predict_proba([instance_vals])[0][1] * 100
        feat_str = ", ".join([f"{k}: {v}" for k,v in instance_vals.items()])
        
        explanation = generate_medical_explanation(risk_prob, feat_str)
        with open(XAI_TEXT, 'w') as f:
            f.write(explanation)
            
        return True
    except Exception as e:
        print(f"Generation Failed: {e}")
        return False

if __name__ == "__main__":
    generate_now()
