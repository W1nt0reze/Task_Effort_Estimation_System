# Task Effort Estimation System

Система прогнозирования длительности выполнения задач по историческим данным из Яндекс.Трекера.

Проект реализует полный локальный цикл работы: подготовка данных, обучение модели машинного обучения, запуск FastAPI-сервера и использование веб-интерфейса для получения прогноза.

## Возможности

- обработка выгрузки задач `tasks.xlsx` и flow-метрик `flow_metrics.csv`;
- фильтрация задач с резолюцией «Решен»;
- выделение команды разработки из тегов задачи;
- обучение регрессионной модели на табличных признаках;
- сохранение модели в `models/effort_model.joblib`;
- получение прогноза через веб-интерфейс и API;
- сохранение новых фактических задач в SQLite;
- автоматическое переобучение модели после накопления 50 новых записей.

## Стек

- Python
- FastAPI
- pandas
- scikit-learn
- SQLite
- HTML/CSS/JavaScript

## Структура проекта

```text
app/                  FastAPI-приложение, API, SQLite, сервис модели
src/                  предобработка данных и обучение модели
static/               веб-интерфейс
data/raw/             исходные выгрузки, не загружаются в GitHub
data/processed/       обработанные датасеты, не загружаются в GitHub
models/               обученные модели, не загружаются в GitHub
requirements.txt      зависимости проекта
```

## Подготовка окружения

Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Подготовка данных

В каталог `data/raw/` нужно положить два файла:

```text
data/raw/tasks.xlsx
data/raw/flow_metrics.csv
```

Реальные файлы данных не входят в репозиторий и игнорируются через `.gitignore`.

## Запуск обработки и обучения

```bash
python -m src.preprocess
python -m src.train_model
```

После выполнения команд будут созданы:

```text
data/processed/dataset_filtered_resolved.csv
models/effort_model.joblib
models/metrics.json
```

Эти файлы являются генерируемыми артефактами и не загружаются в GitHub.

## Запуск приложения

```bash
uvicorn app.main:app --reload
```

После запуска:

```text
Веб-интерфейс: http://127.0.0.1:8000
API-документация: http://127.0.0.1:8000/docs
```

## API

- `GET /api/meta` — справочники приоритетов, типов задач и команд;
- `POST /api/predict` — прогноз длительности выполнения задачи;
- `POST /api/tasks` — сохранение фактической задачи в SQLite.

Отдельной папки `api/` в проекте нет: маршруты FastAPI описаны в файле `app/main.py`.

## Команды разработки

Из тегов Яндекс.Трекера выделяются команды:

```text
cargo_web
courier_product
united_dispatch
cargo_b2b
cargo_c2c
dragon_infra
cargo_pricing
cargo_finance
cargo_planned
motion_model
cargo_support
udp
```

Теги `udp`, `udp_ndd`, `udp_core`, `front_ndd` объединяются в команду `udp`.

## Что не нужно загружать в GitHub

`.gitignore` уже исключает:

```text
tasks.xlsx
flow_metrics.csv
dataset_filtered_resolved.csv
dataset_merged.csv
app.db
effort_model.joblib
metrics.json
__pycache__/
.idea/
```

Перед коммитом можно проверить список файлов командой:

```bash
git status
git ls-files
```
