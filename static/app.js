const messagesEl = document.getElementById("messages");
const welcomeCard = document.getElementById("welcomeCard");
const chatForm = document.getElementById("chatForm");
const promptInput = document.getElementById("promptInput");
const sendButton = document.getElementById("sendButton");
const newChatButton = document.getElementById("newChatButton");
const conversationList = document.getElementById("conversationList");
const modelSelect = document.getElementById("modelSelect");
const thinkingSelect = document.getElementById("thinkingSelect");
const statusPill = document.getElementById("statusPill");
const toggleSidebar = document.getElementById("toggleSidebar");
const sidebar = document.getElementById("sidebar");

const settingsModal = document.getElementById("settingsModal");
const openSettingsButton = document.getElementById("openSettingsButton");
const topSettingsButton = document.getElementById("topSettingsButton");
const closeSettingsButton = document.getElementById("closeSettingsButton");
const saveSettingsButton = document.getElementById("saveSettingsButton");
const resetSettingsButton = document.getElementById("resetSettingsButton");
const testApiButton = document.getElementById("testApiButton");
const copyPreviewButton = document.getElementById("copyPreviewButton");
const apiBaseUrlInput = document.getElementById("apiBaseUrlInput");
const apiEndpointSelect = document.getElementById("apiEndpointSelect");
const apiKeyInput = document.getElementById("apiKeyInput");
const requestFormatSelect = document.getElementById("requestFormatSelect");
const gatewayModelSelect = document.getElementById("gatewayModelSelect");
const gatewayThinkingSelect = document.getElementById("gatewayThinkingSelect");
const requestPreview = document.getElementById("requestPreview");

const STORAGE_KEY = "xjgpt-conversations";
const SETTINGS_STORAGE = "xjgpt-api-settings";
const MODEL_STORAGE = "xjgpt-model";
const THINKING_STORAGE = "xjgpt-thinking";

const DEFAULT_SETTINGS = {
  apiBaseUrl: "",
  chatEndpoint: "/v1/chat",
  apiKey: "sk-student-demo-001",
  requestFormat: "messages"
};

const FALLBACK_MODELS = Array.from(modelSelect.options).map(option => ({
  id: option.value,
  name: option.textContent
}));

const THINKING_OPTIONS = {
  minimal: "关闭思考",
  low: "轻量思考",
  medium: "均衡模式",
  high: "深度分析"
};

let conversations = loadConversations();
let activeConversationId = conversations[0]?.id || createConversation().id;
let isSending = false;
let apiSettings = loadApiSettings();

function loadApiSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE);
    return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : { ...DEFAULT_SETTINGS };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

function saveApiSettings(settings) {
  apiSettings = { ...DEFAULT_SETTINGS, ...settings };
  localStorage.setItem(SETTINGS_STORAGE, JSON.stringify(apiSettings));
}

function applySettingsToForm() {
  apiBaseUrlInput.value = apiSettings.apiBaseUrl || "";
  apiEndpointSelect.value = apiSettings.chatEndpoint || DEFAULT_SETTINGS.chatEndpoint;
  apiKeyInput.value = apiSettings.apiKey || DEFAULT_SETTINGS.apiKey;
  requestFormatSelect.value = apiSettings.requestFormat || DEFAULT_SETTINGS.requestFormat;
  renderRequestPreview();
}

function readSettingsFromForm() {
  return {
    apiBaseUrl: apiBaseUrlInput.value.trim(),
    chatEndpoint: apiEndpointSelect.value,
    apiKey: apiKeyInput.value.trim(),
    requestFormat: requestFormatSelect.value
  };
}

function buildApiUrl() {
  const baseUrl = (apiSettings.apiBaseUrl || "").trim().replace(/\/$/, "");
  const endpoint = apiSettings.chatEndpoint || "/v1/chat";

  if (/^https?:\/\//i.test(endpoint)) {
    return endpoint;
  }

  const normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return baseUrl ? `${baseUrl}${normalizedEndpoint}` : normalizedEndpoint;
}

function buildModelsUrl() {
  const baseUrl = (apiSettings.apiBaseUrl || "").trim().replace(/\/$/, "");
  return baseUrl ? `${baseUrl}/v1/models` : "/v1/models";
}

function buildGatewayConfigUrl() {
  const baseUrl = (apiSettings.apiBaseUrl || "").trim().replace(/\/$/, "");
  return baseUrl ? `${baseUrl}/v1/gateway-config` : "/v1/gateway-config";
}

function ensureSelectOption(selectEl, value, label = value) {
  if (!selectEl || !value) return;

  const hasOption = Array.from(selectEl.options).some(option => option.value === value);
  if (!hasOption) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    selectEl.appendChild(option);
  }
}

