const express = require("express");
const cors = require("cors");

const predictRoutes = require("./routes/predict.routes");
const vitalsRoutes = require("./routes/vitals.routes");
const { getLastAnalysis } = require("./services/liveVitals");

const app = express();

app.use(cors());
app.use(express.json());

app.use("/api/predict", predictRoutes);
app.use("/api/vitals", vitalsRoutes);

app.get("/api/live-vitals", (req, res) => {
  const analysis = getLastAnalysis();
  if (!analysis) {
    return res.status(404).json({ message: "No live data available yet" });
  }
  res.json(analysis);
});

app.get("/", (req, res) => {
  res.send("Health XAI Backend is running");
});

module.exports = app;
