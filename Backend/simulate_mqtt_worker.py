import time
import json
import logging
import subprocess
import os
import paho.mqtt.client as mqtt
from shared.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mqtt_worker_sim")

class MQTTWorkerSimulator:
    def __init__(self):
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        
        logger.info(f"MQTT Settings: Broker={settings.MQTT_BROKER}, Port={settings.MQTT_PORT}, TLS={settings.MQTT_TLS_ENABLED}, User={settings.MQTT_USERNAME}")
        
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        
        if settings.MQTT_TLS_ENABLED:
            import ssl
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.is_alarm_active = False
        self.alarm_start_time = 0
        self.current_event = None
        self.ALARM_TIMEOUT_SECONDS = 180  # 3 minutes
        self.audio_process = None
        self.audio_file = os.path.join(os.path.dirname(__file__), "alert.mp3")

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            logger.info("Connected to MQTT Broker!")
            # Subscribe to all alert topics
            topic = f"{settings.MQTT_TOPIC_PREFIX}/#"
            self.client.subscribe(topic)
            logger.info(f"Subscribed to {topic}")
        else:
            logger.error(f"Failed to connect, reason code: {reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic
            event = payload.get("event")

            logger.info(f"Received message on {topic}: {event}")

            if event == "normal":
                if self.is_alarm_active:
                    self.stop_alarm("Normal state detected")
            elif event in {"sleeping", "using_phone", "distracted", "drowsy"}:
                if not self.is_alarm_active:
                    self.start_alarm(event)
                else:
                    logger.info(f"Alarm already active for {self.current_event}, updating to {event}")
                    self.current_event = event
                    # We don't reset the 3m timer on event change, or should we?
                    # User said "dung lai sau 3p hoac den khi co normal"
                    # Usually 3m from the FIRST alert.
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def start_alarm(self, event):
        self.is_alarm_active = True
        self.alarm_start_time = time.time()
        self.current_event = event
        logger.info(f"🔔 ALERT! Starting alarm sound for: {event.upper()} 🔔")
        self._play_audio()

    def stop_alarm(self, reason):
        self.is_alarm_active = False
        self.current_event = None
        logger.info(f"🔕 Alarm STOPPED. Reason: {reason} 🔕")
        self._stop_audio()

    def _play_audio(self):
        if self.audio_process is None or self.audio_process.poll() is not None:
            if os.path.exists(self.audio_file):
                logger.info(f"Playing {self.audio_file}")
                # Use afplay on macOS to play the sound
                self.audio_process = subprocess.Popen(["afplay", self.audio_file])
            else:
                logger.warning(f"Audio file not found: {self.audio_file}. Using system beep.")
                print("\a")

    def _stop_audio(self):
        if self.audio_process:
            logger.info("Stopping audio process")
            self.audio_process.terminate()
            self.audio_process = None

    def run(self):
        logger.info(f"Connecting to {settings.MQTT_BROKER}:{settings.MQTT_PORT}...")
        self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
        
        # Start the background loop
        self.client.loop_start()

        try:
            while True:
                if self.is_alarm_active:
                    elapsed = time.time() - self.alarm_start_time
                    if elapsed >= self.ALARM_TIMEOUT_SECONDS:
                        self.stop_alarm("Timeout (3 minutes reached)")
                    else:
                        # Ensure audio keeps playing if it finished but alarm is still active
                        self._play_audio()
                
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping simulator...")
        finally:
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    simulator = MQTTWorkerSimulator()
    simulator.run()
