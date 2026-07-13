#!/bin/bash
cd frontend
npm run dev > vite.log 2>&1 &
VITE_PID=$!
cd ..

echo "Waiting for Vite..."
sleep 5
echo "Running Playwright..."

cat << 'PYEOF' > verify_t42_ui.py
from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-web-security'])
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        
        page.on("requestfailed", lambda req: print(f"Failed URL: {req.url}"))
        
        print("Cargando pagina Ejecucion Detalle...")
        page.goto("http://localhost:5173/ejecucion/detalle")
        
        time.sleep(3)
        page.screenshot(path="Docs/evidencia/T-42/debug_screen.png")
        browser.close()

if __name__ == "__main__":
    run()
PYEOF

source backend/venv/bin/activate
python verify_t42_ui.py

kill $VITE_PID || true
