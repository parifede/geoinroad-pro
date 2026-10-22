(function () {
  const username = __USERNAME__;
  const password = __PASSWORD__;
  const statusPrefix = "GEOINROAD_APP::STATUS::";
  const statsPrefix = "GEOINROAD_APP::STATS::";
  const actionPrefix = "GEOINROAD_APP::ACTION::";
  const errorPrefix = "GEOINROAD_APP::ERROR::";
  const sessionKey = "geoinroad_pro_autologin_ts";
  const attemptsKey = "geoinroad_pro_autologin_attempts";
  const maxAttempts = 3;
  const loginPathPattern = /\/login/i;

  function emit(prefix, payload) {
    try {
      console.log(prefix + JSON.stringify(payload));
    } catch (error) {
      console.log(errorPrefix + JSON.stringify({ stage: "emit", message: String(error) }));
    }
  }

  function localIsoDate(value) {
    const d = value instanceof Date ? value : new Date();
    return [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, "0"),
      String(d.getDate()).padStart(2, "0"),
    ].join("-");
  }

  function visible(element) {
    if (!element) return false;
    const style = window.getComputedStyle(element);
    return style.display !== "none" && style.visibility !== "hidden";
  }

  function findUsernameInput() {
    const selectors = [
      'input[name="username"]',
      'input[name="email"]',
      'input[id*="user"]',
      'input[id*="email"]',
      'input[autocomplete="username"]',
      'input[type="email"]',
      'input[type="text"]',
    ];

    for (const selector of selectors) {
      const node = Array.from(document.querySelectorAll(selector)).find(visible);
      if (node) return node;
    }

    return null;
  }

  function findPasswordInput() {
    return Array.from(document.querySelectorAll('input[type="password"]')).find(visible) || null;
  }

  function setInputValue(element, value) {
    if (!element) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
    if (setter) {
      setter.call(element, value);
    } else {
      element.value = value;
    }
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    element.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  function readIntKey(key) {
    try {
      return parseInt(sessionStorage.getItem(key) || "0", 10) || 0;
    } catch (_) {
      return 0;
    }
  }

  function writeKey(key, value) {
    try {
      sessionStorage.setItem(key, String(value));
    } catch (_) {}
  }

  function clearAutologinState() {
    try {
      sessionStorage.removeItem(sessionKey);
      sessionStorage.removeItem(attemptsKey);
    } catch (_) {}
  }

  function submitLoginForm(userInput, passwordInput) {
    const submitButton = Array.from(
      document.querySelectorAll('button[type="submit"], input[type="submit"], button')
    ).find((element) => {
      const text = (element.innerText || element.value || "").trim();
      return visible(element) && /login|sign\s*in|accedi|entra/i.test(text || "submit");
    });

    const form = passwordInput.form || userInput.form;

    if (!submitButton && !form) {
      emit(statusPrefix, {
        stage: "autologin",
        action: "form_not_submitted",
        pathname: window.location.pathname,
      });
      return;
    }

    setTimeout(() => {
      if (userInput.value !== username) setInputValue(userInput, username);
      if (passwordInput.value !== password) setInputValue(passwordInput, password);
      if (submitButton) {
        submitButton.click();
      } else if (form && typeof form.requestSubmit === "function") {
        try { form.requestSubmit(); } catch (_) {
          try { form.submit(); } catch (_2) {}
        }
      } else if (form) {
        try { form.submit(); } catch (_) {}
      }
    }, 300);
    emit(statusPrefix, {
      stage: "autologin",
      action: submitButton ? "submit_clicked" : "form_submitted",
      pathname: window.location.pathname,
    });
  }

  function tryAutoLogin() {
    if (!loginPathPattern.test(window.location.pathname)) {
      clearAutologinState();
      emit(statusPrefix, {
        stage: "autologin",
        action: "skipped_not_login_page",
        pathname: window.location.pathname,
      });
      return false;
    }

    if (window.__geoinroadAutologinRan) {
      emit(statusPrefix, {
        stage: "autologin",
        action: "already_ran_in_page",
        pathname: window.location.pathname,
      });
      return true;
    }

    const attempts = readIntKey(attemptsKey);
    if (attempts >= maxAttempts) {
      emit(statusPrefix, {
        stage: "autologin",
        action: "autologin_max_attempts",
        attempts: attempts,
        pathname: window.location.pathname,
      });
      return true;
    }

    const userInput = findUsernameInput();
    const passwordInput = findPasswordInput();

    if (!userInput || !passwordInput) {
      emit(statusPrefix, {
        stage: "autologin",
        action: "waiting_for_form",
        pathname: window.location.pathname,
      });
      return false;
    }

    setInputValue(userInput, username);
    setInputValue(passwordInput, password);

    emit(statusPrefix, {
      stage: "autologin",
      action: "credentials_filled",
      pathname: window.location.pathname,
    });

    const lastTs = readIntKey(sessionKey);
    const now = Date.now();
    if (now - lastTs < 15000) {
      emit(statusPrefix, {
        stage: "autologin",
        action: "submit_throttled",
        pathname: window.location.pathname,
        elapsed_ms: now - lastTs,
      });
      return true;
    }

    window.__geoinroadAutologinRan = true;
    writeKey(sessionKey, now);
    writeKey(attemptsKey, attempts + 1);
    submitLoginForm(userInput, passwordInput);
    return true;
  }

  function scheduleAutoLogin() {
    if (tryAutoLogin()) return;
    if (!loginPathPattern.test(window.location.pathname)) return;
    let retries = 0;
    const timerId = setInterval(() => {
      retries += 1;
      if (tryAutoLogin() || retries >= 20) {
        clearInterval(timerId);
      }
    }, 500);
  }

  function extractCandidateStats(doc = document, sourceUrl = window.location.href, sourceTitle = document.title) {
    const canUseComputedVisibility = doc === document;
    const bodyText = (doc.body?.innerText || doc.documentElement?.textContent || "")
      .replace(/\u00a0/g, " ")
      .replace(/[\u2010\u2011\u2012\u2013\u2014\u2212]/g, "-")
      .replace(/[ \t]+/g, " ");
    const textNodes = Array.from(doc.querySelectorAll("body *"))
      .filter((node) => !canUseComputedVisibility || visible(node))
      .map((node) => (node.innerText || "").trim())
      .filter(Boolean)
      .slice(0, 500);

    const rows = [];
    const keywordPattern = /(ore|hours?|totale|timelog|straordinari|ordinario)[^0-9]{0,20}([0-9]+(?:[.,][0-9]+)?)/i;
    const timeRangePattern = /(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})/g;
    const datePattern = /(\d{1,2})[/-](\d{1,2})[/-](\d{4})/g;
    const routeLabelPattern = /^(Stazione|Codice|Inizio|Fine|Ruolo|Veicolo|Percorso)[:\s]+(.+)$/i;
    const seenLabels = new Set();
    const dates = Array.from(bodyText.matchAll(datePattern)).map((match) => ({
      index: match.index || 0,
      label: match[0],
      iso: [
        match[3],
        String(match[2]).padStart(2, "0"),
        String(match[1]).padStart(2, "0"),
      ].join("-"),
    }));
    const sourceDateMatch = String(sourceUrl || "").match(/[?&]date=(\d{4}-\d{2}-\d{2})/);
    const isCalendarUrl = /\/calendar/i.test(String(sourceUrl || ""));
    // La SPA puo' ignorare ?date= e mostrare comunque la giornata di oggi:
    // vale la data che la pagina mostra davvero (campo DATA). Se la pagina
    // ne chiede una ma non ne mostra nessuna, le righe giornaliere non
    // possono essere attribuite con certezza e vengono scartate.
    const shownDate = isCalendarUrl ? "" : displayedPageDate();
    const pageDate = shownDate;
    const dayRowsAllowed = !(sourceDateMatch && !shownDate);

    function isoFromAnyDate(text) {
      const value = String(text || "").trim();
      let match = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
      if (match) return match[1] + "-" + match[2] + "-" + match[3];
      match = value.match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/);
      if (match) {
        return [match[3], match[2].padStart(2, "0"), match[1].padStart(2, "0")].join("-");
      }
      match = value.match(/^(?:[A-Za-zÀ-ÿ]{3,}\.?,?\s+)?(\d{1,2})\s+([A-Za-zÀ-ÿ]{3,})\.?(?:\s+(\d{4}))?$/);
      const month = match ? monthNumber(match[2]) : null;
      if (month) {
        return [
          match[3] || String(yearForMonth(month)),
          String(month).padStart(2, "0"),
          match[1].padStart(2, "0"),
        ].join("-");
      }
      return "";
    }

    function displayedPageDate() {
      for (const input of Array.from(doc.querySelectorAll("input"))) {
        const iso = isoFromAnyDate(input.value || input.getAttribute("value") || "");
        if (iso) return iso;
      }
      return "";
    }

    function fallbackDate() {
      return pageDate || dates[0]?.iso || localIsoDate();
    }

    function toMinutes(t) {
      const parts = t.split(":");
      return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
    }

    function dateForIndex(index) {
      if (pageDate) return pageDate;
      let result = fallbackDate();
      for (const item of dates) {
        if (item.index <= index) result = item.iso;
      }
      return result;
    }

    function yearForMonth(month) {
      // A cavallo d'anno il calendario mostra mesi dell'anno vicino:
      // scegli l'anno che rende il mese piu' vicino al mese corrente.
      const now = new Date();
      let year = now.getFullYear();
      const diff = month - (now.getMonth() + 1);
      if (diff > 6) year -= 1;
      if (diff < -6) year += 1;
      return year;
    }

    function monthNumber(label) {
      const normalized = String(label || "").toLowerCase().slice(0, 3);
      const months = {
        gen: 1, feb: 2, mar: 3, apr: 4, mag: 5, giu: 6,
        lug: 7, ago: 8, set: 9, ott: 10, nov: 11, dic: 12,
      };
      return months[normalized] || null;
    }

    function isoFromItalianDay(day, monthLabel) {
      const month = monthNumber(monthLabel);
      if (!month) return fallbackDate();
      return [
        String(yearForMonth(month)),
        String(month).padStart(2, "0"),
        String(day).padStart(2, "0"),
      ].join("-");
    }

    if (!isCalendarUrl && dayRowsAllowed) {
      for (const match of bodyText.matchAll(timeRangePattern)) {
        const contextBefore = bodyText.slice(Math.max(0, (match.index || 0) - 60), match.index || 0);
        if (/pausa|pause|break|riposo/i.test(contextBefore)) continue;
        const startMin = toMinutes(match[1]);
        const endMin = toMinutes(match[2]);
        let deltaMin = endMin - startMin;
        if (deltaMin < 0) deltaMin += 1440;
        const workDate = dateForIndex(match.index || 0);
        const label = "Turno " + match[1] + "-" + match[2];
        const key = workDate + "|" + label;
        if (!seenLabels.has(key)) {
          seenLabels.add(key);
          rows.push({
            label: label,
            value: (deltaMin / 60).toFixed(2),
            raw: bodyText.slice(Math.max(0, (match.index || 0) - 120), (match.index || 0) + 180),
            date: workDate,
            start_time: match[1],
            end_time: match[2],
            source: "dom/time-range",
            source_url: sourceUrl,
          });
        }
      }
    }

    const isCalendar = isCalendarUrl || /CALENDARIO/i.test(bodyText);
    const driverStatusMatch = isCalendar || !dayRowsAllowed
      ? null
      : bodyText.match(/\b(Presente no route|Libero)\s*\(([^)]+)\)\s*(?:(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})|n\.d\.\s*-\s*n\.d\.)?/i);
    if (driverStatusMatch) {
      const status = driverStatusMatch[1];
      const station = driverStatusMatch[2];
      const start = driverStatusMatch[3];
      const end = driverStatusMatch[4];
      const workDate = fallbackDate();
      const value = start && end ? ((toMinutes(end) - toMinutes(start) + 1440) % 1440 / 60).toFixed(2) : "0";
      const label = start && end ? "Turno " + start + "-" + end : status + " (" + station + ")";
      const key = workDate + "|" + label;
      if (status !== "Libero" && !seenLabels.has(key)) {
        seenLabels.add(key);
        rows.push({
          label: label,
          value: value,
          raw: driverStatusMatch[0],
          date: workDate,
          station: station,
          status: status,
          start_time: start || "",
          end_time: end || "",
          source: "dom/driver-status",
          source_url: sourceUrl,
        });
      }
    }

    if (isCalendar) {
      // L'intestazione copre una settimana che puo' cavalcare due mesi
      // ("27 lug ~ 02 ago"): i giorni con numero minore del giorno
      // iniziale appartengono al secondo mese.
      const calendarHeaderMatch = bodyText.match(/\b(\d{1,2})\s+([A-Za-zÀ-ÿ]{3})\s*~\s*(\d{1,2})\s+([A-Za-zÀ-ÿ]{3})/i);
      const headerStartDay = calendarHeaderMatch ? parseInt(calendarHeaderMatch[1], 10) : 0;
      const calendarDefaultMonth = calendarHeaderMatch ? calendarHeaderMatch[2] : "";
      const headerEndMonth = calendarHeaderMatch ? calendarHeaderMatch[4] : "";

      function monthForCalendarDay(dayNumber) {
        if (headerEndMonth && headerStartDay && dayNumber < headerStartDay) {
          return headerEndMonth;
        }
        return calendarDefaultMonth;
      }
      // Ogni riga del calendario e': giorno, numero, SIGLA badge (S pilota,
      // W copilota, A abortive, M malattia, I infortunio, F/FA ferie,
      // GF festivo, R/RC riposo, altre = assenze), stato testuale e stazione.
      // La sigla e' catturata generica (1-2 maiuscole) per coprire anche
      // tipi non ancora noti; il testo di stato e' libero.
      const calendarPattern = /\b(LUN|MAR|MER|GIO|VEN|SAB|DOM)\s+(\d{1,2})(?:\s+([A-Za-z]{3}))?\s+([A-Z]{1,2})\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'. ]{0,30}?)\s*\(([^)]+)\)/g;
      for (const match of bodyText.matchAll(calendarPattern)) {
        const monthLabel = match[3] || monthForCalendarDay(parseInt(match[2], 10));
        const workDate = isoFromItalianDay(match[2], monthLabel);
        const sigla = match[4].toUpperCase();
        // Giornate pagate di default 8 ore: presenze (S/W) senza orario
        // estratto, abortive (A) e ferie (F/FA). L'orario reale letto dal
        // portale vince sempre perche' queste righe hanno priorita' minima.
        const paidDefault = /^(S|W|A|F|FA)$/.test(sigla);
        const label = match[1].toUpperCase() + " " + match[2] + " " + match[5] + " (" + match[6] + ")";
        const key = workDate + "|" + label;
        if (!seenLabels.has(key)) {
          seenLabels.add(key);
          rows.push({
            label: label,
            value: paidDefault ? "8.00" : "0",
            raw: match[0],
            date: workDate,
            station: match[6],
            status: match[5],
            day_code: match[1].toUpperCase(),
            work_marker: sigla,
            source: paidDefault ? "dom/calendar-default" : "dom/calendar",
            source_url: sourceUrl,
          });
        }
      }
    }

    const startMatches = Array.from(bodyText.matchAll(/(?:Inizio|Start)[:\s]+(\d{1,2}:\d{2})/gi));
    const endMatches = Array.from(bodyText.matchAll(/(?:Fine|End)[:\s]+(\d{1,2}:\d{2})/gi));
    let endCursor = 0;
    for (let i = 0; i < startMatches.length && !isCalendarUrl && dayRowsAllowed; i++) {
      const startIndex = startMatches[i].index || 0;
      while (endCursor < endMatches.length && (endMatches[endCursor].index || 0) < startIndex) {
        endCursor += 1;
      }
      if (endCursor >= endMatches.length) break;
      const nextStartIndex =
        i + 1 < startMatches.length ? (startMatches[i + 1].index || 0) : Infinity;
      if ((endMatches[endCursor].index || 0) >= nextStartIndex) continue;
      const endMatch = endMatches[endCursor];
      endCursor += 1;
      const start = startMatches[i][1];
      const end = endMatch[1];
      const startMin = toMinutes(start);
      const endMin = toMinutes(end);
      let deltaMin = endMin - startMin;
      if (deltaMin < 0) deltaMin += 1440;
      const workDate = dateForIndex(startIndex);
      const label = "Turno " + start + "-" + end;
      const key = workDate + "|" + label;
      if (!seenLabels.has(key)) {
        seenLabels.add(key);
        rows.push({
          label: label,
          value: (deltaMin / 60).toFixed(2),
          raw: bodyText.slice(Math.max(0, startIndex - 120), (endMatch.index || 0) + 120),
          date: workDate,
          start_time: start,
          end_time: end,
          source: "dom/start-end",
          source_url: sourceUrl,
        });
      }
    }

    for (const text of textNodes) {
      if (rows.length >= 40 || !dayRowsAllowed) break;

      const kwMatch = text.match(keywordPattern);
      if (kwMatch) {
        const label = kwMatch[1];
        const numericValue = parseFloat(kwMatch[2].replace(",", "."));
        const plausibleHours = isFinite(numericValue) && numericValue > 0 && numericValue <= 24;
        const key = "kw|" + label + "|" + text;
        if (!seenLabels.has(key)) {
          seenLabels.add(key);
          rows.push({
            label: label,
            value: plausibleHours ? kwMatch[2].replace(",", ".") : "0",
            raw: text.slice(0, 180),
            date: fallbackDate(),
            source: "dom/keyword",
            source_url: sourceUrl,
          });
        }
        continue;
      }

      const rlMatch = text.match(routeLabelPattern);
      if (rlMatch) {
        const label = rlMatch[1];
        const key = "meta|" + label + "|" + rlMatch[2];
        if (!seenLabels.has(key)) {
          seenLabels.add(key);
          rows.push({
            label: label,
            value: "0",
            raw: text.slice(0, 180),
            date: fallbackDate(),
            meta: rlMatch[2],
            source: "dom/route-meta",
            source_url: sourceUrl,
          });
        }
      }
    }

    return {
      title: sourceTitle,
      url: sourceUrl,
      captured_at: new Date().toISOString(),
      debug: {
        text_length: bodyText.length,
        text_sample: bodyText.slice(0, 600),
        visible_text_count: textNodes.length,
        time_range_count: Array.from(bodyText.matchAll(timeRangePattern)).length,
        start_count: startMatches.length,
        end_count: endMatches.length,
        date_count: dates.length,
      },
      rows,
    };
  }

  function absoluteDriverUrl(path) {
    try {
      return new URL(path, window.location.origin).href;
    } catch (_) {
      return path;
    }
  }

  function currentMonthDateRange() {
    const start = new Date();
    start.setHours(12, 0, 0, 0);
    start.setDate(1);
    const end = new Date(start);
    end.setMonth(end.getMonth() + 1);
    end.setDate(0);
    return {
      from: localIsoDate(start),
      to: localIsoDate(end),
    };
  }

  function currentWeekRange() {
    // Settimana del portale: lunedi' -> domenica.
    const start = new Date();
    start.setHours(12, 0, 0, 0);
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    const end = new Date(start);
    end.setDate(end.getDate() + 6);
    return {
      from: localIsoDate(start),
      to: localIsoDate(end),
    };
  }

  function decimalHours(start, end) {
    if (!start || !end) return "0";
    const toMinutes = (value) => {
      const parts = String(value).split(":");
      return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
    };
    let delta = toMinutes(end) - toMinutes(start);
    if (delta < 0) delta += 1440;
    return (delta / 60).toFixed(2);
  }

  function firstStringValue(object, keys) {
    for (const key of keys) {
      const value = object?.[key];
      if (typeof value === "string" && /\d{1,2}:\d{2}/.test(value)) return value;
    }
    return "";
  }

  function timeRangeFromApiObject(object) {
    const start = firstStringValue(object, [
      "start_time", "startTime", "start", "from", "begin", "begin_time", "shift_start", "work_start",
    ]);
    const end = firstStringValue(object, [
      "end_time", "endTime", "end", "to", "finish", "finish_time", "shift_end", "work_end",
    ]);
    if (start && end) return { start, end };
    const candidates = [
      object?.time,
      object?.hours,
      object?.range,
      object?.label,
      object?.description,
      object?.title,
      object?.calendar,
    ];
    for (const candidate of candidates) {
      const match = String(candidate || "").match(/(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})/);
      if (match) return { start: match[1], end: match[2] };
    }
    return { start: "", end: "" };
  }

  // L'API calendario non dice la sigla della giornata (S, W, FA, M, RC...)
  // ma solo type_id/activity_id numerici. La sigla compare invece nel
  // calendario renderizzato della settimana corrente: incrociando le due
  // fonti sugli stessi giorni si impara cosa significa ogni id, e la mappa
  // resta salvata nel browser per ricostruire anche i mesi passati.
  const dayTypeStoreKey = "geoinroad_pro_day_types_v1";

  function loadDayTypeMap() {
    try {
      const parsed = JSON.parse(localStorage.getItem(dayTypeStoreKey) || "{}");
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_) {
      return {};
    }
  }

  function saveDayTypeMap(map) {
    try {
      localStorage.setItem(dayTypeStoreKey, JSON.stringify(map));
    } catch (_) {}
  }


  function learnDayTypes(map, payloads, itemsByDay) {
    let learned = 0;
    for (const payload of payloads) {
      for (const row of payload.rows || []) {
        if (!/^dom\/calendar/.test(String(row.source || ""))) continue;
        const marker = String(row.work_marker || "").toUpperCase();
        const item = itemsByDay.get(String(row.date || ""));
        // Solo giorni gia' trascorsi: nel futuro il calendario mostra la
        // presenza pianificata, non il tipo definitivo della giornata.
        if (!marker || !item || String(row.date) > localIsoDate()) continue;
        if (item.activity_id === undefined || item.activity_id === null) continue;
        const key = "a:" + item.activity_id;
        const entry = map[key] || (map[key] = {});
        const slot = entry[marker] || (entry[marker] = { status: "", days: [] });
        if (row.status) slot.status = String(row.status);
        if (!slot.days.includes(row.date)) {
          slot.days.push(row.date);
          if (slot.days.length > 12) slot.days.shift();
          learned += 1;
        }
      }
    }
    return learned;
  }

  function resolveDayType(map, item, storeTypes) {
    // Solo activity_id: lo stesso type_id copre attivita' diverse (es.
    // ferie e malattia), dedurre la sigla dal tipo sbaglierebbe giorni.
    const key = "a:" + (item ? item.activity_id : "");
    const entry = map[key];
    const markers = entry ? Object.keys(entry) : [];
    if (markers.length) {
      markers.sort((a, b) => entry[b].days.length - entry[a].days.length);
      return { marker: markers[0], status: entry[markers[0]].status || "", via: key };
    }
    const fromStore = storeTypes && item ? storeTypes["a:" + item.activity_id] : null;
    if (fromStore) return { marker: fromStore.marker, status: fromStore.status, via: "store" };
    return null;
  }

  function summarizeDayTypes(map) {
    return Object.keys(map)
      .sort()
      .slice(0, 40)
      .map((key) => key + "=" + Object.keys(map[key])
        .map((marker) => marker + "(" + map[key][marker].days.length + ")")
        .join("/"));
  }

  function harvestStoreDayTypes() {
    // Il portale potrebbe tenere nello store Vuex l'elenco delle attivita'
    // con la loro sigla: se c'e', copre gli id non ancora imparati.
    const result = { types: {}, candidates: [] };
    let state = null;
    try {
      state = window.$nuxt && window.$nuxt.$store && window.$nuxt.$store.state;
    } catch (_) {}
    if (!state) return result;
    const codeKeys = ["code", "abbreviation", "acronym", "short_name", "shortName", "sigla", "symbol", "badge", "short", "initials"];
    const nameKeys = ["name", "description", "label", "title", "text"];
    const seen = new Set();
    function visit(value, path, depth) {
      if (!value || typeof value !== "object" || depth > 4 || seen.has(value)) return;
      seen.add(value);
      if (Array.isArray(value)) {
        const sample = value.slice(0, 80).filter((entry) => entry && typeof entry === "object" && entry.id !== undefined);
        if (sample.length < 2) return;
        const codeKey = codeKeys.find((key) =>
          sample.filter((entry) => typeof entry[key] === "string" && /^[A-Z]{1,3}$/.test(entry[key].trim())).length >= sample.length * 0.8
        );
        if (!codeKey) return;
        const nameKey = nameKeys.find((key) => typeof sample[0][key] === "string");
        result.candidates.push({
          path,
          size: value.length,
          sample: sample.slice(0, 12).map((entry) =>
            entry.id + "=" + entry[codeKey] + (nameKey ? " " + String(entry[nameKey]).slice(0, 24) : "")
          ),
        });
        if (/activit/i.test(path)) {
          for (const entry of sample) {
            if (typeof entry[codeKey] !== "string") continue;
            result.types["a:" + entry.id] = {
              marker: entry[codeKey].trim().toUpperCase(),
              status: nameKey ? String(entry[nameKey] || "") : "",
            };
          }
        }
        return;
      }
      for (const key of Object.keys(value).slice(0, 60)) {
        try {
          visit(value[key], path ? path + "." + key : key, depth + 1);
        } catch (_) {}
      }
    }
    visit(state, "", 0);
    result.candidates = result.candidates.slice(0, 6);
    return result;
  }

  function apiCalendarRows(items, typeMap, storeTypes) {
    const rows = [];
    let timeRows = 0;
    const today = localIsoDate();
    for (const item of items) {
      const day = String(item.day || item.date || "");
      if (!day) continue;
      const dayType = resolveDayType(typeMap, item, storeTypes);
      const ids = {
        type_id: item.type_id ?? "",
        activity_id: item.activity_id ?? "",
        day_type_via: dayType ? dayType.via : "",
      };
      const calendarTime = timeRangeFromApiObject(item);
      if (item.present && calendarTime.start && calendarTime.end) {
        timeRows += 1;
        rows.push({
          label: "Turno " + calendarTime.start + "-" + calendarTime.end,
          value: decimalHours(calendarTime.start, calendarTime.end),
          raw: "driver_calendar " + day,
          date: day,
          start_time: calendarTime.start,
          end_time: calendarTime.end,
          status: dayType ? dayType.status : "",
          work_marker: dayType ? dayType.marker : "",
          ...ids,
          source: "geoinroad_api/employees/driver_calendar",
        });
        continue;
      }
      // Oggi e il futuro non vengono marcati dall'assenza API: il
      // calendario puo' non essere ancora aggiornato per la giornata
      // in corso e segnerebbe "riposo" un giorno lavorato.
      if (!item.present && day >= today) continue;
      const absence = String(item.absence_type || item.absence || item.reason || "").trim();
      const marker = dayType ? dayType.marker : (item.present ? "W" : "R");
      const status = (dayType && dayType.status) || absence || (item.present ? "Presente no route" : "Libero");
      // Presenze senza orario, abortive e ferie: 8 ore pagate di default.
      const paid = /^(S|W|A|F|FA)$/.test(marker);
      rows.push({
        label: status,
        value: paid ? "8.00" : "0",
        raw: "driver_calendar " + day,
        date: day,
        status: status,
        work_marker: marker,
        ...ids,
        source: paid
          ? "geoinroad_api/employees/driver_calendar-default"
          : "geoinroad_api/employees/driver_calendar",
      });
    }
    return { rows, timeRows };
  }

  async function collectApiStats(range) {
    const debug = {
      api_available: false,
      employee_id: "",
      calendar_days: 0,
      calendar_time_rows: 0,
      route_days: 0,
      errors: [],
    };
    const api = { debug, items: [], weekItems: [], routeRows: [], calendarOk: false };
    const nuxt = window.$nuxt;
    const axios = nuxt && nuxt.$axios;
    if (!axios || typeof axios.$get !== "function") return api;
    debug.api_available = true;

    let employee = {};
    try {
      employee = JSON.parse(localStorage.getItem("geoinroad_employee") || "{}");
    } catch (error) {
      debug.errors.push("employee parse: " + String(error).slice(0, 120));
    }
    const employeeId = employee.id;
    debug.employee_id = employeeId || "";
    if (!employeeId) {
      debug.errors.push("missing employee id");
      return api;
    }

    async function fetchCalendar(fromDay, toDay) {
      const payload = await axios.$get(
        "/geoinroad_api/employees/driver_calendar?from=" +
          encodeURIComponent(fromDay) +
          "&to=" +
          encodeURIComponent(toDay) +
          "&employee=" +
          encodeURIComponent(employeeId)
      );
      return payload.employee_calendars || payload.calendars || [];
    }

    const { from, to } = range || currentMonthDateRange();
    try {
      api.items = await fetchCalendar(from, to);
      api.calendarOk = true;
      debug.calendar_days = api.items.length;
      debug.calendar_samples = api.items.slice(0, 3).map((item) => {
        try { return JSON.stringify(item).slice(0, 400); } catch (_) { return "unserializable"; }
      });
    } catch (error) {
      debug.errors.push("calendar api: " + String(error).slice(0, 160));
    }

    // La settimana corrente serve sempre: e' quella che il calendario
    // renderizzato mostra con le sigle, da cui si impara la mappa tipi.
    const week = currentWeekRange();
    if (week.from < from || week.to > to) {
      try {
        api.weekItems = await fetchCalendar(week.from, week.to);
      } catch (error) {
        debug.errors.push("week calendar api: " + String(error).slice(0, 120));
      }
    }

    const typeCounts = new Map();
    for (const item of [...api.items, ...api.weekItems]) {
      const key = "t" + item.type_id + "/a" + item.activity_id + (item.present ? "/P" : "/A");
      const current = typeCounts.get(key) || { count: 0, day: "" };
      current.count += 1;
      current.day = current.day || String(item.day || item.date || "");
      typeCounts.set(key, current);
    }
    debug.type_stats = Array.from(typeCounts.entries())
      .slice(0, 30)
      .map(([key, value]) => key + " x" + value.count + " (" + value.day + ")");

    const routeDays = Array.from(new Set(
      api.items.map((item) => String(item.day || item.date || "")).filter(Boolean)
    )).sort();
    for (let cursor = 0; cursor < routeDays.length; cursor += 6) {
      const batch = routeDays.slice(cursor, cursor + 6);
      const batchResults = await Promise.all(batch.map(async (day) => {
        try {
          const routePayload = await axios.$get(
            "/geoinroad_api/planner/route?day=" +
              encodeURIComponent(day) +
              "&employee=" +
              encodeURIComponent(employeeId)
          );
          return { day, routes: routePayload.routes || [], error: "" };
        } catch (error) {
          return { day, routes: [], error: String(error).slice(0, 120) };
        }
      }));
      for (const item of batchResults) {
        const day = item.day;
        if (item.error) {
          debug.errors.push("route api " + day + ": " + item.error);
          continue;
        }
        const routes = item.routes;
        if (routes.length) debug.route_days += 1;
        for (const route of routes) {
          const driver = (route.drivers || []).find(
            (entry) => String(entry.driver_id || "") === String(employeeId)
          );
          const start = driver?.start || route.start || "";
          const end = driver?.end || route.end || "";
          if (!start || !end) continue;
          api.routeRows.push({
            label: "Turno " + start + "-" + end,
            value: decimalHours(start, end),
            raw: "planner route " + (route.code || route.id || day),
            date: driver?.date || route.date || day,
            start_time: start,
            end_time: end,
            station: route.site_id ? String(route.site_id) : "",
            route_id: route.id || "",
            route_code: route.code || "",
            role: driver?.driver_type || "",
            source: "geoinroad_api/planner/route",
          });
        }
      }
    }
    return api;
  }

  function renderedDocLooksReady(doc) {
    try {
      const text = (doc.body && doc.body.innerText) || "";
      return /CALENDARIO|Presente|Libero|Malattia|Ferie|Abortive|Festiva|\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}/i.test(text);
    } catch (_) {
      return false;
    }
  }

  function openRenderedFrame(url) {
    const result = {
      url,
      ok: false,
      status: "iframe",
      rows: 0,
      time_ranges: 0,
      start_count: 0,
      end_count: 0,
      waited_ms: 0,
      error: "",
    };

    return new Promise((resolve) => {
      const iframe = document.createElement("iframe");
      let settled = false;
      let pollId = 0;
      let timeoutId = 0;
      const startedAt = Date.now();
      // Dimensioni da telefono (fuori schermo): a 1px la SPA puo' non
      // disegnare i comandi di navigazione del calendario.
      iframe.style.cssText = [
        "position:fixed",
        "left:-10000px",
        "top:-10000px",
        "width:412px",
        "height:900px",
        "opacity:0",
        "pointer-events:none",
      ].join(";");

      function finish() {
        if (settled) return;
        settled = true;
        clearInterval(pollId);
        clearTimeout(timeoutId);
        result.waited_ms = Date.now() - startedAt;
        try {
          const doc = iframe.contentDocument || iframe.contentWindow?.document;
          if (!doc) throw new Error("iframe document unavailable");
          result.ok = true;
          resolve({ result, iframe, doc });
        } catch (error) {
          result.error = String(error).slice(0, 180);
          try { iframe.remove(); } catch (_) {}
          resolve({ result, iframe: null, doc: null });
        }
      }

      // La SPA del portale si idrata DOPO l'evento load: fotografare la
      // pagina a tempo fisso la coglieva ancora vuota. Si attende che il
      // contenuto compaia davvero (poll ogni 500 ms), con un piccolo
      // margine extra per le righe ancora in arrivo.
      iframe.addEventListener(
        "load",
        () => {
          pollId = setInterval(() => {
            try {
              const doc = iframe.contentDocument || iframe.contentWindow?.document;
              if (doc && renderedDocLooksReady(doc)) {
                clearInterval(pollId);
                setTimeout(finish, 800);
              }
            } catch (_) {}
          }, 500);
        },
        { once: true }
      );
      timeoutId = setTimeout(finish, 15000);
      iframe.src = url;
      document.body.appendChild(iframe);
    });
  }

  function describePayload(result, payload) {
    result.rows = payload.rows.length;
    result.time_ranges = payload.debug.time_range_count || 0;
    result.start_count = payload.debug.start_count || 0;
    result.end_count = payload.debug.end_count || 0;
  }

  async function loadRenderedStatsDocument(url) {
    const frame = await openRenderedFrame(url);
    if (!frame.doc) return { result: frame.result, payload: null };
    try {
      const payload = extractCandidateStats(frame.doc, url, frame.doc.title || "Geoin ROAD");
      describePayload(frame.result, payload);
      return { result: frame.result, payload };
    } catch (error) {
      frame.result.error = String(error).slice(0, 180);
      return { result: frame.result, payload: null };
    } finally {
      try { frame.iframe.remove(); } catch (_) {}
    }
  }

  const calendarHeaderPattern = /\b\d{1,2}\s+[A-Za-zÀ-ÿ]{3}\s*~\s*\d{1,2}\s+[A-Za-zÀ-ÿ]{3}/;

  function calendarHeaderText(doc) {
    const match = ((doc.body && doc.body.innerText) || "").match(calendarHeaderPattern);
    return match ? match[0] : "";
  }

  function calendarDates(payload) {
    return (payload.rows || [])
      .filter((row) => /^dom\/calendar/.test(String(row.source || "")) && row.date)
      .map((row) => String(row.date))
      .sort();
  }

  function findPreviousWeekControl(doc) {
    // Il calendario mostra una settimana alla volta e ignora ?date=: per i
    // giorni passati bisogna premere la freccia "indietro" accanto
    // all'intestazione "19 ott ~ 25 ott".
    let headerNode = null;
    for (const node of Array.from(doc.querySelectorAll("body *"))) {
      const text = node.textContent || "";
      if (!calendarHeaderPattern.test(text)) continue;
      // A parita' di testo vince il nodo piu' interno (l'ordine e' quello
      // del documento, gli antenati arrivano prima).
      if (!headerNode || text.length <= (headerNode.textContent || "").length) headerNode = node;
    }
    if (!headerNode) return null;
    const previousHint = /prev|indietro|precedent|chevron[-_]left|arrow[-_]left|arrow[-_]back|‹|«/i;
    const nextHint = /next|avanti|successiv|chevron[-_]right|arrow[-_]right|arrow[-_]forward|›|»/i;
    const describe = (node) => [
      node.getAttribute("aria-label"),
      node.getAttribute("title"),
      node.getAttribute("class"),
      node.textContent,
    ].join(" ");
    let scope = headerNode.parentElement;
    for (let level = 0; scope && level < 4; level++, scope = scope.parentElement) {
      const candidates = Array.from(
        scope.querySelectorAll('button, [role="button"], a, svg, i, [class*="icon"], [class*="btn"]')
      ).filter((node) => !node.contains(headerNode) && !headerNode.contains(node));
      if (!candidates.length) continue;
      const hinted = candidates.find((node) => previousHint.test(describe(node)) && !nextHint.test(describe(node)));
      // 4 = DOCUMENT_POSITION_FOLLOWING: l'intestazione viene dopo il nodo.
      const before = candidates.filter((node) => node.compareDocumentPosition(headerNode) & 4);
      const pick = hinted || before[before.length - 1];
      if (pick) return pick.closest('button, [role="button"], a') || pick;
    }
    return null;
  }

  function clickElement(doc, element) {
    if (typeof element.click === "function") {
      element.click();
      return;
    }
    const view = doc.defaultView || window;
    element.dispatchEvent(new view.MouseEvent("click", { bubbles: true, cancelable: true }));
  }

  function waitForEarlierCalendarWeek(doc, url, previousDates, timeoutMs) {
    // La settimana precedente e' pronta quando le righe renderizzate
    // cadono tutte prima di quelle gia' lette (non basta il cambio di
    // intestazione: le righe possono arrivare un attimo dopo).
    const startedAt = Date.now();
    const earliest = previousDates[0] || "9999-12-31";
    return new Promise((resolve) => {
      const timerId = setInterval(() => {
        try {
          const payload = extractCandidateStats(doc, url, doc.title || "Geoin ROAD");
          const dates = calendarDates(payload);
          if (dates.length && dates[dates.length - 1] < earliest) {
            clearInterval(timerId);
            setTimeout(() => {
              const settled = extractCandidateStats(doc, url, doc.title || "Geoin ROAD");
              const settledDates = calendarDates(settled);
              resolve(settledDates.length && settledDates[settledDates.length - 1] < earliest ? settled : payload);
            }, 500);
            return;
          }
        } catch (_) {}
        if (Date.now() - startedAt > timeoutMs) {
          clearInterval(timerId);
          resolve(null);
        }
      }, 400);
    });
  }

  async function renderCalendarWeeks(range, fetches) {
    const nav = { weeks_wanted: 0, weeks_read: 0, headers: [], stop: "" };
    const payloads = [];
    const url = absoluteDriverUrl("/driver/calendar");
    const frame = await openRenderedFrame(url);
    fetches.push(frame.result);
    if (!frame.doc) {
      nav.stop = "no_document";
      return { payloads, nav };
    }
    try {
      const doc = frame.doc;
      const first = extractCandidateStats(doc, url, doc.title || "Geoin ROAD");
      describePayload(frame.result, first);
      payloads.push(first);
      nav.headers.push(calendarHeaderText(doc));
      let previousDates = calendarDates(first);
      const weekStart = new Date(currentWeekRange().from + "T12:00:00");
      const fromDate = new Date(range.from + "T12:00:00");
      nav.weeks_wanted = Math.max(0, Math.min(16, Math.ceil((weekStart - fromDate) / (7 * 86400000))));
      for (let step = 0; step < nav.weeks_wanted; step++) {
        if (!previousDates.length) {
          nav.stop = "no_calendar_rows";
          break;
        }
        const control = findPreviousWeekControl(doc);
        if (!control) {
          nav.stop = "no_prev_control";
          break;
        }
        clickElement(doc, control);
        const weekUrl = url + "#settimana-" + (step + 1);
        const payload = await waitForEarlierCalendarWeek(doc, weekUrl, previousDates, 7000);
        if (!payload) {
          nav.stop = "week_unchanged";
          break;
        }
        payloads.push(payload);
        nav.weeks_read += 1;
        nav.headers.push(calendarHeaderText(doc));
        previousDates = calendarDates(payload);
      }
    } catch (error) {
      nav.stop = "error: " + String(error).slice(0, 120);
    } finally {
      try { frame.iframe.remove(); } catch (_) {}
    }
    nav.headers = nav.headers.slice(0, 20);
    return { payloads, nav };
  }

  function mergeStatsPayloads(payloads, fetches) {
    const mergedRows = [];
    const seen = new Set();
    const bestPriorityByDate = new Map();
    for (const payload of payloads) {
      for (const row of payload.rows || []) {
        const value = parseFloat(row.value || "0") || 0;
        if (value <= 0 || !row.date) continue;
        const priority = rowPriority(row);
        const current = bestPriorityByDate.get(row.date);
        if (current === undefined || priority > current) {
          bestPriorityByDate.set(row.date, priority);
        }
      }
    }

    const shiftKeys = new Set();
    for (const payload of payloads) {
      for (const row of payload.rows || []) {
        const value = parseFloat(row.value || "0") || 0;
        if (value > 0 && row.date) {
          const priority = rowPriority(row);
          if (priority !== bestPriorityByDate.get(row.date)) continue;
          // Le 8 ore di default sono una per giorno, qualunque fonte le
          // proponga (API e calendario hanno etichette diverse).
          const shiftKey = priority === 5
            ? row.date + "|default"
            : row.start_time && row.end_time
              ? row.date + "|" + row.start_time + "|" + row.end_time
              : row.date + "|" + String(row.label || "") + "|" + String(row.value || "");
          if (shiftKeys.has(shiftKey)) continue;
          shiftKeys.add(shiftKey);
        } else if (value <= 0 && row.date && bestPriorityByDate.has(row.date)) {
          continue;
        }
        const key = rowIdentity(row);
        if (seen.has(key)) continue;
        seen.add(key);
        mergedRows.push(row);
      }
    }

    const primary = payloads[0] || extractCandidateStats();
    return {
      title: primary.title,
      url: primary.url,
      captured_at: new Date().toISOString(),
      debug: {
        ...primary.debug,
        api_debugs: payloads.map((payload) => payload.debug || {}).filter((debug) => debug.api_available),
        expanded_fetches: fetches.slice(0, 40),
        expanded_fetch_count: fetches.length,
        expanded_payload_count: payloads.length,
        expanded_row_count: mergedRows.length,
      },
      rows: mergedRows,
    };
  }

  function rowIdentity(row) {
    return [
      row.date || "",
      row.label || "",
      row.start_time || "",
      row.end_time || "",
      row.value || "",
      row.source || "",
      row.source_url || "",
    ].join("|");
  }

  function rowPriority(row) {
    const source = String(row.source || "");
    const sourceUrl = String(row.source_url || "");
    // Le 8 ore di default perdono contro qualunque orario reale.
    if (/-default/i.test(source)) return 5;
    if (/dom\/keyword/i.test(source)) return 10;
    if (/planner\/route/i.test(source) || /\/driver\/route\//i.test(sourceUrl)) return 20;
    if (/driver_calendar/i.test(source)) return 80;
    if (/dom\/driver-status|dom\/time-range/i.test(source) && !/\/driver\/route\//i.test(sourceUrl)) return 90;
    if (/dom\/start-end/i.test(source) && !/\/driver\/route\//i.test(sourceUrl)) return 75;
    return 50;
  }

  async function collectExpandedStats(options = {}) {
    // Senza intervallo esplicito si sincronizza il mese corrente; con
    // from/to (navigazione su periodi passati) si recupera quel periodo.
    const hasCustomRange = !!(options.from && options.to);
    const range = hasCustomRange
      ? { from: String(options.from), to: String(options.to) }
      : currentMonthDateRange();
    const { from, to } = range;
    const payloads = [extractCandidateStats()];
    const fetches = [];
    const api = await collectApiStats(range);

    // 1. Sigle giornata dal calendario renderizzato, settimana per
    //    settimana all'indietro fino all'inizio del periodo.
    const weeks = await renderCalendarWeeks(range, fetches);
    // Fuori dal periodo le settimane servono solo a imparare i tipi: le
    // loro 8 ore di default sovrascriverebbero le ore reali gia' salvate.
    for (const payload of weeks.payloads) {
      payloads.push({
        ...payload,
        rows: (payload.rows || []).filter((row) => row.date >= from && row.date <= to),
      });
    }

    // 2. Mappa type/activity id -> sigla, arricchita con queste settimane.
    const typeMap = loadDayTypeMap();
    const itemsByDay = new Map();
    for (const item of [...api.weekItems, ...api.items]) {
      const day = item.day || item.date;
      if (day) itemsByDay.set(String(day), item);
    }
    const learned = learnDayTypes(typeMap, weeks.payloads, itemsByDay);
    if (learned) saveDayTypeMap(typeMap);
    const storeTypes = harvestStoreDayTypes();

    // 3. Righe API tipizzate: ferie, malattia, riposi... non piu' tutto
    //    "Libero".
    const calendar = apiCalendarRows(api.items, typeMap, storeTypes.types);
    const debug = api.debug;
    debug.calendar_time_rows = calendar.timeRows;
    debug.day_types = summarizeDayTypes(typeMap);
    debug.day_types_learned = learned;
    debug.store_day_types = storeTypes.candidates;
    debug.calendar_nav = weeks.nav;
    if (debug.api_available) {
      payloads.push({
        title: document.title,
        url: window.location.href,
        captured_at: new Date().toISOString(),
        debug,
        rows: [...calendar.rows, ...api.routeRows],
      });
    }

    // 4. Senza API (portale cambiato o sessione non pronta): ultima
    //    risorsa, le pagine diario per-giorno, accettate solo se
    //    mostrano davvero la data richiesta.
    if (!api.calendarOk) {
      const startDate = new Date(from + "T12:00:00");
      const endDate = new Date(to + "T12:00:00");
      const rangeDays = Math.round((endDate - startDate) / 86400000) + 1;
      const renderedLimit = Math.min(2 * rangeDays, 62);
      const today = localIsoDate();
      const days = [];
      for (let date = new Date(startDate); date <= endDate; date.setDate(date.getDate() + 1)) {
        if (localIsoDate(date) <= today) days.push(localIsoDate(date));
      }
      const renderBudgetMs = 120000;
      const renderStartedAt = Date.now();
      for (const day of days.reverse().slice(0, renderedLimit)) {
        if (Date.now() - renderStartedAt > renderBudgetMs) break;
        const item = await loadRenderedStatsDocument(
          absoluteDriverUrl("/driver?date=" + encodeURIComponent(day))
        );
        fetches.push(item.result);
        if (item.payload) payloads.push(item.payload);
      }
    }

    const merged = mergeStatsPayloads(payloads, fetches);
    // Con il calendario API letto il periodo e' completo: il salvataggio
    // puo' ripulire le ore vecchie (anche errate) dei giorni del periodo.
    if (api.calendarOk) merged.sync_range = { from, to };
    return merged;
  }

  window.GeoinroadApp = window.GeoinroadApp || {};
  window.GeoinroadApp.extractCandidateStats = extractCandidateStats;
  window.GeoinroadApp.mergeStatsPayloads = mergeStatsPayloads;
  // Esposti per i test automatici dello scraper.
  window.GeoinroadApp.internals = {
    apiCalendarRows,
    learnDayTypes,
    resolveDayType,
    findPreviousWeekControl,
  };
  window.GeoinroadApp.collectStats = async function (options = {}) {
    try {
      const quickPayload = extractCandidateStats();
      const backgroundSync = !!options.background;
      // Per i periodi passati la pagina corrente non c'entra: niente
      // risposta rapida, solo il report del range richiesto.
      if (options.from && quickPayload.rows) quickPayload.rows = [];
      if (quickPayload.rows && quickPayload.rows.length) {
        quickPayload.debug = {
          ...quickPayload.debug,
          quick_response: true,
          background_sync: backgroundSync,
        };
        emit(statsPrefix, quickPayload);
      }
      const payload = await collectExpandedStats(options);
      payload.debug = {
        ...(payload.debug || {}),
        background_sync: backgroundSync,
      };
      emit(statsPrefix, payload);
    } catch (error) {
      emit(errorPrefix, { stage: "stats", message: String(error) });
      const fallback = extractCandidateStats();
      fallback.debug = {
        ...(fallback.debug || {}),
        background_sync: !!options.background,
      };
      emit(statsPrefix, fallback);
    }
  };

  try {
    scheduleAutoLogin();
  } catch (error) {
    emit(errorPrefix, {
      stage: "bootstrap",
      message: String(error),
      pathname: window.location.pathname,
    });
  }
})();
