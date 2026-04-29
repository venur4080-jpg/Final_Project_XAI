const express = require("express");
const router = express.Router();

const { predictRisk } = require("../controllers/predict.controller");

router.post("/", predictRisk);

module.exports = router;
