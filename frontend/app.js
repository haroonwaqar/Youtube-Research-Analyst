
// ━━━ Configuration ━━━
const API_BASE = window.location.origin;
const STORAGE_KEY = "yt-analyst-chat-history";

// ━━━ DOM Elements ━━━
const sidebar = document.getElementById("sidebar");
const sidebarBackdrop = document.getElementById("sidebar-backdrop");
const mobileMenuBtn = document.getElementById("mobile-menu-btn");
const closeSidebarBtn = document.getElementById("close-sidebar-btn");
const urlInput = document.getElementById("url-input");
const processBtn = document.getElementById("process-btn");
const btnLabel = processBtn.querySelector(".btn-label");
const btnLoader = processBtn.querySelector(".btn-loader");
const videoInfo = document.getElementById("video-info");
const videoThumbnail = document.getElementById("video-thumbnail");
const videoTitle = document.getElementById("video-title");
const videoAuthor = document.getElementById("video-author");
const statusMsg = document.getElementById("status-msg");
const messagesContainer = document.getElementById("messages");
const welcomeScreen = document.getElementById("welcome");
const questionInput = document.getElementById("question-input");
const sendBtn = document.getElementById("send-btn");
const charCount = document.getElementById("char-count");
const exportBtn = document.getElementById("export-btn");
const themeBtn = document.getElementById("theme-btn");

// ━━━ State ━━━
let currentUrl = "";
let isProcessing = false;
let isAsking = false;

// VIDEO PROCESSING
async function processVideo() {
    const url = urlInput.value.trim();
    if (!url) return;

    // If the URL changed, clear the old conversation
    if (url !== currentUrl) {
        clearChat();
    }

    isProcessing = true;
    setProcessingUI(true);
    hideStatus();

    try {
        // Fetch video metadata (title, thumbnail) in parallel
        fetchVideoInfo(url);

        // Process the video (transcript → chunks → embeddings)
        const res = await fetch(`${API_BASE}/api/process-video`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to process video");
        }

        const data = await res.json();
        currentUrl = url;

        showStatus(`Ready — ${data.chunk_count} transcript chunks indexed.`, "success");
        enableChat();

        // Save the current URL for chat history
        saveChatMeta();

    } catch (err) {
        showStatus(err.message, "error");
    } finally {
        isProcessing = false;
        setProcessingUI(false);
    }
}

async function fetchVideoInfo(url) {
    try {
        const res = await fetch(`${API_BASE}/api/video-info`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });

        const data = await res.json();

        if (data.title) {
            videoThumbnail.src = data.thumbnail;
            videoThumbnail.alt = data.title;
            videoTitle.textContent = data.title;
            videoAuthor.textContent = data.author;
            videoInfo.classList.remove("hidden");
        }
    } catch {
        // Metadata is optional — silently ignore failures
    }
}


// CHAT — SENDING QUESTIONS & STREAMING RESPONSES
async function sendMessage() {
    const question = questionInput.value.trim();
    if (!question || !currentUrl || isAsking) return;

    isAsking = true;
    sendBtn.disabled = true;

    // Hide welcome screen on first message
    if (welcomeScreen) {
        welcomeScreen.classList.add("hidden");
    }

    // Add user message
    addMessage("user", question);
    questionInput.value = "";
    updateCharCount();
    autoResize(questionInput);

    // Add assistant placeholder with typing indicator
    const assistantEl = addMessage("assistant", "");
    const contentEl = assistantEl.querySelector(".message-content");
    contentEl.innerHTML = createTypingIndicator();

    let fullResponse = "";

    try {
        // Stream the response via SSE
        const res = await fetch(`${API_BASE}/api/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: currentUrl, question }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to get answer");
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        // Read SSE stream
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value, { stream: true });
            const lines = text.split("\n");

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;

                try {
                    const payload = JSON.parse(line.slice(6));

                    if (payload.token) {
                        fullResponse += payload.token;
                        // Render markdown as it streams in
                        contentEl.innerHTML = marked.parse(fullResponse);
                        scrollToBottom();
                    }

                    if (payload.done) {
                        // Final render
                        contentEl.innerHTML = marked.parse(fullResponse);
                    }

                    if (payload.error) {
                        throw new Error(payload.error);
                    }
                } catch (parseErr) {
                    if (parseErr.message !== "Unexpected end of JSON input") {
                        throw parseErr;
                    }
                }
            }
        }

        // Save to chat history
        saveChatHistory();

    } catch (err) {
        contentEl.innerHTML = `<span style="color: var(--error);">${err.message}</span>`;
    } finally {
        isAsking = false;
        sendBtn.disabled = false;
        exportBtn.classList.remove("hidden");
        questionInput.focus();
    }
}


/**
 * Send a question programmatically (used by chips and auto-summary).
 * Works like sendMessage() but takes the question as a parameter
 * instead of reading from the textarea.
 */
async function sendAutoQuestion(question) {
    if (!question || !currentUrl || isAsking) return;

    isAsking = true;
    sendBtn.disabled = true;

    if (welcomeScreen) {
        welcomeScreen.classList.add("hidden");
    }

    addMessage("user", question);

    const assistantEl = addMessage("assistant", "");
    const contentEl = assistantEl.querySelector(".message-content");
    contentEl.innerHTML = createTypingIndicator();

    let fullResponse = "";

    try {
        const res = await fetch(`${API_BASE}/api/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: currentUrl, question }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to get answer");
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value, { stream: true });
            const lines = text.split("\n");

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                try {
                    const payload = JSON.parse(line.slice(6));
                    if (payload.token) {
                        fullResponse += payload.token;
                        contentEl.innerHTML = marked.parse(fullResponse);
                        scrollToBottom();
                    }
                    if (payload.done) {
                        contentEl.innerHTML = marked.parse(fullResponse);
                    }
                    if (payload.error) {
                        throw new Error(payload.error);
                    }
                } catch (parseErr) {
                    if (parseErr.message !== "Unexpected end of JSON input") {
                        throw parseErr;
                    }
                }
            }
        }

        saveChatHistory();

    } catch (err) {
        contentEl.innerHTML = `<span style="color: var(--error);">${err.message}</span>`;
    } finally {
        isAsking = false;
        sendBtn.disabled = false;
        exportBtn.classList.remove("hidden");
        questionInput.focus();
    }
}


