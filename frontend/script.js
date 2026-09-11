/**
 * Pocket C.A. - Modern AI Financial Advisor Frontend
 */

// Auto-detect: use local backend when running locally, Render backend when deployed
const isLocal = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost" || window.location.protocol === "file:";
const PRODUCTION_URL = "https://pocketca-9q42.onrender.com";
const LOCAL_URL = "http://127.0.0.1:8000";
let BACKEND_URL = isLocal ? LOCAL_URL : PRODUCTION_URL;
let currentSessionId = localStorage.getItem("pocketca_session_id") || generateUUID();
let currentMessages = [];

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
    localStorage.setItem("pocketca_session_id", currentSessionId);
    checkBackendHealth();
    renderSessionList();
    loadSessionHistory(currentSessionId);
});

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// --------------------------------------------------------------------------
// Backend Health Check
// --------------------------------------------------------------------------
async function checkBackendHealth() {
    const statusText = document.getElementById("backendStatus");
    const statusMeta = document.getElementById("statusMeta");
    const statusDot = document.querySelector(".pulse-dot");

    try {
        const res = await fetch(`${BACKEND_URL}/`);
        if (res.ok) {
            const data = await res.json();
            statusText.textContent = "Pocket C.A. Online";
            statusDot.style.backgroundColor = "#10B981";
            statusDot.style.boxShadow = "0 0 8px #10B981";
            
            const chunks = data.knowledge_base?.total_chunks || 0;
            const apiSet = data.api_key_configured;
            statusMeta.textContent = `KB: ${chunks} chunks | AI: ${apiSet ? 'Active' : 'Local Mode'}`;
        } else {
            throw new Error();
        }
    } catch (err) {
        statusText.textContent = "Backend Offline";
        statusDot.style.backgroundColor = "#EF4444";
        statusDot.style.boxShadow = "0 0 8px #EF4444";
        statusMeta.textContent = "Start FastAPI server on :8000";
    }
}

// --------------------------------------------------------------------------
// View & Navigation Switching
// --------------------------------------------------------------------------
function switchView(viewName) {
    document.getElementById("chatView").classList.remove("active");
    document.getElementById("toolsView").classList.remove("active");
    document.getElementById("navChat").classList.remove("active");
    document.getElementById("navTools").classList.remove("active");

    if (viewName === "chat") {
        document.getElementById("chatView").classList.add("active");
        document.getElementById("navChat").classList.add("active");
        document.getElementById("viewTitle").textContent = "Chartered Accountant Advisory";
    } else if (viewName === "tools") {
        document.getElementById("toolsView").classList.add("active");
        document.getElementById("navTools").classList.add("active");
        document.getElementById("viewTitle").textContent = "Financial Calculators & Tax Slabs";
    }

    if (window.innerWidth <= 768) {
        document.getElementById("sidebar").classList.remove("open");
    }
}

function switchToolTab(tabId) {
    document.querySelectorAll(".tool-tab").forEach(tab => tab.classList.remove("active"));
    document.querySelectorAll(".tool-card").forEach(card => card.classList.remove("active"));

    // Find clicked tab
    const tabs = document.querySelectorAll(".tool-tab");
    const card = document.getElementById(`tool-${tabId}`);
    if (card) card.classList.add("active");

    event.target.classList.add("active");
}

function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("open");
}

// --------------------------------------------------------------------------
// Session Management
// --------------------------------------------------------------------------
function getSessions() {
    return JSON.parse(localStorage.getItem("pocketca_sessions") || "[]");
}

function saveSessions(sessions) {
    localStorage.setItem("pocketca_sessions", JSON.stringify(sessions));
    renderSessionList();
}

