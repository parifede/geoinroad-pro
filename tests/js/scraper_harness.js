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

process.stdout.write(JSON.stringify(results));
