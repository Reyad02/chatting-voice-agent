let audio = null;
const startStopBtn = document.getElementById("startStopBtn");
const statusText = document.getElementById("status");

let isRunning = false;

startStopBtn.addEventListener("click", async () => {
    if (!isRunning) {
        try {
            statusText.innerText = "Connecting...";
            startStopBtn.disabled = true;

            audio = new ag2client.WebsocketAudio(socketUrl);
            await audio.start();

            statusText.innerText = "Live 🎙️";
            startStopBtn.innerText = "Stop Conversation";
            startStopBtn.style.backgroundColor = "#c00"; 
            isRunning = true;
        } catch (error) {
            console.error("Failed to start audio:", error);
            statusText.innerText = "Error starting audio";
        } finally {
            startStopBtn.disabled = false;
        }
    } else {
        try {
            await audio.stop();
            statusText.innerText = "Idle";
            startStopBtn.innerText = "Start Conversation";
            startStopBtn.style.backgroundColor = "#000";
            isRunning = false;
        } catch (error) {
            console.error("Failed to stop audio:", error);
            statusText.innerText = "Error stopping audio";
        }
    }
});