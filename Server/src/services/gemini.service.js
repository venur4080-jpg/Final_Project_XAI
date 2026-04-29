const { GoogleGenerativeAI } = require("@google/generative-ai");

if (!process.env.GEMINI_API_KEY) {
  throw new Error("GEMINI_API_KEY missing");
}

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

async function getAIExplanation({ disease, vitals, riskLevel, reasons }) {
  const prompt = `
A patient is admitted with ${disease}.
Heart Rate: ${vitals.heartRate}
SpO2: ${vitals.spo2}
Risk Level: ${riskLevel}
Reasons: ${reasons.join(", ")}

Explain this risk level in simple medical terms.
`;

  try {
    const result = await model.generateContent(prompt);
    const response = await result.response;
    return response.text();
  } catch (error) {
    console.warn(`⚠️ Gemini API Error: ${error.message} (Using Simulation)`);

    // Fallback simulated explanation
    if (riskLevel === "HIGH") {
      return `The patient's current vitals (Heart Rate: ${vitals.heartRate}, SpO2: ${vitals.spo2}) indicate a high risk level. This is primarily due to ${reasons.join(" and ")}. Immediate medical intervention is advised to stabilize the patient's condition.`;
    } else if (riskLevel === "MODERATE") {
      return `The patient's vitals show some abnormalities: ${reasons.join(", ")}. While not critical yet, close monitoring is required to prevent further deterioration.`;
    } else {
      return "The patient's vitals are currently within stable ranges. Continue routine monitoring.";
    }
  }
}

module.exports = { getAIExplanation };
