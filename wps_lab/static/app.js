"use strict";
(() => {
  const root = document.documentElement;
  const themeButton = document.getElementById("theme-toggle");
  const preferred = (() => { try { return localStorage.getItem("wps-theme"); } catch { return null; } })();
  function theme(mode) {
    root.dataset.theme = mode;
    themeButton?.setAttribute("aria-label", mode === "dark" ? "Switch to light color theme" : "Switch to dark color theme");
    try { localStorage.setItem("wps-theme", mode); } catch {}
  }
  theme(preferred === "light" ? "light" : "dark");
  themeButton?.addEventListener("click", () => theme(root.dataset.theme === "dark" ? "light" : "dark"));

  const make = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = String(text);
    if (className) el.className = className;
    return el;
  };
  async function json(path) {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error("Local API request failed");
    return res.json();
  }
  async function refresh() {
    const [summary, campaigns, events] = await Promise.all([
      json("/api/v1/summary"), json("/api/v1/campaigns"), json("/api/v1/events")
    ]);
    const fields = {
      "stat-campaigns": summary.campaigns,
      "stat-active": summary.active,
      "stat-participants": summary.consented_participants,
      "stat-acknowledgements": summary.acknowledgements
    };
    for (const [id, value] of Object.entries(fields)) {
      const el = document.getElementById(id);
      if (el) el.textContent = String(value);
    }
    const list = document.getElementById("campaign-list");
    if (list) {
      list.replaceChildren(...campaigns.map(c => {
        const row = make("div", undefined, "campaign-row");
        const heading = make("div");
        heading.append(make("strong", c.name), make("small", c.state.toUpperCase() + " · " + c.consented + " consented demo aliases"));
        const bar = make("div", undefined, "progress-box");
        const progress = make("progress");
        progress.max = Math.max(c.consented, 1);
        progress.value = Math.min(c.acknowledged, progress.max);
        bar.append(progress, make("small", c.acknowledged + " / " + c.consented + " acknowledged"));
        row.append(heading, bar);
        return row;
      }));
    }
    const target = document.getElementById("activity-rows");
    if (target) {
      if (!events.length) {
        const tr = make("tr");
        const cell = make("td", "No acknowledgements yet. Use a synthetic local practice link.", "empty");
        cell.colSpan = 4;
        tr.append(cell);
        target.replaceChildren(tr);
      } else {
        target.replaceChildren(...events.map(e => {
          const tr = make("tr");
          [e.campaign, e.alias, e.kind, e.created_at].forEach((value, i) => {
            const td = make("td");
            td.append(make("span", value, i === 2 ? "event-ok" : undefined));
            tr.append(td);
          });
          return tr;
        }));
      }
    }
    document.getElementById("updated").textContent = "Updated using the local API · " + new Date().toLocaleTimeString();
  }
  let pending = false;
  async function safeRefresh() {
    if (pending || document.hidden) return;
    pending = true;
    try { await refresh(); }
    catch { const label = document.getElementById("updated"); if (label) label.textContent = "Local API unavailable. Try Refresh status."; }
    finally { pending = false; }
  }
  document.getElementById("refresh")?.addEventListener("click", safeRefresh);
  window.setInterval(safeRefresh, 10000);
  document.addEventListener("visibilitychange", safeRefresh);
})();
