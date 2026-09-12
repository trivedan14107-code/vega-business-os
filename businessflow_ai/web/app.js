let csrf = "";
let pendingThread = null;
let currentTab = "dashboard";
let dashboardData = null;

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));

async function api(url, options = {}) {
  const headers = {"Content-Type":"application/json", ...(options.headers || {})};
  if (options.method && options.method !== "GET") headers["X-CSRF-Token"] = csrf;
  const response = await fetch(url, {...options, headers});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Something went wrong");
  return body;
}

function notice(message, error = false) {
  const el = $("notice");
  if (!el) return;
  el.textContent = message;
  el.className = `notice${error ? " error" : ""}`;
  el.classList.remove("hidden");
  if (!error) {
    setTimeout(() => {
      if (el.textContent === message) el.classList.add("hidden");
    }, 8000);
  }
}

function humanRole(role) {
  return String(role).replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
}

function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-pane").forEach(pane => {
    pane.classList.toggle("active", pane.id === `tab-content-${tabId}`);
    pane.classList.toggle("hidden", pane.id !== `tab-content-${tabId}`);
  });
}

function renderMetrics(metrics, data) {
  if ($("kpi-hours")) $("kpi-hours").textContent = `${metrics?.hours_saved || "0.0"} hrs`;
  if ($("kpi-agents")) $("kpi-agents").textContent = `${metrics?.active_agents || data.agents?.length || 10}`;
  if ($("kpi-schedules")) $("kpi-schedules").textContent = `${metrics?.scheduled_automations || 0}`;
  if ($("kpi-outcomes")) $("kpi-outcomes").textContent = `${metrics?.tasks_completed || 0}`;
}

