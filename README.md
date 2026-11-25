# 35AWARDS Archive

Статический каталог лучших фотографий и фотографов конкурса **35AWARDS**. Каталог организован как **срез по номинациям**: годы и конкурсы — это фильтры и метаданные, а не отдельная навигация.

Сейчас в архиве:

- **8 номинаций:** Female portrait (2019–2025), Motion (2019–2025), Nude 18+ (2017–2025), Fashion & Glamour (2017–2025), Portrait (2016–2018), Child portrait (2021–2025), Children staged photography (2021–2025), Children photo (2016–2020);
- **15 тематических конкурсов**, включая свежие завершённые 2026: Female Color Portrait, Blue Color, Red Color, Studio Portrait, Female Portrait with Flowers, Silhouette, Childhood in Motion; детские темы Black and white child portrait, Children emotional portrait, Childhood in motion, Perfect Children staged photography; плюс Concert Photography 2021, Wedding 2022, Emotions Through Nude 18+, Body Lines 2022;
- **1 890 работ** в каталоге: по **топ-35** за каждый доступный год номинации и **все работы с бейджем BEST OF CONTEST** в темах (для старых тем без такого бейджа — TOP-10 с честной пометкой);
- **Полная разметка:** 23 избранных разбора с текстом и 3 рецепта съёмки; для всех 1 890 работ — автоматическая VLM-разметка света, цвета, оптики, фона и фасетов;
- на главной — мультивыбор фильтров по типу, номинации, теме, году, награде, свету, цвету, технике, образу, эмоции и мульти-участию;
- Nomination-страницы — сквозные по годам, с фильтром по году, без деления на «подборки».

Сайт полностью статический: HTML + CSS + JS + локальные изображения. Открывается напрямую (`catalog/index.html`) или через любой веб-сервер.

## Что показывает сайт

- Только топовые работы: **топ-35 номинации** и/или работы с наградами **WIN · 100 лучших**, **BEST OF CONTEST**, **TOP %**, **III stage**.
- Полноразмерные фотографии 1500 px и превью 720 px.
- Автор: имя, аватар, страна/город, ссылки на **35AWARDS** и **35photo.pro**.
- Метрики работы: просмотры, лайки, избранное.
- Метрики автора: подписчики, подписки, количество работ, место в рейтинге Great photographers, жанры, техника.
- **VLM-разбор**: схема и направление света, контраст, палитра, температура, предполагаемое фокусное расстояние и диафрагма, фон, композиционные нюансы.
- **Тематические конкурсы** как отдельный слой: свои страницы, **все работы с бейджем BEST OF CONTEST**, фильтр по теме и участники из других номинаций.
- **Контекст конкурса**: отдельный фильтр и кликабельные бейджи. Нажатие на `TOP 4% · Female studio portrait · 2025` открывает каталог с фильтром по этому конкурсу и уровню награды; в фильтре видно год конкурса.
- **Мульти-награды**: страница `catalog/multi/index.html` с работами, которые участвовали и побеждали в нескольких номинациях/темах.
- Галерея с мультивыбором фильтров и лайтбоксом. Фотография в лайтбоксе не обрезается: она вписывается в сцену через `object-fit: contain`.
- Deep links: `…/index.html#photo_12868266`, `…/11th/index.html#photo_13209701`.

## Мультивыбор фильтров

- Внутри одной группы — **OR**: выбрал «Female portrait» + «Nude» → показать оба.
- Между группами — **AND**: `(Female portrait OR Nude) AND (студийный OR естественный свет) AND (драма OR загадка)`.
- Состояние хранится в URL: `?nomination=female-portrait,nude&award=win`.
- Счётчики у опций показывают, сколько работ содержит это значение; суммы по группам могут превышать общее число работ из-за пересечений и дублей участий.
- «Сбросить фильтры» очищает все группы.

## Персональные разборы

- `catalog/reports/brilenkov/index.html` — разбор 5 работ Алексея Бриленкова в завершённых тематических конкурсах **Female Color Portrait (1083)** и **Blue Color (1074)**: сравнение с топ-10, оценки по свету/цвету/композиции/истории/технике, что доработать и план роста.

## Структура

