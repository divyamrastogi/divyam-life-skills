// Contact form submission. Posts to Supabase REST with the public
// (publishable/anon) key. That key is safe in the browser BECAUSE the table's
// RLS allows insert only — it cannot read or delete anything.
//
// Provide config via a global (e.g. a config.js that sets window.APP_CONFIG),
// or replace the two constants below.
(function () {
  var cfg = window.APP_CONFIG || {};
  var SUPABASE_URL = cfg.SUPABASE_URL || "https://<REF>.supabase.co";
  var SUPABASE_KEY = cfg.SUPABASE_KEY || ""; // publishable (sb_publishable_…) or anon JWT
  var TABLE = cfg.TABLE || "contact_submissions";

  var form = document.getElementById("contact-form");
  var success = document.getElementById("form-success");
  var errorMsg = document.getElementById("form-error");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (!form.reportValidity()) return;

    var button = form.querySelector('button[type="submit"]');
    var payload = {
      name: form.elements.name.value.trim(),
      email: form.elements.email.value.trim(),
      project_type: form.elements.project_type ? form.elements.project_type.value : "",
      details: form.elements.details.value.trim(),
    };

    errorMsg.hidden = true;
    button.disabled = true;
    var original = button.textContent;
    button.textContent = "Sending…";

    var done = function () { form.hidden = true; if (success) success.hidden = false; };
    var fail = function () { errorMsg.hidden = false; button.disabled = false; button.textContent = original; };

    if (!SUPABASE_KEY) { fail(); return; }

    // New sb_publishable_ keys use the apikey header only; legacy JWT (eyJ…)
    // keys also need Authorization: Bearer.
    var headers = {
      "Content-Type": "application/json",
      apikey: SUPABASE_KEY,
      Prefer: "return=minimal",
    };
    if (SUPABASE_KEY.indexOf("eyJ") === 0) {
      headers.Authorization = "Bearer " + SUPABASE_KEY;
    }

    fetch(SUPABASE_URL + "/rest/v1/" + TABLE, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload),
    })
      .then(function (res) { res.ok ? done() : fail(); })
      .catch(fail);
  });
})();
