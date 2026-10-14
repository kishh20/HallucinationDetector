// =========================================================================
// Hallucination Detector — Modern Fast Web Client (ChatGPT & Claude Style)
// =========================================================================

let currentUser = null;
let currentChatId = null;
let conversations = [];
let currentMessages = [];
let isGenerating = false;

// DOM Elements
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const messagesList = document.getElementById("messagesList");
const heroScreen = document.getElementById("heroScreen");
const chatHistoryList = document.getElementById("chatHistoryList");
const newChatBtn = document.getElementById("newChatBtn");
const chatHeaderTitle = document.getElementById("chatHeaderTitle");
const authSection = document.getElementById("authSection");
const openAdminBtn = document.getElementById("openAdminBtn");
const adminModal = document.getElementById("adminModal");
const closeAdminModal = document.getElementById("closeAdminModal");
const authModal = document.getElementById("authModal");
const closeAuthModal = document.getElementById("closeAuthModal");
const mobileMenuBtn = document.getElementById("mobileMenuBtn");
const sidebar = document.getElementById("sidebar");
const chatSearchInput = document.getElementById("chatSearchInput");
const togglePasswordBtn = document.getElementById("togglePasswordBtn");

// -------------------------------------------------------------------------
// Initialization
// -------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  setupMarkedOptions();
  initTheme();
  checkAuth();
  loadConversations();
  setupAutoResizeTextarea();
  setupEventListeners();
});

// Configure Marked with highlight.js
function setupMarkedOptions() {
  if (window.marked && window.hljs) {
    marked.setOptions({
      highlight: function(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
      },
      langPrefix: 'hljs language-',
      breaks: true,
      gfm: true
    });
  }
}

// -------------------------------------------------------------------------
// Theme Handling (Dark / Light)
// -------------------------------------------------------------------------
function initTheme() {
  const saved = localStorage.getItem("hd_theme") || "dark";
  setAppTheme(saved);

  document.querySelectorAll(".theme-seg-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset.themeVal;
      setAppTheme(mode);
    });
  });
}

function setAppTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("hd_theme", theme);

  document.querySelectorAll(".theme-seg-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.themeVal === theme);
  });
}

// -------------------------------------------------------------------------
// Event Listeners
// -------------------------------------------------------------------------
function setupEventListeners() {
  sendBtn.addEventListener("click", handleSend);
  newChatBtn.addEventListener("click", startNewChat);

  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // Sidebar search filter
  if (chatSearchInput) {
    chatSearchInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase().trim();
      filterConversations(query);
    });
  }

  // Password visibility toggle
  if (togglePasswordBtn) {
    togglePasswordBtn.addEventListener("click", () => {
      const input = document.getElementById("authPassword");
      if (input.type === "password") {
        input.type = "text";
        togglePasswordBtn.textContent = "🙈";
      } else {
        input.type = "password";
        togglePasswordBtn.textContent = "👁️";
      }
    });
  }

  if (openAdminBtn) {
    openAdminBtn.addEventListener("click", () => {
      openAdminModal();
    });
  }

  if (closeAdminModal) {
    closeAdminModal.addEventListener("click", () => {
      adminModal.classList.remove("active");
    });
  }

  if (closeAuthModal) {
    closeAuthModal.addEventListener("click", () => {
      authModal.classList.remove("active");
    });
  }

  // Close modals on backdrop click
  window.addEventListener("click", (e) => {
    if (e.target === authModal) authModal.classList.remove("active");
    if (e.target === adminModal) adminModal.classList.remove("active");
  });
}

function setupAutoResizeTextarea() {
  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 180) + "px";
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
}

// -------------------------------------------------------------------------
// Authentication
// -------------------------------------------------------------------------
async function checkAuth() {
  try {
    const res = await fetch("/api/auth/me");
    const data = await res.json();
    if (data.authenticated && data.user) {
      currentUser = data.user;
      renderAuthUser(currentUser);
      if (currentUser.is_admin) {
        openAdminBtn.style.display = "inline-flex";
      }
    } else {
      currentUser = null;
      renderAuthGuest();
      openAdminBtn.style.display = "none";
    }
  } catch (err) {
    console.error("Auth check failed:", err);
  }
}

function renderAuthGuest() {
  authSection.innerHTML = `
    <button class="auth-submit-btn" style="padding:0.6rem; font-size:0.86rem;" onclick="openAuthModal('signin')">
      <span>Sign In / Register</span>
    </button>
  `;
}

