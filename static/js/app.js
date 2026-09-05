// SupportGenie AI - Single Page Application Logic

let currentCustomerId = "CUST-1001";
let currentSessionId = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
    initEventListeners();
    switchCustomer(currentCustomerId);
    loadTickets();
    loadKnowledgeBase();
});

function initEventListeners() {
    // Nav tabs
    document.querySelectorAll(".tab-btn[data-view]").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn[data-view]").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".view-section").forEach(s => s.classList.remove("active"));

            btn.classList.add("active");
            const viewId = btn.getAttribute("data-view");
            const section = document.getElementById(viewId);
            if (section) section.classList.add("active");

            if (viewId === "tickets-view") loadTickets();
            if (viewId === "kb-view") loadKnowledgeBase();
        });
    });

    // Persona Selector
    const personaSelect = document.getElementById("personaSelect");
    personaSelect.addEventListener("change", (e) => {
        switchCustomer(e.target.value);
    });

    // Chat Input & Send Button
    const chatInput = document.getElementById("chatInput");
    const sendBtn = document.getElementById("sendBtn");

    sendBtn.addEventListener("click", () => handleSendMessage());
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    // Close modal on escape or background click
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeModal();
    });
    document.getElementById("evidenceModal").addEventListener("click", (e) => {
        if (e.target.id === "evidenceModal") closeModal();
    });
}

// ---------------------------------------------------------------------
// Customer Profile & Session Management
// ---------------------------------------------------------------------
async function switchCustomer(customerId) {
    currentCustomerId = customerId;
    currentSessionId = null; // Fresh session

    // Reset Chat Box
    const chatHistory = document.getElementById("chatHistory");
    chatHistory.innerHTML = "";
    document.getElementById("quickReplies").innerHTML = "";

    try {
        const res = await fetch(`/api/customers/${customerId}`);
        const data = await res.json();

        // Update Header & Sidebar
        document.getElementById("chatCustomerName").textContent = data.full_name;
        document.getElementById("chatAccountSub").textContent = data.account ? data.account.plan_name : "Broadband";
        document.getElementById("dashCustomerId").textContent = data.customer_id;
        document.getElementById("dashAccountId").textContent = data.account ? data.account.account_id : "N/A";
        document.getElementById("dashPlanName").textContent = data.account ? data.account.plan_name : "N/A";
        document.getElementById("dashMonthlyRate").textContent = data.account ? `$${data.account.monthly_rate.toFixed(2)}/mo` : "N/A";
        document.getElementById("dashBalanceDue").textContent = data.account ? `$${data.account.balance_due.toFixed(2)}` : "$0.00";
        document.getElementById("dashRoaming").textContent = data.account && data.account.roaming_enabled ? "Active" : "Disabled";

        const verBadge = document.getElementById("verificationBadge");
        verBadge.textContent = data.verification_status;
        verBadge.className = data.verification_status === "VERIFIED" ? "status-badge ok" : "status-badge warning";

        // Update Telemetry
        updateTelemetryUI(data.telemetry);

        // Append Welcome Greeting
        const greeting = `Hello **${data.full_name.split(" ")[0]}**! I am **SupportGenie AI**, your customer operations resolution assistant. I have your **${data.account ? data.account.plan_name : "account"}** loaded. How can I assist you today?`;
        appendMessage("assistant", greeting, [], "ACTIVE");

        // Starter replies based on customer scenario
        if (customerId === "CUST-1001") {
            setQuickReplies(["My internet is down, red light on box", "Check line health", "What is my account balance?"]);
        } else if (customerId === "CUST-1003") {
            setQuickReplies(["Dispute accidental $35 data overage charge", "Review my recent bill"]);
        } else if (customerId === "CUST-1004") {
            setQuickReplies(["Dispute unexpected $140 roaming charge", "Explain my roaming usage"]);
        } else if (customerId === "CUST-1005") {
            setQuickReplies(["Help me set up eSIM on iPhone 15", "My eSIM QR code expired"]);
        } else if (customerId === "CUST-1006") {
            setQuickReplies(["Why is my internet completely offline?", "Check for area outages"]);
        } else {
            setQuickReplies(["Optimize my Wi-Fi speed", "Upgrade my broadband tier"]);
        }

    } catch (err) {
        console.error("Error loading customer profile:", err);
    }
}