```
35awards/
├─ config/
│  ├─ catalog.json              # конкурсы, номинации, id по годам
│  ├─ facets.json               # справочник фильтров: свет, цвет, эмоции, сезон...
│  └─ contest_meta.json         # названия и годы контекстов theme:<id> / nomination:<id>
├─ analysis/
│  ├─ analyses.json             # VLM-разборы по photo_id
│  └─ README.md                 # схема разбора и фасетов
├─ scraper/
│  ├─ client.py                 # HTTP-клиент, кэш, вежливые задержки
│  ├─ listing.py                # парсинг страниц результатов (новый и старый формат)
│  ├─ photodata.py              # API карточки: метрики, награды, 1500px
│  ├─ authors.py                # профиль автора: подписчики, жанры, техника
│  ├─ media.py                  # фото, аватары, флаги, превью
│  ├─ technical.py              # авторазметка ч/б
│  ├─ themes.py                 # парсинг тематических конкурсов
│  ├─ pipeline.py               # сквозной сбор одной номинации/года
│  └─ theme_pipeline.py         # сбор темы: BEST OF CONTEST / TOP-10 fallback
├─ scripts/
│  ├─ scrape_nomination.py      # одна номинация + год
│  ├─ scrape_all.py             # все номинации/годы из конфига
│  ├─ scrape_theme.py           # один тематический конкурс
│  ├─ collect_contest_meta.py   # названия/годы контекстов
│  ├─ scrape_author_review.py   # топ темы + работы автора для разбора
│  └─ build_author_report.py    # HTML-отчёт по автору
├─ builder/
│  └─ build.py                  # генерация HTML из data.json
├─ templates/
│  ├─ base.html
│  ├─ index.html                # главная: общий срез
│  ├─ nomination.html
│  ├─ edition.html
│  ├─ theme.html
│  ├─ multi.html
│  ├─ report_brilenkov.html     # персональный разбор
│  ├─ _filters.html
│  ├─ _lightbox.html
│  └─ macros.html
├─ catalog/                     # ГОТОВЫЙ СТАТИЧЕСКИЙ САЙТ
│  ├─ index.html
│  ├─ assets/
│  │  ├─ css/site.css
│  │  ├─ css/report.css
│  │  ├─ js/gallery.js
│  │  ├─ badges/
│  │  └─ flags/
│  ├─ reports/
│  │  └─ brilenkov/             # разбор 5 работ + топ-10 двух тем
│  ├─ multi/
│  │  └─ index.html             # работы с несколькими участиями/наградами
│  ├─ themes/
│  │  ├─ female-color-portrait-2026/1083/
│  │  ├─ blue-color-2026/1074/
│  │  ├─ red-color-2026/1086/
│  │  ├─ studio-portrait-2026/1072/
│  │  ├─ female-portrait-flowers-2026/1048/
│  │  ├─ silhouette-2026/1057/
│  │  ├─ bw-child-portrait-2021/611/
│  │  ├─ children-emotional-portrait-2023/761/
│  │  ├─ childhood-in-motion-2024/802/
│  │  ├─ perfect-children-staged-2024/872/
│  │  ├─ childhood-in-motion-2026/1044/
│  │  ├─ concert-photography-2021/654/
│  │  ├─ wedding-2022/677/
│  │  ├─ emotions-through-nude/836/
│  │  └─ body-lines-2022/676/
│  └─ nominations/
│     ├─ female-portrait/
│     ├─ motion/
│     ├─ nude/
│     ├─ fashion/
│     ├─ portrait-classic/
│     ├─ child-portrait/
│     ├─ children-staged/
│     └─ children-photo/
└─ work/                        # кэш HTTP и профилей (можно удалять)
```

Ключевой принцип: всё, что относится к номинации и году, лежит в одной папке `catalog/nominations/<номинация>/<конкурс>/`. Главная страница агрегирует данные из всех `data.json` и строит общий срез.

## Быстрый старт

```powershell
pip install -r requirements.txt
```

Собрать текущие 10+10 работ:

```powershell
python scripts/scrape_nomination.py --nomination female-portrait --edition 11th --limit 10
python scripts/scrape_nomination.py --nomination female-portrait --edition 10th --limit 10
python builder/build.py
```

Собрать топ-35 по каждому году:

```powershell
python scripts/scrape_nomination.py --nomination female-portrait --edition 11th --limit 35
python scripts/scrape_nomination.py --nomination female-portrait --edition 10th --limit 35
python builder/build.py
```

Или всё из конфига:

```powershell
python scripts/scrape_all.py --limit 35
python builder/build.py
```

## Разбор автора

```powershell
python scripts/scrape_author_review.py --profile brilenkov --themes 1083,1074 --top 10
python scripts/build_author_report.py
```

Скрипт скачивает топ-10 каждого тематического конкурса и работы автора, а затем собирает HTML-отчёт `catalog/reports/brilenkov/index.html` со сравнением, оценками и планом роста.

## Новые номинации и темы

