# Схема массовой разметки

Для каждой фотографии вернуть объект с полями:

```json
{
  "summary": "1–2 предложения по-русски: что происходит в кадре и на чём он держится.",
  "light": {
    "scheme": "Схема света",
    "direction": "Направление и высота источника",
    "ratio": "Примерное соотношение ключ/заполнение",
    "notes": "Мягкость, блики, тени, чем похоже на практике"
  },
  "color": {
    "palette": "Палитра",
    "temperature": "Тёплая / холодная / нейтральная",
    "contrast": "Низкий / средний / высокий",
    "notes": "Насыщенность, тонировка, обработка"
  },
  "lens": {
    "estimate": "Класс фокусного: 24–35 / 50 / 85–105 / 135+ мм",
    "aperture": "Оценка диафрагмы: f/1.4–f/2 / f/2–f/2.8 / f/4–f/5.6 / f/8+",
    "perspective": "Ракурс, дистанция, компрессия",
    "notes": "ГРИП, размытие фона, искажения"
  },
  "background": "Одно предложение о фоне.",
  "nuances": ["2–3 коротких наблюдения о композиции, свете или эмоции"],
  "facets": {
    "light": [],
    "color": [],
    "emotion": [],
    "image": [],
    "technique": [],
    "focal": []
  }
}
```

## Допустимые значения фасетов

Использовать **только** эти значения:

- `light`: `studio`, `natural`, `soft`, `hard`, `loop`, `rembrandt`, `split`, `backlight`, `window`, `low-key`
- `color`: `color`, `bw`, `warm`, `cool`, `muted`, `saturated`
- `emotion`: `calm`, `tender`, `tense`, `dramatic`, `mystery`, `strength`, `sadness`
- `image`: `beauty`, `character`, `fashion`, `minimal`, `fine-art`, `documentary`, `staged`, `vintage`, `cinematic`, `surreal`
- `technique`: `studio`, `natural-light`, `staged`, `documentary`, `fine-art`, `fashion`, `experimental`
- `focal`: `wide`, `normal`, `short-tele`, `tele`

## Правила

- Не выдумывать то, чего не видно. Если параметр не определяется, выбрать наиболее общий тег и написать в `notes`, что это оценка.
- Не добавлять `recipe`, если об этом не попросили отдельно.
- Не менять `id`.
- Если изображение не открывается, вернуть `"summary": "IMAGE_UNREADABLE"` и пустые фасеты.
