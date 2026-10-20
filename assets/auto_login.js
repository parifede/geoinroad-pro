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

    function fallbackDate() {
      return sourceDateMatch?.[1] || dates[0]?.iso || localIsoDate();
    }

    function toMinutes(t) {
      const parts = t.split(":");
      return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
    }

    function dateForIndex(index) {
      if (sourceDateMatch) return sourceDateMatch[1];
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

    if (!isCalendarUrl) {
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
    const driverStatusMatch = isCalendar
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
    for (let i = 0; i < startMatches.length && !isCalendarUrl; i++) {
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
      if (rows.length >= 40) break;

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

  function isoDateOffset(offsetDays) {
    const date = new Date();
    date.setHours(12, 0, 0, 0);
    date.setDate(date.getDate() + offsetDays);
    return localIsoDate(date);
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

  function dateUrlsFor(isoDate) {
    return [
      absoluteDriverUrl("/driver?date=" + encodeURIComponent(isoDate)),
      absoluteDriverUrl("/driver/calendar?date=" + encodeURIComponent(isoDate)),
    ];
  }

  function routeLinksFromDocument(doc) {
    return Array.from(doc.querySelectorAll('a[href*="/driver/route/"]'))
      .map((node) => node.getAttribute("href") || "")
      .filter(Boolean)
      .map((href) => absoluteDriverUrl(href));
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

  async function collectApiStats(range) {
    const debug = {
      api_available: false,
      employee_id: "",
      calendar_days: 0,
      calendar_time_rows: 0,
      route_days: 0,
      errors: [],
    };
    const rows = [];
    const nuxt = window.$nuxt;
    const axios = nuxt && nuxt.$axios;
    if (!axios || typeof axios.$get !== "function") {
      return {
        title: document.title,
        url: window.location.href,
        captured_at: new Date().toISOString(),
        debug,
        rows,
      };
    }
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
      return {
        title: document.title,
        url: window.location.href,
        captured_at: new Date().toISOString(),
        debug,
        rows,
      };
    }

    const { from, to } = range || currentMonthDateRange();
    const daySet = new Set();
    try {
      const calendarPayload = await axios.$get(
        "/geoinroad_api/employees/driver_calendar?from=" +
          encodeURIComponent(from) +
          "&to=" +
          encodeURIComponent(to) +
          "&employee=" +
          encodeURIComponent(employeeId)
      );
      const calendars = calendarPayload.employee_calendars || calendarPayload.calendars || [];
      debug.calendar_days = calendars.length;
      debug.calendar_samples = calendars.slice(0, 3).map((item) => {
        try { return JSON.stringify(item).slice(0, 400); } catch (_) { return "unserializable"; }
      });
      for (const item of calendars) {
        const day = item.day || item.date;
        if (!day) continue;
        daySet.add(day);
        const calendarTime = timeRangeFromApiObject(item);
        if (item.present && calendarTime.start && calendarTime.end) {
          debug.calendar_time_rows += 1;
          rows.push({
            label: "Turno " + calendarTime.start + "-" + calendarTime.end,
            value: decimalHours(calendarTime.start, calendarTime.end),
            raw: "driver_calendar " + day,
            date: day,
            start_time: calendarTime.start,
            end_time: calendarTime.end,
            source: "geoinroad_api/employees/driver_calendar",
          });
        } else if (item.present) {
          rows.push({
            label: "Presente no route",
            value: "8.00",
            raw: "driver_calendar " + day,
            date: day,
            status: "Presente no route",
            work_marker: "W",
            source: "geoinroad_api/employees/driver_calendar-default",
          });
        } else {
          // Oggi e il futuro non vengono marcati dall'assenza API: il
          // calendario puo' non essere ancora aggiornato per la giornata
          // in corso e segnerebbe "riposo" un giorno lavorato.
          if (String(day) >= localIsoDate()) continue;
          const absence = String(
            item.absence_type || item.absence || item.reason || ""
          ).trim();
          rows.push({
            label: absence || "Libero",
            value: "0",
            raw: "driver_calendar " + day,
            date: day,
            status: absence || "Libero",
            work_marker: "R",
            source: "geoinroad_api/employees/driver_calendar",
          });
        }
      }
    } catch (error) {
      debug.errors.push("calendar api: " + String(error).slice(0, 160));
    }

    const routeDays = Array.from(daySet).sort();
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
            (item) => String(item.driver_id || "") === String(employeeId)
          );
          const start = driver?.start || route.start || "";
          const end = driver?.end || route.end || "";
          if (!start || !end) continue;
          rows.push({
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

    return {
      title: document.title,
      url: window.location.href,
      captured_at: new Date().toISOString(),
      debug,
      rows,
    };
  }

  async function fetchStatsDocument(url) {
    const result = {
      url,
      ok: false,
      status: 0,
      rows: 0,
      time_ranges: 0,
      start_count: 0,
      end_count: 0,
      error: "",
    };
    try {
      const response = await fetch(url, { credentials: "include" });
      result.status = response.status;
      const html = await response.text();
      result.ok = response.ok;
      const doc = new DOMParser().parseFromString(html, "text/html");
      const payload = extractCandidateStats(doc, url, doc.title || "Geoin ROAD");
      result.rows = payload.rows.length;
      result.time_ranges = payload.debug.time_range_count || 0;
      result.start_count = payload.debug.start_count || 0;
      result.end_count = payload.debug.end_count || 0;
      return { result, payload, doc };
    } catch (error) {
      result.error = String(error).slice(0, 180);
      return { result, payload: null, doc: null };
    }
  }

  async function loadRenderedStatsDocument(url) {
    const result = {
      url,
      ok: false,
      status: "iframe",
      rows: 0,
      time_ranges: 0,
      start_count: 0,
      end_count: 0,
      error: "",
    };

    return new Promise((resolve) => {
      const iframe = document.createElement("iframe");
      let settled = false;
      let timeoutId = 0;
      iframe.style.cssText = [
        "position:fixed",
        "left:-10000px",
        "top:-10000px",
        "width:1px",
        "height:1px",
        "opacity:0",
        "pointer-events:none",
      ].join(";");

      function finish() {
        if (settled) return;
        settled = true;
        clearTimeout(timeoutId);
        try {
          const doc = iframe.contentDocument || iframe.contentWindow?.document;
          if (!doc) throw new Error("iframe document unavailable");
          const payload = extractCandidateStats(doc, url, doc.title || "Geoin ROAD");
          result.ok = true;
          result.rows = payload.rows.length;
          result.time_ranges = payload.debug.time_range_count || 0;
          result.start_count = payload.debug.start_count || 0;
          result.end_count = payload.debug.end_count || 0;
          iframe.remove();
          resolve({ result, payload, doc });
        } catch (error) {
          result.error = String(error).slice(0, 180);
          try { iframe.remove(); } catch (_) {}
          resolve({ result, payload: null, doc: null });
        }
      }

      iframe.addEventListener("load", () => setTimeout(finish, 1600), { once: true });
      timeoutId = setTimeout(finish, 5200);
      iframe.src = url;
      document.body.appendChild(iframe);
    });
  }

  function isWorkedMarker(marker) {
    const normalized = String(marker || "").toUpperCase();
    return normalized === "W" || normalized === "S";
  }

  function shouldExpandRow(row) {
    // Le pagine diario per-giorno servono solo per i giorni effettivamente
    // in servizio (S/W): abortive e ferie sono pagati 8 ore ma senza turno.
    const marker = String(row.work_marker || "").toUpperCase();
    if (marker) return isWorkedMarker(marker);
    return (parseFloat(row.value || "0") || 0) > 0;
  }

  function addDateUrls(queue, queued, isoDate) {
    if (!isoDate) return;
    for (const url of dateUrlsFor(isoDate)) {
      if (!queued.has(url)) {
        queued.add(url);
        queue.push(url);
      }
    }
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
          if (rowPriority(row) !== bestPriorityByDate.get(row.date)) continue;
          const shiftKey = row.start_time && row.end_time
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
    const payloads = [extractCandidateStats()];
    const fetches = [];
    const apiPayload = await collectApiStats(range);
    if (apiPayload.rows.length || apiPayload.debug.api_available) {
      payloads.push(apiPayload);
    }
    const queue = [];
    const queued = new Set();
    const calendarUrl = absoluteDriverUrl("/driver/calendar");
    queued.add(calendarUrl);
    queue.push(calendarUrl);

    const { from, to } = range;
    const startDate = new Date(from + "T12:00:00");
    const endDate = new Date(to + "T12:00:00");
    for (let date = startDate; date <= endDate; date.setDate(date.getDate() + 1)) {
      addDateUrls(queue, queued, localIsoDate(date));
    }
    for (const row of payloads[0].rows || []) {
      if (shouldExpandRow(row)) {
        addDateUrls(queue, queued, row.date);
      }
    }

    let cursor = 0;
    while (cursor < queue.length && cursor < 90) {
      const batch = queue.slice(cursor, cursor + 5);
      cursor += batch.length;
      const results = await Promise.all(batch.map((url) => fetchStatsDocument(url)));
      for (const item of results) {
        fetches.push(item.result);
        if (item.payload) {
          payloads.push(item.payload);
          for (const row of item.payload.rows || []) {
            if (shouldExpandRow(row)) {
              addDateUrls(queue, queued, row.date);
            }
          }
        }
        if (item.doc) {
          for (const url of routeLinksFromDocument(item.doc)) {
            if (!queued.has(url)) {
              queued.add(url);
              queue.push(url);
            }
          }
        }
      }
    }

    const renderedQueue = [];
    const renderedQueued = new Set();
    function addRenderedUrl(url) {
      if (renderedQueued.has(url)) return;
      renderedQueued.add(url);
      renderedQueue.push(url);
    }

    // Le sigle delle giornate (S, W, A, M, F, GF, R...) vivono solo nelle
    // pagine calendario renderizzate, una settimana per pagina: una
    // renderizzata per settimana del periodo copre tutti i tipi giorno.
    const weekAnchors = [];
    for (let d = new Date(from + "T12:00:00"); d <= endDate; d.setDate(d.getDate() + 7)) {
      weekAnchors.push(localIsoDate(d));
    }
    for (const anchor of weekAnchors) {
      addRenderedUrl(absoluteDriverUrl("/driver/calendar?date=" + encodeURIComponent(anchor)));
    }

    let merged = mergeStatsPayloads(payloads, fetches);
    const hasPositiveRows = merged.rows.some((row) => parseFloat(row.value || "0") > 0);
    const renderedDates = new Set();
    if (hasPositiveRows) {
      for (const row of merged.rows || []) {
        const value = parseFloat(row.value || "0") || 0;
        if (value > 0 && row.date && rowPriority(row) <= 20) renderedDates.add(row.date);
      }
      for (const payload of payloads) {
        for (const row of payload.rows || []) {
          if (row.date && isWorkedMarker(row.work_marker)) renderedDates.add(row.date);
        }
      }
      for (const day of Array.from(renderedDates).sort().reverse().slice(0, 10)) {
        addDateUrls(renderedQueue, renderedQueued, day);
      }
    } else if (hasCustomRange) {
      // Periodo passato senza dati: renderizza tutte le pagine del range.
      for (let date = new Date(from + "T12:00:00"); date <= endDate; date.setDate(date.getDate() + 1)) {
        for (const url of dateUrlsFor(localIsoDate(date))) {
          addRenderedUrl(url);
        }
      }
    } else {
      addRenderedUrl(calendarUrl);
      for (let offset = -8; offset <= 8; offset++) {
        addRenderedUrl(absoluteDriverUrl("/driver?date=" + encodeURIComponent(isoDateOffset(offset))));
      }
    }

    const rangeDays = Math.round((endDate - startDate) / 86400000) + 1;
    const renderedLimit = weekAnchors.length + (hasPositiveRows
      ? 20
      : (hasCustomRange ? Math.min(2 * rangeDays, 62) : 28));
    for (let index = 0; index < renderedQueue.length && index < renderedLimit; index++) {
      const item = await loadRenderedStatsDocument(renderedQueue[index]);
      fetches.push(item.result);
      if (item.payload) {
        payloads.push(item.payload);
        for (const row of item.payload.rows || []) {
          if (shouldExpandRow(row)) {
            for (const url of dateUrlsFor(row.date)) {
              addRenderedUrl(url);
            }
          }
        }
      }
      if (item.doc) {
        for (const url of routeLinksFromDocument(item.doc)) {
          addRenderedUrl(url);
        }
      }
    }

    return mergeStatsPayloads(payloads, fetches);
  }

  window.GeoinroadApp = window.GeoinroadApp || {};
  window.GeoinroadApp.extractCandidateStats = extractCandidateStats;
  window.GeoinroadApp.mergeStatsPayloads = mergeStatsPayloads;
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