```powershell
# Motion и Nude за 11th и 10th, топ-35
python scripts/scrape_nomination.py --nomination motion --edition 11th --limit 35
python scripts/scrape_nomination.py --nomination motion --edition 10th --limit 35
python scripts/scrape_nomination.py --nomination nude --edition 11th --limit 35
python scripts/scrape_nomination.py --nomination nude --edition 10th --limit 35

# Референсы для съёмки мероприятий в сложном свете
python scripts/scrape_theme.py --theme concert-photography-2021
python scripts/scrape_theme.py --theme wedding-2022
python scripts/scrape_theme.py --theme emotions-through-nude
python scripts/scrape_theme.py --theme body-lines-2022

# Свежие завершённые темы 2026 — только BEST OF CONTEST
python scripts/scrape_theme.py --theme female-color-portrait-2026
python scripts/scrape_theme.py --theme blue-color-2026
python scripts/scrape_theme.py --theme red-color-2026
python scripts/scrape_theme.py --theme studio-portrait-2026
python scripts/scrape_theme.py --theme female-portrait-flowers-2026
python scripts/scrape_theme.py --theme silhouette-2026

python builder/build.py
```

Посмотреть сайт:

```powershell
cd catalog
python -m http.server 8765
# http://127.0.0.1:8765/
```

## Политика отбора

Pipeline берёт работы из верхушки рейтинга номинации. В каталог попадают:

- работы с `rank <= 35`;
- либо работы за пределами топ-35, но с наградой `WIN`, `BEST OF CONTEST` или `TOP %`.

Сейчас для каждой доступной номинации и года сохранён **топ-35**, для тем — все работы с **BEST OF CONTEST** (или TOP-10, если бейджа нет).

## Фильтры

На главной доступны группы:

- **Номинация** — срез по номинациям;
- **Год** — все годы архива;
- **Награда** — WIN · 100 лучших, BEST OF CONTEST, TOP %, III stage, Топ-35;
- **Свет** — студийный, естественный, мягкий, жёсткий, Рембрандт, боковой, контровой, оконный, низкий ключ (по размеченным работам);
- **Цвет** — цвет, ч/б, тёплый, холодный, приглушённый, насыщенный (цвет/ч-б — автоматически для всех);
- **Техника** — студия, естественный свет, постановка, документальное, fine art, fashion, эксперимент (по размеченным работам);
- **Образ** — beauty, характер, fashion, минимализм, fine art, документальный, постановочный, винтаж, кинематографичный, сюрреализм (по размеченным работам);
- **Эмоция** — спокойствие, нежность, напряжение, драма, загадка, сила, грусть (по размеченным работам);
- **Мульти-участие** — 2+/3+/4+ конкурса, 2+/3+/4+ награды, 2+ номинации, 2+ темы.

Фильтры **фокусное** и **сезон** убраны: по изображению они определяются ненадёжно, а разметка есть лишь у малой части архива. Фокусное остаётся в тексте разбора, но не в фильтрах.

Фильтры работают как пересечение групп (AND): например, «свет: студийный» + «эмоция: загадка» + «награда: WIN». Внутри одной группы — выбранное значение.

## Годы

- **2015** — специальный альбом «100 Best Art Photos», без обычных номинаций.
- **2016–2018** — ранняя общая номинация **Portrait** (в каталоге — `portrait-classic`).
- **2016–2020** — общая **Children photo** («Детская фотография»).
- **2021–2025** — **Child portrait** и **Children staged photography**.
- **2017–2025** — **Nude 18+** и **Fashion & Glamour**.
- **2019–2025** — **Female portrait** и **Motion**.
- Везде, где номинация существует, берётся **топ-35** за год.

Несуществующие номинации не выдумываются: если в 2015–2018 не было отдельной Female portrait, её нет и в архиве.

## Цвет и ч/б

`bw` — единственный монохромный тег. Отдельный `monochrome` убран: он дублировал «Ч/Б» и показывал тот же счётчик. Если позже понадобится отличать нейтральное ч/б от тонированного (сепия, цианотипия), это будет отдельный тег `toned`, а не второй синоним.

## Контекст конкурса

В фильтрах есть отдельный **«Контекст»** — выбор конкретного конкурса/номинации с годом. Он собирается из `memberships` всех фото и `config/contest_meta.json`.

Номинации сгруппированы по названию: внутри группы годы идут от новых к старым, а пункт **«Все годы»** выбирает всю номинацию сразу. Если у конкурса нет названия в конфиге, оно берётся из `memberships` (поэтому вместо `nomination:277` показывается `Conceptual photo · 2018`).

- `Female studio portrait · 2025`
- `Women's Emotions · 2026`
- `Female portrait · 2025`

Клик по бейджу в карточке (`TOP 4% · Female studio portrait · 2025`) ставит этот контекст и уровень награды; в результате появляется плашка контекста и активный фильтр награды. Так можно посмотреть все работы архива с этим бейджем в этом конкурсе.

Ограничение: это фильтр по локальному архиву, а не по полному списку участников конкурса. Для полного списка нужна отдельная выгрузка результатов соответствующего subcontest.

## Мульти-участие

Как вытащить «разносторонне сильные» работы:

1. Для каждого фото API `author/photodata` отдаёт `contests[]` — все номинации и тематические конкурсы, где работа участвовала.
2. Pipeline сохраняет это в `memberships` (`type`, `contest_id`, `under_id`, `badge`).
3. Builder считает:
   - `multi` — 2+ конкурса, `contests_3` — 3+, `contests_4` — 4+;
   - `multi_award` — 2+ награды уровня `WIN / BEST OF CONTEST / TOP %`, `awards_3` — 3+, `awards_4` — 4+;
   - `multi_nomination` — 2+ основные номинации;
   - `multi_theme` — 2+ тематических конкурса;
   - `score` — индекс силы: `2 × конкурсы + 5 × награды + 3 × номинации + темы`.
4. На главной есть фильтры по этим порогам, а на `catalog/multi/index.html` — список, отсортированный по индексу силы.

Это не идеальная метрика, но она показывает, какие работы чаще выставлялись и чаще получали награды в разных конкурсах.

## VLM-разбор

`analysis/analyses.json` содержит разбор по каждому `photo_id`. Builder подмешивает его при сборке, поэтому новые разборы не требуют повторного скрейпа. Схема описана в `analysis/README.md`.

Важно: фокусное расстояние, диафрагма и схема света — **экспертная оценка по изображению**, а не EXIF. В карточке сайта это указано. Для избранных работ добавлен блок `recipe`: режим камеры, диапазоны настроек, схема света, уверенность, альтернативы и тест-протокол.

### Массовая разметка

- **23 избранных разбора** — ручные/курируемые, с подробным текстом и (для 3 работ) рецептом съёмки.
- **Автоматическая VLM-разметка** — для всех остальных работ: свет, цвет, оптика, фон, нюансы и фасеты для фильтров. Такие записи помечены `"auto": true` в `analysis/analyses.json`; схема — `analysis/BULK_SCHEMA.md`.
- В фильтре **«Разбор»** доступны: `есть разбор` (весь архив), `есть рецепт` (3), `избранные` (23).
- Страница `catalog/reviews/index.html` показывает избранные разборы; полная разметка открывается в лайтбоксе любой работы и через фильтр `?review=analysis`.

## Номинации и темы

Полный разбор 24 основных номинаций, списка тематических конкурсов и плана интеграции — в `docs/nominations-and-themes.md`. Кратко: основные номинации остаются первым уровнем, тематические конкурсы (Red Color, Nature Under Snow, Black and White Female Portrait и др.) добавляются отдельным слоем `themes/`, а VLM-фасеты (цвет, сезон, погода, монохром) позволяют собирать темы даже среди работ, не подававшихся в соответствующий конкурс.

## Данные

Каждый `data.json` содержит:

- `nomination` — название, русское название, количество работ и авторов;
- `edition` — конкурс, год, ссылки на результаты;
- `photos[]`:
  - `rank`, `id`, `title`, `description`, `top35`;
  - `image.full`, `image.thumb`, `width`, `height`;
  - `award`, `honours`, `badge_images`;
  - `analysis` — VLM-разбор;
  - `facets` — значения для фильтров;
  - `metrics` — просмотры, лайки, избранное;
  - `author` — профиль, ссылки, аватар, страна/город, подписчики, работы,
    место в рейтинге, жанры, техника.

Builder дополнительно добавляет в каждую фотографию `nomination`/`edition` контекст и готовые `*_url`, чтобы одна и та же карточка работала и на главной, и на странице года.

## Как добавить номинацию или год

Все источники описаны в `config/catalog.json`.

```json
{
  "editions": {
    "11th": { "year": 2025, "winners_path": "winners11th", "title": "11th 35AWARDS" },
    "10th": { "year": 2024, "winners_path": "winners10th", "title": "10th 35AWARDS" }
  },
  "nominations": {
    "female-portrait": {
      "name": "Female portrait",
      "name_ru": "Женский портрет",
      "editions": { "11th": 1197, "10th": 1009 }
    }
  }
}
```

- `winners_path` — сегмент URL результатов (`https://35awards.com/<winners_path>/nomination/<id>/`).
- `editions.<slug>` — id номинации на странице конкретного конкурса.
- После добавления запустите скрейпер и `python builder/build.py`.

## Публикация на GitHub Pages

Сайт публикуется workflow `.github/workflows/pages.yml`: он загружает только папку `catalog` как артефакт Pages, поэтому сайт открывается в корне репозитория.

1. В GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. После push в `main` workflow запускается автоматически.
3. Ручной перезапуск: **Actions → Deploy catalog to GitHub Pages → Run workflow**.

Адрес сайта: `https://<user>.github.io/<repo>/`.

## Правовой момент

Проект — неофициальный архив. Фотографии принадлежат их авторам, конкурс и платформа — 35AWARDS. На сайте указаны ссылки на профили авторов и исходные страницы работ. Используйте каталог для личного просмотра и исследований; для публичного переиспользования изображений нужно согласие авторов.
