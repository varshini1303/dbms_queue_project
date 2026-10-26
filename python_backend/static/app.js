/**
 * BankQueue Web Client
 * Unified Full-Stack Bank Queue Management System
 * Preserves 100% theme, colors, layout, styling and features
 */

const BACKEND_URL = window.BACKEND_URL || (window.__ENV__ && window.__ENV__.BACKEND_URL) || window.location.origin;
console.log(`[BankQueue] Connected to Backend API at: ${BACKEND_URL}`);

let activeServices = [];
let activeCounters = [];

// ==========================================
// 1. INITIALIZATION ON DOM LOAD
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    initAuth();
    loadServices();
    initBookingDates();
    loadLiveQueue();
    setupWebSocket();
    setInterval(loadLiveQueue, 5000); // Live fallback polling
});

// ==========================================
// 2. AUTHENTICATION & USER SESSION
// ==========================================
function getAuthToken() {
    return localStorage.getItem("bank_token");
}

function getAuthUser() {
    try {
        const u = localStorage.getItem("bank_user");
        return u ? JSON.parse(u) : null;
    } catch (e) {
        return null;
    }
}

function saveAuth(token, user) {
    localStorage.setItem("bank_token", token);
    localStorage.setItem("bank_user", JSON.stringify(user));
    updateAuthUI();
}

function handleLogout() {
    localStorage.removeItem("bank_token");
    localStorage.removeItem("bank_user");
    // Clear any previous form data to guarantee isolation
    resetBookingForm();
    updateAuthUI();
    // If on a subpage or want a clean refresh
    window.location.hash = "#home";
}

function updateAuthUI() {
    const user = getAuthUser();
    const token = getAuthToken();

    const loggedOutNav = document.getElementById("navAuthLoggedOut");
    const loggedInNav = document.getElementById("navAuthLoggedIn");
    const navName = document.getElementById("navUserName");

    const bookingGate = document.getElementById("bookingAuthRequired");
    const bookingForm = document.getElementById("bookingFormWrapper");

    if (user && token) {
        // User is Logged In
        if (loggedOutNav) loggedOutNav.classList.replace("d-flex", "d-none") || loggedOutNav.classList.add("d-none");
        if (loggedInNav) loggedInNav.classList.replace("d-none", "d-flex") || loggedInNav.classList.remove("d-none");
        if (navName) navName.textContent = user.full_name.split(" ")[0] || "Customer";

        if (bookingGate) bookingGate.classList.add("d-none");
        if (bookingForm) bookingForm.classList.remove("d-none");

        // Set customer name/email from session if currently empty
        const nameInput = document.getElementById("custName");
        const emailInput = document.getElementById("custEmail");
        const phoneInput = document.getElementById("custPhone");
        if (nameInput && !nameInput.value) nameInput.value = user.full_name;
        if (emailInput && !emailInput.value && user.email) emailInput.value = user.email;
        if (phoneInput && !phoneInput.value && user.phone) phoneInput.value = user.phone;
    } else {
        // User is Logged Out
        if (loggedOutNav) loggedOutNav.classList.replace("d-none", "d-flex") || loggedOutNav.classList.remove("d-none");
        if (loggedInNav) loggedInNav.classList.replace("d-flex", "d-none") || loggedInNav.classList.add("d-none");

        if (bookingGate) bookingGate.classList.remove("d-none");
        if (bookingForm) bookingForm.classList.add("d-none");

        resetBookingForm();
    }
}

async function initAuth() {
    const token = getAuthToken();
    if (token) {
        try {
            const res = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const user = await res.json();
                localStorage.setItem("bank_user", JSON.stringify(user));
            } else {
                localStorage.removeItem("bank_token");
                localStorage.removeItem("bank_user");
            }
        } catch (e) {
            console.warn("Auth check offline fallback", e);
        }
    }
    updateAuthUI();
}

function openAuthModal(mode) {
    clearModalErrors();
    switchModalAuthTab(mode || "login");
    const modalEl = document.getElementById("loginModal");
    if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }
}