function renderModelOptions(models, selectedModel) {
  const previousValue = selectedModel || modelSelect.value || "auto";
  const seen = new Set();
  modelSelect.innerHTML = "";

  models.forEach(model => {
    if (!model?.id || seen.has(model.id)) return;
    seen.add(model.id);

    const option = document.createElement("option");
    option.value = model.id;
    option.textContent = model.name || model.id;

    if (model.description) {
      option.title = model.description;
    }

    modelSelect.appendChild(option);
  });

  if (seen.has(previousValue)) {
    modelSelect.value = previousValue;
  } else if (seen.has("auto")) {
    modelSelect.value = "auto";
  }

  localStorage.setItem(MODEL_STORAGE, modelSelect.value);
  syncGatewayModelOptions();
  renderRequestPreview();
}

async function loadModelOptions() {
  const selectedModel = localStorage.getItem(MODEL_STORAGE) || modelSelect.value || "auto";

  try {
    const response = await fetch(buildModelsUrl());
    const data = await response.json().catch(() => ({}));

    if (!response.ok || !Array.isArray(data.data)) {
      throw new Error(data.detail || "模型列表读取失败");
    }

    renderModelOptions(data.data, selectedModel);
  } catch {
    renderModelOptions(FALLBACK_MODELS, selectedModel);
  }
}

function applyGatewayConfigData(config) {
  if (!config || typeof config !== "object") return;

  if (config.model) {
    ensureSelectOption(modelSelect, config.model, config.model_name || config.model);
    modelSelect.value = config.model;
    localStorage.setItem(MODEL_STORAGE, modelSelect.value);
  }

  if (config.thinking && THINKING_OPTIONS[config.thinking]) {
    thinkingSelect.value = config.thinking;
    localStorage.setItem(THINKING_STORAGE, thinkingSelect.value);
  }

  syncGatewayConfigForm();
  renderRequestPreview();
}

async function loadGatewayConfig() {
  try {
    const response = await fetch(buildGatewayConfigUrl());
    const data = await response.json().catch(() => ({}));

    if (!response.ok || !data.data) {
      throw new Error(data.detail || "中转站配置读取失败");
    }

    applyGatewayConfigData(data.data);
  } catch {
    syncGatewayConfigForm();
  }
}

