window.CareerResults = (function () {
  var JOB_SET_OPTIONS = [
    { value: "core_30", label: "Catalogue 30 métiers", file: "jobs_30_core.json" },
    { value: "client_40", label: "Catalogue 40 métiers", file: "jobs_40_client.json" },
  ];

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function jobLabel(job) {
    return job.job_label || job.job || "";
  }

  function scoreRingHtml(score, jobStep) {
    var wavePath =
      "M0 8 C16 2 34 14 50 8 S84 2 100 8 L100 16 L0 16 Z";
    var waveSvg =
      '<svg viewBox="0 0 100 16" preserveAspectRatio="none" aria-hidden="true">' +
      '<path d="' + wavePath + '"/></svg>';

    return (
      '<div class="score-ring" style="--score:' + score + ";--i:" + jobStep + '">' +
      '<div class="score-liquid" aria-hidden="true">' +
      '<div class="score-wave">' +
      '<div class="score-wave-surface score-wave-surface--back">' + waveSvg + waveSvg + "</div>" +
      '<div class="score-wave-surface score-wave-surface--front">' + waveSvg + waveSvg + "</div>" +
      '<div class="score-wave-body"></div>' +
      "</div></div>" +
      "<span>" + score + "</span></div>"
    );
  }

  function renderLoadingHtml(statusText) {
    var statusLine = statusText
      ? '<p class="loader-status">' + escapeHtml(statusText) + "</p>"
      : "";
    return (
      '<div class="card loader-panel" role="status" aria-live="polite" aria-busy="true" aria-label="Chargement des résultats">' +
      '<div class="loader-scene" aria-hidden="true">' +
      '<div class="loader-ring loader-ring--1"></div>' +
      '<div class="loader-ring loader-ring--2"></div>' +
      '<div class="loader-ring loader-ring--3"></div>' +
      '<div class="loader-radar"></div>' +
      '<div class="loader-dims">' +
      "<span class=\"loader-dim\">A</span><span class=\"loader-dim\">B</span><span class=\"loader-dim\">C</span>" +
      "<span class=\"loader-dim\">D</span><span class=\"loader-dim\">E</span><span class=\"loader-dim\">F</span>" +
      "</div>" +
      '<div class="loader-hub"></div>' +
      "</div>" +
      '<div class="loader-progress" aria-hidden="true"></div>' +
      '<div class="loader-copy">' +
      '<p class="loader-title">Découverte de vos métiers</p>' +
      statusLine +
      '<div class="loader-messages">' +
      "<span>Analyse de vos réponses…</span>" +
      "<span>Calcul de vos correspondances…</span>" +
      "<span>Préparation de vos recommandations…</span>" +
      "</div></div></div>"
    );
  }

  function renderJobSetPicker(selectedJobSet, showPicker) {
    if (!showPicker) {
      return "";
    }
    var options = JOB_SET_OPTIONS.map(function (option) {
      var checked = option.value === selectedJobSet ? " checked" : "";
      var selectedClass = option.value === selectedJobSet ? " is-selected" : "";
      return (
        '<label class="job-set-option' + selectedClass + '">' +
        '<input type="radio" name="job_set" value="' + option.value + '"' + checked + ">" +
        "<span><span class=\"job-set-label\">" + escapeHtml(option.label) + "</span>" +
        '<span class="job-set-file">' + escapeHtml(option.file) + "</span></span></label>"
      );
    }).join("");

    return (
      '<div class="card job-set-card">' +
      '<p class="section-label"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M4 12h16M4 17h10"/></svg>Catalogue</p>' +
      '<h2 class="section-title">Jeu de métiers</h2>' +
      '<p class="section-desc">Choisissez le catalogue utilisé pour le calcul.</p>' +
      '<div class="job-set-picker">' + options + "</div></div>"
    );
  }

  function renderErrorHtml(msg) {
    return (
      '<div class="state-panel error">' +
      '<div class="state-icon" aria-hidden="true">' +
      '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>' +
      "</svg></div>" +
      '<p class="state-title">Impossible d\'afficher les résultats</p>' +
      '<p class="state-msg">' + msg + "</p></div>"
    );
  }

  function renderDataHtml(data, selectedJobSet, showPicker) {
    var jobs = data.top_jobs || [];
    var step = 0;
    var html = '<div class="results-reveal">';

    if (showPicker) {
      html += '<div class="reveal-block" style="--i:' + step++ + '">' + renderJobSetPicker(selectedJobSet, true) + "</div>";
    }

    if (data.email) {
      html +=
        '<div class="reveal-block" style="--i:' + step++ + '">' +
        '<div class="user-chip">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4z" opacity="0"/><path d="M4 8l8 5 8-5"/><rect x="4" y="6" width="16" height="12" rx="2"/></svg>' +
        escapeHtml(data.email) +
        "</div></div>";
    }

    html +=
      '<div class="reveal-block" style="--i:' + step++ + '">' +
      '<div class="card card-glow insight-card">' +
      '<p class="section-label"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l2.4 7.4H22l-6 4.6 2.3 7L12 16.8 5.7 21l2.3-7-6-4.6h7.6z"/></svg>Synthèse</p>' +
      "<p>" + escapeHtml(data.summary || "") + "</p></div></div>";

    html +=
      '<div class="card jobs-section">' +
      '<p class="section-label"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>Classement</p>' +
      '<h2 class="section-title">Top 5 des correspondances</h2>' +
      '<p class="section-desc">Les métiers les plus alignés avec votre profil.</p>' +
      '<ul class="jobs-list">';

    jobs.forEach(function (job, index) {
      var rank = index + 1;
      var score = Number(job.score) || 0;
      var rankClass = rank === 1 ? " is-top" : rank === 2 ? " rank-2" : rank === 3 ? " rank-3" : "";
      var jobStep = step + index;
      html +=
        '<li class="job-card' + rankClass + '" style="--i:' + jobStep + '">' +
        '<div class="job-aside">' +
        '<span class="job-rank">' + rank + "</span>" +
        scoreRingHtml(score, jobStep) +
        "</div>" +
        '<div class="job-body">' +
        '<h3 class="job-title">' + escapeHtml(jobLabel(job)) + "</h3>" +
        '<p class="job-reason">' + escapeHtml(job.reason || "") + "</p>" +
        (rank === 1 ? '<span class="job-badge">Meilleure correspondance</span>' : "") +
        "</div></li>";
    });

    html += "</ul></div></div>";
    return html;
  }

  function playResultsReveal(container) {
    var reveal = container.querySelector(".results-reveal");
    if (!reveal) {
      return;
    }
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        reveal.classList.add("is-active");
      });
    });
  }

  function init(options) {
    options = options || {};
    var apiBase = options.apiBase != null ? options.apiBase : "";
    var showJobSetPicker = options.showJobSetPicker === true;

    var params = new URLSearchParams(window.location.search);
    var email = params.get("email");
    var app = document.getElementById("app");
    if (!app) {
      return;
    }

    var selectedJobSet = params.get("job_set") === "client_40" ? "client_40" : "core_30";
    var activeRequest = 0;
    var retryAttempts = options.resultsRetryAttempts != null ? options.resultsRetryAttempts : 15;
    var retryDelayMs = options.resultsRetryDelayMs != null ? options.resultsRetryDelayMs : 3000;

    function sleep(ms) {
      return new Promise(function (resolve) {
        window.setTimeout(resolve, ms);
      });
    }

    function isPendingSubmissionError(detail) {
      var text = String(detail || "").toLowerCase();
      return text.indexOf("no response row") !== -1 || text.indexOf("google sheets") !== -1;
    }

    function isRetryableError(error) {
      if (!error) {
        return false;
      }
      if (error.status === 404 && isPendingSubmissionError(error.detail || error.message)) {
        return true;
      }
      if (error.status === 502 || error.status === 503 || error.status === 504) {
        return true;
      }
      return !error.status && (error instanceof TypeError || String(error.message) === "Failed to fetch");
    }

    function formatErrorMessage(error) {
      if (isPendingSubmissionError(error.detail || error.message)) {
        return (
          "Vos réponses ne sont pas encore disponibles. " +
          "Si vous venez de terminer le questionnaire, patientez quelques instants puis réessayez."
        );
      }
      return error.message || String(error);
    }

    function syncJobSetToUrl() {
      var next = new URLSearchParams(window.location.search);
      next.set("job_set", selectedJobSet);
      var query = next.toString();
      window.history.replaceState(null, "", window.location.pathname + (query ? "?" + query : ""));
    }

    function bindJobSetPicker() {
      if (!showJobSetPicker) {
        return;
      }
      var inputs = app.querySelectorAll('input[name="job_set"]');
      inputs.forEach(function (input) {
        input.onchange = function () {
          if (input.value !== "core_30" && input.value !== "client_40") {
            return;
          }
          if (input.value === selectedJobSet) {
            return;
          }
          selectedJobSet = input.value;
          syncJobSetToUrl();
          loadResults();
        };
      });
    }

    function renderLoading(statusText) {
      app.innerHTML = renderLoadingHtml(statusText);
    }

    function updateLoadingStatus(statusText) {
      var statusEl = app.querySelector(".loader-status");
      if (statusEl) {
        statusEl.textContent = statusText;
        return;
      }
      renderLoading(statusText);
    }

    function renderError(msg) {
      app.innerHTML = renderErrorHtml(msg);
    }

    function renderData(data) {
      app.classList.add("is-swapping");
      window.setTimeout(function () {
        try {
          app.innerHTML = renderDataHtml(data, selectedJobSet, showJobSetPicker);
          bindJobSetPicker();
          app.classList.remove("is-swapping");
          playResultsReveal(app);
        } catch (e) {
          app.classList.remove("is-swapping");
          renderError(e.message || String(e));
        }
      }, 140);
    }

    async function fetchResultsOnce() {
      var query = "email=" + encodeURIComponent(email) + "&job_set=" + encodeURIComponent(selectedJobSet);
      var r = await fetch(apiBase + "/api/results?" + query);
      if (!r.ok) {
        var err = await r.json().catch(function () {
          return {};
        });
        var error = new Error(err.detail || r.statusText || "Request failed");
        error.status = r.status;
        error.detail = err.detail;
        throw error;
      }
      return r.json();
    }

    async function fetchResults(requestId) {
      for (var attempt = 1; attempt <= retryAttempts; attempt++) {
        if (requestId !== activeRequest) {
          return null;
        }
        try {
          return await fetchResultsOnce();
        } catch (e) {
          if (!isRetryableError(e) || attempt === retryAttempts) {
            throw e;
          }
          updateLoadingStatus(
            "Enregistrement de vos réponses… (" + attempt + "/" + retryAttempts + ")"
          );
          await sleep(retryDelayMs);
        }
      }
      return null;
    }

    async function loadResults() {
      var requestId = ++activeRequest;
      renderLoading();
      try {
        var data = await fetchResults(requestId);
        if (requestId !== activeRequest || data == null) {
          return;
        }
        renderData(data);
      } catch (e) {
        if (requestId !== activeRequest) {
          return;
        }
        renderError(formatErrorMessage(e));
      }
    }

    if (!email) {
      renderError(
        "Ajoutez votre e-mail dans l'URL, par exemple : <code>results.html?email=vous@exemple.com</code>"
      );
      return;
    }

    syncJobSetToUrl();
    loadResults();
  }

  return { init: init };
})();