function updateTelemetryUI(tel) {
    if (!tel) return;

    // Modem
    const modemBadge = document.getElementById("telModemStatus");
    modemBadge.textContent = tel.modem_online ? "ONLINE" : "OFFLINE";
    modemBadge.className = tel.modem_online ? "status-badge ok" : "status-badge critical";

    // Optical Power
    const pwrBadge = document.getElementById("telOpticalPower");
    pwrBadge.textContent = `${tel.optical_rx_power_dbm.toFixed(1)} dBm`;
    pwrBadge.className = tel.optical_rx_power_dbm >= -27.0 ? "status-badge ok" : "status-badge critical";

    // LOS Alarm
    const losBadge = document.getElementById("telLosAlarm");
    losBadge.textContent = tel.optical_los_alarm ? "ACTIVE (RED)" : "NORMAL";
    losBadge.className = tel.optical_los_alarm ? "status-badge critical" : "status-badge ok";

    // Outage
    const outBadge = document.getElementById("telAreaOutage");
    outBadge.textContent = tel.area_outage_detected ? "OUTAGE DETECTED" : "NO OUTAGE";
    outBadge.className = tel.area_outage_detected ? "status-badge critical" : "status-badge ok";
}

async function simulateTelemetry(payload) {
    try {
        await fetch(`/api/customers/${currentCustomerId}/telemetry`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const res = await fetch(`/api/customers/${currentCustomerId}`);
        const data = await res.json();
        updateTelemetryUI(data.telemetry);
    } catch (err) {
        console.error("Failed to simulate telemetry:", err);
    }
}

// ---------------------------------------------------------------------
// Chat Interaction
// ---------------------------------------------------------------------
async function handleSendMessage(customText = null) {
    const inputEl = document.getElementById("chatInput");
    const message = (customText || inputEl.value).trim();
    if (!message) return;

    inputEl.value = "";
    appendMessage("user", message);
    document.getElementById("quickReplies").innerHTML = "";

    // Show typing status
    const statusPill = document.getElementById("chatSessionStatus");
    statusPill.textContent = "AI Reasoning & Grounding...";

    try {
        const response = await fetch("/api/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: currentSessionId,
                customer_id: currentCustomerId,
                message: message
            })
        });

        const data = await response.json();
        currentSessionId = data.session_id;

        // Render response
        appendMessage("assistant", data.content, data.citations, data.status, data.escalation_ticket_id);

        if (data.status === "ESCALATED") {
            statusPill.textContent = "Escalated to Human Specialist";
            statusPill.style.color = "var(--accent-red)";
            loadTickets(); // Refresh tickets badge & queue
        } else if (data.status === "RESOLVED") {
            statusPill.textContent = "Inquiry Resolved";
            statusPill.style.color = "var(--accent-green)";
        } else {
            statusPill.textContent = "AI Assistant Active";
            statusPill.style.color = "var(--accent-green)";
        }

        // Suggested quick replies
        if (data.suggested_quick_replies && data.suggested_quick_replies.length > 0) {
            setQuickReplies(data.suggested_quick_replies);
        }

        // Refresh customer sidebar in case balance was updated
        const custRes = await fetch(`/api/customers/${currentCustomerId}`);
        const custData = await custRes.json();
        if (custData.account) {
            document.getElementById("dashBalanceDue").textContent = `$${custData.account.balance_due.toFixed(2)}`;
        }

    } catch (err) {
        console.error("Error sending message:", err);
        appendMessage("assistant", "⚠️ Error processing message. Please check backend connection.");
        statusPill.textContent = "Connection Error";
    }
}

function sendPresetMessage(text) {
    handleSendMessage(text);
}