// UI HELPERS
function addMessage(role, content) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = role === "user" ? "Y" : "AI";

    const contentEl = document.createElement("div");
    contentEl.className = "message-content";

    if (role === "assistant" && content) {
        contentEl.innerHTML = marked.parse(content);
    } else {
        contentEl.textContent = content;
    }

    wrapper.appendChild(avatar);
    wrapper.appendChild(contentEl);
    messagesContainer.appendChild(wrapper);
    scrollToBottom();
    return wrapper;
}

function createTypingIndicator() {
    return `<div class="typing-indicator">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
    </div>`;
}

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function setProcessingUI(loading) {
    processBtn.disabled = loading;
    urlInput.disabled = loading;
    btnLabel.classList.toggle("hidden", loading);
    btnLoader.classList.toggle("hidden", !loading);
}

function enableChat() {
    questionInput.disabled = false;
    sendBtn.disabled = false;
    enableQuickChips();
    questionInput.focus();
}

function clearChat() {
    // Remove all message elements but keep the welcome screen
    const messages = messagesContainer.querySelectorAll(".message");
    messages.forEach((el) => el.remove());

    // Show welcome screen again
    if (welcomeScreen) {
        welcomeScreen.classList.remove("hidden");
    }

    // Hide export button and quick chips
    exportBtn.classList.add("hidden");
    disableQuickChips();

    // Clear stored history
    sessionStorage.removeItem(STORAGE_KEY);
}

function showStatus(text, type) {
    statusMsg.textContent = text;
    statusMsg.className = `status-msg ${type}`;
    statusMsg.classList.remove("hidden");
}

function hideStatus() {
    statusMsg.classList.add("hidden");
}

function updateCharCount() {
    const len = questionInput.value.length;
    charCount.textContent = `${len}/500`;
    charCount.style.color = len > 450 ? "var(--error)" : "var(--text-tertiary)";
}

function autoResize(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
}


// EXPORT CHAT — Download
function exportChat() {
    const messageEls = messagesContainer.querySelectorAll(".message");
    if (messageEls.length === 0) return;

    const title = videoTitle.textContent || "YouTube Video";

    // Build clean HTML for printing as PDF
    let content = "";
    messageEls.forEach((el) => {
        const role = el.classList.contains("user") ? "user" : "assistant";
        const contentEl = el.querySelector(".message-content");

        if (role === "user") {
            content += `<div style="margin:20px 0 8px;padding:10px 16px;background:#0A84FF;color:#fff;border-radius:10px;display:inline-block;font-weight:600;">${contentEl.textContent}</div>`;
        } else {
            content += `<div style="margin:0 0 20px;padding:16px;background:#f5f5f7;border-radius:10px;line-height:1.7;color:#1d1d1f;">${contentEl.innerHTML}</div>`;
        }
    });

    const html = `<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>Research Notes — ${title}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 24px; color: #1d1d1f; }
  h1 { font-size: 24px; margin-bottom: 4px; }
  .meta { color: #86868b; font-size: 13px; margin-bottom: 24px; }
  .meta a { color: #0A84FF; text-decoration: none; }
  hr { border: none; border-top: 1px solid #e5e5e5; margin: 24px 0; }
  @media print { body { padding: 0; } }
</style>
</head><body>
<h1>🎥 ${title}</h1>
<div class="meta"><a href="${currentUrl}">${currentUrl}</a> · Exported ${new Date().toLocaleDateString()}</div>
<hr>
${content}
<hr>
<div class="meta" style="text-align:center;">Generated by YouTube Research Analyst</div>
</body></html>`;

    // Open in new window for printing (Cmd+P → Save as PDF)
    const printWindow = window.open("", "_blank");
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    // Small delay to let content render before print dialog
    setTimeout(() => printWindow.print(), 400);
}

