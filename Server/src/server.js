require("dotenv").config({ path: ".env" });

const app = require("./app");
const { startLiveSimulation } = require("./services/liveVitals");

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log("Server running on port", PORT);
  startLiveSimulation();
});