function renderPlaybooks(playbooks) {
  const container = $("playbooks-grid");
  if (!container) return;
  const list = playbooks || [];
  if (!list.length) {
    container.innerHTML = `<div class="empty">No playbooks loaded.</div>`;
    return;
  }
  container.innerHTML = list.map(p => `
    <div class="playbook-card">
      <div>
        <div class="playbook-top">
          <span class="playbook-icon">${escapeHtml(p.icon || "⚡")}</span>
          <div>
            <div class="playbook-title">${escapeHtml(p.title)}</div>
            <span class="badge" style="font-size:10px;">${escapeHtml(p.category || "Workflow")}</span>
          </div>
        </div>
        <p class="playbook-desc" style="margin-top:10px;">${escapeHtml(p.description)}</p>
      </div>
      <div>
        <div class="playbook-meta">
          <span>⏱️ Saves ~${p.estimated_time_saved_minutes || 30} mins</span>
          <span>🤖 ${p.specialist_roles?.length || 2} Specialists</span>
        </div>
        <button type="button" class="primary small-btn btn-launch-playbook" style="width:100%;margin-top:10px;" data-prompt="${escapeHtml(p.prompt_template)}">
          ▶️ Launch Playbook
        </button>
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".btn-launch-playbook").forEach(btn => {
    btn.addEventListener("click", () => {
      const prompt = btn.dataset.prompt;
      $("goal").value = prompt;
      switchTab("dashboard");
      $("goal").focus();
      notice("Playbook loaded into composer. Click 'Ask Vega' or 'Schedule' to execute.");
    });
  });
}

async function loadWorkforceStudio() {
  const container = $("workforce-grid");
  if (!container) return;
  try {
    const templates = await api("/api/workforce");
    container.innerHTML = templates.map(t => `
      <div class="workforce-card">
        <div class="workforce-header">
          <strong>${escapeHtml(humanRole(t.role))} Specialist</strong>
          <span class="badge ${escapeHtml(t.risk_level)}">${escapeHtml(t.risk_level)} Risk</span>
        </div>
        <div style="font-size:13px;color:#444;">${escapeHtml(t.responsibilities?.[0] || "")}</div>
        <div>
          <small style="color:var(--muted);font-weight:700;">ALLOWED TOOLSET:</small>
          <div class="tool-tags">
            ${(t.allowed_tools || []).map(tool => `<span class="tool-tag">${escapeHtml(tool)}</span>`).join("")}
          </div>
        </div>
        <div>
          <small style="color:var(--muted);font-weight:700;">GOVERNANCE RULE:</small>
          <div style="font-size:12px;color:#555;margin-top:2px;"><em>"${escapeHtml(t.business_rules?.[0] || "Execute with owner signoff")}"</em></div>
        </div>
        <button type="button" class="secondary small-btn btn-prompt-specialist" data-role="${escapeHtml(t.role)}" style="margin-top:6px;">
          ⚡ Prompt ${escapeHtml(humanRole(t.role))}
        </button>
      </div>
    `).join("");

    container.querySelectorAll(".btn-prompt-specialist").forEach(btn => {
      btn.addEventListener("click", () => {
        const role = btn.dataset.role;
        $("goal").value = `Direct request for ${humanRole(role)} specialist: `;
        switchTab("dashboard");
        $("goal").focus();
      });
    });
  } catch (err) {
    container.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
  }
}

function renderAgents(agents) {
  const countEl = $("agent-count");
  if (countEl) countEl.textContent = agents.length;
  const container = $("agents");
  if (!container) return;
  container.className = agents.length ? "list" : "list empty";
  container.innerHTML = agents.length ? agents.map(agent => `
    <div class="row">
      <div class="row-main">
        <strong>${escapeHtml(humanRole(agent.role))}</strong>
        <small>${escapeHtml(agent.responsibilities?.[0] || "Ready for work")}</small>
      </div>
      <span class="badge ${escapeHtml(agent.status)}">${escapeHtml(agent.status)}</span>
    </div>
  `).join("") : "No active agents initialized yet.";
}

function renderConnections(connections) {
  const byProvider = Object.fromEntries(connections.map(c => [c.provider, c]));
  const google = byProvider.google_workspace;
  const slack = byProvider.slack;

  const html = `
    <div class="row">
      <div class="row-main">
        <strong>Google Workspace</strong>
        <small>${escapeHtml(google?.account_email || "Calendar, Meet, Gmail & Sheets")}</small>
      </div>
      <span class="badge ${google ? 'completed' : 'pending'}">${google ? "Connected" : "Required"}</span>
    </div>
    <div id="slack-row" class="row">
      <div class="row-main">
        <strong>Slack Team Channels</strong>
        <small>${slack ? "Workspace connected" : "Team notifications"}</small>
      </div>
      ${slack ? '<span class="badge completed">Connected</span>' : '<a class="link-button" href="/api/oauth/slack/start">Connect</a>'}
    </div>
  `;

  if ($("connections")) $("connections").innerHTML = html;
  if ($("settings-connections")) $("settings-connections").innerHTML = html;
}

function selectContactAction(contact, action) {
  const textarea = $("goal");
  if (action === "email") {
    textarea.value = `Send an email update to ${contact.name} (${contact.email || "email"}) regarding sprint deliverables`;
  } else if (action === "meet") {
    textarea.value = `Schedule a 30-minute sync meeting with ${contact.name} tomorrow at 11:00 AM on Google Meet`;
  }
  switchTab("dashboard");
  textarea.focus();
  notice(`Ready to ${action} ${contact.name}. Click 'Ask Vega' or 'Schedule' to execute.`);
}

function renderQuickChips(contacts) {
  const container = $("quick-chips");
  if (!container) return;
  if (!contacts || !contacts.length) {
    container.innerHTML = `<span style="color:#888;font-size:12px;">No contacts yet</span>`;
    return;
  }
  container.innerHTML = contacts.map(c => `
    <button type="button" class="chip" data-name="${escapeHtml(c.name)}">
      <strong>${escapeHtml(c.name)}</strong> <small>(${escapeHtml(c.role)})</small>
    </button>
  `).join("");

  container.querySelectorAll(".chip").forEach((chip, idx) => {
    chip.addEventListener("click", () => selectContactAction(contacts[idx], "meet"));
  });
}

function renderContacts(contacts) {
  renderQuickChips(contacts);
  const list = contacts || [];

  const dashContainer = $("dash-contacts");
  if (dashContainer) {
    dashContainer.innerHTML = list.slice(0, 3).map((c, idx) => `
      <div class="row">
        <div class="row-main">
          <strong>${escapeHtml(c.name)}</strong>
          <small>${escapeHtml(c.role)} · ${escapeHtml(c.phone || c.email || "")}</small>
        </div>
        <div style="display:flex;gap:4px;">
          <button type="button" class="secondary small-btn btn-meet-dash" data-idx="${idx}">📅 Meet</button>
        </div>
      </div>
    `).join("");

    dashContainer.querySelectorAll(".btn-meet-dash").forEach(btn => {
      btn.addEventListener("click", () => selectContactAction(list[btn.dataset.idx], "meet"));
    });
  }

  const crmContainer = $("contacts");
  if (crmContainer) {
    crmContainer.innerHTML = list.map((c, idx) => `
      <div class="contact-card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <strong>${escapeHtml(c.name)}</strong>
          <span class="badge" style="font-size:10px;">${escapeHtml(c.category || "teammate")}</span>
        </div>
        <div style="font-size:13px;color:#444;">${escapeHtml(c.role)}</div>
        <div style="font-size:12px;color:var(--muted);">📞 ${escapeHtml(c.phone || "No phone")} · ✉️ ${escapeHtml(c.email || "No email")}</div>
        ${c.notes ? `<div style="font-size:11px;color:#666;"><em>"${escapeHtml(c.notes)}"</em></div>` : ''}
        <div class="contact-actions">
          <button type="button" class="secondary small-btn btn-email" data-idx="${idx}">✉️ Email</button>
          <button type="button" class="secondary small-btn btn-meet" data-idx="${idx}">📅 Schedule Meet</button>
        </div>
      </div>
    `).join("");

    crmContainer.querySelectorAll(".btn-email").forEach(btn => {
      btn.addEventListener("click", () => selectContactAction(list[btn.dataset.idx], "email"));
    });
    crmContainer.querySelectorAll(".btn-meet").forEach(btn => {
      btn.addEventListener("click", () => selectContactAction(list[btn.dataset.idx], "meet"));
    });
  }
}

function formatTimeUntil(dateString) {
  const target = new Date(dateString).getTime();
  const now = Date.now();
  const diffMs = target - now;
  if (diffMs <= 0) return "Due now";
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `in ${diffDays}d ${diffHours % 24}h`;
  if (diffHours > 0) return `in ${diffHours}h ${diffMins % 60}m`;
  if (diffMins > 0) return `in ${diffMins}m ${diffSecs % 60}s`;
  return `in ${diffSecs}s`;
}

function renderSchedules(schedules) {
  const activeSchedules = schedules || [];
  const pendingCount = activeSchedules.filter(s => s.status === "pending" || s.status === "running").length;
  if ($("schedule-count")) $("schedule-count").textContent = pendingCount;

  const html = activeSchedules.length ? activeSchedules.map(s => {
    const runAtDate = new Date(s.run_at);
    const timeUntil = formatTimeUntil(s.run_at);
    const isPending = s.status === "pending";
    return `
      <div class="row" style="flex-direction: column; align-items: flex-start; gap: 6px;">
        <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
          <div class="row-main">
            <strong>${escapeHtml(s.goal)}</strong>
            <small>⏱️ ${runAtDate.toLocaleString()} (${escapeHtml(timeUntil)})</small>
          </div>
          <span class="badge ${escapeHtml(s.status)}">${escapeHtml(s.status)}</span>
        </div>
        <div class="schedule-row-actions" style="display: flex; gap: 6px; width: 100%; justify-content: flex-end; margin-top: 2px;">
          ${isPending || s.status === "failed" ? `<button type="button" class="primary small-btn btn-run-schedule" data-id="${escapeHtml(s.schedule_id)}">▶️ Run Now</button>` : ''}
          <button type="button" class="secondary small-btn btn-cancel-schedule" style="color: var(--danger);" data-id="${escapeHtml(s.schedule_id)}">✖ Cancel</button>
        </div>
      </div>
    `;
  }).join("") : "No scheduled workflows yet.";

  if ($("schedules")) {
    $("schedules").className = activeSchedules.length ? "list" : "list empty";
    $("schedules").innerHTML = html;
  }
  if ($("scheduler-full-list")) {
    $("scheduler-full-list").className = activeSchedules.length ? "list" : "list empty";
    $("scheduler-full-list").innerHTML = html;
  }

  document.querySelectorAll(".btn-run-schedule").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      notice("Executing scheduled workflow autonomously…");
      try {
        await api(`/api/schedules/${encodeURIComponent(btn.dataset.id)}/run`, {method: "POST", body: "{}"});
        notice("Scheduled workflow executed successfully.");
        await loadDashboard();
      } catch (err) {
        notice(err.message, true);
      } finally {
        btn.disabled = false;
      }
    });
  });

  document.querySelectorAll(".btn-cancel-schedule").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await api(`/api/schedules/${encodeURIComponent(btn.dataset.id)}`, {method: "DELETE"});
        notice("Scheduled workflow cancelled.");
        await loadDashboard();
      } catch (err) {
        notice(err.message, true);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function renderTasks(tasks) {
  const container = $("tasks");
  if (!container) return;
  const list = tasks || [];
  container.className = list.length ? "list" : "list empty";
  container.innerHTML = list.length ? list.map(task => {
    const results = task.execution_results || [];
    const otherResults = results;
    let subagentExtra = "";
    if (otherResults.length > 0) {
      subagentExtra = `
        <div class="subagent-results" style="margin-top: 8px; display: flex; flex-direction: column; gap: 6px; width: 100%;">
          ${otherResults.map(r => `
            <div style="padding: 10px 14px; background: #faf9f5; border: 1px solid #e8e6dc; border-radius: 6px; font-size: 0.84rem;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: var(--green); font-size: 12px;">⚙️ ${escapeHtml(humanRole(r.adapter || "Specialist Agent"))}</strong>
                <span class="badge" style="font-size: 10px;">${escapeHtml(r.outcome_state || "completed")}</span>
              </div>
              <div style="margin-top: 4px; color: #333; white-space: pre-line;">${escapeHtml(r.summary || JSON.stringify(r))}</div>
              ${r.pdf_url ? `
                <div style="margin-top: 8px;">
                  <a href="${escapeHtml(r.pdf_url)}" target="_blank" download class="primary small-btn" style="display: inline-flex; align-items: center; gap: 6px; text-decoration: none;">
                    📄 Download Executive PDF Brief
                  </a>
                </div>
              ` : ''}
            </div>
          `).join("")}
        </div>
      `;
    }

    return `
    <div class="row" style="flex-direction: column; align-items: flex-start; gap: 4px;">
      <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
        <div class="row-main">
          <strong>${escapeHtml(task.owner_goal)}</strong>
          <small>${new Date(task.updated_at).toLocaleString()}</small>
        </div>
        <span class="badge ${escapeHtml(task.status)}">${escapeHtml(task.status.replaceAll("_", " "))}</span>
      </div>
      ${subagentExtra}
    </div>`;
  }).join("") : "Your verified outcomes will appear here.";
}

function renderAuditEvents(events) {
  const container = $("audit-events-list");
  if (!container) return;
  const list = events || [];
  container.className = list.length ? "list" : "list empty";
  container.innerHTML = list.length ? list.map(ev => `
    <div class="row" style="flex-direction: column; align-items: flex-start; gap: 4px;">
      <div style="display:flex;justify-content:space-between;width:100%;align-items:center;">
        <div class="row-main">
          <strong>🛡️ ${escapeHtml(ev.event_type || "SYSTEM_AUDIT_LOG")}</strong>
          <small>${new Date(ev.created_at).toLocaleString()}</small>
        </div>
        <span class="badge completed">Immutable Verified</span>
      </div>
      <div style="font-family:monospace;font-size:11px;background:#f8f9fa;padding:6px 10px;border-radius:6px;width:100%;overflow-x:auto;color:#333;">
        ${escapeHtml(JSON.stringify(ev.details || {}))}
      </div>
    </div>
  `).join("") : "No audit events logged yet.";
}

async function exportBusinessRecords() {
  try {
    notice("Generating cryptographic export receipt…");
    const data = await api("/api/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `vega-verified-records-${new Date().toISOString().slice(0,10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    notice("Business records exported successfully.");
  } catch (err) {
    notice(err.message, true);
  }
}

async function loadDashboard() {
  dashboardData = await api("/api/dashboard");
  renderMetrics(dashboardData.metrics, dashboardData);
  renderAgents(dashboardData.agents || []);
  renderConnections(dashboardData.connections || []);
  renderContacts(dashboardData.contacts || []);
  renderSchedules(dashboardData.schedules || []);
  renderTasks(dashboardData.tasks || []);
  renderPlaybooks(dashboardData.playbooks || []);
  renderAuditEvents(dashboardData.events || []);
}

function handleVega(result) {
  notice(result.message);
  if (result.status === "waiting_approval") {
    pendingThread = result.thread_id;
    const roles = (result.agents || []).map(a => humanRole(a.role)).join(" and ");
    $("approval-text").textContent = `${roles} will perform an external action. Nothing happens until you approve.`;
    $("approval").classList.remove("hidden");
  } else if (result.status === "waiting_access") {
    const request = result.access_requests?.[0];
    if (request?.connect_url) {
      notice(`Vega needs ${humanRole(request.provider)} access. Use Business Apps to connect it.`);
    }
  } else {
    pendingThread = null;
    $("approval").classList.add("hidden");
  }
}

async function submitGoal(event) {
  event.preventDefault();
  const button = $("send");
  button.disabled = true;
  notice("Vega is assembling the specialist workforce…");
  try {
    const result = await api("/api/goals", {method:"POST", body:JSON.stringify({goal:$("goal").value.trim()})});
    handleVega(result);
    await loadDashboard();
  } catch (error) { notice(error.message, true); }
  finally { button.disabled = false; }
}

async function decide(approved) {
  if (!pendingThread) return;
  $("approve").disabled = true;
  $("reject").disabled = true;
  notice(approved ? "Vega is executing and verifying the work…" : "Cancelling the action…");
  try {
    const result = await api(`/api/approvals/${encodeURIComponent(pendingThread)}`, {method:"POST", body:JSON.stringify({approved})});
    handleVega(result);
    await loadDashboard();
  } catch (error) { notice(error.message, true); }
  finally { $("approve").disabled = false; $("reject").disabled = false; }
}

async function handleAddContact(event) {
  event.preventDefault();
  const name = $("contact-name").value.trim();
  const role = $("contact-role").value.trim();
  const phone = $("contact-phone").value.trim();
  const email = $("contact-email").value.trim();
  const category = $("contact-category").value;
  const notes = $("contact-notes") ? $("contact-notes").value.trim() : "";
  if (!name || !role) return;

  try {
    await api("/api/contacts", {
      method: "POST",
      body: JSON.stringify({ name, role, phone, email, category, notes }),
    });
    notice(`Added ${name} to company directory.`);
    $("contact-form").reset();
    $("contact-form").classList.add("hidden");
    await loadDashboard();
  } catch (error) {
    notice(error.message, true);
  }
}

function formatLocalDateTime(date) {
  const pad = (n) => String(n).padStart(2, "0");
  const y = date.getFullYear();
  const m = pad(date.getMonth() + 1);
  const d = pad(date.getDate());
  const h = pad(date.getHours());
  const min = pad(date.getMinutes());
  return `${y}-${m}-${d}T${h}:${min}`;
}

function initScheduleControls() {
  const toggleBtn = $("toggle-schedule-btn");
  const drawer = $("schedule-drawer");
  const customInput = $("sched-custom-time");
  const sched1h = $("sched-1h");
  const schedTomorrow9am = $("sched-tomorrow-9am");
  const schedTomorrow2pm = $("sched-tomorrow-2pm");
  const confirmBtn = $("confirm-schedule-btn");

  if (toggleBtn && drawer) {
    toggleBtn.addEventListener("click", () => {
      drawer.classList.toggle("hidden");
      if (!drawer.classList.contains("hidden") && customInput && !customInput.value) {
        const d = new Date();
        d.setHours(d.getHours() + 1);
        customInput.value = formatLocalDateTime(d);
      }
    });
  }

  if (sched1h && customInput) {
    sched1h.addEventListener("click", () => {
      const d = new Date();
      d.setHours(d.getHours() + 1);
      customInput.value = formatLocalDateTime(d);
    });
  }

  if (schedTomorrow9am && customInput) {
    schedTomorrow9am.addEventListener("click", () => {
      const d = new Date();
      d.setDate(d.getDate() + 1);
      d.setHours(9, 0, 0, 0);
      customInput.value = formatLocalDateTime(d);
    });
  }

  if (schedTomorrow2pm && customInput) {
    schedTomorrow2pm.addEventListener("click", () => {
      const d = new Date();
      d.setDate(d.getDate() + 1);
      d.setHours(14, 0, 0, 0);
      customInput.value = formatLocalDateTime(d);
    });
  }

  if (confirmBtn) {
    confirmBtn.addEventListener("click", async () => {
      const goal = $("goal").value.trim();
      const timeVal = customInput ? customInput.value : "";
      const preapproved = Boolean($("sched-preapprove")?.checked);
      if (!goal) {
        notice("Please enter a business goal before scheduling.", true);
        $("goal").focus();
        return;
      }
      if (!timeVal) {
        notice("Please select a valid scheduled time.", true);
        return;
      }
      if (!preapproved) {
        notice("Please approve the described actions before scheduling.", true);
        return;
      }
      confirmBtn.disabled = true;
      notice("Scheduling workflow for automated background execution…");
      try {
        const runAt = new Date(timeVal).toISOString();
        await api("/api/schedules", {
          method: "POST",
          body: JSON.stringify({
            goal,
            run_at: runAt,
            schedule_type: "once",
            preapproved: true,
          }),
        });
        notice(`Workflow scheduled for ${new Date(timeVal).toLocaleString()}. Vega will execute it autonomously.`);
        $("goal").value = "";
        drawer.classList.add("hidden");
        await loadDashboard();
      } catch (err) {
        notice(err.message, true);
      } finally {
        confirmBtn.disabled = false;
      }
    });
  }
}

function initNavTabs() {
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      switchTab(tab.dataset.tab);
      if (tab.dataset.tab === "workforce") {
        loadWorkforceStudio();
      }
    });
  });

  const gotoContacts = $("goto-contacts-tab");
  if (gotoContacts) {
    gotoContacts.addEventListener("click", () => switchTab("contacts"));
  }

  const exportDash = $("export-btn-dash");
  if (exportDash) exportDash.addEventListener("click", exportBusinessRecords);
  const exportTasks = $("export-btn-tasks");
  if (exportTasks) exportTasks.addEventListener("click", exportBusinessRecords);
  const exportAudit = $("export-btn-audit");
  if (exportAudit) exportAudit.addEventListener("click", exportBusinessRecords);
}