function renderAuthUser(user) {
  authSection.innerHTML = `
    <div class="user-profile-row">
      <span class="user-name-tag">
        👤 <strong>${escapeHtml(user.username)}</strong>
        ${user.is_admin ? '<span class="badge-tag tag-success">Admin</span>' : ''}
      </span>
      <span class="logout-link" onclick="handleLogout()">Sign Out</span>
    </div>
    <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.2rem; cursor: pointer;" onclick="handleDeleteAccount()">
      Delete Account (GDPR)
    </div>
  `;
}

function openAuthModal(mode = "signin") {
  authModal.classList.add("active");
  switchAuthTab(mode);
}

function continueAsGuest() {
  authModal.classList.remove("active");
}

function switchAuthTab(mode) {
  const tabIn = document.getElementById("tabSignIn");
  const tabUp = document.getElementById("tabSignUp");
  const title = document.getElementById("authModalTitle");
  const submitBtn = document.getElementById("authSubmitBtn");
  const errorBox = document.getElementById("authError");
  errorBox.style.display = "none";

  if (mode === "signin") {
    tabIn.classList.add("active");
    tabUp.classList.remove("active");
    title.textContent = "Welcome Back";
    submitBtn.querySelector("span").textContent = "Sign In";
    submitBtn.dataset.mode = "signin";
  } else {
    tabUp.classList.add("active");
    tabIn.classList.remove("active");
    title.textContent = "Create Free Account";
    submitBtn.querySelector("span").textContent = "Create Account";
    submitBtn.dataset.mode = "signup";
  }
}

document.getElementById("tabSignIn").addEventListener("click", () => switchAuthTab("signin"));
document.getElementById("tabSignUp").addEventListener("click", () => switchAuthTab("signup"));

