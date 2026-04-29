function analyzeVitals(vitals) {
  let riskScore = 0;
  let reasons = [];

  // Heart Rate
  if (vitals.heartRate > 100) {
    riskScore++;
    reasons.push("Heart rate above normal range");
  }

  // Oxygen Saturation
  if (vitals.spo2 < 94) {
    riskScore++;
    reasons.push("Low oxygen saturation detected");
  }

  // Temperature
  if (vitals.temperature && (vitals.temperature >= 38 || vitals.temperature <= 35)) {
    riskScore++;
    reasons.push("Abnormal body temperature");
  }

  // Risk level mapping
  let riskLevel = "LOW";
  if (riskScore === 1) riskLevel = "MODERATE";
  if (riskScore >= 2) riskLevel = "HIGH";

  return {
    riskLevel,
    riskScore,
    reasons
  };
}

module.exports = analyzeVitals;
