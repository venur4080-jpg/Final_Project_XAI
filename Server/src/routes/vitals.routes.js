const express = require("express");
const router = express.Router();
const { processVitals } = require("../services/liveVitals");

// POST /api/vitals - Receive vitals from ESP32
router.post("/", async (req, res) => {
    try {
        const { heartRate, spo2, temperature } = req.body;

        if (!heartRate || !spo2 || !temperature) {
            return res.status(400).json({ message: "Missing vital signs data" });
        }

        // Process data (analyze + AI explanation)
        const result = await processVitals({
            heartRate: Number(heartRate),
            spo2: Number(spo2),
            temperature: Number(temperature)
        });

        res.status(200).json({ message: "Data received", result });
    } catch (error) {
        console.error("Error processing vitals:", error);
        res.status(500).json({ message: "Internal server error" });
    }
});

module.exports = router;
