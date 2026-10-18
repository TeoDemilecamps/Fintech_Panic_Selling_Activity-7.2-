// Panic Sale Risk Predictor: front-end behaviour.
// Without JavaScript the form still works (it posts to "/" and the server renders the result).
(function () {
  "use strict";

  var features = window.APP_FEATURES || {};
  var names = Object.keys(features);
  var form = document.getElementById("predict-form");
  var button = document.getElementById("submit-btn");
  var formError = document.getElementById("form-error");

  function byId(id) { return document.getElementById(id); }

  // Keep slider, number box and the value label in sync.
  names.forEach(function (name) {
    var num = byId(name);
    var range = byId(name + "_range");
    var out = byId(name + "_out");

    function setValue(v) {
      out.textContent = v === "" ? "" : v;
      clearError(name);
    }
    range.addEventListener("input", function () {
      num.value = range.value;
      setValue(range.value);
    });
    num.addEventListener("input", function () {
      var n = parseFloat(num.value);
      if (!isNaN(n)) {
        range.value = Math.min(Math.max(n, features[name].min), features[name].max);
      }
      setValue(num.value);
    });
  });

  function clearError(name) {
    var e = byId(name + "_error");
    e.textContent = "";
    byId(name).closest(".field").classList.remove("has-error");
  }
  function showError(name, msg) {
    byId(name + "_error").textContent = msg;
    byId(name).closest(".field").classList.add("has-error");
  }

  // Client-side validation mirrors the server rules.
  function validate() {
    var values = {};
    var ok = true;
    names.forEach(function (name) {
      var spec = features[name];
      var raw = byId(name).value.trim();
      clearError(name);
      if (raw === "") { showError(name, "This value is required."); ok = false; return; }
      var n = Number(raw);
      if (!isFinite(n)) { showError(name, "Must be a number."); ok = false; return; }
      if (n < spec.min || n > spec.max) {
        showError(name, "Must be between " + spec.min + " and " + spec.max + ".");
        ok = false; return;
      }
      values[name] = n;
    });
    return ok ? values : null;
  }

  function pct(x) { return (x * 100).toFixed(1) + "%"; }

  function showResult(r) {
    byId("result-empty").hidden = true;
    byId("result-body").hidden = false;
    var badge = byId("risk-badge");
    badge.className = "badge " + r.risk_level;
    badge.textContent = r.risk_label;
    byId("prob-panic").textContent = pct(r.probability_panic_sale);
    byId("verdict").textContent = r.prediction_label;
    byId("prob-stays").textContent = pct(r.probability_stays_invested);
    byId("action").textContent = r.recommended_action;
    byId("meter-marker").style.left = (r.probability_panic_sale * 100) + "%";
  }

  form.addEventListener("submit", function (event) {
    var values = validate();
    if (!values) { event.preventDefault(); return; }
    if (!window.fetch) { return; } // older browsers: normal form post

    event.preventDefault();
    formError.textContent = "";
    button.disabled = true;
    button.textContent = "Predicting...";

    fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values)
    })
      .then(function (res) {
        return res.json().then(function (data) { return { ok: res.ok, data: data }; });
      })
      .then(function (out) {
        if (out.ok) {
          showResult(out.data);
          if (window.matchMedia("(max-width: 860px)").matches) {
            byId("result-card").scrollIntoView({ behavior: "smooth", block: "start" });
          }
        } else {
          var details = out.data.details || {};
          Object.keys(details).forEach(function (n) { if (byId(n)) showError(n, details[n]); });
          formError.textContent = out.data.error || "Something went wrong.";
        }
      })
      .catch(function () {
        formError.textContent = "Could not reach the server. Please try again.";
      })
      .then(function () {
        button.disabled = false;
        button.textContent = "Predict panic-sale risk";
      });
  });

  // Example presets.
  Array.prototype.forEach.call(document.querySelectorAll(".chip"), function (chip) {
    chip.addEventListener("click", function () {
      var parts = chip.getAttribute("data-preset").split(",");
      names.forEach(function (name, i) {
        byId(name).value = parts[i];
        byId(name + "_range").value = parts[i];
        byId(name + "_out").textContent = parts[i];
        clearError(name);
      });
      form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
  });
})();
