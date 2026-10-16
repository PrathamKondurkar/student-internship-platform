const $ = (selector) => document.querySelector(selector);
const state = { user: null, authMode: "login", internships: [] };

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || "Something went wrong. Please try again.");
  return payload;
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}
function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 3200);
}
function setAuthMode(mode) {
  state.authMode = mode;
  const registering = mode === "register";
  $("#nameField").classList.toggle("hidden", !registering);
  $("#roleField").classList.toggle("hidden", !registering);
  $("#authTitle").textContent = registering ? "Make room for what's next." : "Welcome back.";
  $("#authSubtitle").textContent = registering ? "Create your SkillBridge account." : "Pick up where you left off.";
  $("#authSubmit").textContent = registering ? "Create account" : "Log in";
  $("#authPassword").autocomplete = registering ? "new-password" : "current-password";
  $("#authName").required = registering;
  $("#authRole").required = registering;
  $("#authMessage").textContent = "";
  document.querySelectorAll(".tab").forEach(tab => tab.classList.toggle("active", tab.dataset.mode === mode));
}
function openAuth(mode = "login") {
  $("#authModal").classList.remove("hidden");
  setAuthMode(mode);
}
function closeAuth() { $("#authModal").classList.add("hidden"); }

async function loadInternships(query = "") {
  const grid = $("#internshipGrid");
  grid.innerHTML = '<div class="loading-card">Finding opportunities...</div>';
  try {
    const data = await api(`/api/internships${query ? `?q=${encodeURIComponent(query)}` : ""}`);
    state.internships = data.internships || [];
    renderInternships(state.internships);
  } catch (error) {
    grid.innerHTML = `<div class="loading-card">${escapeHtml(error.message)}<br><small>Make sure the backend and MongoDB are running.</small></div>`;
  }
}
function renderInternships(items) {
  const grid = $("#internshipGrid");
  if (!items.length) {
    grid.innerHTML = '<div class="loading-card">No internships found yet. Check back soon, or sign in as a company to post one.</div>';
    return;
  }
  grid.innerHTML = items.map((item, index) => `
    <article class="internship-card">
      <div class="card-top"><div class="company-symbol">${escapeHtml((item.company_name || "C").slice(0,1).toUpperCase())}</div><span class="tag">INTERNSHIP</span></div>
      <h3>${escapeHtml(item.title)}</h3><div class="company-name">${escapeHtml(item.company_name || "Company")}</div>
      <p class="card-description">${escapeHtml((item.description || "").slice(0,145))}${(item.description || "").length > 145 ? "…" : ""}</p>
      <div class="skill-tags">${(item.required_skills || []).slice(0,4).map(skill => `<span>${escapeHtml(skill)}</span>`).join("")}</div>
      <div class="card-footer"><span class="location">⌖ ${escapeHtml(item.location || "Location flexible")}</span>
      <button class="apply-btn" data-apply="${escapeHtml(item._id)}">View / apply ↗</button></div>
    </article>`).join("");
}
function statusPill(status) { return `<span class="status ${escapeHtml(status)}">${escapeHtml(status)}</span>`; }