async function init() {
  try {
    const session = await api("/api/session");
    csrf = session.csrf_token;
    if (!session.authenticated) {
      $("welcome").classList.remove("hidden");
      return;
    }
    $("workspace").classList.remove("hidden");
    $("nav-tabs").classList.remove("hidden");
    $("account").innerHTML = `<span>${escapeHtml(session.email)}</span><button id="logout" class="secondary">Sign out</button>`;
    $("logout").addEventListener("click", async () => { await api("/api/logout", {method:"POST", body:"{}"}); location.reload(); });
    await loadDashboard();
    initNavTabs();
    initScheduleControls();
    loadWorkforceStudio();
    setInterval(() => {
      loadDashboard().catch(() => {});
    }, 10000);
  } catch (error) { notice(error.message, true); $("workspace").classList.remove("hidden"); }
}

$("goal-form").addEventListener("submit", submitGoal);
$("approve").addEventListener("click", () => decide(true));
$("reject").addEventListener("click", () => decide(false));
$("refresh").addEventListener("click", () => loadDashboard().catch(e => notice(e.message, true)));

const toggleBtn = $("toggle-add-contact");
if (toggleBtn) {
  toggleBtn.addEventListener("click", () => {
    $("contact-form").classList.toggle("hidden");
  });
}
const contactForm = $("contact-form");
if (contactForm) {
  contactForm.addEventListener("submit", handleAddContact);
}

init();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Vega remains fully usable as a normal mobile website.
    });
  });
}
