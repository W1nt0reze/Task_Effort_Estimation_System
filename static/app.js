const form = document.getElementById("task-form");
const msg = document.getElementById("msg");
const predictOut = document.getElementById("predict-out");

const selPriority = document.getElementById("priority");
const selType = document.getElementById("type");
const selTeam = document.getElementById("team");

function showMsg(text, kind) {
  msg.textContent = text;
  msg.className = "msg " + (kind || "info");
}

function clearMsg() {
  msg.textContent = "";
  msg.className = "msg";
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getFormPayload() {
  const fd = new FormData(form);

  return {
    title: String(fd.get("title") || "").trim(),
    priority: fd.get("priority"),
    type: fd.get("type"),
    team: fd.get("team"),
    story_points: parseFloat(fd.get("story_points") || "0") || 0,
    actual_hours: parseFloat(fd.get("actual_hours") || "0"),
  };
}

async function loadMeta() {
  const r = await fetch("/api/meta");

  if (!r.ok) {
    throw new Error("Не удалось загрузить справочники");
  }

  const data = await r.json();

  selPriority.innerHTML = (data.priorities || [])
    .map((p) => `<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`)
    .join("");

  selType.innerHTML = (data.types || [])
    .map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`)
    .join("");

  selTeam.innerHTML = (data.teams || [])
    .map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`)
    .join("");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearMsg();
  predictOut.hidden = true;

  const body = getFormPayload();

  if (!body.title) {
    showMsg("Введите описание задачи.", "err");
    return;
  }

  if (!body.team) {
    showMsg("Выберите команду.", "err");
    return;
  }

  if (!(body.actual_hours > 0)) {
    showMsg("Укажите фактические часы больше нуля.", "err");
    return;
  }

  try {
    const r = await fetch("/api/tasks", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body),
    });

    const data = await r.json().catch(() => ({}));

    if (!r.ok) {
      showMsg(data.detail || "Ошибка сохранения", "err");
      return;
    }

    let text = "Сохранено, id: " + data.id;

    if (data.retrain_scheduled) {
      text += ". Модель автоматически переобучается в фоне.";
    }

    showMsg(text, "ok");
  } catch (err) {
    showMsg(String(err.message || err), "err");
  }
});

document.getElementById("btn-predict").addEventListener("click", async () => {
  clearMsg();
  predictOut.hidden = true;

  const body = getFormPayload();

  if (!body.priority || !body.type || !body.team) {
    showMsg("Выберите приоритет, тип и команду.", "err");
    return;
  }

  try {
    const r = await fetch("/api/predict", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        priority: body.priority,
        type: body.type,
        team: body.team,
        story_points: body.story_points,
      }),
    });

    const data = await r.json().catch(() => ({}));

    if (!r.ok) {
      showMsg(
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail || data),
        "err"
      );
      return;
    }

    predictOut.hidden = false;
    predictOut.textContent =
      "Оценка модели: ~" + data.estimated_hours + " ч (по текущим признакам)";

    showMsg("Оценка получена.", "ok");
  } catch (err) {
    showMsg(String(err.message || err), "err");
  }
});

loadMeta().catch((err) => showMsg(String(err.message || err), "err"));
