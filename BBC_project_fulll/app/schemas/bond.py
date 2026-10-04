from pydantic import BaseModel, Field


class BondData(BaseModel):
    """Данные облигации из MOEX."""

    secid: str = Field(description="Тикер")
    secname: str = Field(description="Название")
    listlevel: int | None = Field(None, description="Уровень листинга")
    prevprice: float | None = Field(None, description="Цена")
    effectiveyield: float | None = Field(None, alias="yieldatprevwaprice", description="Доходность")
    matdate: str | None = Field(None, description="Дата погашения")
    status: str | None = Field(None, description="Статус")
    couponpercent: float | None = Field(None, description="Ставка купона")
    creditrating: str | None = Field(None, description="Кредитный рейтинг эмитента")
    facevalue: float | None = Field(None, description="Номинал облигации")
    sectype: str | None = Field(None, description="Тип облигации")
    issuesize: float | None = Field(None, description="Объем выпуска")
    couponfrequency: int | None = Field(None, description="Частота выплаты купона (раз в год)")
    duration: float | None = Field(None, description="Дюрация Маколея")
    faceunit: str | None = Field(None, description="Валюта номинала")
    volume: float | None = Field(None, description="Объем торгов")

    class Config:
        populate_by_name = True
        extra = "ignore"


class FilteredBond(BaseModel):
    """Отфильтрованная облигация."""

    ticker: str
    name: str
    price: float
    course_percent: float
    maturity_date: str
    coupon_rate: float | None
    currency: str = "RUB"


class BondScreenResult(BaseModel):
    """Результат скрининга."""

    bonds: list[FilteredBond]
    total_fetched: int
    total_filtered: int
    boards: list[str]
