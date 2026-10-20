// Менеджер картинок записи (Vue 3, глобальная сборка, без сборщика).
// Контракт эндпоинтов: расширенное ТЗ, раздел 2.8.
(function () {
  const root = document.getElementById("images-app");
  if (!root || !window.Vue) return;

  const { createApp, ref, computed } = Vue;
  const recordId = root.dataset.recordId;
  const maxImages = Number(root.dataset.max);
  const maxMb = Number(root.dataset.maxMb);
  const initial = JSON.parse(document.getElementById("images-data").textContent);
  const ALLOWED = ["image/jpeg", "image/png", "image/webp"];

  // Запрос к JSON-API: при ошибке бросает Error с русским текстом от сервера
  async function api(url, options) {
    const response = await fetch(url, options);
    if (response.status === 204) return null;
    let body = null;
    try {
      body = await response.json();
    } catch (_) {
      /* пустой или не JSON */
    }
    if (!response.ok) {
      const detail = body && typeof body.detail === "string" ? body.detail : null;
      throw new Error(detail || "Ошибка сервера (" + response.status + ")");
    }
    return body;
  }

  createApp({
    setup() {
      const images = ref(initial);
      const uploads = ref([]); // файлы в очереди: {key, name, status, message}
      const message = ref("");
      let counter = 0;

      const canAdd = computed(() => images.value.length < maxImages);
      const busy = computed(() => uploads.value.some((u) => u.status === "uploading"));

      function fail(error) {
        message.value = error.message;
      }

      async function onFiles(event) {
        const files = Array.from(event.target.files);
        event.target.value = "";
        message.value = "";
        for (const file of files) {
          const entry = { key: ++counter, name: file.name, status: "uploading", message: "" };
          uploads.value.push(entry);
          const item = uploads.value[uploads.value.length - 1];
          if (images.value.length >= maxImages) {
            item.status = "error";
            item.message = "Не больше " + maxImages + " картинок на запись";
            continue;
          }
          if (!ALLOWED.includes(file.type)) {
            item.status = "error";
            item.message = "Допустимы только JPEG, PNG и WebP";
            continue;
          }
          if (file.size > maxMb * 1024 * 1024) {
            item.status = "error";
            item.message = "Файл больше " + maxMb + " МБ";
            continue;
          }
          const form = new FormData();
          form.append("file", file);
          try {
            const created = await api("/admin/api/records/" + recordId + "/images", {
              method: "POST",
              body: form,
            });
            images.value.push(created);
            uploads.value = uploads.value.filter((u) => u.key !== entry.key);
          } catch (error) {
            item.status = "error";
            item.message = error.message;
          }
        }
      }

      function dismiss(key) {
        uploads.value = uploads.value.filter((u) => u.key !== key);
      }

      async function saveAlt(image) {
        try {
          await api("/admin/api/images/" + image.id, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ alt: image.alt }),
          });
          message.value = "";
        } catch (error) {
          fail(error);
        }
      }

      async function move(index, step) {
        const target = index + step;
        if (target < 0 || target >= images.value.length) return;
        const previous = images.value.slice();
        const list = images.value.slice();
        [list[index], list[target]] = [list[target], list[index]];
        images.value = list;
        try {
          await api("/admin/api/records/" + recordId + "/images/order", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ids: list.map((i) => i.id) }),
          });
          message.value = "";
        } catch (error) {
          images.value = previous; // откат, если сервер не принял
          fail(error);
        }
      }

      async function remove(image) {
        if (!window.confirm("Удалить эту картинку?")) return;
        try {
          await api("/admin/api/images/" + image.id, { method: "DELETE" });
          images.value = images.value.filter((i) => i.id !== image.id);
          message.value = "";
        } catch (error) {
          fail(error);
        }
      }

      return { images, uploads, message, canAdd, busy, maxImages, maxMb, onFiles, dismiss, saveAlt, move, remove };
    },
    template: `
      <div class="images">
        <p v-if="message" class="notice notice-error" role="alert">{{ message }}</p>

        <ul v-if="images.length" class="image-list">
          <li v-for="(image, index) in images" :key="image.id" class="image-item">
            <div class="image-thumb">
              <img :src="image.thumb_url" :alt="image.alt" loading="lazy" />
              <span v-if="index === 0" class="badge badge-ok">Обложка</span>
            </div>
            <div class="image-fields">
              <label class="form-label form-label-sub" :for="'alt' + image.id">Подпись (alt)</label>
              <input type="text" :id="'alt' + image.id" v-model="image.alt" maxlength="200"
                     placeholder="Что на картинке" @change="saveAlt(image)" />
              <div class="image-buttons">
                <button type="button" class="btn btn-small" :disabled="index === 0"
                        :aria-label="'Поднять картинку ' + (index + 1)" @click="move(index, -1)">↑ Выше</button>
                <button type="button" class="btn btn-small" :disabled="index === images.length - 1"
                        :aria-label="'Опустить картинку ' + (index + 1)" @click="move(index, 1)">↓ Ниже</button>
                <button type="button" class="btn btn-small btn-danger" @click="remove(image)">Удалить</button>
              </div>
            </div>
          </li>
        </ul>
        <p v-else class="form-hint">Картинок пока нет.</p>

        <ul v-if="uploads.length" class="upload-list">
          <li v-for="item in uploads" :key="item.key" :class="{ 'upload-error': item.status === 'error' }">
            <span class="upload-name">{{ item.name }}</span>
            <span v-if="item.status === 'uploading'">Загрузка…</span>
            <template v-else>
              <span>{{ item.message }}</span>
              <button type="button" class="btn btn-small" @click="dismiss(item.key)">Скрыть</button>
            </template>
          </li>
        </ul>

        <div class="image-add">
          <label class="btn btn-primary" :class="{ 'is-disabled': !canAdd || busy }">
            Добавить картинки
            <input type="file" accept="image/jpeg,image/png,image/webp" multiple
                   :disabled="!canAdd || busy" @change="onFiles" class="visually-hidden" />
          </label>
          <span class="form-hint">
            {{ images.length }} из {{ maxImages }}. JPEG, PNG или WebP до {{ maxMb }} МБ.
            Размер и формат сайт подберёт сам.
          </span>
        </div>
      </div>
    `,
  }).mount(root);
})();
