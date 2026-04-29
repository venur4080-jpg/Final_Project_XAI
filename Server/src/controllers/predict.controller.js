const analyzeVitals = require("../services/ruleEngine");
const { getAIExplanation } = require("../services/gemini.service");

exports.predictRisk = async (req, res) => {
  try {
    const { disease, patient, vitals } = req.body;

    if (!disease || !patient || !vitals) {
      return res.status(400).json({ error: "Missing required data" });
    }

    const analysis = analyzeVitals(vitals);

    // 🔮 AI Explanation (XAI Layer)
    const aiExplanation = await getAIExplanation({
      disease,
      vitals,
      riskLevel: analysis.riskLevel,
      reasons: analysis.reasons
    });

    res.json({
      disease,
      patientSummary: {
        age: patient.age,
        bmi: (patient.weight / ((patient.height / 100) ** 2)).toFixed(2)
      },
      vitals,
      prediction: analysis.riskLevel,
      ruleExplanation: analysis.reasons,
      aiExplanation,
      recommendation: getRecommendation(analysis.riskLevel)
    });

  } catch (err) {
  console.error(" GEMINI ERROR FULL:", err);
  res.status(500).json({
    error: "AI explanation failed",
    message: err.message,
    stack: err.stack
  });
}
};

function getRecommendation(riskLevel) {
  if (riskLevel === "HIGH") {
    return "Immediate medical attention is recommended.";
  }
  if (riskLevel === "MODERATE") {
    return "Monitor vitals closely and consult a doctor.";
  }
  return "Vitals are stable. Maintain healthy lifestyle.";
}
