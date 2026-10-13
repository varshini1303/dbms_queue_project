/**
 * BankQueue Web Client
 * Connects frontend directly to the Python Backend API & Database
 * Supports BACKEND_URL environment variable for public cloud deployments
 */

const BACKEND_URL = window.BACKEND_URL || (window.__ENV__ && window.__ENV__.BACKEND_URL) || window.location.origin;
console.log(`[BankQueue] Connected to Backend API at: ${BACKEND_URL}`);

let activeServices = [];
let activeCounters = [];

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
    loadServices();
    loadLiveQueue();
    setupWebSocket();
    setInterval(loadLiveQueue, 5000); // Polling fallback alongside WebSocket
});

// 1. Load Services from Database
async function loadServices() {
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/services`);
        if (!res.ok) throw new Error("Could not fetch services");
        activeServices = await res.json();

        // Populate dropdown on booking form
        const serviceSelect = document.getElementById("bookingService");
        const walkInSelect = document.getElementById("walkInService");
        if (serviceSelect) {
            serviceSelect.innerHTML = activeServices.map(s => 
                `<option value="${s.id}">${s.name} (~${s.estimated_time}) [Prefix: ${s.prefix}]</option>`
            ).join("");
        }
        if (walkInSelect) {
            walkInSelect.innerHTML = activeServices.map(s => 
                `<option value="${s.id}">${s.name} (${s.estimated_time})</option>`
            ).join("");
        }

        // Render Services Cards
        const grid = document.getElementById("servicesList");
        if (grid) {
            grid.innerHTML = activeServices.map(s => `
                <div class="col-md-6 col-lg-4">
                    <div class="card-custom h-100 d-flex flex-column">
                        <div class="d-flex align-items-center justify-content-between mb-3">
                            <span class="badge bg-light text-primary border fw-bold px-3 py-1">Prefix ${s.prefix}</span>
                            <span class="text-muted small"><i class="bi bi-clock me-1"></i>~${s.estimated_time}</span>
                        </div>
                        <h5 class="fw-bold text-navy mb-2">${s.name}</h5>
                        <p class="text-muted small flex-grow-1">${s.description}</p>
                        <div class="pt-3 border-top mt-auto d-flex justify-content-between align-items-center">
                            <button class="btn btn-sm btn-outline-primary" onclick="selectServiceForBooking(${s.id})">
                                Select Service &rarr;
                            </button>
                        </div>
                    </div>
                </div>
            `).join("");
        }
    } catch (err) {
        console.error("Error loading services:", err);
    }
}

function selectServiceForBooking(serviceId) {
    const sel = document.getElementById("bookingService");
    if (sel) {
        sel.value = serviceId;
        window.location.hash = "#book";
    }
}

// 2. Load Real-time Live Queue Status
async function loadLiveQueue() {
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/queue/live`);
        if (!res.ok) throw new Error("Could not fetch live queue");
        const data = await res.json();

        // Update Overview Stats
        const elWaiting = document.getElementById("statWaiting");
        const elServed = document.getElementById("statServed");
        const elCounters = document.getElementById("statActiveCounters");
        const elAvgWait = document.getElementById("statAvgWait");

        if (elWaiting) elWaiting.textContent = data.total_waiting;
        if (elServed) elServed.textContent = data.total_served_today;
        if (elCounters) elCounters.textContent = data.active_counters_count;
        if (elAvgWait) elAvgWait.textContent = `${data.average_wait_minutes} min`;

        // Render Counter Desks
        const countersGrid = document.getElementById("countersGrid");
        const staffCountersGrid = document.getElementById("staffCountersGrid");

        if (countersGrid) {
            countersGrid.innerHTML = data.counters.map(c => `
                <div class="col-md-6 col-lg-3">
                    <div class="counter-card h-100">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <h6 class="fw-bold mb-0 text-navy">${c.name}</h6>
                            <span class="badge ${c.status === 'BUSY' ? 'bg-danger' : 'bg-success'}">${c.status}</span>
                        </div>
                        <div class="text-muted small mb-3">${c.desk_label} &bull; ${c.staff_name}</div>
                        <div class="p-3 bg-light rounded-3 text-center mb-3 border">
                            <div class="text-muted small fw-semibold">NOW SERVING</div>
                            <div class="token-display">${c.current_token_number || '&mdash;'}</div>
                        </div>
                        <div class="d-flex justify-content-between small text-muted">
                            <span>Waiting:</span>
                            <span class="fw-bold text-navy">${c.waiting_count} in line</span>
                        </div>
                    </div>
                </div>
            `).join("");
        }

        // Render Staff Console Controls
        if (staffCountersGrid) {
            staffCountersGrid.innerHTML = data.counters.map(c => `
                <div class="col-md-6 col-lg-3">
                    <div class="card-custom h-100 border">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="fw-bold">${c.name}</span>
                            <span class="badge ${c.status === 'BUSY' ? 'bg-danger' : 'bg-success'}">${c.status}</span>
                        </div>
                        <div class="small text-muted mb-2">${c.desk_label} (${c.staff_name})</div>
                        <div class="bg-light p-2 rounded text-center mb-2 border">
                            <span class="small text-muted">Current:</span>
                            <div class="fs-4 fw-bold text-primary">${c.current_token_number || 'None'}</div>
                        </div>
                        <div class="small text-muted mb-3">Line length: <strong>${c.waiting_count}</strong></div>
                        <div class="d-grid gap-2">
                            <button class="btn btn-sm btn-success fw-bold" onclick="staffCallNext(${c.id})">
                                <i class="bi bi-megaphone me-1"></i>Call Next
                            </button>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-secondary" onclick="staffRecall(${c.id})" title="Recall / Chime">Recall</button>
                                <button class="btn btn-outline-danger" onclick="staffSkip(${c.id})" title="Mark No-Show">Skip</button>
                                <button class="btn btn-outline-primary" onclick="staffComplete(${c.id})" title="Finish">Done</button>
                            </div>
                        </div>
                    </div>
                </div>
            `).join("");
        }

        // Render Upcoming Queue List
        const upcomingList = document.getElementById("upcomingQueueList");
        if (upcomingList && data.upcoming_tokens) {
            if (data.upcoming_tokens.length === 0) {
                upcomingList.innerHTML = `<li class="list-group-item text-muted text-center py-3">No customers currently waiting.</li>`;
            } else {
                upcomingList.innerHTML = data.upcoming_tokens.map(t => `
                    <li class="list-group-item d-flex justify-content-between align-items-center py-2">
                        <div>
                            <span class="fw-bold text-navy me-2">${t.token_number}</span>
                            <span class="badge bg-light text-dark border me-2">${t.service_name}</span>
                            <span class="small text-muted">${t.customer_name} &bull; ${t.counter_name}</span>
                        </div>
                        <div>
                            <span class="status-badge ${t.status === 'APPROACHING' ? 'status-approaching' : 'status-waiting'} me-2">
                                ${t.status}
                            </span>
                            <span class="small text-muted">~${t.estimated_wait_minutes}m wait</span>
                        </div>
                    </li>
                `).join("");
            }
        }

        // Render Live Updates Ticker
        const ticker = document.getElementById("liveActivityTicker");
        if (ticker && data.recent_updates) {
            ticker.innerHTML = data.recent_updates.map(u => `
                <div class="py-1 border-bottom d-flex justify-content-between small">
                    <span><i class="bi bi-dot text-primary fs-5 align-middle"></i>${u.text}</span>
                    <span class="text-muted">${u.timestamp}</span>
                </div>
            `).join("");
        }

    } catch (err) {
        console.error("Error loading live queue:", err);
    }
}