function renderSessionList() {
    const list = document.getElementById("historyList");
    const sessions = getSessions();
    list.innerHTML = "";

    if (sessions.length === 0) {
        list.innerHTML = `<span style="font-size:11.5px;color:var(--text-muted);padding-left:8px;">No previous sessions</span>`;
        return;
    }

    sessions.forEach(sess => {
        const item = document.createElement("div");
        item.className = `history-item ${sess.id === currentSessionId ? 'active' : ''}`;
        item.textContent = sess.title || "Consultation";
        item.onclick = () => switchSession(sess.id);
        list.appendChild(item);
    });
}

function startNewChat() {
    currentSessionId = generateUUID();
    localStorage.setItem("pocketca_session_id", currentSessionId);
    currentMessages = [];
    
    const chatBox = document.getElementById("chatBox");
    chatBox.innerHTML = "";
    
    // Restore welcome banner
    const banner = createWelcomeBanner();
    chatBox.appendChild(banner);
    
    switchView("chat");
    renderSessionList();
}

function switchSession(sessionId) {
    currentSessionId = sessionId;
    localStorage.setItem("pocketca_session_id", currentSessionId);
    switchView("chat");
    renderSessionList();
    loadSessionHistory(sessionId);
}

async function loadSessionHistory(sessionId) {
    try {
        const res = await fetch(`${BACKEND_URL}/history/${sessionId}`);
        if (res.ok) {
            const data = await res.json();
            const chatBox = document.getElementById("chatBox");
            chatBox.innerHTML = "";

            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    appendMessageUI(msg.role, msg.content, msg.sources, false);
                });
                chatBox.scrollTop = chatBox.scrollHeight;
            } else {
                chatBox.appendChild(createWelcomeBanner());
            }
        }
    } catch (err) {
        console.warn("Could not load remote history:", err);
    }
}

async function clearCurrentChat() {
    if (!confirm("Are you sure you want to clear this consultation?")) return;
    try {
        await fetch(`${BACKEND_URL}/history/${currentSessionId}`, { method: "DELETE" });
    } catch (e) {}

    // Remove from local sessions
    let sessions = getSessions().filter(s => s.id !== currentSessionId);
    saveSessions(sessions);
    startNewChat();
}

function exportChat() {
    if (currentMessages.length === 0) {
        alert("No messages to export.");
        return;
    }

    let markdownContent = `# Pocket C.A. Consultation Summary\nSession ID: ${currentSessionId}\nDate: ${new Date().toLocaleString()}\n\n---\n\n`;
    currentMessages.forEach(m => {
        markdownContent += `### ${m.role === 'user' ? 'Client' : 'Pocket C.A.'}\n\n${m.content}\n\n`;
        if (m.sources && m.sources.length) {
            markdownContent += `*Sources: ${m.sources.join(", ")}*\n\n`;
        }
        markdownContent += `---\n\n`;
    });

    const blob = new Blob([markdownContent], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `PocketCA-Consultation-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

// --------------------------------------------------------------------------
// Chat Logic
// --------------------------------------------------------------------------
function formatMarkdown(text) {
    if (window.marked) {
        try {
            return marked.parse(text);
        } catch (e) {}
    }
    // Fallback simple parser
    let escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return `<p>${escaped.replace(/\n\n/g, "</p><p>").replace(/\n/g, "<br>")}</p>`;
}

function appendMessageUI(role, content, sources = [], animate = true) {
    const chatBox = document.getElementById("chatBox");
    const welcome = document.getElementById("welcomeBanner");
    if (welcome) welcome.remove();

    const isUser = role === "user";
    const row = document.createElement("div");
    row.className = `message-row ${isUser ? 'user-row' : 'bot-row'}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = isUser ? "U" : "CA";

    const wrapper = document.createElement("div");
    wrapper.className = "message-content-wrapper";

    const header = document.createElement("div");
    header.className = "message-header";
    header.innerHTML = `
        <span class="sender-name">${isUser ? 'You' : 'Pocket C.A.'}</span>
        <span class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
    `;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = formatMarkdown(content);

    // Append source citations if available
    if (sources && sources.length > 0) {
        const sourcesBar = document.createElement("div");
        sourcesBar.className = "sources-bar";
        sourcesBar.innerHTML = `<span style="font-size:11px;color:var(--text-muted);font-weight:600;">Statutory References:</span>`;
        sources.forEach(src => {
            const badge = document.createElement("span");
            badge.className = "source-badge";
            badge.innerHTML = `📚 ${src}`;
            sourcesBar.appendChild(badge);
        });
        bubble.appendChild(sourcesBar);
    }

    wrapper.appendChild(header);
    wrapper.appendChild(bubble);

    // Action button (Copy)
    if (!isUser) {
        const actions = document.createElement("div");
        actions.className = "message-actions";
        const copyBtn = document.createElement("button");
        copyBtn.className = "copy-btn";
        copyBtn.textContent = "Copy";
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(content);
            copyBtn.textContent = "Copied!";
            setTimeout(() => copyBtn.textContent = "Copy", 1500);
        };
        actions.appendChild(copyBtn);
        wrapper.appendChild(actions);
    }

    row.appendChild(avatar);
    row.appendChild(wrapper);
    chatBox.appendChild(row);

    chatBox.scrollTop = chatBox.scrollHeight;
    currentMessages.push({ role, content, sources });
}

