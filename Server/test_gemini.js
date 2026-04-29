require("dotenv").config({ path: ".env" });
const { getAIExplanation } = require("./src/services/gemini.service");

async function test() {
    console.log("Testing Gemini API...");
    try {
        const result = await getAIExplanation({
            disease: "Test Disease",
            vitals: { heartRate: 100, spo2: 95 },
            riskLevel: "MODERATE",
            reasons: ["Test Reason"]
        });
        console.log("Result:", result);
    } catch (e) {
        console.error("Error:", e);
    }
}

test();
