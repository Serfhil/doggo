// Общие мелочи админки без фреймворков
(function () {
  // Подтверждение для форм с data-confirm. Текст берём из атрибута, а не из inline-JS
  document.addEventListener("submit", function (event) {
    const message = event.target.dataset && event.target.dataset.confirm;
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });

  // Предупреждение при уходе со страницы с несохранёнными изменениями
  const guarded = document.querySelector("form[data-guard]");
  if (guarded) {
    let dirty = false;
    let submitting = false;
    guarded.addEventListener("input", function () { dirty = true; });
    guarded.addEventListener("submit", function () { submitting = true; });
    window.addEventListener("admin:dirty", function () { dirty = true; });
    window.addEventListener("beforeunload", function (event) {
      if (dirty && !submitting) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
  }
})();
