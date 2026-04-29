const analyzeVitals = require("./ruleEngine");
const { getAIExplanation } = require("./gemini.service");


let lastAnalysis = null;

// Patient info (could be dynamic in a real app)
const patient = { name: "John Doe", age: 65 };
const disease = "Congestive Heart Failure";

async function processVitals(vitals) {
    const analysis = analyzeVitals(vitals);

    console.log(`\n[${new Date().toLocaleTimeString()}] 📊 NEW DATA RECEIVED`);
    console.log(`Vitals: HR ${vitals.heartRate} bpm | SpO2 ${vitals.spo2}% | Temp ${vitals.temperature}°C`);
    console.log(`Risk Level: ${analysis.riskLevel}`);

    let aiExplanation = null;
    try {
        aiExplanation = await getAIExplanation({
            disease,
            vitals,
            riskLevel: analysis.riskLevel,
            reasons: analysis.reasons
        });

        console.log(`🔮 AI EXPLANATION: ${aiExplanation}`);
    } catch (err) {
        console.error("❌ Failed to get AI explanation:", err.message);
    }

    lastAnalysis = {
        timestamp: new Date().toISOString(),
        vitals,
        analysis,
        aiExplanation
    };

    return lastAnalysis;
}

function startLiveSimulation() {
    console.log("-----------------------------------------");
    console.log("🩺 Live Vitals Monitoring Started (Simulation)");
    console.log("-----------------------------------------");

    // Run simulation every 15 seconds
    setInterval(async () => {
        // Generate random vitals with occasional high risk
        const vitals = {
            heartRate: Math.floor(Math.random() * (130 - 60) + 60),
            spo2: Math.floor(Math.random() * (100 - 88) + 88),
            temperature: (Math.random() * (39 - 36.5) + 36.5).toFixed(1)
        };

        await processVitals(vitals);
        console.log("-----------------------------------------");
    }, 15000);
}

module.exports = { startLiveSimulation, getLastAnalysis: () => lastAnalysis, processVitals };
