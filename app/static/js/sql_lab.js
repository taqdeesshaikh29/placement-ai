const form = document.getElementById("sqlForm");
const editor = document.getElementById("query");

// Tab inserts spaces; Ctrl+Enter runs the query
editor.addEventListener("keydown", (e) => {
  if (e.key === "Tab") {
    e.preventDefault();
    const { selectionStart: s, selectionEnd: end } = editor;
    editor.setRangeText("  ", s, end, "end");
  } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    form.querySelector('button[value="run"]').click();
  }
});

// Prevent double submits (a repeated "Check Answer" would save a duplicate attempt)
let busy = false;
form.addEventListener("submit", (e) => {
  if (busy) { e.preventDefault(); return; }
  busy = true;
  const action = e.submitter ? e.submitter.value : "run";
  // disabled buttons are not sent, so keep the chosen action in a hidden field
  const hidden = document.createElement("input");
  hidden.type = "hidden"; hidden.name = "action"; hidden.value = action;
  form.appendChild(hidden);
  form.querySelectorAll("button").forEach((b) => (b.disabled = true));
});