function showTypingIndicator() {
    const chatBox = document.getElementById("chatBox");
    const row = document.createElement("div");
    row.className = "message-row bot-row";
    row.id = "typingIndicator";

    row.innerHTML = `
        <div class="message-avatar">CA</div>
        <div class="message-content-wrapper">
            <div class="message-header">
                <span class="sender-name">Pocket C.A.</span>
                <span class="message-time">Computing...</span>
            </div>
            <div class="message-bubble">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById("typingIndicator");
    if (indicator) indicator.remove();
}

async function askQuestion() {
    const input = document.getElementById("question");
    const question = input.value.trim();
    if (!question) return;

    input.value = "";
    autoResize(input);

    // Add user message to UI
    appendMessageUI("user", question);

    // Update session title in list if this is the first message
    let sessions = getSessions();
    let curr = sessions.find(s => s.id === currentSessionId);
    if (!curr) {
        let title = question.slice(0, 30) + (question.length > 30 ? "..." : "");
        sessions.unshift({ id: currentSessionId, title, timestamp: Date.now() });
        saveSessions(sessions);
    }

    showTypingIndicator();

    try {
        const response = await fetch(`${BACKEND_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: question,
                session_id: currentSessionId,
                use_rag: true
            })
        });

        const data = await response.json();
        removeTypingIndicator();

        if (response.ok) {
            appendMessageUI("assistant", data.answer, data.sources || []);
        } else {
            appendMessageUI("assistant", `⚠️ **Error from server:** ${data.detail || 'An unexpected error occurred.'}`);
        }
    } catch (err) {
        removeTypingIndicator();
        appendMessageUI("assistant", `⚠️ **Could not connect to backend server at ${BACKEND_URL}.**\nPlease ensure the FastAPI server is running (\`uvicorn main:app --reload\`).`);
    }
}

function sendSuggestion(text) {
    document.getElementById("question").value = text;
    askQuestion();
}