async function handleAuthSubmit(e) {
  e.preventDefault();
  const mode = document.getElementById("authSubmitBtn").dataset.mode || "signin";
  const username = document.getElementById("authUsername").value.trim();
  const password = document.getElementById("authPassword").value;
  const errorBox = document.getElementById("authError");
  const submitBtn = document.getElementById("authSubmitBtn");
  errorBox.style.display = "none";

  const originalHtml = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span>Processing...</span>`;

  const endpoint = mode === "signin" ? "/api/auth/login" : "/api/auth/register";

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) {
      errorBox.textContent = data.detail || "Authentication failed.";
      errorBox.style.display = "block";
      return;
    }
    authModal.classList.remove("active");
    checkAuth();
    loadConversations();
  } catch (err) {
    errorBox.textContent = "Network error. Please check your connection.";
    errorBox.style.display = "block";
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalHtml;
  }
}

async function handleLogout() {
  await fetch("/api/auth/logout", { method: "POST" });
  currentUser = null;
  checkAuth();
  startNewChat();
}

async function handleDeleteAccount() {
  if (!confirm("Are you sure you want to permanently delete your account and all saved conversations? This cannot be undone.")) return;
  await fetch("/api/user/account", { method: "DELETE" });
  currentUser = null;
  checkAuth();
  startNewChat();
}

// -------------------------------------------------------------------------
// Chat & Messaging Logic
// -------------------------------------------------------------------------
function startNewChat() {
  currentChatId = "chat_" + Date.now();
  currentMessages = [];
  chatHeaderTitle.textContent = "New Verification";
  renderMessages();
  if (window.innerWidth <= 768) {
    sidebar.classList.remove("open");
  }
}

function askSuggestion(text) {
  chatInput.value = text;
  handleSend();
}

async function handleSend() {
  const text = chatInput.value.trim();
  if (!text || isGenerating) return;

  chatInput.value = "";
  chatInput.style.height = "auto";
  isGenerating = true;
  sendBtn.disabled = true;

  if (!currentChatId) {
    currentChatId = "chat_" + Date.now();
  }

  // Add User Message
  currentMessages.push({ role: "user", content: text });
  renderMessages();

  // Temporary placeholder for assistant
  const tempMsgId = "loading_" + Date.now();
  const loadingNode = appendLoadingMessage(tempMsgId);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: text,
        conversation_id: currentChatId,
        history: currentMessages.slice(-6)
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to process question.");
    }

    loadingNode.remove();
    currentMessages.push({
      role: "assistant",
      content: data.answer,
      verification: data.verification,
      sources: data.sources,
      message_id: data.message_id,
      model: data.model,
      elapsed: data.elapsed,
      query: text
    });

    renderMessages();
    saveCurrentConversation();
  } catch (err) {
    loadingNode.remove();
    currentMessages.push({
      role: "assistant",
      content: "⚠️ An error occurred while generating or verifying the answer: " + err.message,
      verification: { supported: false, confidence: 0, reason: "Error" }
    });
    renderMessages();
  } finally {
    isGenerating = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

function renderMessages() {
  if (currentMessages.length === 0) {
    heroScreen.style.display = "flex";
    messagesList.innerHTML = "";
    return;
  }

  heroScreen.style.display = "none";
  messagesList.innerHTML = "";

  currentMessages.forEach((msg, idx) => {
    if (msg.role === "user") {
      const row = document.createElement("div");
      row.className = "message-row user";
      row.innerHTML = `<div class="message-bubble">${escapeHtml(msg.content)}</div>`;
      messagesList.appendChild(row);
    } else {
      const row = createAssistantRow(msg, idx);
      messagesList.appendChild(row);
    }
  });

  // Enhance rendered code blocks with language headers and copy buttons
  postProcessCodeBlocks();

  const container = document.getElementById("messagesContainer");
  container.scrollTop = container.scrollHeight;
}

function createAssistantRow(msg, idx) {
  const row = document.createElement("div");
  row.className = "message-row assistant";

  // Verification Badge
  const isVerified = msg.verification && msg.verification.supported;
  const conf = msg.verification ? Math.round(msg.verification.confidence) : 90;
  const badgeClass = isVerified ? "badge-verified" : "badge-unsupported";
  const badgeIcon = isVerified ? "✓" : "⚠️";
  const badgeText = isVerified 
    ? `Faithful Evidence (${conf}%)` 
    : `Potential Hallucination (${conf}%)`;

  // Parse Markdown
  const parsedMarkdown = marked.parse(msg.content || "");

  // Render Citations & Sources Box
  let sourcesHtml = "";
  if (msg.sources && msg.sources.length > 0) {
    const sourceItems = msg.sources.map((s, sIdx) => {
      let domain = "web";
      try {
        const u = new URL(s.url);
        domain = u.hostname.replace("www.", "");
      } catch (e) {}

      return `
        <div class="source-item">
          <div>
            <span class="source-domain-pill">${escapeHtml(domain.toUpperCase())}</span>
            <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener" class="source-link">
              ${escapeHtml(s.title || "Web Reference")} ↗
            </a>
          </div>
          <div class="source-snippet">${escapeHtml(s.content ? s.content.slice(0, 180) + "..." : "")}</div>
        </div>
      `;
    }).join("");

    sourcesHtml = `
      <div class="sources-accordion">
        <div class="sources-header" onclick="toggleSources(${idx})">
          <span>📚 ${msg.sources.length} Live Evidence Sources Cross-Checked</span>
          <span id="sourcesArrow_${idx}">▼</span>
        </div>
        <div class="sources-list" id="sourcesList_${idx}">
          ${sourceItems}
        </div>
      </div>
    `;
  }

  // Claude / ChatGPT Style Feedback Bar
  const msgId = msg.message_id || `msg_${idx}`;
  const feedbackBar = `
    <div class="feedback-bar">
      <button class="feedback-btn" onclick="copyAnswerText(${idx}, this)" title="Copy Answer Markdown">
        📋 Copy
      </button>
      <button class="feedback-btn" id="thumbUp_${msgId}" onclick="submitReaction('${msgId}', 'up', ${idx}, this)" title="Helpful response">
        👍 Helpful
      </button>
      <button class="feedback-btn" id="thumbDown_${msgId}" onclick="submitReaction('${msgId}', 'down', ${idx}, this)" title="Unhelpful response">
        👎 Unhelpful
      </button>
      <span class="feedback-msg" id="feedbackMsg_${msgId}" style="display:none;"></span>
    </div>
  `;

  row.innerHTML = `
    <div class="assistant-header">
      <div class="assistant-avatar">✓</div>
      <span class="verification-badge ${badgeClass}" title="${escapeHtml(msg.verification?.reason || 'Verified')}">
        <span>${badgeIcon}</span>
        <span>${badgeText}</span>
      </span>
      ${msg.elapsed ? `<span style="font-size:0.75rem; color:var(--text-muted);">${msg.elapsed}s</span>` : ''}
    </div>
    <div class="assistant-body">${parsedMarkdown}</div>
    ${sourcesHtml}
    ${feedbackBar}
  `;

  return row;
}

// Enhances code blocks with header and copy button
function postProcessCodeBlocks() {
  document.querySelectorAll(".assistant-body pre").forEach((pre, i) => {
    if (pre.parentElement.classList.contains("code-container")) return;

    const code = pre.querySelector("code");
    const lang = code ? (code.className.match(/language-(\w+)/) || [, 'code'])[1] : 'code';

    const container = document.createElement("div");
    container.className = "code-container";

    const header = document.createElement("div");
    header.className = "code-header-bar";
    header.innerHTML = `
      <span>${lang}</span>
      <button class="copy-code-btn" onclick="copyCodeBlock(this)">
        📋 Copy code
      </button>
    `;

    pre.parentNode.insertBefore(container, pre);
    container.appendChild(header);
    container.appendChild(pre);
  });
}

function copyCodeBlock(btn) {
  const code = btn.closest(".code-container").querySelector("pre code").innerText;
  navigator.clipboard.writeText(code);
  const orig = btn.innerHTML;
  btn.innerHTML = "✓ Copied!";
  setTimeout(() => { btn.innerHTML = orig; }, 2000);
}

function appendLoadingMessage(id) {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.id = id;
  row.innerHTML = `
    <div class="assistant-header">
      <div class="assistant-avatar">✓</div>
      <span class="verification-badge badge-verified">
        <span class="pulse-dot"></span>
        <span>Cross-checking live web evidence...</span>
      </span>
    </div>
    <div class="assistant-body" style="color:var(--text-muted); font-size:0.92rem;">
      Searching Wikipedia, Google News, and DuckDuckGo for factual grounds...
    </div>
  `;
  messagesList.appendChild(row);
  const container = document.getElementById("messagesContainer");
  container.scrollTop = container.scrollHeight;
  return row;
}

function toggleSources(idx) {
  const el = document.getElementById(`sourcesList_${idx}`);
  const arrow = document.getElementById(`sourcesArrow_${idx}`);
  if (!el) return;
  if (el.style.display === "flex") {
    el.style.display = "none";
    arrow.textContent = "▼";
  } else {
    el.style.display = "flex";
    arrow.textContent = "▲";
  }
}

function copyAnswerText(idx, btn) {
  const msg = currentMessages[idx];
  if (!msg) return;
  navigator.clipboard.writeText(msg.content);
  const original = btn.innerHTML;
  btn.innerHTML = "✓ Copied!";
  setTimeout(() => {
    btn.innerHTML = original;
  }, 2000);
}

// -------------------------------------------------------------------------
// Thumbs Up / Down Feedback (Claude Style)
// -------------------------------------------------------------------------
async function submitReaction(messageId, rating, idx, btn) {
  const msg = currentMessages[idx] || {};
  const upBtn = document.getElementById(`thumbUp_${messageId}`);
  const downBtn = document.getElementById(`thumbDown_${messageId}`);
  const statusMsg = document.getElementById(`feedbackMsg_${messageId}`);

  if (rating === "up") {
    upBtn.classList.add("active-up");
    downBtn.classList.remove("active-down");
  } else {
    downBtn.classList.add("active-down");
    upBtn.classList.remove("active-up");
  }

  statusMsg.textContent = "✓ Feedback saved. Thank you!";
  statusMsg.style.display = "inline";

  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message_id: messageId,
        query: msg.query || "Verification Question",
        answer: (msg.content || "").slice(0, 800),
        rating: rating === "up" ? "thumbs_up" : "thumbs_down"
      })
    });
  } catch (err) {
    console.error("Failed to post feedback:", err);
  }
}

// -------------------------------------------------------------------------
// Conversations Persistence
// -------------------------------------------------------------------------
async function loadConversations() {
  if (!currentUser) return;
  try {
    const res = await fetch("/api/conversations");
    const data = await res.json();
    conversations = data.conversations || [];
    renderHistoryList(conversations);
  } catch (err) {
    console.error("Failed to load chats:", err);
  }
}

function filterConversations(query) {
  if (!query) {
    renderHistoryList(conversations);
    return;
  }
  const filtered = conversations.filter(c => (c.title || "").toLowerCase().includes(query));
  renderHistoryList(filtered);
}

function renderHistoryList(listToRender) {
  chatHistoryList.innerHTML = "";
  if (!listToRender || listToRender.length === 0) {
    chatHistoryList.innerHTML = `<div style="padding:0.6rem 0.8rem; font-size:0.8rem; color:var(--text-muted);">No saved chats found.</div>`;
    return;
  }

  listToRender.forEach((conv) => {
    const item = document.createElement("div");
    item.className = "history-item " + (conv.id === currentChatId ? "active" : "");
    item.innerHTML = `
      <span class="history-title" onclick="loadChat('${conv.id}')">${escapeHtml(conv.title || "Chat")}</span>
      <button class="delete-chat-btn" onclick="deleteChat('${conv.id}', event)">✕</button>
    `;
    chatHistoryList.appendChild(item);
  });
}

function loadChat(id) {
  const found = conversations.find(c => c.id === id);
  if (!found) return;
  currentChatId = found.id;
  currentMessages = found.messages || [];
  chatHeaderTitle.textContent = found.title || "Verification Chat";
  renderMessages();
  renderHistoryList(conversations);
  if (window.innerWidth <= 768) {
    sidebar.classList.remove("open");
  }
}

async function saveCurrentConversation() {
  if (!currentUser || currentMessages.length === 0) return;
  const firstUserMsg = currentMessages.find(m => m.role === "user");
  const title = firstUserMsg ? firstUserMsg.content.slice(0, 35) : "Verified Chat";
  chatHeaderTitle.textContent = title;

  const payload = {
    id: currentChatId,
    title: title,
    messages: currentMessages
  };

  await fetch("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  loadConversations();
}

async function deleteChat(id, event) {
  event.stopPropagation();
  if (!confirm("Delete this conversation?")) return;
  await fetch(`/api/conversations/${id}`, { method: "DELETE" });
  if (currentChatId === id) {
    startNewChat();
  }
  loadConversations();
}

// -------------------------------------------------------------------------
// Admin Dashboard
// -------------------------------------------------------------------------
let currentAdminAnalytics = null;

async function openAdminModal() {
  adminModal.classList.add("active");
  switchAdminTab("overview");
}

async function switchAdminTab(tabName) {
  document.querySelectorAll(".admin-tab").forEach(t => t.classList.remove("active"));
  const clickedTab = Array.from(document.querySelectorAll(".admin-tab")).find(t => t.textContent.toLowerCase().includes(tabName));
  if (clickedTab) clickedTab.classList.add("active");

  const content = document.getElementById("adminTabContent");
  content.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--text-muted);">Loading live analytics...</div>`;

  try {
    const res = await fetch("/api/admin/analytics");
    if (!res.ok) {
      content.innerHTML = `<div style="color:#ef4444; padding:1rem;">Unauthorized: Admin access only.</div>`;
      return;
    }
    currentAdminAnalytics = await res.json();
    renderAdminTab(tabName, currentAdminAnalytics);
  } catch (err) {
    content.innerHTML = `<div style="color:#ef4444; padding:1rem;">Error loading data: ${err.message}</div>`;
  }
}