function appendMessage(sender, content, citations = [], status = "ACTIVE", ticketId = null) {
    const history = document.getElementById("chatHistory");
    const row = document.createElement("div");
    row.className = `message-row ${sender}`;

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = sender === "user" ? "You" : "SupportGenie AI";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = formatMarkdown(content);

    // Citations box
    if (citations && citations.length > 0) {
        const citBox = document.createElement("div");
        citBox.className = "citations-box";

        citations.forEach(c => {
            const chip = document.createElement("button");
            chip.className = "citation-chip";
            const label = c.article_id ? `📑 [${c.article_id}]` : (c.metric ? `📡 [Telemetry: ${c.metric}]` : `⚖️ [Policy]`);
            chip.innerHTML = `${label} <span style="font-size:10px;">${c.similarity_score ? Math.round(c.similarity_score * 100) + '%' : ''}</span>`;
            chip.addEventListener("click", () => showEvidence(c));
            citBox.appendChild(chip);
        });

        bubble.appendChild(citBox);
    }

    // Escalation Banner
    if (status === "ESCALATED" && ticketId) {
        const banner = document.createElement("div");
        banner.className = "escalation-banner";
        banner.innerHTML = `
            <span>🛡️</span>
            <div>
                <strong>Handed Over to Human Operator:</strong> Ticket <code>${ticketId}</code> created.
                <button onclick="viewTicket('${ticketId}')" style="background:transparent; border:none; color:white; text-decoration:underline; cursor:pointer; margin-left:8px;">View Handover Brief &rarr;</button>
            </div>
        `;
        bubble.appendChild(banner);
    }

    row.appendChild(meta);
    row.appendChild(bubble);
    history.appendChild(row);
    history.scrollTop = history.scrollHeight;
}

function setQuickReplies(replies) {
    const container = document.getElementById("quickReplies");
    container.innerHTML = "";
    replies.forEach(r => {
        const btn = document.createElement("button");
        btn.className = "quick-reply-btn";
        btn.textContent = r;
        btn.addEventListener("click", () => handleSendMessage(r));
        container.appendChild(btn);
    });
}

function formatMarkdown(text) {
    if (!text) return "";
    let html = text
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\n\n/g, "<br><br>")
        .replace(/\n- (.*?)/g, "<br>• $1");
    return html;
}

// ---------------------------------------------------------------------
// Evidence & Citation Inspector Modal
// ---------------------------------------------------------------------
function showEvidence(citation) {
    const modal = document.getElementById("evidenceModal");
    const title = document.getElementById("modalTitle");
    const meta = document.getElementById("modalMeta");
    const body = document.getElementById("modalBody");

    title.textContent = citation.title || citation.article_id || "Citation Details";
    meta.textContent = `Source Type: ${citation.source_type} ${citation.similarity_score ? `| Grounding Score: ${(citation.similarity_score * 100).toFixed(1)}%` : ""}`;

    let html = "";
    if (citation.section) {
        html += `<p><strong>Section / Reference</strong>: ${citation.section}</p><br>`;
    }
    if (citation.metric) {
        html += `<p><strong>Telemetry Metric</strong>: <code>${citation.metric} = ${citation.value}</code></p><br>`;
    }
    if (citation.excerpt) {
        html += `
            <p><strong>Grounded Knowledge Excerpt</strong>:</p>
            <blockquote style="border-left:3px solid var(--accent-blue); padding-left:12px; margin-top:8px; color:#cbd5e1; font-style:italic;">
                ${citation.excerpt}
            </blockquote>
        `;
    }

    body.innerHTML = html;
    modal.classList.add("active");
}

function closeModal() {
    document.getElementById("evidenceModal").classList.remove("active");
}

