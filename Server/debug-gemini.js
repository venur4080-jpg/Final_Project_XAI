const { GoogleGenerativeAI } = require("@google/generative-ai");
require("dotenv").config({ path: ".env" });

const apiKey = process.env.GEMINI_API_KEY || "AIzaSyAngc__ZWSN5JxG5vPvceJZtHxUCIcpKYg";
const genAI = new GoogleGenerativeAI(apiKey);

async function testModel(modelName, apiVersion) {
    console.log(`--- Testing Model: ${modelName} (API: ${apiVersion || 'default'}) ---`);
    try {
        const model = genAI.getGenerativeModel({ model: modelName }, { apiVersion });
        const result = await model.generateContent("Hello");
        const response = await result.response;
        console.log(`✅ ${modelName} SUCCESS:`, response.text());
        return true;
    } catch (err) {
        console.error(`❌ ${modelName} FAILED:`, err.message);
        if (err.response) {
            console.error(`Status: ${err.response.status}, StatusText: ${err.response.statusText}`);
        }
        return false;
    }
}

async function runTests() {
    const models = ["gemini-2.0-flash", "gemini-flash-latest", "gemini-pro-latest"];
    for (const m of models) {
        await testModel(m);
        await testModel(m, "v1beta");
    }
}


runTests();


