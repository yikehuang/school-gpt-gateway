const messagesEl = document.getElementById("messages");
const welcomeCard = document.getElementById("welcomeCard");
const chatForm = document.getElementById("chatForm");
const promptInput = document.getElementById("promptInput");
const sendButton = document.getElementById("sendButton");
const newChatButton = document.getElementById("newChatButton");
const conversationList = document.getElementById("conversationList");
const apiKeyInput = document.getElementById("apiKeyInput");
const statusPill = document.getElementById("statusPill");
const toggleSidebar = document.getElementById("toggleSidebar");
const sidebar = document.getElementById("sidebar");

const STORAGE_KEY = "xjgpt-conversations";
const API_KEY_STORAGE = "xjgpt-api-key";

let conversations = loadConversations();
let activeConversationId = conversations[0]?.id || createConversation().id;
let isSending = false;

apiKeyInput.value = localStorage.getItem(API_KEY_STORAGE) || apiKeyInput.value;
apiKeyInput.addEventListener("input", () => {
  localStorage.setItem(API_KEY_STORAGE, apiKeyInput.value.trim());
});

function loadConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveConversations() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.slice(0, 20)));
}

function createConversation() {
  const conversation = {
    id: crypto.randomUUID(),
    title: "新的会话",
    messages: [],
    createdAt: Date.now()
  };
  conversations.unshift(conversation);
  saveConversations();
  return conversation;
}

function getActiveConversation() {
  let conversation = conversations.find(item => item.id === activeConversationId);
  if (!conversation) {
    conversation = createConversation();
    activeConversationId = conversation.id;
  }
  return conversation;
}

function renderConversationList() {
  conversationList.innerHTML = "";
  conversations.forEach(conversation => {
    const button = document.createElement("button");
    button.className = "conversation-item" + (conversation.id === activeConversationId ? " active" : "");
    button.textContent = conversation.title || "新的会话";
    button.type = "button";
    button.addEventListener("click", () => {
      activeConversationId = conversation.id;
      render();
      sidebar.classList.remove("open");
    });
    conversationList.appendChild(button);
  });
}

function renderMessages() {
  const conversation = getActiveConversation();
  messagesEl.innerHTML = "";

  if (conversation.messages.length === 0) {
    messagesEl.appendChild(welcomeCard);
    welcomeCard.style.display = "block";
    attachSuggestionEvents();
    return;
  }

  welcomeCard.style.display = "none";
  conversation.messages.forEach(message => {
    messagesEl.appendChild(createMessageNode(message));
  });
  scrollToBottom();
}

function createMessageNode(message) {
  const row = document.createElement("article");
  row.className = `message-row ${message.role}`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = message.role === "user" ? "你" : "XJ";

  const contentWrap = document.createElement("div");
  contentWrap.className = "message-content";

  const role = document.createElement("div");
  role.className = "message-role";
  role.textContent = message.role === "user" ? "You" : "XJGPT";

  const content = document.createElement("div");
  content.textContent = message.content;

  contentWrap.appendChild(role);
  contentWrap.appendChild(content);

  if (message.meta) {
    const meta = document.createElement("div");
    meta.className = "message-meta";
    Object.entries(message.meta).forEach(([key, value]) => {
      const chip = document.createElement("span");
      chip.className = "meta-chip";
      chip.textContent = `${key}: ${value}`;
      meta.appendChild(chip);
    });
    contentWrap.appendChild(meta);
  }

  row.appendChild(avatar);
  row.appendChild(contentWrap);
  return row;
}

function render() {
  renderConversationList();
  renderMessages();
}

function attachSuggestionEvents() {
  document.querySelectorAll(".suggestion").forEach(button => {
    button.onclick = () => {
      promptInput.value = button.textContent.trim();
      resizeTextarea();
      promptInput.focus();
    };
  });
}

function setStatus(text, state = "ready") {
  statusPill.textContent = text;
  statusPill.className = "status-pill";
  if (state !== "ready") {
    statusPill.classList.add(state);
  }
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  });
}

function resizeTextarea() {
  promptInput.style.height = "auto";
  promptInput.style.height = `${Math.min(promptInput.scrollHeight, 180)}px`;
}

function addTypingMessage() {
  const row = document.createElement("article");
  row.className = "message-row assistant";
  row.id = "typingMessage";
  row.innerHTML = `
    <div class="message-avatar">XJ</div>
    <div class="message-content">
      <div class="message-role">XJGPT</div>
      <div class="typing"><span></span><span></span><span></span> 正在通过学校 XipuAI 获取回答</div>
    </div>
  `;
  messagesEl.appendChild(row);
  scrollToBottom();
}

function removeTypingMessage() {
  const typing = document.getElementById("typingMessage");
  if (typing) typing.remove();
}

async function sendMessage(question) {
  const apiKey = apiKeyInput.value.trim();
  if (!apiKey) {
    setStatus("Missing API key", "error");
    alert("请先填写 API Key。默认演示 Key 是 sk-student-demo-001。 ");
    return;
  }

  const conversation = getActiveConversation();
  conversation.messages.push({ role: "user", content: question });

  if (conversation.title === "新的会话") {
    conversation.title = question.slice(0, 28) || "新的会话";
  }

  saveConversations();
  render();
  addTypingMessage();

  isSending = true;
  sendButton.disabled = true;
  setStatus("Asking XipuAI", "loading");

  try {
    const response = await fetch("/v1/chat", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ question })
    });

    const data = await response.json();
    removeTypingMessage();

    if (!response.ok) {
      const detail = data.detail || "请求失败";
      throw new Error(detail);
    }

    conversation.messages.push({
      role: "assistant",
      content: data.answer || "学校 GPT 返回了空回答。",
      meta: {
        model: data.model || "school-web-gpt",
        tokens: data.usage?.total_tokens ?? "-",
        latency: `${data.latency_ms ?? "-"}ms`
      }
    });

    saveConversations();
    setStatus("Ready");
    render();
  } catch (error) {
    removeTypingMessage();
    conversation.messages.push({
      role: "assistant",
      content: `请求失败：${error.message}\n\n请检查：1）是否已运行 python login_once.py 保存登录状态；2）XipuAI 页面是否能正常访问；3）页面选择器是否需要调整。`
    });
    saveConversations();
    setStatus("Error", "error");
    render();
  } finally {
    isSending = false;
    sendButton.disabled = false;
    promptInput.focus();
  }
}

chatForm.addEventListener("submit", event => {
  event.preventDefault();
  if (isSending) return;

  const question = promptInput.value.trim();
  if (!question) return;

  promptInput.value = "";
  resizeTextarea();
  sendMessage(question);
});

promptInput.addEventListener("input", resizeTextarea);
promptInput.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

newChatButton.addEventListener("click", () => {
  const conversation = createConversation();
  activeConversationId = conversation.id;
  render();
  promptInput.focus();
});

toggleSidebar.addEventListener("click", () => {
  sidebar.classList.toggle("open");
});

render();
resizeTextarea();