async function refreshSession() {
  try {
    const data = await api("/api/me");
    state.user = data.user;
  } catch { state.user = null; }
  updateHeader();
  renderDashboard();
}
function updateHeader() {
  const loggedIn = !!state.user;
  $("#openAuthBtn").classList.toggle("hidden", loggedIn);
  $("#logoutBtn").classList.toggle("hidden", !loggedIn);
  $("#userBadge").classList.toggle("hidden", !loggedIn);
  $("#userBadge").textContent = loggedIn ? `${state.user.name} · ${state.user.role}` : "";
}
async function renderDashboard() {
  const root = $("#dashboardContent");
  if (!state.user) {
    root.innerHTML = `<div class="empty-state"><div class="empty-icon">↗</div><h3>Your next opportunity is waiting</h3><p>Create an account or log in to unlock your personalized dashboard.</p><button class="btn btn-primary" id="dashboardAuthInner">Log in / Sign up</button></div>`;
    $("#dashboardAuthInner").addEventListener("click", () => openAuth("login"));
    return;
  }
  if (state.user.role === "student") return renderStudentDashboard(root);
  if (state.user.role === "company") return renderCompanyDashboard(root);
  root.innerHTML = `<div class="dashboard-grid"><div class="dashboard-block"><h3>Admin overview</h3><p class="muted">View platform-level application and skill analytics.</p><button class="btn btn-primary" id="loadAnalytics">Load analytics</button></div><div class="dashboard-block" id="analyticsBox"><p class="muted">Analytics will appear here.</p></div></div>`;
  $("#loadAnalytics").addEventListener("click", loadAnalytics);
}
async function renderStudentDashboard(root) {
  let profile = { skills: [], interests: "", education: "", resume_url: "" };
  let applications = [];
  let recommendations = [];
  try {
    [profile, applications, recommendations] = await Promise.all([
      api("/api/student/profile").then(d => d.profile),
      api("/api/applications/mine").then(d => d.applications),
      api("/api/recommendations").then(d => d.recommendations)
    ]);
  } catch (error) { showToast(error.message); }
  root.innerHTML = `
    <div class="dashboard-grid">
      <div class="dashboard-block"><h3>Your student profile</h3>
        <form id="profileForm" class="profile-form">
          <div class="field full"><label for="profileSkills">Skills (comma-separated)</label><input id="profileSkills" value="${escapeHtml((profile.skills || []).join(", "))}" placeholder="Python, SQL, MongoDB"></div>
          <div class="field full"><label for="profileEducation">Education</label><input id="profileEducation" value="${escapeHtml(profile.education || "")}" placeholder="Degree, college, year"></div>
          <div class="field full"><label for="profileInterests">Career interests</label><textarea id="profileInterests" placeholder="What kind of work interests you?">${escapeHtml(profile.interests || "")}</textarea></div>
          <div class="field full"><label for="profileResume">Resume URL (optional)</label><input id="profileResume" type="url" value="${escapeHtml(profile.resume_url || "")}" placeholder="https://..."></div>
          <div class="full"><button class="btn btn-primary" type="submit">Save profile</button></div>
        </form>
      </div>
      <div class="dashboard-block"><h3>Recommended for you</h3><div class="data-list">
        ${recommendations.length ? recommendations.slice(0,5).map(item => `<div class="data-row"><div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.company_name)} · ${item.match.score}% match</small><small>Missing: ${escapeHtml(item.match.missing_skills.join(", ") || "None — great fit!")}</small></div><span class="match-score">${item.match.score}%</span></div>`).join("") : '<p class="muted">Add skills and explore open internships to get personalized matches.</p>'}
      </div></div>
      <div class="dashboard-block" style="grid-column:1/-1"><h3>Your applications</h3><div class="data-list">
        ${applications.length ? applications.map(item => `<div class="data-row"><div><strong>${escapeHtml(item.internship_title)}</strong><small>${escapeHtml(item.company_name)} · Applied ${escapeHtml((item.applied_at || "").slice(0,10))}</small></div>${statusPill(item.status)}</div>`).join("") : '<p class="muted">No applications yet. Explore the opportunities above to get started.</p>'}
      </div></div>
    </div>`;
  $("#profileForm").addEventListener("submit", async event => {
    event.preventDefault();
    const skills = $("#profileSkills").value.split(",").map(s => s.trim()).filter(Boolean);
    try {
      await api("/api/student/profile", { method: "PUT", body: JSON.stringify({
        skills, education: $("#profileEducation").value,
        interests: $("#profileInterests").value, resume_url: $("#profileResume").value
      })});
      showToast("Profile saved. Your recommendations are refreshed.");
      renderDashboard();
    } catch (error) { showToast(error.message); }
  });
}
async function renderCompanyDashboard(root) {
  let applications = [];
  try { applications = (await api("/api/company/applications")).applications; } catch (error) { showToast(error.message); }
  root.innerHTML = `
    <div class="dashboard-grid">
      <div class="dashboard-block"><h3>Post an internship</h3>
        <form id="internshipForm">
          <div class="field"><label for="postTitle">Role title</label><input id="postTitle" required minlength="3" placeholder="Data Analyst Intern"></div>
          <div class="field"><label for="postDescription">Description</label><textarea id="postDescription" required minlength="10" placeholder="Describe the work, learning goals, and expectations."></textarea></div>
          <div class="field"><label for="postSkills">Required skills (comma-separated)</label><input id="postSkills" placeholder="Python, SQL, Excel"></div>
          <div class="field"><label for="postLocation">Location / work mode</label><input id="postLocation" placeholder="Pune / Hybrid / Remote"></div>
          <button class="btn btn-primary" type="submit">Publish internship</button>
        </form>
      </div>
      <div class="dashboard-block"><h3>Applicant pipeline</h3><div class="data-list">
        ${applications.length ? applications.map(item => `<div class="data-row"><div><strong>${escapeHtml(item.student_name)}</strong><small>${escapeHtml(item.internship_title)} · ${escapeHtml(item.company_name)}</small><small>Skills: ${escapeHtml((item.skills_at_application || []).join(", ") || "Not added")}</small><div class="inline-actions" style="margin-top:8px"><select aria-label="Application status" data-status-select="${escapeHtml(item._id)}">${["pending","shortlisted","rejected","accepted"].map(s => `<option value="${s}" ${item.status===s?"selected":""}>${s}</option>`).join("")}</select><button class="small-btn" data-save-status="${escapeHtml(item._id)}">Update</button></div></div>${statusPill(item.status)}</div>`).join("") : '<p class="muted">Applicants will appear here when students apply to your internships.</p>'}
      </div></div>
    </div>`;
  $("#internshipForm").addEventListener("submit", async event => {
    event.preventDefault();
    try {
      await api("/api/internships", { method: "POST", body: JSON.stringify({
        title: $("#postTitle").value, description: $("#postDescription").value,
        required_skills: $("#postSkills").value.split(",").map(s=>s.trim()).filter(Boolean),
        location: $("#postLocation").value
      })});
      showToast("Internship published.");
      $("#internshipForm").reset();
      loadInternships();
    } catch (error) { showToast(error.message); }
  });
}
async function loadAnalytics() {
  try {
    const data = await api("/api/analytics");
    $("#analyticsBox").innerHTML = `<h3>Platform analytics</h3><p class="muted">Active listings: ${data.internship_count}</p><h4>Application statuses</h4><div class="data-list">${data.application_statuses.map(x=>`<div class="data-row"><span>${escapeHtml(x.status)}</span><strong>${x.count}</strong></div>`).join("") || '<p class="muted">No application data yet.</p>'}</div><h4>Popular student skills</h4><div class="data-list">${data.popular_student_skills.map(x=>`<div class="data-row"><span>${escapeHtml(x.skill)}</span><strong>${x.students} students</strong></div>`).join("") || '<p class="muted">No skills added yet.</p>'}</div><h4>SQL joined report</h4><div class="data-list">${data.sql_application_summary.map(x=>`<div class="data-row"><span>${escapeHtml(x.title)} · ${escapeHtml(x.status)}</span><strong>${x.total}</strong></div>`).join("") || '<p class="muted">SQL report fills as applications are submitted.</p>'}</div>`;
  } catch (error) { showToast(error.message); }
}

