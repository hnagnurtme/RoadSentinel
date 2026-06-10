import asyncio
import sys

async def test_ws(url):
    try:
        import websockets
    except ImportError:
        print("websockets package not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
        import websockets

    print(f"Testing connection to {url}...")
    try:
        async with websockets.connect(url, open_timeout=5) as ws:
            print(f"SUCCESS! Connected to {url}")
            await ws.close()
    except Exception as e:
        print(f"FAILED to connect to {url}: {e}")

async def main():
    # Test both endpoints
    await test_ws("ws://localhost:8000/api/v1/ws/camera")
    await test_ws("ws://localhost:8000/ws/camera")

if __name__ == "__main__":
    asyncio.run(main())
