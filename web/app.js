// Posts the signup form to /signup and shows the result in #banner.
(function () {
  var form = document.getElementById("signup-form");
  var banner = document.getElementById("banner");

  function show(text, isError) {
    banner.textContent = text;
    banner.classList.toggle("error", !!isError);
    banner.hidden = false;
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var payload = {
      name: document.getElementById("name").value.trim(),
      email: document.getElementById("email").value.trim()
    };
    fetch("/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res.json().then(function (body) { return { ok: res.status === 201, body: body }; });
      })
      .then(function (r) {
        if (r.ok) {
          show("Welcome aboard!", false);
          form.reset();
        } else {
          show("Signup failed: " + (r.body.error || "unknown error"), true);
        }
      })
      .catch(function (err) {
        show("Signup failed: " + err.message, true);
      });
  });
})();
