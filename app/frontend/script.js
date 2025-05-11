document.addEventListener("DOMContentLoaded", () => {
    const uploadForm = document.getElementById("uploadForm");
    if (!uploadForm) {
        console.error("Upload form not found!");
        alert("Error: Upload form not found!");
        return;
    }

    uploadForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        console.log("Form submitted");

        const fileInput = document.getElementById("fileUpload");
        const resultContainer = document.getElementById("resultContainer");
        const subtitleText = document.getElementById("subtitleText");
        const copyButton = document.getElementById("copyButton");
        const downloadLink = document.getElementById("downloadLink");
        const loading = document.getElementById("loading");
        const file = fileInput.files[0];

        if (!file) {
            alert("Please select a file!");
            console.error("No file selected");
            return;
        }

        console.log(`Uploading file: ${file.name}, Size: ${file.size} bytes`);
        loading.style.display = "block";
        resultContainer.style.display = "none";
        subtitleText.textContent = "";
        copyButton.style.display = "none";
        downloadLink.style.display = "none";

        const formData = new FormData();
        formData.append("file", file);

        try {
            console.log("Sending request to http://localhost:8000/transcribe");
            const response = await fetch("http://localhost:8000/transcribe", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("Response received:", data);

            loading.style.display = "none";

            if (data.error) {
                alert("Error: " + data.error);
                console.error("Server error:", data.error);
            } else {
                // Xử lý chuỗi phiên âm (có thể là các đoạn nhỏ của từng chunk)
                const subtitles = data.text.split("\n"); // Giả sử mỗi chunk trả về một dòng mới
                subtitleText.textContent = subtitles.join("\n\n"); // Hiển thị mỗi chunk trên một dòng mới
                resultContainer.style.display = "block";
                copyButton.style.display = "inline";
                
                const blob = new Blob([subtitleText.textContent], { type: "text/plain" });
                const url = window.URL.createObjectURL(blob);
                downloadLink.href = url;
                downloadLink.download = "transcription.txt";
                downloadLink.style.display = "inline";
            }
        } catch (error) {
            loading.style.display = "none";
            alert("Error: " + error.message);
            console.error("Fetch error:", error);
        }
    });
});

function copyToClipboard() {
    const subtitleText = document.getElementById("subtitleText");
    const textarea = document.createElement("textarea");
    textarea.value = subtitleText.textContent;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    alert("Text copied to clipboard!");
}