$("#authForm").addEventListener("submit", async event => {
  event.preventDefault();
  const registering = state.authMode === "register";
  $("#authSubmit").disabled = true;
  $("#authMessage").textContent = "Please wait...";
  try {
    const payload = {
      email: $("#authEmail").value.trim(),
      password: $("#authPassword").value,
    };
    if (registering) {
      payload.name = $("#authName").value.trim();
      payload.role = $("#authRole").value;
    }
    const data = await api(registering ? "/api/auth/register" : "/api/auth/login", {
      method: "POST", body: JSON.stringify(payload)
    });
    state.user = data.user;
    closeAuth();
    $("#authForm").reset();
    updateHeader();
    await renderDashboard();
    showToast(`Welcome${state.user.name ? `, ${state.user.name}` : ""}!`);
  } catch (error) {
    $("#authMessage").textContent = error.message;
  } finally { $("#authSubmit").disabled = false; }
});

document.querySelectorAll("[data-mode]").forEach(button => button.addEventListener("click", () => setAuthMode(button.dataset.mode)));
document.querySelectorAll("[data-close]").forEach(element => element.addEventListener("click", closeAuth));
["#openAuthBtn","#heroAuthBtn","#dashboardAuthBtn","#ctaAuthBtn"].forEach(selector => $(selector).addEventListener("click", () => openAuth("login")));
$("#logoutBtn").addEventListener("click", async () => {
  try { await api("/api/auth/logout", { method: "POST" }); } catch {}
  state.user = null; updateHeader(); renderDashboard(); showToast("You are logged out.");
});
$("#searchBtn").addEventListener("click", () => loadInternships($("#searchInput").value.trim()));
$("#searchInput").addEventListener("keydown", event => { if (event.key === "Enter") loadInternships($("#searchInput").value.trim()); });
$("#internshipGrid").addEventListener("click", async event => {
  const button = event.target.closest("[data-apply]");
  if (!button) return;
  if (!state.user) return openAuth("login");
  if (state.user.role !== "student") return showToast("Log in as a student to apply.");
  try {
    await api(`/api/internships/${button.dataset.apply}/apply`, { method: "POST", body: "{}" });
    showToast("Application submitted!");
    await renderDashboard();
    await loadInternships($("#searchInput").value.trim());
  } catch (error) { showToast(error.message); }
});
$("#dashboardContent").addEventListener("click", async event => {
  const button = event.target.closest("[data-save-status]");
  if (!button) return;
  const id = button.dataset.saveStatus;
  const select = $(`[data-status-select="${CSS.escape(id)}"]`);
  try {
    await api(`/api/applications/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: select.value }) });
    showToast("Application status updated.");
    renderDashboard();
  } catch (error) { showToast(error.message); }
});
refreshSession();
loadInternships();
