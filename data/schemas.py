from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class RecordCreate(BaseModel):
    """Данные записи на входе (форма админки). Теги приходят строками."""

    title: str
    description: str
    text: str
    record_type: str
    tags: list[str] = []


class RecordRead(RecordCreate):
    """Запись на выходе: те же поля + то, что выдаёт БД."""

    # from_attributes позволяет делать RecordRead.model_validate(orm_obj),
    # то есть читать поля из атрибутов объекта, а не из словаря
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
    author: str | None = None
    # В БД text может быть пустым, на входе он обязателен
    text: str | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def tags_to_names(cls, value):
        # В ORM теги это объекты Tag, а нам нужны только их имена
        return [getattr(tag, "name", tag) for tag in value or []]