// 3. Book Token (Submit Form)
async function handleBookToken(event) {
    event.preventDefault();
    const btn = document.getElementById("btnBookSubmit");
    if (btn) btn.disabled = true;

    const payload = {
        customer_name: document.getElementById("custName").value.trim(),
        customer_phone: document.getElementById("custPhone").value.trim(),
        customer_email: document.getElementById("custEmail").value.trim() || null,
        customer_account_number: document.getElementById("custAccount").value.trim() || null,
        service_id: parseInt(document.getElementById("bookingService").value),
        booking_date: document.getElementById("bookingDate").value,
        time_slot: document.getElementById("bookingSlot").value,
    };

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/tokens/book`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Booking failed");
        }

        const data = await res.json();

        // Populate Ticket Confirmation Display
        document.getElementById("resToken").textContent = data.token_number;
        document.getElementById("resService").textContent = data.service_name;
        document.getElementById("resDesk").textContent = `${data.counter_name} (${data.desk_label})`;
        document.getElementById("resAhead").textContent = `${data.people_ahead} customer(s)`;
        document.getElementById("resWait").textContent = `~${data.estimated_wait_minutes} mins`;
        document.getElementById("resArrival").textContent = data.recommended_arrival_time;
        document.getElementById("resNotice").textContent = data.status === "APPROACHING" ? 
            "Your turn is approaching soon! Please arrive 10-15 minutes prior." : 
            "Token confirmed. You can track live queue status anytime from home.";

        document.getElementById("tokenSuccessCard").classList.remove("d-none");
        document.getElementById("tokenSuccessCard").scrollIntoView({ behavior: "smooth" });

        loadLiveQueue();
    } catch (err) {
        alert("Booking Error: " + err.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

// 4. Track Token Status
async function handleTrackToken(event) {
    if (event) event.preventDefault();
    const tokenInput = document.getElementById("trackTokenInput").value.trim().toUpperCase();
    if (!tokenInput) {
        alert("Please enter a token number (e.g. A108, B201)");
        return;
    }

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/tokens/track/${encodeURIComponent(tokenInput)}`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Token ${tokenInput} not found. Please verify.`);
        }

        const data = await res.json();

        document.getElementById("trackResultNum").textContent = data.token_number;
        document.getElementById("trackResultStatus").textContent = data.status;
        document.getElementById("trackResultNotice").textContent = data.notice;
        document.getElementById("trackCustomerName").textContent = data.customer_name;
        document.getElementById("trackServiceName").textContent = data.service_name;
        document.getElementById("trackDeskName").textContent = `${data.counter_name} (${data.desk_label})`;
        document.getElementById("trackAheadCount").textContent = `${data.people_ahead} ahead`;
        document.getElementById("trackWaitTime").textContent = `~${data.estimated_wait_minutes} mins`;
        document.getElementById("trackArrivalGuidance").textContent = data.recommended_arrival_time;

        const card = document.getElementById("trackResultCard");
        card.classList.remove("d-none");
        card.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
        alert(err.message);
    }
}

// 5. Staff Console Actions
async function staffCallNext(counterId) {
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/counters/${counterId}/call-next`, { method: "POST" });
        const data = await res.json();
        loadLiveQueue();
        loadStaffTable();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function staffComplete(counterId) {
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/counters/${counterId}/complete`, { method: "POST" });
        const data = await res.json();
        loadLiveQueue();
        loadStaffTable();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function staffRecall(counterId) {
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/counters/${counterId}/recall`, { method: "POST" });
        const data = await res.json();
        alert(data.message);
        loadLiveQueue();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function staffSkip(counterId) {
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/counters/${counterId}/skip`, { method: "POST" });
        const data = await res.json();
        loadLiveQueue();
        loadStaffTable();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// Walk-in Ticket Issuance
async function handleWalkInIssue(event) {
    event.preventDefault();
    const serviceId = document.getElementById("walkInService").value;
    const name = document.getElementById("walkInName").value.trim() || "Walk-in Visitor";

    try {
        const url = `${BACKEND_URL}/api/v1/tokens/walk-in?service_id=${serviceId}&customer_name=${encodeURIComponent(name)}`;
        const res = await fetch(url, { method: "POST" });
        if (!res.ok) throw new Error("Could not issue ticket");
        const data = await res.json();
        alert(`Walk-In Ticket Generated: ${data.token_number} (${data.service_name})`);
        loadLiveQueue();
        loadStaffTable();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// Staff Queue Table
async function loadStaffTable() {
    const tableBody = document.getElementById("staffQueueTableBody");
    if (!tableBody) return;
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/queue/manage-tokens`);
        const data = await res.json();
        tableBody.innerHTML = data.map(t => `
            <tr>
                <td class="fw-bold text-navy">${t.token_number}</td>
                <td>${t.customer_name}</td>
                <td>${t.service_name}</td>
                <td>${t.counter_name}</td>
                <td><span class="status-badge ${t.status === 'SERVING' ? 'status-serving' : (t.status === 'APPROACHING' ? 'status-approaching' : 'status-waiting')}">${t.status}</span></td>
                <td>${t.time_slot}</td>
                <td>${t.created_at}</td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Staff table error:", err);
    }
}

// 6. Contact Form
async function handleContactSubmit(event) {
    event.preventDefault();
    const payload = {
        name: document.getElementById("contactName").value.trim(),
        email: document.getElementById("contactEmail").value.trim(),
        message: document.getElementById("contactMessage").value.trim(),
    };

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/contact`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        alert(data.message);
        event.target.reset();
    } catch (err) {
        alert("Failed to send inquiry: " + err.message);
    }
}

