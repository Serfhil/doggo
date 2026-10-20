// Редактор основного текста (Quill 2, локально). Quill остаётся обычным JS, без Vue.
(function () {
  const area = document.getElementById("text");
  const host = document.getElementById("editor");
  const form = document.getElementById("recordForm");
  if (!area || !host || !form || !window.Quill) return; // без JS остаётся обычное поле

  const quill = new Quill(host, {
    theme: "snow",
    placeholder: "Основной текст записи",
    modules: {
      toolbar: [
        [{ header: [2, 3, false] }],
        ["bold", "italic", "underline", "strike"],
        [{ list: "ordered" }, { list: "bullet" }],
        ["blockquote", "link"],
        ["clean"],
      ],
    },
  });

  if (area.value.trim()) {
    quill.clipboard.dangerouslyPasteHTML(area.value);
  }
  area.hidden = true;
  host.hidden = false;

  quill.on("text-change", function (_delta, _old, source) {
    if (source === "user") window.dispatchEvent(new Event("admin:dirty"));
  });

  // Перед отправкой кладём HTML в скрытое поле; сервер сам его очистит (nh3)
  form.addEventListener("submit", function () {
    area.value = quill.getText().trim() ? quill.getSemanticHTML() : "";
  });
})();
