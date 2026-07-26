const chatBox = document.getElementById("chatBox");

async function askQuestion() {

    const input = document.getElementById("question");

    const question = input.value.trim();

    if (question === "") return;

    chatBox.innerHTML += `
        <div class="message">
            <span class="user">You:</span><br>
            ${question}
        </div>
    `;

    input.value = "";

    chatBox.innerHTML += `
        <div class="message" id="loading">
            <span class="bot">Pocket C.A.:</span><br>
            Thinking...
        </div>
    `;

    chatBox.scrollTop = chatBox.scrollHeight;

    try {

        const response = await fetch("http://127.0.0.1:8000/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                question: question
            })

        });

        const data = await response.json();

        document.getElementById("loading").remove();

        chatBox.innerHTML += `
            <div class="message">
                <span class="bot">Pocket C.A.:</span><br>
                ${data.answer}
            </div>
        `;

    } catch (err) {

        document.getElementById("loading").remove();

        chatBox.innerHTML += `
            <div class="message">
                <span class="bot">Pocket C.A.:</span><br>
                Error connecting to backend.
            </div>
        `;
    }

    chatBox.scrollTop = chatBox.scrollHeight;
}

document.getElementById("question").addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
        askQuestion();
    }
});