// The site's only script, loaded in <head>. Everything it adds is optional:
// without JavaScript its buttons stay hidden and the pages work as they are.
//
// 1. Display preferences: dark theme and sans-serif text, each kept in this
//    browser's localStorage and applied before the page is drawn.
// 2. Copy buttons: a button with data-copy="<element id>" copies that
//    element's text and says so beside it.
// 3. Chart hover notes: an element with data-tip shows that text beside the
//    pointer at once, without the browser's tooltip delay. A bar with
//    data-hover-fill (a hatched, incomplete day) takes that fill while the
//    pointer is on it.
(function () {
  var root = document.documentElement;
  root.classList.add("js");

  // Each preference sets data-<name> on <html> to its non-default value.
  var choices = { theme: "dark", font: "sans" };

  function saved(name) {
    try { return localStorage.getItem(name); } catch (e) { return null; }
  }
  function save(name, value) {
    try {
      if (value) { localStorage.setItem(name, value); } else { localStorage.removeItem(name); }
    } catch (e) { /* storage blocked: the choice lasts for this page only */ }
  }

  Object.keys(choices).forEach(function (name) {
    if (saved(name) === choices[name]) { root.setAttribute("data-" + name, choices[name]); }
  });

  function toggle(button) {
    var name = button.getAttribute("data-toggle");
    var on = root.getAttribute("data-" + name) !== choices[name];
    if (on) { root.setAttribute("data-" + name, choices[name]); } else { root.removeAttribute("data-" + name); }
    save(name, on ? choices[name] : null);
  }

  // Shows a short note next to a copy button, then hides it again.
  function announce(button, text) {
    var note = button.parentNode.querySelector(".copy-note");
    if (!note) { return; }
    note.textContent = text;
    note.classList.add("shown");
    clearTimeout(note.hideTimer);
    note.hideTimer = setTimeout(function () { note.classList.remove("shown"); }, 2000);
  }

  // Selects the text, so it can be copied by hand when the clipboard is
  // not available to the page.
  function select(target) {
    var range = document.createRange();
    range.selectNodeContents(target);
    var selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }

  function copy(button) {
    var target = document.getElementById(button.getAttribute("data-copy"));
    if (!target) { return; }
    var text = target.textContent.trim();
    var fallback = function () {
      select(target);
      announce(button, "Press Ctrl+C to copy");
    };
    if (!navigator.clipboard) { fallback(); return; }
    navigator.clipboard.writeText(text).then(function () {
      announce(button, "Copied to clipboard!");
    }, fallback);
  }

  var tip = null;
  var hovered = null; // the hatched bar whose fill is swapped, if any
  function hover(bar) {
    if (bar === hovered) { return; }
    if (hovered) { hovered.setAttribute("fill", hovered.getAttribute("data-fill")); }
    hovered = null;
    if (bar && bar.hasAttribute("data-hover-fill")) {
      bar.setAttribute("data-fill", bar.getAttribute("fill"));
      bar.setAttribute("fill", bar.getAttribute("data-hover-fill"));
      hovered = bar;
    }
  }
  function showTip(event) {
    var bar = event.target.closest && event.target.closest("[data-tip]");
    hover(bar);
    if (!bar) {
      if (tip) { tip.hidden = true; }
      return;
    }
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "chart-tip";
      document.body.appendChild(tip);
    }
    tip.textContent = bar.getAttribute("data-tip");
    tip.hidden = false;
    // Beside the pointer, flipped to the left near the window's right edge,
    // and always kept inside the window (the note wraps at its max-width).
    var x = event.clientX + 14;
    if (x + tip.offsetWidth > window.innerWidth - 8) { x = event.clientX - 14 - tip.offsetWidth; }
    x = Math.min(x, window.innerWidth - 8 - tip.offsetWidth);
    tip.style.left = Math.max(8, x) + "px";
    tip.style.top = Math.max(8, event.clientY - tip.offsetHeight - 10) + "px";
  }
  document.addEventListener("mousemove", showTip);
  document.addEventListener("mouseleave", function () {
    hover(null);
    if (tip) { tip.hidden = true; }
  });

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-toggle], [data-copy]");
    if (!button) { return; }
    if (button.hasAttribute("data-toggle")) { toggle(button); } else { copy(button); }
  });
})();