// ---------------------------------------------------------------------
// Human Agent Ops Queue
// ---------------------------------------------------------------------
async function loadTickets() {
    try {
        const res = await fetch("/api/tickets");
        const tickets = await res.json();

        const badge = document.getElementById("ticketCountBadge");
        if (tickets.length > 0) {
            badge.textContent = tickets.length;
            badge.style.display = "inline";
        } else {
            badge.style.display = "none";
        }

        const grid = document.getElementById("ticketsGrid");
        if (tickets.length === 0) {
            grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--text-muted);">No open escalation tickets. All inquiries resolved autonomously! 🎉</div>`;
            return;
        }

        grid.innerHTML = "";
        tickets.forEach(t => {
            const card = document.createElement("div");
            card.className = `ticket-card ${t.priority.toLowerCase()}`;
            card.id = `ticket-card-${t.ticket_id}`;

            card.innerHTML = `
                <div class="ticket-header-line">
                    <div>
                        <strong style="color:var(--accent-blue);">${t.ticket_id}</strong>
                        <span class="status-badge ${t.priority === 'CRITICAL' ? 'critical' : (t.priority === 'HIGH' ? 'warning' : 'ok')}" style="margin-left:8px;">${t.priority}</span>
                    </div>
                    <span style="font-size:12px; color:var(--text-muted);">${t.status}</span>
                </div>
                <div>
                    <h4 style="margin-bottom:4px;">${t.customer_name} (${t.customer_id})</h4>
                    <p style="font-size:12px; color:var(--text-muted);">Reason: <strong>${t.reason.replace(/_/g, ' ')}</strong></p>
                </div>
                <div class="handover-brief-box">${t.handover_summary}</div>
                <div class="ticket-actions">
                    ${t.status === 'OPEN' ? `<button class="btn-resolve" onclick="resolveTicket('${t.ticket_id}')">Mark Resolved</button>` : `<span style="font-size:12px; color:var(--accent-green);">Resolved by Agent</span>`}
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (err) {
        console.error("Error loading tickets:", err);
    }
}

async function resolveTicket(ticketId) {
    try {
        await fetch(`/api/tickets/${ticketId}/resolve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ resolution_notes: "Resolved by human specialist via console." })
        });
        loadTickets();
    } catch (err) {
        console.error("Failed to resolve ticket:", err);
    }
}

function viewTicket(ticketId) {
    // Switch to tickets view and scroll to ticket
    document.querySelector('.tab-btn[data-view="tickets-view"]').click();
}

// ---------------------------------------------------------------------
// Knowledge Base Explorer
// ---------------------------------------------------------------------
async function loadKnowledgeBase() {
    try {
        const res = await fetch("/api/kb/articles");
        const articles = await res.json();
        renderKbGrid(articles);
    } catch (err) {
        console.error("Error loading KB articles:", err);
    }
}

async function searchKnowledgeBase() {
    const q = document.getElementById("kbSearchInput").value.trim();
    if (!q) {
        loadKnowledgeBase();
        return;
    }

    try {
        const res = await fetch(`/api/kb/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        const articles = data.results.map(r => ({
            article_id: r.article_id,
            category: r.category,
            title: r.title,
            summary: r.snippet,
            policy_code: r.policy_code,
            score: r.score
        }));
        renderKbGrid(articles, true);
    } catch (err) {
        console.error("Search failed:", err);
    }
}

function renderKbGrid(articles, isSearch = false) {
    const grid = document.getElementById("kbGrid");
    grid.innerHTML = "";

    articles.forEach(a => {
        const card = document.createElement("div");
        card.className = "ticket-card";
        card.innerHTML = `
            <div class="ticket-header-line">
                <span class="status-badge ok">${a.category}</span>
                <span style="font-size:11px; color:var(--text-muted);">${a.policy_code || a.article_id}</span>
            </div>
            <h4 style="color:var(--text-main);">${a.title}</h4>
            <p style="font-size:12px; color:var(--text-muted); line-height:1.5;">${a.summary}</p>
            ${isSearch ? `<div style="font-size:11px; color:var(--accent-blue);">Retrieval Match: ${Math.round((a.score || 0) * 100)}%</div>` : ''}
        `;
        grid.appendChild(card);
    });
}
