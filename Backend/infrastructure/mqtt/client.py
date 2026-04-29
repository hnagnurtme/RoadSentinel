import logging
import json
import ssl
from typing import Any, Optional
import paho.mqtt.client as mqtt
from shared.config import settings

logger = logging.getLogger("roadsentinel.mqtt")

class MQTTClient:
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.enabled = settings.MQTT_ENABLED
        if not self.enabled:
            logger.info("MQTT is disabled by configuration.")
            return

        try:
            # Use callback_api_version to avoid deprecation warnings in paho-mqtt 2.x
            self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
            
            if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
                self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
            
            if settings.MQTT_TLS_ENABLED:
                self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
                
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            # Connect in a non-blocking way if possible, or handle it in a thread
            # For simplicity in this backend, we'll connect and start the loop
            self.client.connect_async(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.client.loop_start()
            logger.info(f"MQTT Client initialized, connecting to {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
        except Exception as e:
            logger.error(f"Failed to initialize MQTT client: {e}")
            self.client = None

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            logger.info("Connected to MQTT Broker successfully")
        else:
            logger.error(f"Failed to connect to MQTT Broker, reason code: {reason_code}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        logger.warning(f"Disconnected from MQTT Broker, reason code: {reason_code}")

    def publish(self, topic_suffix: str, payload: Any, qos: int = 1, retain: bool = False):
        if not self.client or not self.enabled:
            return

        full_topic = f"{settings.MQTT_TOPIC_PREFIX}/{topic_suffix}"
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        
        try:
            result = self.client.publish(full_topic, payload, qos=qos, retain=retain)
            status = result.rc
            if status == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published message to {full_topic}")
            else:
                logger.error(f"Failed to publish message to {full_topic}, status: {status}")
        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

mqtt_client = MQTTClient()
