# Gamma Vendor (Universal)

**Универсальный инструмент для w2a (Web-to-App).** Скачивает любой опубликованный сайт Gamma со всем React-рантаймом, обходит Cloudflare и готовит его к запуску в Android WebView.

## 🎯 Что это даёт

Gamma — это профессиональный GUI Builder. Мы используем его для генерации UI, а этот репозиторий **компилирует** сгенерированный сайт в автономный пакет для мобильного приложения.

- **Полный React-рантайм.** Скачивает все чанки Next.js (20+ MB, 100+ файлов).
- **Обход Cloudflare.** Использует Playwright + `fetch()` внутри Chromium.
- **100% офлайн.** Работает без интернета.
- **Privacy Shield.** Удаляет Cloudflare RUM, Google Analytics, Yandex Metrika.
- **Anti-FOUC.** Устраняет белую вспышку при загрузке.
- **Готов к W2A.** Включает `server.go` и `server.py` для локального хостинга.

## 🚀 Как использовать

### Вариант 1: GitHub Actions (Рекомендуется)

1. Нажми **Use this template** → создай новый репозиторий.
2. Перейди в **Actions** → **Universal Vendor** → **Run workflow**.
3. Введи URL своего сайта: `https://your-site.gamma.site/`.
4. Дождись завершения (2-4 минуты).
5. Клонируй результат и запусти сервер:

```bash
git clone https://github.com/ТВОЙ_НИК/ТВОЙ_РЕПО.git
cd ТВОЙ_РЕПО
python server.py
```

6. Открой `http://localhost:8080` в браузере.

### Вариант 2: Локально (Termux/Linux)

```bash
pip install playwright beautifulsoup4
playwright install chromium

export TARGET_URL="https://your-site.gamma.site/"
python vendor.py

python server.py
```

## 📱 Интеграция с W2A (Android)

### Как собрать APK

1. **Скомпилируй Go-сервер:**
```bash
GOOS=android GOARCH=arm64 go build -o server server.go
```

2. **Упакуй всё в APK:** `server`, `index.html`, `_next/`, `assets/`.
3. **Java-код (при старте приложения):**
```java
ProcessBuilder pb = new ProcessBuilder(getFilesDir() + "/server");
pb.directory(getFilesDir());
pb.start();
webView.loadUrl("http://127.0.0.1:8080");
```

4. **Программный скролл (для инициализации React):**
```java
webView.evaluateJavascript(
    "setTimeout(() => { " +
    "  window.scrollTo(0, document.body.scrollHeight); " +
    "  setTimeout(() => window.scrollTo(0, 0), 300); " +
    "}, 500);", null);
```

## 🛠 Архитектура

```
vendor.py           # Экстрактор: скачивает сайт, обходит Cloudflare
server.py           # Локальный Python-сервер (для тестов)
server.go           # Локальный Go-сервер (для APK)
.github/workflows/  # GitHub Actions pipeline
_next/              # React-рантайм (скачивается автоматически)
assets/             # Картинки и шрифты
index.html          # Главная страница
```

## 🔒 Privacy Shield

`vendor.py` автоматически удаляет:
- `cloudflareinsights.com` (Cloudflare RUM)
- `cdn-cgi/rum`
- `google-analytics.com`
- `googletagmanager.com`
- `mc.yandex.ru`
- `top-fwz1.mail.ru`
- `connect.facebook.net`
- `hotjar.com`

Все запросы перенаправляются на `about:blank` или заменяются на `void(0)`.

## 🧐 Известные ограничения

- **Анимации и lazy-загрузка.** React может требовать внешнего триггера (скролла) для завершения инициализации. Решается в W2A программным скроллом.
- **Карта (Yandex Maps).** Требует интернета. Для офлайна — статичное изображение.
- **Размер.** Полный React-рантайм весит ~20 MB. Для APK это нормально.

## 📄 Лицензия

MIT. Используй как хочешь.