function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        askQuestion();
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function createWelcomeBanner() {
    const banner = document.createElement("div");
    banner.className = "welcome-banner";
    banner.id = "welcomeBanner";
    banner.innerHTML = `
        <div class="welcome-badge">ICAI Compliance & Tax Advisory</div>
        <h2>Namaste! I am your AI Chartered Accountant.</h2>
        <p>Ask me any question regarding Indian Accounting, GST, Income Tax (New vs Old Slabs), TDS deductions, Financial Statements, or Balance Sheet preparation.</p>
        <div class="suggestion-grid">
            <button class="suggestion-chip" onclick="sendSuggestion('Compare Old vs New Tax Regime for ₹12 Lakh salary under FY 2024-25')">
                📊 <strong>Tax Comparison</strong>: Old vs New Regime for ₹12L
            </button>
            <button class="suggestion-chip" onclick="sendSuggestion('Calculate 18% GST on ₹75,000 exclusive with CGST and SGST breakdown')">
                🧾 <strong>GST Calculation</strong>: ₹75,000 @ 18%
            </button>
            <button class="suggestion-chip" onclick="sendSuggestion('What are the four mandatory conditions to claim Input Tax Credit (ITC) under Section 16?')">
                📑 <strong>ITC Rules</strong>: Section 16 Conditions
            </button>
            <button class="suggestion-chip" onclick="sendSuggestion('What is the TDS rate and threshold under Section 194J for professional fees?')">
                💼 <strong>TDS Slabs</strong>: Section 194J Rates
            </button>
            <button class="suggestion-chip" onclick="sendSuggestion('Provide the standard double-entry journal entry for purchasing machinery of ₹2,00,000 on credit with 18% GST')">
                ✍️ <strong>Journal Entry</strong>: Purchase of Machinery
            </button>
            <button class="suggestion-chip" onclick="sendSuggestion('What is the structure of a Balance Sheet under Schedule III of Companies Act 2013?')">
                🏛️ <strong>Balance Sheet</strong>: Schedule III Format
            </button>
        </div>
    `;
    return banner;
}

// --------------------------------------------------------------------------
// Financial Calculators Logic
// --------------------------------------------------------------------------
function formatINR(num) {
    return '₹' + Number(num).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function executeGstCalc() {
    const amount = parseFloat(document.getElementById("gstAmount").value) || 0;
    const rate = parseFloat(document.getElementById("gstRate").value) || 0;
    const taxType = document.getElementById("gstType").value;
    const isInterstate = document.getElementById("gstSupply").value === "inter";
    const resBox = document.getElementById("gstResult");

    try {
        const res = await fetch(`${BACKEND_URL}/tools/gst`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount, rate, tax_type: taxType, is_interstate: isInterstate })
        });
        const data = await res.json();

        resBox.innerHTML = `
            <div class="result-stat-grid">
                <div class="stat-box">
                    <div class="stat-label">Taxable Value</div>
                    <div class="stat-val">${formatINR(data.taxable_value)}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">${isInterstate ? 'IGST (' + rate + '%)' : 'CGST + SGST'}</div>
                    <div class="stat-val" style="color:#60A5FA">${formatINR(data.total_gst)}</div>
                </div>
                <div class="stat-box highlight">
                    <div class="stat-label">Total Invoice Amount</div>
                    <div class="stat-val">${formatINR(data.total_amount)}</div>
                </div>
            </div>
            <div class="recommendation-banner" style="margin-top:14px;background:rgba(37,99,235,0.1);border-color:#3B82F6;color:#93C5FD;">
                ℹ️ ${data.tax_split}
            </div>
            <button class="tool-calc-btn" style="margin-top:12px;background:#334155;font-size:12px;padding:8px 14px;" onclick="sendCalcToChat('${data.summary.replace(/'/g, "\\'")}')">
                Send to Chat Consultation 💬
            </button>
        `;
        resBox.classList.add("visible");
    } catch (e) {
        alert("Failed to compute GST. Ensure backend is running.");
    }
}

