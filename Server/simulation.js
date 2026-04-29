require("dotenv").config({ path: ".env" });
const analyzeVitals = require("./src/services/ruleEngine");
const { getAIExplanation } = require("./src/services/gemini.service");

async function simulatePatient() {
    const patient = {
        name: "John Doe",
        age: 65,
        weight: 85,
        height: 175
    };

    const disease = "Congestive Heart Failure";

    // Simulate some high-risk vitals
    const vitals = {
        heartRate: 110,
        spo2: 91,
        temperature: 38.2
    };

    console.log("-------------------------------------------");
    console.log("🏥 HEALTH MONITORING SYSTEM - XAI SIMULATION");
    console.log("-------------------------------------------");
    console.log(`👤 Patient: ${patient.name} (${patient.age} years)`);
    console.log(`📋 Condition: ${disease}`);
    console.log(`💓 Heart Rate: ${vitals.heartRate} bpm`);
    console.log(`🫁 SpO2: ${vitals.spo2}%`);
    console.log(`🌡️ Temp: ${vitals.temperature}°C`);
    console.log("-------------------------------------------");

    const analysis = analyzeVitals(vitals);

    console.log(`🔍 Prediction: ${analysis.riskLevel}`);
    console.log(`📝 Rule-based reasons: ${analysis.reasons.join(", ")}`);
    console.log("-------------------------------------------");

    console.log("🧠 Generating AI Explanation...");
    const aiExplanation = await getAIExplanation({
        disease,
        vitals,
        riskLevel: analysis.riskLevel,
        reasons: analysis.reasons
    });

    console.log("-------------------------------------------");
    console.log("🔮 AI EXPLANATION (XAI):");
    console.log(aiExplanation);
    console.log("-------------------------------------------");
}

simulatePatient();