function renderAdminTab(tab, data) {
  const content = document.getElementById("adminTabContent");
  const s = data.summary;

  if (tab === "overview") {
    content.innerHTML = `
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Total Site Visits</div>
          <div class="stat-number">${s.total_visits}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Unique Visitors</div>
          <div class="stat-number">${s.unique_visitors}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total Logins</div>
          <div class="stat-number">${s.total_logins}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Satisfaction Rate</div>
          <div class="stat-number" style="color:var(--accent);">${s.satisfaction_pct}%</div>
        </div>
      </div>
      <div style="display:flex; gap:1rem;">
        <div class="stat-card" style="flex:1;">
          <div class="stat-label">👍 Positive Feedbacks</div>
          <div class="stat-number" style="color:var(--accent);">${s.thumbs_up}</div>
        </div>
        <div class="stat-card" style="flex:1;">
          <div class="stat-label">👎 Negative Feedbacks</div>
          <div class="stat-number" style="color:#ef4444;">${s.thumbs_down}</div>
        </div>
        <div class="stat-card" style="flex:1;">
          <div class="stat-label">👥 Total Registered Users</div>
          <div class="stat-number">${s.total_users}</div>
        </div>
      </div>
    `;
  } else if (tab === "feedback") {
    const rows = data.recent_feedbacks.map(f => `
      <tr>
        <td><strong>${f.rating === 'thumbs_up' ? '👍 Helpful' : '👎 Unhelpful'}</strong></td>
        <td>${escapeHtml(f.username || 'Anonymous')}</td>
        <td><strong>${escapeHtml(f.query || '')}</strong></td>
        <td style="color:var(--text-secondary);">${escapeHtml((f.answer || '').slice(0, 120))}...</td>
        <td style="white-space:nowrap; color:var(--text-muted);">${f.created_at}</td>
      </tr>
    `).join("");

    content.innerHTML = `
      <table class="admin-table">
        <thead>
          <tr>
            <th>Rating</th>
            <th>User</th>
            <th>Question</th>
            <th>Answer Snippet</th>
            <th>Date & Time</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows : '<tr><td colspan="5" style="text-align:center;">No feedback recorded yet.</td></tr>'}
        </tbody>
      </table>
    `;
  } else if (tab === "logins") {
    const rows = data.recent_logins.map(l => `
      <tr>
        <td><strong>${escapeHtml(l.username)}</strong></td>
        <td>
          <span class="badge-tag ${l.status === 'SUCCESS' ? 'tag-success' : 'tag-danger'}">
            ${l.status}
          </span>
        </td>
        <td style="font-family:monospace; color:var(--text-muted);">${l.ip_hash}</td>
        <td style="color:var(--text-secondary); max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
          ${escapeHtml(l.user_agent || '')}
        </td>
        <td style="white-space:nowrap; color:var(--text-muted);">${l.timestamp}</td>
      </tr>
    `).join("");

    content.innerHTML = `
      <table class="admin-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Status</th>
            <th>IP Hash</th>
            <th>Device / User-Agent</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows : '<tr><td colspan="5" style="text-align:center;">No logins recorded yet.</td></tr>'}
        </tbody>
      </table>
    `;
  } else if (tab === "visitors") {
    const rows = data.recent_visitors.map(v => `
      <tr>
        <td style="font-family:monospace; color:var(--text-muted);">${v.ip_hash}</td>
        <td>${escapeHtml(v.path)}</td>
        <td>${v.username ? `👤 ${escapeHtml(v.username)}` : 'Guest'}</td>
        <td style="color:var(--text-secondary); max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
          ${escapeHtml(v.user_agent || '')}
        </td>
        <td style="white-space:nowrap; color:var(--text-muted);">${v.visited_at}</td>
      </tr>
    `).join("");

    content.innerHTML = `
      <table class="admin-table">
        <thead>
          <tr>
            <th>IP Hash (Anonymized)</th>
            <th>Path</th>
            <th>User</th>
            <th>Browser / Device</th>
            <th>Visit Time</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows : '<tr><td colspan="5" style="text-align:center;">No visitors recorded yet.</td></tr>'}
        </tbody>
      </table>
    `;
  } else if (tab === "users") {
    fetchUsersTab(content);
  }
}