// 7. WebSocket Live Updates Stream
function setupWebSocket() {
    try {
        const wsProto = BACKEND_URL.startsWith("https") ? "wss" : "ws";
        const wsHost = BACKEND_URL.replace(/^https?:\/\//, "");
        const ws = new WebSocket(`${wsProto}://${wsHost}/ws`);

        ws.onopen = () => console.log("[BankQueue] WebSocket connected for real-time live events");
        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                console.log("[BankQueue Event]", msg);
                loadLiveQueue();
                if (document.getElementById("staffSection")) {
                    loadStaffTable();
                }
            } catch (e) {}
        };
        ws.onclose = () => {
            setTimeout(setupWebSocket, 4000); // Reconnect
        };
    } catch (e) {
        console.warn("WebSocket setup warning, relying on polling fallback", e);
    }
}

// 8. Single-Page Embedded Modal Login & Profile State
function fillModalDemo(ident, pass) {
    document.getElementById("modalLoginIdent").value = ident;
    document.getElementById("modalLoginPass").value = pass;
}

async function handleModalLogin(e) {
    e.preventDefault();
    const ident = document.getElementById("modalLoginIdent").value.trim();
    const pass = document.getElementById("modalLoginPass").value;

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifier: ident, password: pass })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Invalid login credentials");
        }
        const data = await res.json();
        localStorage.setItem("bank_token", data.access_token);
        localStorage.setItem("bank_user", JSON.stringify(data.user));
        updateNavAndModalAuth(data.user);
    } catch (err) {
        alert("Login Error: " + err.message);
    }
}