async function executeTaxCalc() {
    const grossIncome = parseFloat(document.getElementById("taxGross").value) || 0;
    const financialYear = document.getElementById("taxYear").value;
    const deductions80c = parseFloat(document.getElementById("tax80c").value) || 0;
    const deductions80d = parseFloat(document.getElementById("tax80d").value) || 0;
    const otherDeductions = parseFloat(document.getElementById("taxOther").value) || 0;
    const isSenior = document.getElementById("taxAge").value === "senior";
    const resBox = document.getElementById("taxResult");

    try {
        const res = await fetch(`${BACKEND_URL}/tools/tax`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                gross_income: grossIncome,
                financial_year: financialYear,
                deductions_80c: deductions80c,
                deductions_80d: deductions80d,
                other_deductions: otherDeductions,
                is_senior_citizen: isSenior
            })
        });
        const data = await res.json();
        const nr = data.new_regime;
        const or = data.old_regime;
        const isNewWinner = data.recommendation.optimal_regime.includes("New");

        resBox.innerHTML = `
            <div class="recommendation-banner">
                🏆 <strong>${data.recommendation.optimal_regime}:</strong> ${data.recommendation.summary}
            </div>
            <div class="comparison-wrapper">
                <div class="regime-box ${isNewWinner ? 'winner' : ''}">
                    <div class="regime-title">
                        New Tax Regime (u/s 115BAC)
                        ${isNewWinner ? '<span class="winner-badge">Recommended</span>' : ''}
                    </div>
                    <div class="regime-tax">${formatINR(nr.total_tax_payable)}</div>
                    <div class="regime-row"><span>Standard Deduction</span><span>${formatINR(nr.standard_deduction)}</span></div>
                    <div class="regime-row"><span>Net Taxable Income</span><span>${formatINR(nr.net_taxable_income)}</span></div>
                    <div class="regime-row"><span>Base Slab Tax</span><span>${formatINR(nr.base_tax)}</span></div>
                    <div class="regime-row"><span>Section 87A Rebate</span><span style="color:#34D399">-${formatINR(nr.rebate_87a)}</span></div>
                    <div class="regime-row"><span>Health & Education Cess (4%)</span><span>${formatINR(nr.cess_4_percent)}</span></div>
                </div>
                <div class="regime-box ${!isNewWinner ? 'winner' : ''}">
                    <div class="regime-title">
                        Old Tax Regime
                        ${!isNewWinner ? '<span class="winner-badge">Recommended</span>' : ''}
                    </div>
                    <div class="regime-tax">${formatINR(or.total_tax_payable)}</div>
                    <div class="regime-row"><span>Standard Deduction</span><span>${formatINR(or.standard_deduction)}</span></div>
                    <div class="regime-row"><span>Total Deductions (80C/80D)</span><span>${formatINR(or.total_deductions)}</span></div>
                    <div class="regime-row"><span>Net Taxable Income</span><span>${formatINR(or.net_taxable_income)}</span></div>
                    <div class="regime-row"><span>Base Slab Tax</span><span>${formatINR(or.base_tax)}</span></div>
                    <div class="regime-row"><span>Section 87A Rebate</span><span style="color:#34D399">-${formatINR(or.rebate_87a)}</span></div>
                    <div class="regime-row"><span>Health & Education Cess (4%)</span><span>${formatINR(or.cess_4_percent)}</span></div>
                </div>
            </div>
            <button class="tool-calc-btn" style="margin-top:14px;background:#334155;font-size:12px;padding:8px 14px;" onclick="sendCalcToChat('Tax computation for Gross Income ${formatINR(grossIncome)}: ${data.recommendation.summary} (New Regime Tax: ${formatINR(nr.total_tax_payable)} vs Old Regime Tax: ${formatINR(or.total_tax_payable)})')">
                Send Comparison to Chat 💬
            </button>
        `;
        resBox.classList.add("visible");
    } catch (e) {
        alert("Failed to compute tax comparison. Ensure backend is running.");
    }
}