async function saveGatewayConfigToBackend() {
  const apiKey = apiSettings.apiKey.trim();

  if (!apiKey) {
    throw new Error("API Key 缺失，无法保存后端默认配置。");
  }

  const payload = {
    model: modelSelect.value,
    thinking: getSelectedThinking(),
    reasoning_effort: getSelectedThinking()
  };

  const response = await fetch(buildGatewayConfigUrl(), {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok || !data.data) {
    throw new Error(data.detail || data.error?.message || "后端默认配置保存失败");
  }

  applyGatewayConfigData(data.data);
  return data.data;
}

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

function getSelectedModelName() {
  return modelSelect.options[modelSelect.selectedIndex]?.textContent || modelSelect.value;
}

function getSelectedThinking() {
  return thinkingSelect.value || "minimal";
}

function getSelectedThinkingName() {
  return thinkingSelect.options[thinkingSelect.selectedIndex]?.textContent || THINKING_OPTIONS[thinkingSelect.value] || thinkingSelect.value;
}

function getConfiguredModel() {
  if (settingsModal?.classList.contains("open") && gatewayModelSelect?.value) {
    return gatewayModelSelect.value;
  }

  return modelSelect.value;
}

function getConfiguredThinking() {
  if (settingsModal?.classList.contains("open") && gatewayThinkingSelect?.value) {
    return gatewayThinkingSelect.value;
  }

  return getSelectedThinking();
}

function loadThinkingSelection() {
  const savedThinking = localStorage.getItem(THINKING_STORAGE);

  if (savedThinking && THINKING_OPTIONS[savedThinking]) {
    thinkingSelect.value = savedThinking;
  }
}

function syncGatewayModelOptions() {
  if (!gatewayModelSelect) return;

  const selectedValue = gatewayModelSelect.value || modelSelect.value || "auto";
  gatewayModelSelect.innerHTML = modelSelect.innerHTML;

  const hasSelectedValue = Array.from(gatewayModelSelect.options).some(option => option.value === selectedValue);
  if (hasSelectedValue) {
    gatewayModelSelect.value = selectedValue;
  } else {
    gatewayModelSelect.value = modelSelect.value || "auto";
  }
}

function syncGatewayConfigForm() {
  syncGatewayModelOptions();

  if (gatewayThinkingSelect) {
    gatewayThinkingSelect.value = getSelectedThinking();
  }
}

function applyGatewayConfigFromForm() {
  if (gatewayModelSelect?.value) {
    modelSelect.value = gatewayModelSelect.value;
    localStorage.setItem(MODEL_STORAGE, modelSelect.value);
  }

  if (gatewayThinkingSelect?.value) {
    thinkingSelect.value = gatewayThinkingSelect.value;
    localStorage.setItem(THINKING_STORAGE, thinkingSelect.value);
  }
}

function buildChatPayload(question, model, thinking = getSelectedThinking()) {
  const format = apiSettings.requestFormat || "messages";

  if (format === "question") {
    return {
      question,
      model,
      thinking
    };
  }

  return {
    model,
    thinking,
    reasoning_effort: thinking,
    messages: [
      {
        role: "user",
        content: question
      }
    ]
  };
}

function renderRequestPreview() {
  if (!requestPreview) return;

  const draftSettings = readSettingsFromForm();
  const previousSettings = apiSettings;
  apiSettings = { ...DEFAULT_SETTINGS, ...draftSettings };

  const payload = buildChatPayload("请只回复两个字：成功", getConfiguredModel(), getConfiguredThinking());
  const preview = {
    url: buildApiUrl(),
    method: "POST",
    headers: {
      Authorization: "Bearer " + maskApiKey(apiSettings.apiKey),
      "Content-Type": "application/json"
    },
    body: payload
  };

  apiSettings = previousSettings;
  requestPreview.textContent = JSON.stringify(preview, null, 2);
}

function maskApiKey(key) {
  if (!key) return "";
  if (key.length <= 8) return "********";
  return `${key.slice(0, 5)}****${key.slice(-4)}`;
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

function addTypingMessage(modelName) {
  const row = document.createElement("article");
  row.className = "message-row assistant";
  row.id = "typingMessage";
  row.innerHTML = `
    <div class="message-avatar">XJ</div>
    <div class="message-content">
      <div class="message-role">XJGPT</div>
      <div class="typing"><span></span><span></span><span></span> 正在通过学校 XipuAI 获取回答，模型：${modelName}</div>
    </div>
  `;
  messagesEl.appendChild(row);
  scrollToBottom();
}

function removeTypingMessage() {
  const typing = document.getElementById("typingMessage");
  if (typing) typing.remove();
}

function parseAssistantAnswer(data) {
  return data.answer || data.choices?.[0]?.message?.content || "学校 GPT 返回了空回答。";
}

function parseUsage(data) {
  const total = data.usage?.total_tokens ?? data.usage?.total ?? "-";
  const prompt = data.usage?.input_tokens ?? data.usage?.prompt_tokens ?? "-";
  const completion = data.usage?.output_tokens ?? data.usage?.completion_tokens ?? "-";
  return { total, prompt, completion };
}

async function callConfiguredApi(question, model, thinking = getSelectedThinking()) {
  const apiKey = apiSettings.apiKey.trim();

  if (!apiKey) {
    throw new Error("API Key 缺失。请打开设置填写 Authorization Bearer Key。");
  }

  const response = await fetch(buildApiUrl(), {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(buildChatPayload(question, model, thinking))
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = data.detail || data.error?.message || "请求失败";
    throw new Error(detail);
  }

  return data;
}

async function sendMessage(question) {
  const model = modelSelect.value;
  const modelName = getSelectedModelName();
  const thinking = getSelectedThinking();
  const thinkingName = getSelectedThinkingName();

  const conversation = getActiveConversation();
  conversation.messages.push({
    role: "user",
    content: question,
    meta: {
      model: modelName,
      thinking: thinkingName,
      endpoint: apiSettings.chatEndpoint
    }
  });

  if (conversation.title === "新的会话") {
    conversation.title = question.slice(0, 28) || "新的会话";
  }

  saveConversations();
  render();
  addTypingMessage(`${modelName} / ${thinkingName}`);

  isSending = true;
  sendButton.disabled = true;
  setStatus(`Asking ${modelName}`, "loading");

  try {
    const data = await callConfiguredApi(question, model, thinking);
    const answer = parseAssistantAnswer(data);
    const usage = parseUsage(data);
    removeTypingMessage();

    conversation.messages.push({
      role: "assistant",
      content: answer,
      meta: {
        model: data.model_name || data.model || modelName,
        runtime: data.runtime_model || data.model || "-",
        thinking: data.thinking_name || data.thinking || thinkingName,
        tokens: usage.total,
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
      content: `请求失败：${error.message}\n\n请检查：1）设置里的 API Base URL、Endpoint 和 Key 是否正确；2）是否已运行 python login_once.py 保存登录状态；3）XipuAI 页面是否能正常访问；4）页面选择器是否需要调整；5）你选择的模型名称是否和学校网页里的模型名称一致。`
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

function openSettings() {
  applySettingsToForm();
  syncGatewayConfigForm();
  renderRequestPreview();
  settingsModal.classList.add("open");
  settingsModal.setAttribute("aria-hidden", "false");
  gatewayModelSelect.focus();
}

function closeSettings() {
  settingsModal.classList.remove("open");
  settingsModal.setAttribute("aria-hidden", "true");
}

async function saveSettingsFromModal() {
  applyGatewayConfigFromForm();
  saveApiSettings(readSettingsFromForm());
  renderRequestPreview();
  saveSettingsButton.disabled = true;
  saveSettingsButton.textContent = "保存中...";
  setStatus("Saving settings", "loading");

  try {
    await saveGatewayConfigToBackend();
    await loadModelOptions();
    renderRequestPreview();
    setStatus("Settings saved");
    closeSettings();
  } catch (error) {
    setStatus("Save failed", "error");
    alert(`保存失败：${error.message}`);
  } finally {
    saveSettingsButton.disabled = false;
    saveSettingsButton.textContent = "保存设置";
  }
}

async function resetSettings() {
  saveApiSettings({ ...DEFAULT_SETTINGS });
  applySettingsToForm();
  modelSelect.value = "auto";
  thinkingSelect.value = "minimal";
  localStorage.setItem(MODEL_STORAGE, modelSelect.value);
  localStorage.setItem(THINKING_STORAGE, thinkingSelect.value);
  syncGatewayConfigForm();
  resetSettingsButton.disabled = true;
  setStatus("Resetting settings", "loading");

  try {
    await saveGatewayConfigToBackend();
    await loadModelOptions();
    setStatus("Settings reset");
  } catch (error) {
    setStatus("Reset failed", "error");
    alert(`恢复默认失败：${error.message}`);
  } finally {
    resetSettingsButton.disabled = false;
  }
}

async function testApiFromSettings() {
  applyGatewayConfigFromForm();
  saveApiSettings(readSettingsFromForm());
  renderRequestPreview();
  testApiButton.disabled = true;
  testApiButton.textContent = "测试中...";
  setStatus("Testing API", "loading");

  try {
    await saveGatewayConfigToBackend();
    const data = await callConfiguredApi("请只回复两个字：成功", modelSelect.value, getSelectedThinking());
    const answer = parseAssistantAnswer(data);
    setStatus("API OK");
    alert(`API 测试成功：${answer}`);
  } catch (error) {
    setStatus("API Error", "error");
    alert(`API 测试失败：${error.message}`);
  } finally {
    testApiButton.disabled = false;
    testApiButton.textContent = "测试 API";
  }
}

async function copyPreview() {
  try {
    await navigator.clipboard.writeText(requestPreview.textContent);
    setStatus("Copied");
  } catch {
    setStatus("Copy failed", "error");
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

openSettingsButton.addEventListener("click", openSettings);
topSettingsButton.addEventListener("click", openSettings);
closeSettingsButton.addEventListener("click", closeSettings);
saveSettingsButton.addEventListener("click", saveSettingsFromModal);
resetSettingsButton.addEventListener("click", resetSettings);
testApiButton.addEventListener("click", testApiFromSettings);
copyPreviewButton.addEventListener("click", copyPreview);

[apiBaseUrlInput, apiEndpointSelect, apiKeyInput, requestFormatSelect].forEach(input => {
  input.addEventListener("input", renderRequestPreview);
  input.addEventListener("change", renderRequestPreview);
});

[gatewayModelSelect, gatewayThinkingSelect].forEach(input => {
  input.addEventListener("change", renderRequestPreview);
});

modelSelect.addEventListener("change", () => {
  localStorage.setItem(MODEL_STORAGE, modelSelect.value);
  syncGatewayConfigForm();
  renderRequestPreview();
});

thinkingSelect.addEventListener("change", () => {
  localStorage.setItem(THINKING_STORAGE, thinkingSelect.value);
  syncGatewayConfigForm();
  renderRequestPreview();
});

settingsModal.addEventListener("click", event => {
  if (event.target === settingsModal) {
    closeSettings();
  }
});

document.addEventListener("keydown", event => {
  if (event.key === "Escape" && settingsModal.classList.contains("open")) {
    closeSettings();
  }
});

loadThinkingSelection();
applySettingsToForm();
loadModelOptions().then(loadGatewayConfig);
render();
resizeTextarea();
