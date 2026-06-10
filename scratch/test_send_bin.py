import asyncio
import websockets
import time

async def test_send():
    url = "ws://localhost:8000/api/v1/ws/camera"
    print(f"Connecting to {url}...")
    try:
        async with websockets.connect(url) as ws:
            print("Connected! Sending text hello...")
            await ws.send('{"type":"hello","device":"esp32-cam","mode":"high-fps"}')
            
            print("Sending 50 binary frames (10KB each) at 15 fps...")
            dummy_frame = b"\xff\xd8" + b"\x00" * 10000 + b"\xff\xd9" # 10KB dummy JPEG
            
            for i in range(50):
                t0 = time.time()
                await ws.send(dummy_frame)
                print(f"Sent frame {i+1}/50")
                elapsed = time.time() - t0
                sleep_time = max(0, 0.066 - elapsed)
                await asyncio.sleep(sleep_time)
                
            print("All frames sent successfully! Closing connection...")
    except Exception as e:
        print(f"Error during WS stream test: {e}")

if __name__ == "__main__":
    asyncio.run(test_send())
