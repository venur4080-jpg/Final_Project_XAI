require("dotenv").config({ path: ".env" });
const { GoogleGenerativeAI } = require("@google/generative-ai");

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

async function listModels() {
    try {
        // For google-generative-ai SDK, we typically don't fail on client init.
        // We usually check model by trying to use it or listing if supported (SDK might not expose list directly easily in all versions, but let's try generic approach or just testing known ones).
        // Actually, the SDK doesn't have a simple "listModels" on the client root in all versions, 
        // but we can try to run a simple prompt on a few known candidates.

        const candidates = ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"];

        console.log("Testing model availability...");

        for (const modelName of candidates) {
            console.log(`\nChecking ${modelName}...`);
            try {
                const model = genAI.getGenerativeModel({ model: modelName });
                const result = await model.generateContent("Hello");
                const response = await result.response;
                console.log(`✅ SUCCESS: ${modelName} is working!`);
                console.log("Response:", response.text());
                return; // Found a working one
            } catch (error) {
                console.log(`❌ FAILED: ${modelName}`);
                // console.log(error.message); // Keep it clean
            }
        }
        console.log("\n❌ No working models found in standard list.");

    } catch (error) {
        console.error("Fatal error:", error);
    }
}

listModels();
