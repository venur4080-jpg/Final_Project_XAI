const axios = require("axios");

axios.post("http://localhost:5000/api/predict", {
  disease: "Heart Failure",
  vitals: {
    heartRate: 120,
    spo2: 90
  },
  patient: {
    age: 65,
    weight: 80,
    height: 175
  },
  riskLevel: "HIGH",
  reasons: [
    "Heart rate above normal range",
    "Low oxygen saturation detected"
  ]
})
  .then(res => {
    console.log("✅ RESPONSE:");
    console.log(res.data);
  })
  .catch(err => {
    console.error("❌ ERROR:");
    console.error(err.response?.data || err.message);
  });