function switchModalAuthTab(target) {
    clearModalErrors();
    if (target === "register") {
        const regTab = document.getElementById("modal-tab-register");
        if (regTab) bootstrap.Tab.getOrCreateInstance(regTab).show();
        document.getElementById("modalAuthTitle").textContent = "Create New Account";
        document.getElementById("modalAuthSubtitle").textContent = "Sign up to request bank tokens from home within the next 2 days.";
    } else {
        const logTab = document.getElementById("modal-tab-login");
        if (logTab) bootstrap.Tab.getOrCreateInstance(logTab).show();
        document.getElementById("modalAuthTitle").textContent = "Customer Portal Access";
        document.getElementById("modalAuthSubtitle").textContent = "Sign in to request bank tokens and track your place in queue.";
    }
}

function showModalError(msg) {
    const alertBox = document.getElementById("modalAuthAlert");
    if (alertBox) {
        alertBox.textContent = msg;
        alertBox.classList.remove("d-none");
    }
}

function clearModalErrors() {
    const alertBox = document.getElementById("modalAuthAlert");
    if (alertBox) {
        alertBox.textContent = "";
        alertBox.classList.add("d-none");
    }
}

async function handleModalLogin(e) {
    e.preventDefault();
    clearModalErrors();
    const email = document.getElementById("modalLoginEmail").value.trim();
    const pass = document.getElementById("modalLoginPass").value;

    if (!email) {
        showModalError("Please enter your email address.");
        return;
    }
    if (!pass) {
        showModalError("Please enter your password.");
        return;
    }

    const btn = document.getElementById("btnModalLoginSubmit");
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, password: pass })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Invalid email or password.");
        }

        const data = await res.json();
        saveAuth(data.access_token, data.user);

        // Hide modal
        const modalEl = document.getElementById("loginModal");
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }

        // Smooth scroll to booking section
        window.location.hash = "#book";
    } catch (err) {
        showModalError(err.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function handleModalRegister(e) {
    e.preventDefault();
    clearModalErrors();
    const name = document.getElementById("modalRegName").value.trim();
    const email = document.getElementById("modalRegEmail").value.trim();
    const pass = document.getElementById("modalRegPass").value;
    const confirmPass = document.getElementById("modalRegConfirmPass").value;

    if (name.length < 2) {
        showModalError("Please enter your full name.");
        return;
    }
    if (!email || !email.includes("@") || !email.includes(".")) {
        showModalError("Please enter a valid email address.");
        return;
    }
    if (pass.length < 6) {
        showModalError("Password must be at least 6 characters long.");
        return;
    }
    if (pass !== confirmPass) {
        showModalError("Passwords do not match. Please re-enter your password.");
        return;
    }

    const btn = document.getElementById("btnModalRegSubmit");
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                full_name: name,
                email: email,
                password: pass,
                confirm_password: confirmPass
            })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Registration failed. Please try again.");
        }

        const data = await res.json();
        saveAuth(data.access_token, data.user);

        // Hide modal
        const modalEl = document.getElementById("loginModal");
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }

        window.location.hash = "#book";
    } catch (err) {
        showModalError(err.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

// =========================================================
// 3. GET TOKEN FROM HOME (NO DEFAULT VALUES, 2-DAY LIMIT)
// =========================================================

// Initialize 2-day allowed dates dynamically
function initBookingDates() {
    const dateSelect = document.getElementById("bookingDate");
    if (!dateSelect) return;

    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);

    const formatDateVal = (d) => {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${y}-${m}-${day}`;
    };

    const formatDateLabel = (d, prefix) => {
        const options = { month: "short", day: "numeric", weekday: "short" };
        return `${prefix} (${d.toLocaleDateString("en-US", options)})`;
    };

    const todayVal = formatDateVal(today);
    const tomorrowVal = formatDateVal(tomorrow);

    // Completely empty select with placeholder only
    dateSelect.innerHTML = `
        <option value="" disabled selected>-- Select Visit Date (Within 2 Days) --</option>
        <option value="${todayVal}">${formatDateLabel(today, "Today")}</option>
        <option value="${tomorrowVal}">${formatDateLabel(tomorrow, "Tomorrow")}</option>
    `;
}

// 4. Load Services from Database (No default selected)
async function loadServices() {
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/services`);
        if (!res.ok) throw new Error("Could not fetch services");
        activeServices = await res.json();

        // Populate dropdown on booking form with no default selection
        const serviceSelect = document.getElementById("bookingService");
        const walkInSelect = document.getElementById("walkInService");

        if (serviceSelect) {
            serviceSelect.innerHTML = `<option value="" disabled selected>-- Select a Banking Service --</option>` + 
                activeServices.map(s => 
                    `<option value="${s.id}">${s.name} (~${s.estimated_time}) [Prefix: ${s.prefix}]</option>`
                ).join("");
        }
        if (walkInSelect) {
            walkInSelect.innerHTML = activeServices.map(s => 
                `<option value="${s.id}">${s.name} (${s.estimated_time})</option>`
            ).join("");
        }

        // Render Services Cards on Home Page
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
    if (!getAuthToken()) {
        openAuthModal("login");
        return;
    }
    const sel = document.getElementById("bookingService");
    if (sel) {
        sel.value = serviceId;
        handleServiceOrDateChange();
        window.location.hash = "#book";
    }
}

// 5. Handle Service or Date Change & Fetch Real Available Slots
async function handleServiceOrDateChange() {
    const serviceSelect = document.getElementById("bookingService");
    const dateSelect = document.getElementById("bookingDate");
    const slotSelect = document.getElementById("bookingSlot");
    const infoText = document.getElementById("slotAvailabilityInfo");

    const serviceId = serviceSelect ? serviceSelect.value : "";
    const selectedDate = dateSelect ? dateSelect.value : "";

    if (!serviceId || !selectedDate) {
        if (slotSelect) {
            slotSelect.innerHTML = `<option value="" disabled selected>-- Select Service &amp; Date First --</option>`;
            slotSelect.disabled = true;
        }
        if (infoText) {
            infoText.textContent = "Select date and service to view genuine available slots.";
            infoText.className = "form-text small text-muted";
        }
        return;
    }

    if (slotSelect) {
        slotSelect.disabled = true;
        slotSelect.innerHTML = `<option value="" disabled selected>Checking slot availability in database...</option>`;
    }
    if (infoText) {
        infoText.textContent = "Checking live availability...";
        infoText.className = "form-text small text-info";
    }

    try {
        const url = `${BACKEND_URL}/api/v1/tokens/slots?service_id=${encodeURIComponent(serviceId)}&booking_date=${encodeURIComponent(selectedDate)}`;
        const res = await fetch(url);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Unable to check slot availability.");
        }

        const data = await res.json();
        const slots = data.slots || [];

        if (slots.length === 0) {
            slotSelect.innerHTML = `<option value="" disabled selected>No slots available for this date.</option>`;
            infoText.textContent = "No working slots scheduled for this date.";
            infoText.className = "form-text small text-danger";
            return;
        }

        let availableCount = 0;
        let optionsHtml = `<option value="" disabled selected>-- Select an Available Time Slot --</option>`;

        slots.forEach(s => {
            if (s.available) {
                availableCount++;
                optionsHtml += `<option value="${s.slot}">${s.slot} (${s.status_text})</option>`;
            } else {
                optionsHtml += `<option value="${s.slot}" disabled>${s.slot} (Full / Unavailable)</option>`;
            }
        });

        slotSelect.innerHTML = optionsHtml;
        slotSelect.disabled = false;

        if (availableCount > 0) {
            infoText.textContent = `✓ ${availableCount} time slots available for ${data.date_label}.`;
            infoText.className = "form-text small text-success fw-semibold";
        } else {
            infoText.textContent = `All time slots are currently booked for ${data.date_label}. Please select another date.`;
            infoText.className = "form-text small text-danger fw-semibold";
        }

    } catch (err) {
        console.error("Slot fetch error:", err);
        if (slotSelect) {
            slotSelect.innerHTML = `<option value="" disabled selected>Error loading slots</option>`;
        }
        if (infoText) {
            infoText.textContent = err.message;
            infoText.className = "form-text small text-danger";
        }
    }
}