async function fetchUsersTab(content) {
  try {
    const res = await fetch("/api/admin/users");
    const data = await res.json();
    const rows = (data.users || []).map(u => `
      <tr>
        <td><strong>${escapeHtml(u.username)}</strong></td>
        <td>${u.is_admin ? '<span class="badge-tag tag-success">Admin</span>' : '<span class="badge-tag tag-info">User</span>'}</td>
        <td>${u.is_blocked ? '<span class="badge-tag tag-danger">Blocked</span>' : '<span class="badge-tag tag-success">Active</span>'}</td>
        <td>${u.conversation_count}</td>
        <td style="white-space:nowrap; color:var(--text-muted);">${u.last_login}</td>
        <td>
          ${u.is_admin ? '<span style="color:var(--text-muted);">Protected</span>' : `
            <button class="feedback-btn" onclick="toggleBlockUser(${u.id}, ${!u.is_blocked})">
              ${u.is_blocked ? 'Unblock' : 'Block'}
            </button>
            <button class="feedback-btn" onclick="adminResetPassword(${u.id})">
              Reset Pass
            </button>
          `}
        </td>
      </tr>
    `).join("");

    content.innerHTML = `
      <table class="admin-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Role</th>
            <th>Status</th>
            <th>Chats</th>
            <th>Last Login</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows : '<tr><td colspan="6" style="text-align:center;">No users registered yet.</td></tr>'}
        </tbody>
      </table>
    `;
  } catch (err) {
    content.innerHTML = `<div style="color:#ef4444;">Failed to fetch users: ${err.message}</div>`;
  }
}

async function toggleBlockUser(userId, block) {
  await fetch(`/api/admin/users/${userId}/toggle-block`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ block })
  });
  switchAdminTab("users");
}

async function adminResetPassword(userId) {
  const newPass = prompt("Enter new password for user (min 8 chars):");
  if (!newPass || newPass.length < 8) return;
  await fetch(`/api/admin/users/${userId}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPass })
  });
  alert("Password reset successfully.");
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
