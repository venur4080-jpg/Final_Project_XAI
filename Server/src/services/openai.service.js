const OpenAI = require("openai");

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

async function getAIExplanation({ disease, vitals, riskLevel, reasons }) {
  const prompt = `
A patient is admitted with ${disease}.
Heart Rate: ${vitals.heartRate}
SpO2: ${vitals.spo2}
Risk Level: ${riskLevel}
Reasons: ${reasons.join(", ")}

Explain this risk level in simple medical terms.
`;

  const response = await client.responses.create({
    model: "gpt-3.5-turbo",
    input: prompt
  });

  return response.output_text;
}

module.exports = { getAIExplanation };