function enableQuickChips() {
    const quickChips = document.getElementById("quick-chips");
    if (quickChips) quickChips.classList.remove("hidden");
}

function disableQuickChips() {
    const quickChips = document.getElementById("quick-chips");
    if (quickChips) quickChips.classList.add("hidden");
}

function saveChatMeta() {
    const history = { url: currentUrl, messages: [] };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

function saveChatHistory() {
    const messageEls = messagesContainer.querySelectorAll(".message");
    const messages = [];

    messageEls.forEach((el) => {
        const role = el.classList.contains("user") ? "user" : "assistant";
        const contentEl = el.querySelector(".message-content");
        // Store raw text for user messages, HTML for assistant (since it's already rendered markdown)
        const content = role === "user"
            ? contentEl.textContent
            : contentEl.innerHTML;
        messages.push({ role, content });
    });

    const history = { url: currentUrl, messages };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

function loadChatHistory() {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        if (!raw) return;

        const history = JSON.parse(raw);
        if (!history.url || !history.messages || history.messages.length === 0) return;

        // Restore URL
        currentUrl = history.url;
        urlInput.value = history.url;

        // Restore messages
        welcomeScreen.classList.add("hidden");
        history.messages.forEach(({ role, content }) => {
            const el = addMessage(role, "");
            const contentEl = el.querySelector(".message-content");
            if (role === "assistant") {
                contentEl.innerHTML = content; // Already rendered HTML
            } else {
                contentEl.textContent = content;
            }
        });

        // Fetch video info & re-process video in background
        fetchVideoInfo(history.url);
        reprocessVideo(history.url);

    } catch {
        sessionStorage.removeItem(STORAGE_KEY);
    }
}

async function reprocessVideo(url) {
    // Silently re-process the video so the cache is warm
    // This is needed because the in-memory ChromaDB is lost on server restart
    try {
        const res = await fetch(`${API_BASE}/api/process-video`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });

        if (res.ok) {
            enableChat();
            showStatus("Session restored — ready to chat.", "success");
        }
    } catch {
        showStatus("Please re-analyze the video to continue.", "error");
    }
}


// EVENT LISTENERS

// Process video button
processBtn.addEventListener("click", processVideo);

// Also process on Enter in URL field
urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !isProcessing) {
        processVideo();
    }
});

// Send message button
sendBtn.addEventListener("click", sendMessage);

// Enter to send, Shift+Enter for newline
questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Character counter & auto-resize
questionInput.addEventListener("input", () => {
    updateCharCount();
    autoResize(questionInput);
});

// Suggested question chips (welcome screen)
document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        const question = chip.getAttribute("data-question");
        if (currentUrl && !isAsking) {
            sendAutoQuestion(question);
        } else if (!currentUrl) {
            showStatus("Please analyze a video first.", "error");
        }
    });
});

// Quick preset chips (above input bar)
document.querySelectorAll(".chip-sm").forEach((chip) => {
    chip.addEventListener("click", () => {
        const question = chip.getAttribute("data-question");
        if (currentUrl && !isAsking) {
            sendAutoQuestion(question);
        }
    });
});

// Export button
exportBtn.addEventListener("click", exportChat);

// Mobile Sidebar Toggle
mobileMenuBtn.addEventListener("click", () => {
    sidebar.classList.add("open");
    sidebarBackdrop.classList.add("show");
});

sidebarBackdrop.addEventListener("click", () => {
    sidebar.classList.remove("open");
    sidebarBackdrop.classList.remove("show");
});

closeSidebarBtn.addEventListener("click", () => {
    sidebar.classList.remove("open");
    sidebarBackdrop.classList.remove("show");
});

// Theme Toggle
function setupTheme() {
    let theme = localStorage.getItem("yt-analyst-theme");
    if (!theme) {
        theme = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }
    document.documentElement.setAttribute("data-theme", theme);
    updateThemeBtn(theme);

    themeBtn.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme");
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("yt-analyst-theme", next);
        updateThemeBtn(next);
    });
}

function updateThemeBtn(theme) {
    if (theme === "dark") {
        themeBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="5"/>
                <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
            Light Mode
        `;
    } else {
        themeBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
            Dark Mode
        `;
    }
}

// Load chat history and theme on page load
document.addEventListener("DOMContentLoaded", () => {
    loadChatHistory();
    setupTheme();
});