async function executeTdsCalc() {
    const section = document.getElementById("tdsSection").value;
    const amount = parseFloat(document.getElementById("tdsAmount").value) || 0;
    const panAvailable = document.getElementById("tdsPan").value === "yes";
    const payeeType = document.getElementById("tdsPayee").value;
    const resBox = document.getElementById("tdsResult");

    try {
        const res = await fetch(`${BACKEND_URL}/tools/tds`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ section, amount, pan_available: panAvailable, payee_type: payeeType })
        });
        const data = await res.json();

        resBox.innerHTML = `
            <div class="result-stat-grid">
                <div class="stat-box">
                    <div class="stat-label">Statutory Rate</div>
                    <div class="stat-val" style="color:#FBBF24">${data.applied_rate_percent}%</div>
                </div>
                <div class="stat-box highlight">
                    <div class="stat-label">TDS to Deduct</div>
                    <div class="stat-val">${formatINR(data.tds_amount)}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Net Payable to Vendor</div>
                    <div class="stat-val" style="color:#60A5FA">${formatINR(data.net_payable)}</div>
                </div>
            </div>
            <div class="recommendation-banner" style="margin-top:14px;background:rgba(30,41,59,0.7);border-color:#475569;color:#CBD5E1;">
                ℹ️ ${data.pan_note} (Threshold: ${formatINR(data.threshold)})
            </div>
            <button class="tool-calc-btn" style="margin-top:12px;background:#334155;font-size:12px;padding:8px 14px;" onclick="sendCalcToChat('${data.summary.replace(/'/g, "\\'")}')">
                Send to Chat Consultation 💬
            </button>
        `;
        resBox.classList.add("visible");
    } catch (e) {
        alert("Failed to compute TDS.");
    }
}

async function executeEmiCalc() {
    const principal = parseFloat(document.getElementById("emiPrincipal").value) || 0;
    const annualRate = parseFloat(document.getElementById("emiRate").value) || 0;
    const tenureMonths = parseInt(document.getElementById("emiTenure").value) || 0;
    const resBox = document.getElementById("emiResult");

    try {
        const res = await fetch(`${BACKEND_URL}/tools/emi`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ principal, annual_rate: annualRate, tenure_months: tenureMonths })
        });
        const data = await res.json();

        resBox.innerHTML = `
            <div class="result-stat-grid">
                <div class="stat-box highlight">
                    <div class="stat-label">Monthly EMI</div>
                    <div class="stat-val">${formatINR(data.monthly_emi)}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Interest Outgo</div>
                    <div class="stat-val" style="color:#F87171">${formatINR(data.total_interest_payable)}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Repayment Amount</div>
                    <div class="stat-val">${formatINR(data.total_amount_payable)}</div>
                </div>
            </div>
            <button class="tool-calc-btn" style="margin-top:12px;background:#334155;font-size:12px;padding:8px 14px;" onclick="sendCalcToChat('${data.summary.replace(/'/g, "\\'")}')">
                Send to Chat Consultation 💬
            </button>
        `;
        resBox.classList.add("visible");
    } catch (e) {
        alert("Failed to compute EMI.");
    }
}

async function executeHraCalc() {
    const basic = parseFloat(document.getElementById("hraBasic").value) || 0;
    const received = parseFloat(document.getElementById("hraReceived").value) || 0;
    const rent = parseFloat(document.getElementById("hraRent").value) || 0;
    const isMetro = document.getElementById("hraMetro").value === "metro";
    const resBox = document.getElementById("hraResult");

    try {
        const res = await fetch(`${BACKEND_URL}/tools/hra`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ basic_salary: basic, hra_received: received, rent_paid: rent, is_metro: isMetro })
        });
        const data = await res.json();

        resBox.innerHTML = `
            <div class="result-stat-grid">
                <div class="stat-box highlight">
                    <div class="stat-label">Exempt HRA (Tax-Free u/s 10(13A))</div>
                    <div class="stat-val">${formatINR(data.exempt_hra)}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Taxable HRA</div>
                    <div class="stat-val" style="color:#F87171">${formatINR(data.taxable_hra)}</div>
                </div>
            </div>
            <button class="tool-calc-btn" style="margin-top:12px;background:#334155;font-size:12px;padding:8px 14px;" onclick="sendCalcToChat('${data.summary.replace(/'/g, "\\'")}')">
                Send to Chat Consultation 💬
            </button>
        `;
        resBox.classList.add("visible");
    } catch (e) {
        alert("Failed to compute HRA exemption.");
    }
}

