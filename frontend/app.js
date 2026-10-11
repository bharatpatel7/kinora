const $ = (id) => document.getElementById(id);
const providerSelect = $("provider");
const jobsEl = $("jobs");
let providers = [];
let pollTimer = null;

async function api(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail?.[0]?.msg || data.detail || `HTTP ${res.status}`);
  return data;
}

async function loadProviders() {
  const data = await api("/api/providers");
  providers = data.providers;
  providerSelect.innerHTML = "";
  for (const p of providers) {
    const opt = new Option(p.available ? p.label : `${p.label} — unavailable`, p.name);
    opt.disabled = !p.available;
    providerSelect.add(opt);
  }
  const fallback = providers.find((p) => p.available)?.name;
  providerSelect.value = providers.find((p) => p.name === data.default && p.available) ? data.default : fallback;
  updateNote();
}

function updateNote() {
  const p = providers.find((x) => x.name === providerSelect.value);
  const unavailable = providers.filter((x) => !x.available).map((x) => `${x.label}: ${x.reason}`);
  $("provider-note").textContent = [p?.description, ...unavailable].filter(Boolean).join("  ·  ");
}

function renderJobs(jobs) {
  jobsEl.replaceChildren(
    ...jobs.map((job) => {
      const card = document.createElement("article");
      card.className = `job ${job.status}`;
      const media = job.video_url
        ? Object.assign(document.createElement("video"), { src: job.video_url, controls: true, loop: true, muted: true, playsInline: true })
        : Object.assign(document.createElement("div"), {
            className: "placeholder",
            textContent: job.status === "failed" ? "Generation failed" : job.status === "queued" ? "Queued…" : "Generating…",
          });
      const bar = document.createElement("div");
      bar.className = "bar";
      bar.innerHTML = `<div style="width:${Math.round(job.progress * 100)}%"></div>`;

      const meta = document.createElement("div");
      meta.className = "meta";
      const prompt = document.createElement("p");
      prompt.className = "prompt";
      prompt.textContent = job.prompt;
      const status = document.createElement("div");
      status.className = "status";
      const left = document.createElement("span");
      left.textContent = job.status === "failed" ? job.error : `${job.status} · ${job.provider}`;
      const right = document.createElement("span");
      if (job.video_url) {
        right.innerHTML = `<a href="${job.video_url}" download>Download</a>`;
      } else if (job.status === "running") {
        right.textContent = `${Math.round(job.progress * 100)}%`;
      }
      status.append(left, right);
      meta.append(prompt, status);
      card.append(media, bar, meta);
      return card;
    }),
  );
}

async function refreshJobs() {
  const jobs = await api("/api/jobs");
  // Avoid re-rendering finished videos (which would restart playback) when nothing changed.
  const signature = JSON.stringify(jobs.map((j) => [j.id, j.status, j.progress]));
  if (signature !== jobsEl.dataset.signature) {
    jobsEl.dataset.signature = signature;
    renderJobs(jobs);
  }
  const active = jobs.some((j) => j.status === "queued" || j.status === "running");
  clearTimeout(pollTimer);
  if (active) pollTimer = setTimeout(refreshJobs, 1000);
}

$("gen-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = $("error");
  errorEl.hidden = true;
  $("submit").disabled = true;
  try {
    const seed = $("seed").value;
    await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify({
        prompt: $("prompt").value,
        negative_prompt: $("negative").value,
        provider: providerSelect.value,
        width: Number($("width").value),
        height: Number($("height").value),
        seconds: Number($("seconds").value),
        seed: seed === "" ? null : Number(seed),
      }),
    });
    await refreshJobs();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.hidden = false;
  } finally {
    $("submit").disabled = false;
  }
});

providerSelect.addEventListener("change", updateNote);
$("prompt").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) $("gen-form").requestSubmit();
});

loadProviders().then(refreshJobs).catch((err) => {
  $("error").textContent = `Could not reach the Kinora server: ${err.message}`;
  $("error").hidden = false;
});
