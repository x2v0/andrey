"""Universal Gamma Vendoring: download everything, patch CDN, auto-stub missing."""
import asyncio
from playwright.async_api import async_playwright
import pathlib, os, re, urllib.parse

TARGET_URL = os.environ.get("TARGET_URL", "https://iskusstvo-zaboty-o-t-qqkkaff.gamma.site/")
ROOT = pathlib.Path(".")

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        c = await b.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        
        async def handle_route(route):
            url = route.request.url
            if url.startswith("data:") or url.startswith("blob:"):
                return await route.continue_()
            try:
                response = await route.fetch()
                body = await response.body()
                if response.ok and url.startswith("http"):
                    parsed = urllib.parse.urlparse(url)
                    path = parsed.path.lstrip("/")
                    if path.startswith("5s9bbrdpq/"): path = path[len("5s9bbrdpq/"):]
                    if not path: path = "index.html"
                    filepath = ROOT / path
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    if not filepath.exists():
                        with open(filepath, "wb") as f:
                            f.write(body)
                await route.fulfill(response=response)
            except Exception:
                await route.continue_()

        await c.route("**/*", handle_route)
        page = await c.new_page()
        print(f"Navigating to {TARGET_URL}...")
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=90000)

        # АГРЕССИВНЫЙ СКРОЛЛ ДО КОНЦА (Гарантирует загрузку всех lazy-chunks)
        print("Scrolling to the very bottom...")
        last_height = await page.evaluate("document.body.scrollHeight")
        while True:
            # Прокручиваем вниз
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000) # Ждем загрузки новых чанков
            
            # Проверяем, изменилась ли высота (значит, подгрузился новый контент)
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break # Достигли дна
            last_height = new_height

        # Возвращаемся наверх
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(2000)

        await page.wait_for_timeout(5000)
        # --- FORCE DOWNLOAD MISSING CHUNKS ---
        print("Force downloading missing chunks via browser fetch...")
        import json as json_mod
        stubs_list = []
        if pathlib.Path("stubs_to_download.json").exists():
            stubs_list = json_mod.loads(pathlib.Path("stubs_to_download.json").read_text())
        
        base_cdn = "https://assets.gammahosted.com/5s9bbrdpq/_next/static/immutable/chunks/"
        downloaded = 0
        for chunk_name in stubs_list:
            try:
                data = await page.evaluate("""
                    async (url) => {
                        try {
                            const r = await fetch(url);
                            if (!r.ok) return null;
                            const buf = await r.arrayBuffer();
                            return Array.from(new Uint8Array(buf));
                        } catch(e) { return null; }
                    }
                """, base_cdn + chunk_name)
                
                if data and len(data) > 100:
                    cf = ROOT / "_next" / "static" / "immutable" / "chunks" / chunk_name
                    cf.parent.mkdir(parents=True, exist_ok=True)
                    cf.write_bytes(bytes(data))
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"  Downloaded {downloaded}/{len(stubs_list)}")
            except Exception:
                pass
        print(f"✅ Force downloaded {downloaded} chunks.")
        
        html = await page.content()
        await b.close()

    print("Patching HTML...")
    cdn_regex = re.compile(r'https?://assets\.gammahosted\.com(?:/[a-z0-9]+)?')
    html_str = cdn_regex.sub('', html)
    
    # Anti-FOUC: Убираем белую полосу при загрузке
    # Принудительно ставим темный фон на html и body ДО того, как React загрузится
    anti_fouc_css = """
    <style id="anti-fouc">
      /* Принудительный темный фон ДО загрузки React */
      html, body { 
        background-color: #2d3133 !important; 
        color: #d6d9d7 !important;
        margin: 0; padding: 0; 
        overflow-x: hidden !important; 
      }
      #__next { 
        background-color: #2d3133 !important; 
        min-height: 100vh; 
      }
      /* Скрываем белый "мигающий" контент до гидратации */
      #__next:empty { background-color: #2d3133 !important; }
    </style>
    """
    if "</head>" in html_str:
        html_str = html_str.replace("</head>", anti_fouc_css + "</head>", 1)
    html_str = html_str.replace("url('/**/')", "none").replace('url("/**/")', "none")
    
    pathlib.Path("index.html").write_text(html_str, encoding="utf-8")

    # --- MANIFEST PARSING (Скачиваем ВСЁ из карты Next.js) ---
    print("Parsing Next.js manifests to download all chunks...")
    
    # Ищем файлы манифестов в скачанных файлах
    manifests = [
        ROOT / "_next" / "static" / "vQyp7iVN1nGPS1LA7cgut" / "_buildManifest.js",
        ROOT / "_next" / "static" / "vQyp7iVN1nGPS1LA7cgut" / "_ssgManifest.js",
        ROOT / "_next" / "static" / "vQyp7iVN1nGPS1LA7cgut" / "_clientMiddlewareManifest.js"
    ]
    
    all_chunks_to_download = set()
    for manifest in manifests:
        if manifest.exists():
            content = manifest.read_text(encoding="utf-8", errors="ignore")
            # Ищем все пути к чанкам (они лежат внутри манифеста)
            chunks = re.findall(r'chunks/([a-zA-Z0-9_-]+\.js)', content)
            all_chunks_to_download.update(chunks)
            print(f"  Found {len(chunks)} chunks in {manifest.name}")
    
    # Скачиваем всё, что нашли в манифестах
    downloaded = 0
    base_url = "https://assets.gammahosted.com/5s9bbrdpq/_next/static/immutable/chunks/"
    for chunk in all_chunks_to_download:
        cf = ROOT / "_next" / "static" / "immutable" / "chunks" / chunk
        if not cf.exists():
            try:
                import urllib.request
                req = urllib.request.Request(base_url + chunk, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = r.read()
                cf.parent.mkdir(parents=True, exist_ok=True)
                cf.write_bytes(data)
                downloaded += 1
            except:
                pass
    print(f"✅ Downloaded {downloaded} missing chunks from manifest.")

    # Добиваем оставшиеся заглушками (на всякий случай)
    html_clean = pathlib.Path("index.html").read_text(encoding="utf-8")
    referenced_chunks = set(re.findall(r'chunks/([a-zA-Z0-9_-]+\.js)', html_clean))
    stubs = 0
    for chunk in referenced_chunks:
        cf = ROOT / "_next" / "static" / "immutable" / "chunks" / chunk
        if not cf.exists():
            cf.parent.mkdir(parents=True, exist_ok=True)
            cf.write_text("console.log('stub');", encoding="utf-8")
            stubs += 1
    if stubs: print(f"  Created {stubs} stubs for remaining chunks")

    # --- PRIVACY SHIELD ---
    # Список доменов и путей, которые занимаются слежкой/аналитикой
    TRACKERS = [
        "cloudflareinsights.com", "cdn-cgi/rum", "google-analytics.com",
        "googletagmanager.com", "mc.yandex.ru", "top-fwz1.mail.ru",
        "connect.facebook.net", "static.hotjar.com", "script.hotjar.com"
    ]
    
    patched_count = 0
    telemetry_removed = 0

    for filepath in ROOT.rglob("*"):
        if filepath.is_file() and filepath.suffix in [".js", ".css", ".json"]:
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                orig = content

                # 1. Убираем CDN пути
                if "gammahosted.com" in content:
                    content = cdn_regex.sub('', content)

                # 2. Вырезаем телеметрию и скрипты слежки (Total Privacy)
                for tracker in TRACKERS:
                    if tracker in content:
                        # Вырезаем вызовы аналитики (например, fetch('/cdn-cgi/rum'))
                        content = re.sub(r'fetch\([^)]*' + re.escape(tracker) + r'[^)]*\)', 'void(0)', content)
                        content = re.sub(r'sendBeacon\([^)]*' + re.escape(tracker) + r'[^)]*\)', 'void(0)', content)
                        # Вырезаем создание img-пикселей
                        content = re.sub(r'new Image\([^)]*' + re.escape(tracker) + r'[^)]*\)', 'void(0)', content)
                        # Вырезаем текстовые ссылки
                        content = content.replace(tracker, 'about:blank')
                        telemetry_removed += 1
                
                if content != orig:
                    filepath.write_text(content, encoding="utf-8")
                    patched_count += 1
            except Exception:
                pass

    # 3. Чистим телеметрию в HTML
    for tracker in TRACKERS:
        html_str = html_str.replace(tracker, 'about:blank')
    pathlib.Path("index.html").write_text(html_str, encoding="utf-8")
    print(f"✅ Privacy Shield: удалено телеметрии в {telemetry_removed} местах.")
    print(f"✅ Done. Patched {patched_count} files. Created {stubs} stubs.")

    # === АВТО-ЗАГЛУШКИ ===
    print("Creating stubs for missing chunks...")
    html = pathlib.Path("index.html").read_text(encoding="utf-8")
    referenced = set(re.findall(r'/_next/static/immutable/chunks/([a-zA-Z0-9_-]+\.js)', html))
    stubs_created = 0
    for chunk in referenced:
        filepath = ROOT / "_next" / "static" / "immutable" / "chunks" / chunk
        if not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text("// stub for offline mode", encoding="utf-8")
            stubs_created += 1

    print(f"✅ Done. Patched {patched_count} files. Created {stubs_created} stubs.")

if __name__ == "__main__":
    asyncio.run(main())
