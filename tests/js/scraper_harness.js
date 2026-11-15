// Esegue lo script iniettato in un finto browser (senza dipendenze) e
// stampa in JSON i risultati dei casi controllati da test_scraper_behavior.py.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const source = fs
  .readFileSync(path.join(__dirname, "..", "..", "assets", "auto_login.js"), "utf8")
  .replace("__USERNAME__", '"user"')
  .replace("__PASSWORD__", '"secret"');

const RealDate = Date;
const NOW = new RealDate("2026-10-22T10:00:00").getTime();
class FixedDate extends RealDate {
  constructor(...args) {
    if (args.length) super(...args);
    else super(NOW);
  }
  static now() {
    return NOW;
  }
}

function fakeDoc(text, inputs = []) {
  return {
    title: "Geoin ROAD",
    body: { innerText: text },
    documentElement: { textContent: text },
    querySelectorAll(selector) {
      if (selector === "input") {
        return inputs.map((value) => ({ value, getAttribute: () => value }));
      }
      return [];
    },
  };
}

const storage = new Map();
const window = {
  location: { href: "https://geoinroad.dimetior.com/driver", pathname: "/driver", origin: "https://geoinroad.dimetior.com" },
  getComputedStyle: () => ({ display: "block", visibility: "visible" }),
};
window.document = fakeDoc("");
const context = vm.createContext({
  window,
  document: window.document,
  console: { log() {} },
  sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  localStorage: {
    getItem: (key) => (storage.has(key) ? storage.get(key) : null),
    setItem: (key, value) => storage.set(key, String(value)),
  },
  Date: FixedDate,
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
  URL,
});
vm.runInContext(source, context);
const app = window.GeoinroadApp;
const t = app.internals;
const results = {};

const shiftText = "Federico P.\nDRIVER\nDATA:\nPresente no route (HPI7) 06:25 - 15:15";
results.shown_date_wins = app
  .extractCandidateStats(fakeDoc(shiftText, ["22/10/2026"]), "https://geoinroad.dimetior.com/driver?date=2026-08-04")
  .rows.map((row) => row.date);
results.unverified_date_rows = app
  .extractCandidateStats(fakeDoc(shiftText), "https://geoinroad.dimetior.com/driver?date=2026-08-04")
  .rows.length;
results.current_page_rows = app
  .extractCandidateStats(fakeDoc(shiftText, ["mer 22 ott 2026"]), "https://geoinroad.dimetior.com/driver")
  .rows.map((row) => row.date);

const map = {};
const itemsByDay = new Map([
  ["2026-10-20", { day: "2026-10-20", present: false, type_id: 3, activity_id: 9 }],
  ["2026-10-24", { day: "2026-10-24", present: false, type_id: 2, activity_id: 6 }],
]);
results.learned = t.learnDayTypes(
  map,
  [{ rows: [
    { date: "2026-10-20", work_marker: "FA", status: "Ferie e ROL", source: "dom/calendar-default" },
    { date: "2026-10-24", work_marker: "W", status: "Presente no route", source: "dom/calendar-default" },
  ] }],
  itemsByDay
);
results.map_keys = Object.keys(map);
const api = t.apiCalendarRows(
  [
    { day: "2026-08-10", present: false, type_id: 3, activity_id: 9 },
    { day: "2026-08-11", present: false, type_id: 3, activity_id: 7 },
    { day: "2026-08-12", present: true, type_id: 1, activity_id: 1, start_time: "06:25", end_time: "15:15" },
    { day: "2026-10-25", present: false, type_id: 2, activity_id: 6 },
  ],
  map,
  {}
);
results.api_rows = api.rows.map((row) => [row.date, row.work_marker, row.value, row.source]);

const merged = app.mergeStatsPayloads(
  [
    { debug: {}, rows: [{ date: "2026-10-20", label: "MAR 20 Ferie e ROL (HPI7)", value: "8.00", source: "dom/calendar-default" }] },
    { debug: {}, rows: [{ date: "2026-10-20", label: "Ferie e ROL", value: "8.00", source: "geoinroad_api/employees/driver_calendar-default" }] },
  ],
  []
);
results.default_rows_per_day = merged.rows.filter((row) => row.date === "2026-10-20").length;

// Storico: un mese passato solo dalle API, senza calendario renderizzato
// (nel finto browser non si possono aprire iframe: se lo script ci
// provasse, il mese tornerebbe senza sync_range).
const emitted = [];
context.console.log = (line) => emitted.push(String(line));
const requested = [];
storage.set("geoinroad_employee", JSON.stringify({ id: 42 }));
window.$nuxt = {
  $axios: {
    async $get(url) {
      requested.push(url);
      if (url.includes("driver_calendar")) {
        return {
          employee_calendars: [
            { day: "2026-09-01", present: true, type_id: 1, activity_id: 1, start_time: "06:00", end_time: "14:30" },
            { day: "2026-09-02", present: false, type_id: 3, activity_id: 9 },
          ],
        };
      }
      return { routes: [] };
    },
  },
};

(async () => {
  await app.collectStats({
    background: true,
    history: true,
    from: "2026-09-01",
    to: "2026-09-30",
    month: "2026-09",
  });
  const stats = emitted
    .filter((line) => line.startsWith("GEOINROAD_APP::STATS::"))
    .map((line) => JSON.parse(line.slice("GEOINROAD_APP::STATS::".length)));
  const last = stats[stats.length - 1] || {};
  results.history = {
    payload_count: stats.length,
    sync_range: last.sync_range || null,
    history_month: (last.debug || {}).history_month || "",
    background: !!(last.debug || {}).background_sync,
    row_dates: Array.from(new Set((last.rows || []).map((row) => row.date))).sort(),
    calendar_calls: requested.filter((url) => url.includes("driver_calendar")).length,
    route_calls: requested.filter((url) => url.includes("planner/route")).length,
  };
  process.stdout.write(JSON.stringify(results));
})();
