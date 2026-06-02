import logging
import json
import ssl
from typing import Any, Optional
import paho.mqtt.client as mqtt
from shared.config import settings

logger = logging.getLogger("roadsentinel.mqtt")

class MQTTClient:
    def __init__(self):
        self.client = None
        self.enabled = settings.MQTT_ENABLED
        if not self.enabled:
            print("[MQTT] Disabled by configuration.", flush=True)
            logger.info("MQTT is disabled by configuration.")
            return

        try:
            self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
            
            if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
                self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
            
            if settings.MQTT_TLS_ENABLED:
                self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
                
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            self.client.connect_async(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.client.loop_start()
            print(f"[MQTT INIT] Connecting asynchronously to {settings.MQTT_BROKER}:{settings.MQTT_PORT}...", flush=True)
            logger.info(f"MQTT Client initialized, connecting to {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
        except Exception as e:
            print(f"[MQTT INIT ERROR] Failed to initialize: {e}", flush=True)
            logger.error(f"Failed to initialize MQTT client: {e}")
            self.client = None

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print("[MQTT STATUS] Connected to MQTT Broker successfully!", flush=True)
            logger.info("Connected to MQTT Broker successfully")
        else:
            print(f"[MQTT STATUS ERROR] Failed to connect to MQTT Broker, reason code: {reason_code}", flush=True)
            logger.error(f"Failed to connect to MQTT Broker, reason code: {reason_code}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        print(f"[MQTT STATUS WARNING] Disconnected from MQTT Broker, reason code: {reason_code}", flush=True)
        logger.warning(f"Disconnected from MQTT Broker, reason code: {reason_code}")

    def publish(self, topic_suffix: str, payload: Any, qos: int = 1, retain: bool = False):
        if not self.client or not self.enabled:
            print(f"[MQTT WARNING] Publish bypassed. Client initialized: {self.client is not None}, Enabled: {self.enabled}", flush=True)
            return

        if topic_suffix.startswith("roadsentinel/"):
            full_topic = topic_suffix
        else:
            full_topic = f"{settings.MQTT_TOPIC_PREFIX}/{topic_suffix}"
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        
        try:
            result = self.client.publish(full_topic, payload, qos=qos, retain=retain)
            status = result.rc
            if status == mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT SUCCESS] Published message to {full_topic} successfully: {payload}", flush=True)
                logger.info(f"Published message to {full_topic} successfully: {payload}")
            else:
                print(f"[MQTT ERROR] Failed to publish message to {full_topic}, status: {status}", flush=True)
                logger.error(f"Failed to publish message to {full_topic}, status: {status}")
        except Exception as e:
            print(f"[MQTT EXCEPTION] Error publishing to MQTT: {e}", flush=True)
            logger.error(f"Error publishing to MQTT: {e}")

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

mqtt_client = MQTTClient()
