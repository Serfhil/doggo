from pydantic import BaseModel, field_validator

from utils.text import clean_name

TITLE_MAX = 120
DESCRIPTION_MAX = 300
NAME_MAX = 40


class RecordForm(BaseModel):
    """Данные формы записи. Сами не падают: ошибки отдаёт errors() для показа в форме."""

    title: str = ""
    category_id: int | None = None
    description: str = ""
    text: str = ""  # уже очищенный HTML
    is_published: bool = True

    @field_validator("title", "description")
    @classmethod
    def strip_spaces(cls, value: str) -> str:
        return value.strip()

    def errors(self) -> dict[str, str]:
        """Правила из ТЗ 3.4: поле -> сообщение."""
        found: dict[str, str] = {}
        if not self.title:
            found["title"] = "Введите название"
        elif len(self.title) > TITLE_MAX:
            found["title"] = f"Название не длиннее {TITLE_MAX} символов"
        if len(self.description) > DESCRIPTION_MAX:
            found["description"] = (
                f"Краткое описание не длиннее {DESCRIPTION_MAX} символов"
            )
        if self.category_id is None:
            found["category_id"] = "Выберите категорию"
        if self.is_published and not self.text:
            found["text"] = "Для публикации нужен основной текст"
        return found


def check_name(value: str) -> tuple[str, str | None]:
    """Название тега или категории: (очищенное название, ошибка или None)."""
    value = clean_name(value)
    if not value:
        return value, "Введите название"
    if len(value) > NAME_MAX:
        return value, f"Название не длиннее {NAME_MAX} символов"
    return value, None