async function handleModalRegister(e) {
    e.preventDefault();
    const payload = {
        full_name: document.getElementById("modalRegName").value.trim(),
        phone: document.getElementById("modalRegPhone").value.trim(),
        email: document.getElementById("modalRegEmail").value.trim(),
        password: document.getElementById("modalRegPass").value
    };

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Registration failed");
        }
        const data = await res.json();
        localStorage.setItem("bank_token", data.access_token);
        localStorage.setItem("bank_user", JSON.stringify(data.user));
        alert("Account registered successfully!");
        updateNavAndModalAuth(data.user);
    } catch (err) {
        alert("Registration Error: " + err.message);
    }
}

function updateNavAndModalAuth(user) {
    const navText = document.getElementById("navUserBtnText");
    if (navText) navText.textContent = user.full_name.split(" ")[0];

    const tabs = document.getElementById("modalAuthTabs");
    const content = document.getElementById("modalAuthTabContent");
    const loggedInView = document.getElementById("modalLoggedInView");

    if (tabs) tabs.classList.add("d-none");
    if (content) content.classList.add("d-none");
    if (loggedInView) {
        loggedInView.classList.remove("d-none");
        document.getElementById("modalUserName").textContent = user.full_name;
        document.getElementById("modalUserDetail").textContent = `${user.email} • ${user.phone}`;
        document.getElementById("modalUserRole").textContent = user.role;
        loadModalUserTokens(user.phone);
    }
}

async function loadModalUserTokens(phone) {
    const container = document.getElementById("modalUserTokens");
    if (!container) return;
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/tokens/my-tokens?phone=${encodeURIComponent(phone)}`);
        const tokens = await res.json();
        if (!tokens || tokens.length === 0) {
            container.innerHTML = `<span class="text-muted">No active tokens reserved yet.</span>`;
        } else {
            container.innerHTML = tokens.map(t => `
                <div class="py-1 border-bottom d-flex justify-content-between align-items-center">
                    <div>
                        <span class="fw-bold text-navy">${t.token_number}</span> (${t.service_name})
                        <div class="text-muted small">${t.time_slot} • ${t.desk_label}</div>
                    </div>
                    <span class="badge ${t.status === 'SERVING' ? 'bg-success' : 'bg-primary'}">${t.status}</span>
                </div>
            `).join("");
        }
    } catch (e) {
        console.error("Token load error", e);
    }
}

function handleModalLogout() {
    localStorage.removeItem("bank_token");
    localStorage.removeItem("bank_user");
    window.location.reload();
}

// Check saved user on startup
document.addEventListener("DOMContentLoaded", () => {
    const saved = localStorage.getItem("bank_user");
    if (saved) {
        try {
            updateNavAndModalAuth(JSON.parse(saved));
        } catch (e) {}
    }
});