async function executeDeprCalc() {
    const cost = parseFloat(document.getElementById("deprCost").value) || 0;
    const salvage = parseFloat(document.getElementById("deprSalvage").value) || 0;
    const years = parseInt(document.getElementById("deprYears").value) || 5;
    const method = document.getElementById("deprMethod").value;
    const resBox = document.getElementById("deprResult");

    try {
        const res = await fetch(`${BACKEND_URL}/tools/depreciation`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cost, salvage_value: salvage, useful_life_years: years, method })
        });
        const data = await res.json();

        let tableRows = data.schedule.map(s => `
            <tr>
                <td>Year ${s.year}</td>
                <td>${formatINR(s.opening_value)}</td>
                <td style="color:#F87171">${formatINR(s.depreciation_charge)}</td>
                <td style="font-weight:600">${formatINR(s.closing_value)}</td>
            </tr>
        `).join("");

        resBox.innerHTML = `
            <div class="recommendation-banner" style="background:rgba(37,99,235,0.1);border-color:#3B82F6;color:#93C5FD;">
                ${data.summary}
            </div>
            <table style="margin-top:14px;">
                <thead>
                    <tr><th>Period</th><th>Opening Value</th><th>Depreciation</th><th>Closing Book Value</th></tr>
                </thead>
                <tbody>${tableRows}</tbody>
            </table>
        `;
        resBox.classList.add("visible");
    } catch (e) {
        alert("Failed to compute depreciation schedule.");
    }
}

function sendCalcToChat(text) {
    switchView("chat");
    sendSuggestion(text);
}

// --------------------------------------------------------------------------
// Settings Modal & API Key Configuration
// --------------------------------------------------------------------------
function openSettingsModal() {
    document.getElementById("backendUrlInput").value = BACKEND_URL;
    document.getElementById("settingsFeedback").style.display = "none";
    document.getElementById("settingsModal").classList.add("active");
}

function closeSettingsModal() {
    document.getElementById("settingsModal").classList.remove("active");
}

async function saveSettings() {
    const newUrl = document.getElementById("backendUrlInput").value.trim();
    const feedback = document.getElementById("settingsFeedback");

    if (newUrl) {
        BACKEND_URL = newUrl;
        localStorage.setItem("pocketca_backend_url", BACKEND_URL);
    }

    feedback.className = "modal-feedback success";
    feedback.textContent = "Settings saved successfully!";
    checkBackendHealth();
    setTimeout(() => closeSettingsModal(), 800);
}

// --------------------------------------------------------------------------
// Document Upload
// --------------------------------------------------------------------------
function openUploadModal() {
    document.getElementById("uploadStatus").innerHTML = "";
    document.getElementById("uploadModal").classList.add("active");
}

function closeUploadModal() {
    document.getElementById("uploadModal").classList.remove("active");
}

async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const status = document.getElementById("uploadStatus");
    status.innerHTML = `⏳ Uploading and indexing <strong>${file.name}</strong>...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${BACKEND_URL}/upload`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            status.innerHTML = `<span style="color:#10B981">✓ ${data.message} (${data.details?.chunks_added || 0} chunks added to Knowledge Base)</span>`;
            checkBackendHealth();
            // Automatically inform chat
            switchView("chat");
            closeUploadModal();
            appendMessageUI("assistant", `📄 **Document Uploaded & Indexed:** \`${file.name}\`\nYou can now ask questions about this document's financial figures, ledger entries, or tax implications.`);
        } else {
            status.innerHTML = `<span style="color:#EF4444">⚠️ Error: ${data.detail || 'Upload failed.'}</span>`;
        }
    } catch (e) {
        status.innerHTML = `<span style="color:#EF4444">⚠️ Could not connect to backend server.</span>`;
    }
}