function handleSlotChange() {
    const slotSelect = document.getElementById("bookingSlot");
    const infoText = document.getElementById("slotAvailabilityInfo");
    if (slotSelect && slotSelect.value && infoText) {
        infoText.textContent = `Selected slot: ${slotSelect.value}. Ready to generate your token.`;
        infoText.className = "form-text small text-primary fw-semibold";
    }
}

// 6. Book Token (Submit Form with Validation)
async function handleBookToken(event) {
    event.preventDefault();
    const token = getAuthToken();
    if (!token) {
        openAuthModal("login");
        return;
    }

    const alertBox = document.getElementById("bookingAlert");
    if (alertBox) alertBox.classList.add("d-none");

    const name = document.getElementById("custName").value.trim();
    const phone = document.getElementById("custPhone").value.trim();
    const email = document.getElementById("custEmail").value.trim() || null;
    const account = document.getElementById("custAccount").value.trim() || null;
    const serviceId = parseInt(document.getElementById("bookingService").value);
    const dateVal = document.getElementById("bookingDate").value;
    const slotVal = document.getElementById("bookingSlot").value;

    // Field Validations
    if (!name) {
        showBookingError("Please enter your full name.");
        return;
    }
    if (!phone || phone.length < 10) {
        showBookingError("Please enter a valid 10-digit mobile number.");
        return;
    }
    if (!serviceId) {
        showBookingError("Please select a banking service.");
        return;
    }
    if (!dateVal) {
        showBookingError("Please select a visit date within the next 2 days.");
        return;
    }
    if (!slotVal) {
        showBookingError("Please select an available time slot.");
        return;
    }

    const btn = document.getElementById("btnBookSubmit");
    if (btn) btn.disabled = true;

    const payload = {
        customer_name: name,
        customer_phone: phone,
        customer_email: email,
        customer_account_number: account,
        service_id: serviceId,
        booking_date: dateVal,
        time_slot: slotVal,
    };

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/tokens/book`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Booking failed. Please check slot availability.");
        }

        const data = await res.json();

        // Populate Ticket Confirmation Display
        document.getElementById("resToken").textContent = data.token_number;
        document.getElementById("resService").textContent = data.service_name;
        document.getElementById("resDateSlot").textContent = `${data.booking_date} • ${data.time_slot}`;
        document.getElementById("resDesk").textContent = `${data.counter_name} (${data.desk_label})`;
        document.getElementById("resAhead").textContent = `${data.people_ahead} customer(s)`;
        document.getElementById("resWait").textContent = `~${data.estimated_wait_minutes} mins`;
        document.getElementById("resArrival").textContent = data.recommended_arrival_time;
        document.getElementById("resNotice").textContent = data.status === "APPROACHING" ? 
            "Your turn is approaching soon! Please arrive 10-15 minutes prior to your slot." : 
            "Token confirmed. You can track your place in the live queue anytime from home.";

        // Show success card and hide booking form
        document.getElementById("tokenSuccessCard").classList.remove("d-none");
        document.getElementById("formBookToken").classList.add("d-none");
        document.getElementById("tokenSuccessCard").scrollIntoView({ behavior: "smooth" });

        // Clear the form inputs completely so another token request starts with clean fields
        resetBookingForm();

        loadLiveQueue();
    } catch (err) {
        showBookingError(err.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

function showBookingError(msg) {
    const alertBox = document.getElementById("bookingAlert");
    if (alertBox) {
        alertBox.textContent = msg;
        alertBox.classList.remove("d-none");
        alertBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

function resetBookingForm() {
    const form = document.getElementById("formBookToken");
    if (form) form.reset();

    // Reset dropdowns to placeholder option
    const srv = document.getElementById("bookingService");
    const dte = document.getElementById("bookingDate");
    const slt = document.getElementById("bookingSlot");
    const info = document.getElementById("slotAvailabilityInfo");
    const alertBox = document.getElementById("bookingAlert");

    if (srv) srv.selectedIndex = 0;
    if (dte) dte.selectedIndex = 0;
    if (slt) {
        slt.innerHTML = `<option value="" disabled selected>-- Select Service &amp; Date First --</option>`;
        slt.disabled = true;
    }
    if (info) {
        info.textContent = "Select date and service to view genuine available slots.";
        info.className = "form-text small text-muted";
    }
    if (alertBox) alertBox.classList.add("d-none");

    // Populate user name and email from session if logged in
    const user = getAuthUser();
    if (user) {
        const nameInput = document.getElementById("custName");
        const emailInput = document.getElementById("custEmail");
        const phoneInput = document.getElementById("custPhone");
        if (nameInput) nameInput.value = user.full_name;
        if (emailInput && user.email) emailInput.value = user.email;
        if (phoneInput && user.phone) phoneInput.value = user.phone;
    }
}

function startNewBooking() {
    document.getElementById("tokenSuccessCard").classList.add("d-none");
    document.getElementById("formBookToken").classList.remove("d-none");
    resetBookingForm();
    document.getElementById("book").scrollIntoView({ behavior: "smooth" });
}

// ==========================================
// 7. USER DATA ISOLATION: MY TOKENS MODAL
// ==========================================
async function openMyTokensModal() {
    const token = getAuthToken();
    if (!token) {
        openAuthModal("login");
        return;
    }

    const modalEl = document.getElementById("myTokensModal");
    if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }

    const container = document.getElementById("myTokensList");
    if (!container) return;
    container.innerHTML = `<div class="text-center py-4"><span class="spinner-border spinner-border-sm text-primary me-2"></span>Loading your tokens...</div>`;

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/tokens/my-tokens`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Could not load your tokens.");
        const tokens = await res.json();

        if (!tokens || tokens.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-ticket-detailed fs-1 text-secondary d-block mb-2"></i>
                    No tokens booked yet. You can book a bank token from home for today or tomorrow.
                    <div class="mt-3">
                        <a href="#book" class="btn btn-sm btn-bank-primary" data-bs-dismiss="modal">Book Your Token</a>
                    </div>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Token</th>
                        <th>Service</th>
                        <th>Date &amp; Slot</th>
                        <th>Desk</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${tokens.map(t => `
                        <tr>
                            <td class="fw-bold text-navy fs-5">${t.token_number}</td>
                            <td>${t.service_name}</td>
                            <td><span class="fw-semibold">${t.booking_date}</span><br><small class="text-muted">${t.time_slot}</small></td>
                            <td>${t.counter_name || 'Counter 1'} (${t.desk_label || 'Service Desk'})</td>
                            <td>
                                <span class="badge ${t.status === 'SERVING' ? 'bg-success' : (t.status === 'APPROACHING' ? 'bg-warning text-dark' : (t.status === 'COMPLETED' ? 'bg-secondary' : (t.status === 'CANCELLED' ? 'bg-danger' : 'bg-primary')))}">
                                    ${t.status}
                                </span>
                            </td>
                            <td>
                                ${t.status === 'WAITING' || t.status === 'APPROACHING' ? `
                                    <button class="btn btn-sm btn-outline-danger" onclick="cancelUserToken('${t.token_number}')">
                                        Cancel
                                    </button>
                                ` : `<span class="text-muted small">&mdash;</span>`}
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    } catch (err) {
        container.innerHTML = `<div class="text-danger text-center py-3">${err.message}</div>`;
    }
}

async function cancelUserToken(tokenNumber) {
    if (!confirm(`Are you sure you want to cancel token ${tokenNumber}?`)) return;

    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/tokens/${encodeURIComponent(tokenNumber)}/cancel`, {
            method: "DELETE"
        });
        if (!res.ok) throw new Error("Could not cancel token.");
        alert(`Token ${tokenNumber} has been cancelled.`);
        openMyTokensModal(); // Refresh modal
        loadLiveQueue();
    } catch (err) {
        alert(err.message);
    }
}

// ==========================================
// 8. REAL-TIME LIVE QUEUE STATUS
// ==========================================
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

// ==========================================
// 9. TRACK TOKEN BY NUMBER
// ==========================================
async function handleTrackToken(event) {
    if (event) event.preventDefault();
    const tokenInput = document.getElementById("trackTokenInput").value.trim().toUpperCase();
    if (!tokenInput) {
        alert("Please enter a token number (e.g. A101, B102)");
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

// ==========================================
// 10. STAFF CONSOLE & WALK-IN ISSUANCE
// ==========================================
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

// ==========================================
// 11. CONTACT INQUIRY FORM
// ==========================================
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

// ==========================================
// 12. WEBSOCKET REAL-TIME BROADCASTS
// ==========================================
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
