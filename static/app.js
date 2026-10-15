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
  renderDynamicSuggestions();
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

  const sidebarBackdrop = document.getElementById("sidebarBackdrop");
  if (mobileMenuBtn && sidebarBackdrop) {
    mobileMenuBtn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
      sidebarBackdrop.classList.toggle("active");
    });
    sidebarBackdrop.addEventListener("click", () => {
      sidebar.classList.remove("open");
      sidebarBackdrop.classList.remove("active");
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
    sendBtn.disabled = !chatInput.value.trim() || isGenerating;
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
        if (window.location.search.includes("open_admin=1")) {
          setTimeout(() => {
            openAdminModal();
            window.history.replaceState({}, document.title, window.location.pathname);
          }, 150);
        }
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
// Dynamic Suggestions Pool (Rotates diverse factual queries on load & new chat)
// -------------------------------------------------------------------------
const SUGGESTION_POOL = [
  {
    category: "Health & Science",
    title: "Distilled Water Safety",
    desc: "Can humans safely drink distilled water long-term? What does medical research say?",
    query: "Can humans safely drink distilled water long-term? What does medical research say?"
  },
  {
    category: "Health & Medicine",
    title: "Cold Weather & Viruses",
    desc: "Does cold weather directly cause the common cold or flu, or is it a common myth?",
    query: "Does cold weather directly cause the common cold or flu, or is it a common myth?"
  },
  {
    category: "Nutrition & Myth",
    title: "Carrots & Night Vision",
    desc: "Does eating carrots genuinely improve human night vision, or was it WWII radar propaganda?",
    query: "Does eating carrots genuinely improve human night vision, or was it WWII radar propaganda?"
  },
  {
    category: "Neuroscience",
    title: "Adult Brain Regeneration",
    desc: "Can neurons regenerate in adult humans, and where does adult neurogenesis occur?",
    query: "Can neurons regenerate in adult humans, and where does adult neurogenesis occur?"
  },
  {
    category: "Physics & Space",
    title: "Gravitational Time Dilation",
    desc: "Why does time pass slower near massive objects like black holes or near Earth?",
    query: "Why does time pass slower near massive objects like black holes or near Earth?"
  },
  {
    category: "Physics",
    title: "The Mpemba Effect",
    desc: "Does hot water really freeze faster than cold water in controlled laboratory experiments?",
    query: "Does hot water really freeze faster than cold water in controlled laboratory experiments?"
  },
  {
    category: "Space Observation",
    title: "Great Wall from Space",
    desc: "Is the Great Wall of China truly visible from low Earth orbit with the naked human eye?",
    query: "Is the Great Wall of China truly visible from low Earth orbit with the naked human eye?"
  },
  {
    category: "Optics & Perception",
    title: "Mirror Reflection Symmetry",
    desc: "Why do plane mirrors appear to flip images horizontally (left-right) but not vertically?",
    query: "Why do plane mirrors appear to flip images horizontally (left-right) but not vertically?"
  },
  {
    category: "Quantum Tech",
    title: "Quantum Cryptography",
    desc: "How does Quantum Key Distribution (QKD) physically detect and prevent eavesdroppers?",
    query: "How does Quantum Key Distribution (QKD) physically detect and prevent eavesdroppers?"
  },
  {
    category: "Artificial Intelligence",
    title: "LLM Hallucinations",
    desc: "Why do large language models generate hallucinations and how does real-time search fix it?",
    query: "Why do large language models generate hallucinations and how does real-time search fix it?"
  },
  {
    category: "Computer Science",
    title: "P vs NP Problem",
    desc: "What is the P vs NP problem in computer science and why has it remained unsolved?",
    query: "What is the P vs NP problem in computer science and why has it remained unsolved?"
  },
  {
    category: "Clean Energy",
    title: "Solid-State Batteries",
    desc: "How do solid-state electrolytes differ from conventional lithium-ion batteries?",
    query: "How do solid-state electrolytes differ from conventional lithium-ion batteries?"
  },
  {
    category: "History & Myth",
    title: "The Sphinx's Broken Nose",
    desc: "Did Napoleon Bonaparte's artillery actually break the nose off the Great Sphinx of Giza?",
    query: "Did Napoleon Bonaparte's artillery actually break the nose off the Great Sphinx of Giza?"
  },
  {
    category: "History of Tech",
    title: "Invention of the Lightbulb",
    desc: "Who actually invented the incandescent electric lightbulb before Thomas Edison patented it?",
    query: "Who actually invented the incandescent electric lightbulb before Thomas Edison patented it?"
  },
  {
    category: "Ancient Civilizations",
    title: "Bronze Age Collapse",
    desc: "What caused the sudden collapse of Mediterranean civilizations around 1200 BCE?",
    query: "What caused the sudden collapse of Mediterranean civilizations around 1200 BCE?"
  },
  {
    category: "Classical History",
    title: "Roman Gladiators Gestures",
    desc: "Did ancient Roman crowds actually use thumbs up or down to indicate death for gladiators?",
    query: "Did ancient Roman crowds actually use thumbs up or down to indicate death for gladiators?"
  },
  {
    category: "Oceanography",
    title: "Challenger Deep Exploration",
    desc: "What is the deepest measured point in Earth's oceans and what pressures exist there?",
    query: "What is the deepest measured point in Earth's oceans and what pressures exist there?"
  },
  {
    category: "Geology & Climate",
    title: "Sahara's Fossil Aquifers",
    desc: "Why is there a massive freshwater aquifer deep beneath the hyper-arid Sahara Desert?",
    query: "Why is there a massive freshwater aquifer deep beneath the hyper-arid Sahara Desert?"
  },
  {
    category: "Geography",
    title: "Tallest Mountain on Earth",
    desc: "Why is Mauna Kea considered taller than Mount Everest when measured from base to peak?",
    query: "Why is Mauna Kea considered taller than Mount Everest when measured from base to peak?"
  },
  {
    category: "Atmospheric Science",
    title: "Volcanic & Upper Lightning",
    desc: "What causes electrical lightning storms during explosive volcanic eruptions?",
    query: "What causes electrical lightning storms during explosive volcanic eruptions?"
  },
  {
    category: "Probability & Logic",
    title: "Monty Hall Paradox",
    desc: "Why does switching doors in the Monty Hall problem give a 2/3 mathematical probability?",
    query: "Why does switching doors in the Monty Hall problem give a 2/3 mathematical probability?"
  },
  {
    category: "Mathematics",
    title: "Hilbert's Infinite Hotel",
    desc: "How can an infinite hotel with all rooms occupied still accommodate infinitely many new guests?",
    query: "How can an infinite hotel with all rooms occupied still accommodate infinitely many new guests?"
  },
  {
    category: "Logic & Philosophy",
    title: "Gödel's Incompleteness",
    desc: "What did Kurt Gödel prove about mathematical systems and unprovable truths in 1931?",
    query: "What did Kurt Gödel prove about mathematical systems and unprovable truths in 1931?"
  },
  {
    category: "Astrobiology",
    title: "The Fermi Paradox",
    desc: "If extraterrestrial life is statistically probable, why haven't we detected any evidence?",
    query: "If extraterrestrial life is statistically probable, why haven't we detected any evidence?"
  }
];

function renderDynamicSuggestions() {
  const grid = document.getElementById("suggestionsGrid");
  if (!grid) return;

  const shuffled = [...SUGGESTION_POOL].sort(() => 0.5 - Math.random());
  const selected = shuffled.slice(0, 4);

  grid.innerHTML = selected.map(s => `
    <div class="suggestion-card" data-query="${escapeHtml(s.query)}" onclick="askSuggestion(this.getAttribute('data-query'))">
      <div class="suggestion-header">
        <span class="sugg-category">${escapeHtml(s.category)}</span>
      </div>
      <div class="sugg-title">${escapeHtml(s.title)}</div>
      <div class="sugg-desc">${escapeHtml(s.desc)}</div>
      <div class="sugg-arrow">→</div>
    </div>
  `).join("");
}

// -------------------------------------------------------------------------
// Chat & Messaging Logic
// -------------------------------------------------------------------------
function startNewChat() {
  currentChatId = "chat_" + Date.now();
  currentMessages = [];
  chatHeaderTitle.textContent = "New Verification";
  renderDynamicSuggestions();
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

  // ChatGPT Iconic Action Bar (Image 2 style: Copy, Read aloud, Thumbs up, Thumbs down, Regenerate)
  const msgId = msg.message_id || `msg_${idx}`;
  const isUp = msg.userRating === "up";
  const isDown = msg.userRating === "down";
  const feedbackBar = `
    <div class="chatgpt-actions-bar">
      <button class="chatgpt-action-btn" onclick="copyAnswerText(${idx}, this)" title="Copy" aria-label="Copy">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      </button>
      <button class="chatgpt-action-btn" id="readBtn_${msgId}" onclick="readAloudAnswer(${idx}, this)" title="Read aloud" aria-label="Read aloud">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
        </svg>
      </button>
      <button class="chatgpt-action-btn ${isUp ? 'active-up' : ''}" id="thumbUp_${msgId}" onclick="submitReaction('${msgId}', 'up', ${idx}, this)" title="Good response" aria-label="Good response">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
        </svg>
      </button>
      <button class="chatgpt-action-btn ${isDown ? 'active-down' : ''}" id="thumbDown_${msgId}" onclick="submitReaction('${msgId}', 'down', ${idx}, this)" title="Bad response" aria-label="Bad response">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path>
        </svg>
      </button>
      <button class="chatgpt-action-btn" onclick="retryMessage(${idx})" title="Try again" aria-label="Try again">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19"></path>
        </svg>
      </button>
      <span class="feedback-msg" id="feedbackMsg_${msgId}" style="display:${isUp || isDown ? 'inline' : 'none'}; font-size:0.75rem; color:var(--text-muted); margin-left:0.35rem;">
        ${isUp ? '✓ Saved' : (isDown ? 'Feedback logged' : '')}
      </span>
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
  const origHtml = btn.innerHTML;
  btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10a37f" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
  btn.title = "Copied!";
  setTimeout(() => {
    btn.innerHTML = origHtml;
    btn.title = "Copy";
  }, 2000);
}

let currentSpeakingBtn = null;

function readAloudAnswer(idx, btn) {
  const msg = currentMessages[idx];
  if (!msg || !("speechSynthesis" in window)) {
    alert("Text-to-speech is not supported by your browser.");
    return;
  }

  if (window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    if (currentSpeakingBtn) {
      currentSpeakingBtn.classList.remove("speaking");
    }
    if (currentSpeakingBtn === btn) {
      currentSpeakingBtn = null;
      return;
    }
  }

  const cleanText = (msg.content || "")
    .replace(/```[\s\S]*?```/g, " code block omitted. ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1")
    .replace(/[#*_~>]/g, "")
    .replace(/\n+/g, " ");

  if (!cleanText.trim()) return;

  const utt = new SpeechSynthesisUtterance(cleanText);
  utt.rate = 1.0;
  utt.pitch = 1.0;

  utt.onend = () => {
    btn.classList.remove("speaking");
    currentSpeakingBtn = null;
  };
  utt.onerror = () => {
    btn.classList.remove("speaking");
    currentSpeakingBtn = null;
  };

  btn.classList.add("speaking");
  currentSpeakingBtn = btn;
  window.speechSynthesis.speak(utt);
}

function retryMessage(idx) {
  if (isGenerating) return;
  const msg = currentMessages[idx];
  let queryToRetry = msg ? msg.query : null;

  if (!queryToRetry) {
    for (let i = idx - 1; i >= 0; i--) {
      if (currentMessages[i].role === "user") {
        queryToRetry = currentMessages[i].content;
        break;
      }
    }
  }

  if (!queryToRetry) return;

  if ("speechSynthesis" in window && window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
  }

  currentMessages.splice(idx, 1);
  renderMessages();

  chatInput.value = queryToRetry;
  handleSend();
}

// -------------------------------------------------------------------------
// Thumbs Up / Down Feedback (Claude Style with Diagnostic Prompt)
// -------------------------------------------------------------------------
let feedbackSelectedChips = {};

async function submitReaction(messageId, rating, idx, btn) {
  const msg = currentMessages[idx] || {};
  const upBtn = document.getElementById(`thumbUp_${messageId}`);
  const downBtn = document.getElementById(`thumbDown_${messageId}`);
  const statusMsg = document.getElementById(`feedbackMsg_${messageId}`);

  if (rating === "up") {
    upBtn.classList.add("active-up");
    downBtn.classList.remove("active-down");
    statusMsg.textContent = "✓ Helpful feedback saved. Thank you!";
    statusMsg.style.display = "inline";

    dismissFeedbackPrompt(messageId);

    if (currentMessages[idx]) {
      currentMessages[idx].userRating = rating;
      saveCurrentConversation();
    }

    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message_id: messageId,
          query: msg.query || "Verification Question",
          answer: (msg.content || "").slice(0, 1000),
          rating: "thumbs_up",
          comment: ""
        })
      });
    } catch (err) {
      console.error("Failed to post feedback:", err);
    }
  } else {
    // Thumbs down
    downBtn.classList.add("active-down");
    upBtn.classList.remove("active-up");
    statusMsg.style.display = "none";

    if (currentMessages[idx]) {
      currentMessages[idx].userRating = rating;
      saveCurrentConversation();
    }

    // Open inline diagnostic prompt to ask why the user gave thumbs down
    showFeedbackReasonCard(messageId, idx);
  }
}

function showFeedbackReasonCard(messageId, idx) {
  let card = document.getElementById(`feedbackPrompt_${messageId}`);
  if (card) return;

  const bar = document.getElementById(`thumbDown_${messageId}`)?.closest(".chatgpt-actions-bar") || document.getElementById(`thumbDown_${messageId}`)?.closest(".feedback-bar");
  if (!bar) return;

  card = document.createElement("div");
  card.className = "feedback-reason-card";
  card.id = `feedbackPrompt_${messageId}`;
  card.innerHTML = `
    <div class="feedback-reason-header">
      <span class="feedback-reason-title">
        <span>⚠️</span> Tell us what went wrong
      </span>
      <button type="button" class="feedback-close-chip" onclick="dismissFeedbackPrompt('${messageId}')" title="Dismiss">✕</button>
    </div>
    <div class="feedback-reason-subtitle">Why was this response unhelpful or incorrect?</div>
    <div class="feedback-chips-row">
      <button type="button" class="feedback-chip" onclick="toggleFeedbackChip('${messageId}', this, 'Hallucination / Inaccurate facts')">❌ Inaccurate / Hallucination</button>
      <button type="button" class="feedback-chip" onclick="toggleFeedbackChip('${messageId}', this, 'Incomplete / Evasive answer')">⚠️ Incomplete / Evasive</button>
      <button type="button" class="feedback-chip" onclick="toggleFeedbackChip('${messageId}', this, 'Irrelevant to prompt')">🚫 Irrelevant</button>
      <button type="button" class="feedback-chip" onclick="toggleFeedbackChip('${messageId}', this, 'Outdated information')">🐌 Outdated sources</button>
      <button type="button" class="feedback-chip" onclick="toggleFeedbackChip('${messageId}', this, 'Poor code or formatting')">💻 Code / Format bug</button>
    </div>
    <div class="feedback-input-row">
      <input 
        type="text" 
        class="feedback-detail-input" 
        id="feedbackNote_${messageId}" 
        placeholder="Add details (e.g. 'Says Einstein won for relativity, but it was photoelectric effect')..."
        onkeydown="if(event.key==='Enter') sendDetailedFeedback('${messageId}', ${idx})"
      >
      <button type="button" class="feedback-submit-act-btn" onclick="sendDetailedFeedback('${messageId}', ${idx})">Submit</button>
      <button type="button" class="feedback-skip-btn" onclick="skipDetailedFeedback('${messageId}', ${idx})">Skip</button>
    </div>
  `;

  bar.parentNode.insertBefore(card, bar.nextSibling);
}

function toggleFeedbackChip(messageId, btn, chipText) {
  btn.classList.toggle("active");
  if (!feedbackSelectedChips[messageId]) {
    feedbackSelectedChips[messageId] = new Set();
  }
  if (btn.classList.contains("active")) {
    feedbackSelectedChips[messageId].add(chipText);
  } else {
    feedbackSelectedChips[messageId].delete(chipText);
  }
}

function dismissFeedbackPrompt(messageId) {
  const card = document.getElementById(`feedbackPrompt_${messageId}`);
  if (card) card.remove();
  delete feedbackSelectedChips[messageId];
}

async function sendDetailedFeedback(messageId, idx) {
  const msg = currentMessages[idx] || {};
  const noteInput = document.getElementById(`feedbackNote_${messageId}`);
  const note = (noteInput ? noteInput.value.trim() : "");
  
  const selected = Array.from(feedbackSelectedChips[messageId] || []);
  let fullComment = selected.join("; ");
  if (note) {
    fullComment = fullComment ? `${fullComment}: ${note}` : note;
  }
  if (!fullComment) {
    fullComment = "Unhelpful response (no specific critique added)";
  }

  const card = document.getElementById(`feedbackPrompt_${messageId}`);
  if (card) {
    card.innerHTML = `
      <div style="color:var(--accent); font-size:0.84rem; font-weight:500; display:flex; align-items:center; gap:0.4rem; padding:0.25rem 0;">
        <span>✓</span> Thank you for your feedback! Our system will inspect why this happened and prepare a resolution.
      </div>
    `;
    setTimeout(() => { dismissFeedbackPrompt(messageId); }, 3500);
  }

  const statusMsg = document.getElementById(`feedbackMsg_${messageId}`);
  if (statusMsg) {
    statusMsg.textContent = "✓ Negative feedback logged";
    statusMsg.style.display = "inline";
  }

  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message_id: messageId,
        query: msg.query || "Verification Question",
        answer: (msg.content || "").slice(0, 1000),
        rating: "thumbs_down",
        comment: fullComment
      })
    });
  } catch (err) {
    console.error("Failed to post detailed feedback:", err);
  }
}

async function skipDetailedFeedback(messageId, idx) {
  const msg = currentMessages[idx] || {};
  dismissFeedbackPrompt(messageId);

  const statusMsg = document.getElementById(`feedbackMsg_${messageId}`);
  if (statusMsg) {
    statusMsg.textContent = "✓ Feedback saved";
    statusMsg.style.display = "inline";
  }

  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message_id: messageId,
        query: msg.query || "Verification Question",
        answer: (msg.content || "").slice(0, 1000),
        rating: "thumbs_down",
        comment: "Unhelpful response (skipped details)"
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
  if (!currentUser) {
    // Check if guest has an active conversation stored in sessionStorage
    const guestData = sessionStorage.getItem("hd_guest_chat");
    if (guestData) {
      try {
        const parsed = JSON.parse(guestData);
        currentMessages = parsed.messages || [];
        currentChatId = parsed.id || ("chat_" + Date.now());
        if (currentMessages.length > 0) {
          renderMessages();
        }
      } catch (e) {}
    }
    return;
  }

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
    const backdrop = document.getElementById("sidebarBackdrop");
    if (backdrop) backdrop.classList.remove("active");
  }
}

async function saveCurrentConversation() {
  if (currentMessages.length === 0) return;
  const firstUserMsg = currentMessages.find(m => m.role === "user");
  const title = firstUserMsg ? firstUserMsg.content.slice(0, 35) : "Verified Chat";
  chatHeaderTitle.textContent = title;

  if (!currentUser) {
    sessionStorage.setItem("hd_guest_chat", JSON.stringify({
      id: currentChatId,
      title: title,
      messages: currentMessages
    }));
    return;
  }

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
  document.querySelectorAll(".admin-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === tabName);
  });

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
          <div class="stat-label">🛡️ Resolved Issues</div>
          <div class="stat-number" style="color:#60a5fa;">${s.resolved_count || 0}</div>
        </div>
        <div class="stat-card" style="flex:1;">
          <div class="stat-label">👥 Total Registered Users</div>
          <div class="stat-number">${s.total_users}</div>
        </div>
      </div>
    `;
  } else if (tab === "feedback") {
    const rows = data.recent_feedbacks.map(f => {
      const isUp = f.rating === 'thumbs_up';
      const status = f.status || (isUp ? 'helpful' : 'pending');
      
      let statusBadge = '<span class="badge-tag tag-success">Helpful</span>';
      if (!isUp) {
        if (status === 'resolved') {
          statusBadge = '<span class="badge-tag tag-resolved">✓ Resolved</span>';
        } else if (status === 'diagnosed') {
          statusBadge = '<span class="badge-tag tag-diagnosed">⚡ Diagnosed</span>';
        } else if (status === 'dismissed') {
          statusBadge = '<span class="badge-tag tag-dismissed">Dismissed</span>';
        } else {
          statusBadge = '<span class="badge-tag tag-pending">Review Needed</span>';
        }
      }

      let actionBtn = '-';
      if (!isUp) {
        if (status === 'resolved') {
          actionBtn = `<button class="feedback-btn" onclick="openFeedbackDiagnostic(${f.id})">👁️ Resolution</button>`;
        } else {
          actionBtn = `<button class="feedback-btn" style="border-color:#ef4444; color:#f87171;" onclick="openFeedbackDiagnostic(${f.id})">🔍 Diagnose & Solve</button>`;
        }
      }

      return `
        <tr>
          <td><strong>${isUp ? '👍 Helpful' : '👎 Unhelpful'}</strong></td>
          <td>${escapeHtml(f.username || 'Anonymous')}</td>
          <td style="max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(f.query || '')}">
            <strong>${escapeHtml(f.query || '')}</strong>
          </td>
          <td style="color:${isUp ? 'var(--text-muted)' : '#fca5a5'}; font-size:0.82rem; max-width:200px;">
            ${escapeHtml(f.comment || (isUp ? 'Positive reaction' : 'No details provided'))}
          </td>
          <td>${statusBadge}</td>
          <td style="white-space:nowrap; color:var(--text-muted); font-size:0.8rem;">${f.created_at}</td>
          <td>${actionBtn}</td>
        </tr>
      `;
    }).join("");

    content.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
        <span style="font-size:0.85rem; color:var(--text-secondary);">
          Review user reactions, inspect reasons for dissatisfaction, and authorize verified resolutions with permission.
        </span>
        <button class="feedback-btn" onclick="switchAdminTab('feedback')">🔄 Refresh</button>
      </div>
      <table class="admin-table">
        <thead>
          <tr>
            <th>Rating</th>
            <th>User</th>
            <th>Question</th>
            <th>User Reason / Critique</th>
            <th>Status</th>
            <th>Date & Time</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows : '<tr><td colspan="7" style="text-align:center;">No feedback recorded yet.</td></tr>'}
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

// -------------------------------------------------------------------------
// Admin Feedback Diagnostic & Resolution Review Functions
// -------------------------------------------------------------------------
function closeFeedbackResolveModal() {
  const modal = document.getElementById("feedbackResolveModal");
  if (modal) modal.classList.remove("active");
}

async function openFeedbackDiagnostic(feedbackId) {
  if (!currentAdminAnalytics || !currentAdminAnalytics.recent_feedbacks) return;
  const f = currentAdminAnalytics.recent_feedbacks.find(x => x.id === feedbackId);
  if (!f) return;

  const modal = document.getElementById("feedbackResolveModal");
  if (modal) modal.classList.add("active");

  renderFeedbackDiagnosticBody(f);
}

function renderFeedbackDiagnosticBody(f, liveDiag = null) {
  const body = document.getElementById("diagModalBody");
  if (!body) return;

  const isResolved = f.status === 'resolved';
  const isDiagnosed = f.status === 'diagnosed' || liveDiag !== null;

  let diagData = liveDiag;
  if (!diagData && f.diagnosis) {
    try {
      diagData = JSON.parse(f.diagnosis);
    } catch(e) {
      diagData = { 
        why_negative: f.diagnosis, 
        root_cause: "Parsed from diagnosis text.", 
        system_recommendation: "Review grounding." 
      };
    }
  }

  const proposedAnswer = (liveDiag && liveDiag.proposed_answer) || f.proposed_fix || "";

  body.innerHTML = `
    <!-- 1. User Complaint Context -->
    <div class="diag-card" style="border-color:rgba(239, 68, 68, 0.35);">
      <div class="diag-title" style="color:#f87171;">User Complaint Context</div>
      <div style="display:flex; flex-direction:column; gap:0.45rem; margin-top:0.35rem;">
        <div><strong>User:</strong> 👤 ${escapeHtml(f.username || 'Anonymous')} <span style="color:var(--text-muted); font-size:0.8rem; margin-left:0.5rem;">(${f.created_at})</span></div>
        <div><strong>Question:</strong> <span style="color:var(--text-primary); font-weight:600;">${escapeHtml(f.query || '')}</span></div>
        <div style="background:var(--bg-input); padding:0.6rem 0.8rem; border-radius:6px; border:1px solid var(--border); font-size:0.86rem; color:var(--text-secondary); max-height:120px; overflow-y:auto;">
          <strong>Original Answer:</strong><br>${escapeHtml(f.answer || '')}
        </div>
        <div style="margin-top:0.25rem;">
          <strong>Reported Critique / Reason:</strong> 
          <span style="color:#fca5a5; font-weight:600;">${escapeHtml(f.comment || 'No specific critique text provided by user')}</span>
        </div>
      </div>
    </div>

    <!-- 2. AI Root Cause Diagnostic Audit -->
    <div class="diag-card" id="diagAuditCard">
      <div class="diag-title" style="color:#60a5fa;">AI Root-Cause Diagnostic Analysis</div>
      ${!isDiagnosed ? `
        <div style="color:var(--text-secondary); font-size:0.88rem; margin:0.5rem 0;">
          An automated root-cause audit has not yet run for this complaint.
        </div>
        <button class="btn-authorize" style="background:#3b82f6;" onclick="runDiagnosisForFeedback(${f.id})">
          ⚡ Run AI Root-Cause Diagnostic Audit
        </button>
      ` : `
        <div style="display:flex; flex-direction:column; gap:0.6rem; margin-top:0.4rem;">
          <div>
            <strong style="color:var(--text-primary); font-size:0.85rem;">🔍 Why User Gave Negative Feedback:</strong>
            <div class="diag-content" style="margin-top:0.2rem; color:var(--text-secondary);">${escapeHtml(diagData.why_negative || '')}</div>
          </div>
          <div>
            <strong style="color:var(--text-primary); font-size:0.85rem;">⚙️ Technical Root Cause:</strong>
            <div class="diag-content" style="margin-top:0.2rem; color:var(--text-secondary);">${escapeHtml(diagData.root_cause || '')}</div>
          </div>
          <div>
            <strong style="color:var(--text-primary); font-size:0.85rem;">💡 System Recommendation:</strong>
            <div class="diag-content" style="margin-top:0.2rem; color:var(--text-secondary);">${escapeHtml(diagData.system_recommendation || '')}</div>
          </div>
        </div>
      `}
    </div>

    <!-- 3. Proposed Grounded Solution -->
    ${proposedAnswer ? `
      <div class="diag-card" style="border-color:rgba(16, 163, 127, 0.4);">
        <div class="diag-title" style="color:var(--accent);">Proposed Verified Corrected Answer</div>
        <div class="diag-content" style="margin-top:0.35rem; line-height:1.6;">
          ${marked ? marked.parse(proposedAnswer) : escapeHtml(proposedAnswer)}
        </div>
      </div>
    ` : ''}

    <!-- 4. Explicit Admin Permission & Authorization Section -->
    <div class="permission-banner">
      <div class="permission-header">
        <span>🛡️</span>
        <span>${isResolved ? 'Issue Resolved with Administrator Authorization' : 'Administrator Permission & Authorization Required'}</span>
      </div>
      <div class="permission-desc">
        ${isResolved 
          ? `This feedback was reviewed and authorized as resolved by <strong>${escapeHtml(f.resolved_by || 'Admin')}</strong> on ${f.resolved_at}.`
          : `Review the user complaint, diagnosis, and proposed answer. The system will only apply and save this resolution with your explicit permission.`
        }
      </div>

      ${!isResolved ? `
        <div style="margin-bottom:0.75rem;">
          <label style="font-size:0.8rem; font-weight:600; color:var(--text-secondary); display:block; margin-bottom:0.3rem;">Resolution Note / Approved Answer Override:</label>
          <textarea id="diagResolutionNoteInput" rows="3" class="feedback-detail-input" style="width:100%; resize:vertical;">${escapeHtml(proposedAnswer || f.resolution || '')}</textarea>
        </div>
        <div class="permission-actions">
          <button class="btn-authorize" onclick="submitFeedbackResolution(${f.id}, true)">
            ✓ Authorize & Mark Resolved
          </button>
          <button class="btn-dismiss" onclick="submitFeedbackResolution(${f.id}, false)">
            Dismiss Without Applying
          </button>
          <button class="feedback-skip-btn" onclick="closeFeedbackResolveModal()">
            Cancel
          </button>
        </div>
      ` : `
        <div style="background:var(--bg-input); border:1px solid var(--border); border-radius:6px; padding:0.75rem; font-size:0.86rem; color:var(--text-secondary); margin-bottom:0.75rem;">
          <strong>Resolution Note:</strong><br>${escapeHtml(f.resolution || proposedAnswer || 'Marked resolved without extra note.')}
        </div>
        <button class="feedback-btn" onclick="closeFeedbackResolveModal()">Close</button>
      `}
    </div>
  `;
}

async function runDiagnosisForFeedback(feedbackId) {
  const card = document.getElementById("diagAuditCard");
  if (card) {
    card.innerHTML = `
      <div class="diag-title" style="color:#60a5fa;">AI Root-Cause Diagnostic Analysis</div>
      <div style="display:flex; align-items:center; gap:0.5rem; color:var(--accent); padding:1rem 0; font-size:0.9rem;">
        <span class="pulse-dot"></span>
        <span>Searching live web sources and diagnosing root cause...</span>
      </div>
    `;
  }

  try {
    const res = await fetch(`/api/admin/feedback/${feedbackId}/diagnose`, {
      method: "POST"
    });
    if (!res.ok) {
      throw new Error("Diagnosis failed");
    }
    const data = await res.json();
    const f = currentAdminAnalytics.recent_feedbacks.find(x => x.id === feedbackId);
    if (f) {
      f.status = "diagnosed";
      f.diagnosis = JSON.stringify(data.diagnosis);
      f.proposed_fix = data.diagnosis.proposed_answer;
    }
    renderFeedbackDiagnosticBody(f, data.diagnosis);
  } catch (err) {
    alert("Error diagnosing feedback: " + err.message);
  }
}

async function submitFeedbackResolution(feedbackId, approved) {
  const noteInput = document.getElementById("diagResolutionNoteInput");
  const note = noteInput ? noteInput.value.trim() : "";

  try {
    const res = await fetch(`/api/admin/feedback/${feedbackId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        approved: approved,
        resolution_note: note
      })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Resolution failed");
    }

    alert(approved ? "✓ Resolution authorized and recorded!" : "Complaint dismissed.");
    closeFeedbackResolveModal();
    // Refresh admin feedback tab
    switchAdminTab("feedback");
  } catch (err) {
    alert("Failed to submit resolution: " + err.message);
  }
}

