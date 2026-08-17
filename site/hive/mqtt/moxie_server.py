'''
MOXIE SERVER - Primary service handler for Moxie
'''
import concurrent
import paho.mqtt.client as mqtt
import json
import time
import re
import logging
import base64
import ssl
import threading
from datetime import datetime, timezone
from .ai_factory import set_openai_key, configure_ai
from .robot_credentials import RobotCredentials
from .robot_data import RobotData
from .moxie_remote_chat import RemoteChat
from .protos.embodied.logging.Log_pb2 import ProtoSubscribe
from .protos.embodied.logging.Cloud2_pb2 import ServiceConfiguration2
from .protos.embodied.wifiapp.QRCommands_pb2 import StartPairingQR
from .zmq_stt_handler import STTHandler
from ..models import HiveConfiguration

_BASIC_FORMAT = '{1}'
_MOXIE_SERVICE_INSTANCE = None
# OpenMoxie doesn't support any, but providing a dummy token can unblock some Moxie actions like OTA download
_PROVIDE_HTTP_TOKENS=False
# As this key is expressly shared and thus usably by any clients, this turns it off
_SHARE_GOOGLE_KEY=True

def now_ms():
    return time.time_ns() // 1_000_000

logger = logging.getLogger(__name__)

'''
MoxieServer provides cloud services to client Moxies.  Because this is MQTT, services are
provided using TOPICS.  With the exception of the ZMQ, all topics communicate using JSON
message paylods.  Moxie Server notably:
- Subscribes to the event, state, and log topics produced by ALL moxie devices
- Sends responses to device command topics to provide services and control Moxies
- Listens to system topics from mosquitto MQTT to detect devices connecting and disconnecting

As implemented there is a singleton MoxieService created using the instance creation method
near the end of this file.  It connects to the MQTT broker, which cooredinates all exchanges
of topics between Moxie's and MoxieServer.
'''
class MoxieServer:
    _robot : any
    _remote_chat : any
    _client : any
    _mqtt_client_id: str
    _mqtt_project_id: str
    _cert_required: bool
    _topic_handlers: dict
    _zmq_handlers: dict
    _client_metrics: dict
    _google_service_account: str
    _robot_data: RobotData
    _remote_chat: RemoteChat
    def __init__(self, robot, rbdata, project_id, mqtt_host, mqtt_port, cert_required=True):
        self._robot = robot
        self._robot_data = rbdata
        self._mqtt_project_id = project_id
        self._mqtt_endpoint = mqtt_host
        self._port = mqtt_port
        self._cert_required = cert_required
        self._mqtt_client_id = _BASIC_FORMAT.format(self._mqtt_project_id, self._robot.device_id)
        logger.info(f"Creating client with id: {self._mqtt_client_id}")
        # Pin the legacy callback shape explicitly when using paho-mqtt 2.x.  Without
        # this, a future callback API default can add parameters to on_connect and
        # silently stop all subscriptions from being installed.
        if hasattr(mqtt, "CallbackAPIVersion"):
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=self._mqtt_client_id,
                transport="tcp",
            )
        else:
            self._client = mqtt.Client(client_id=self._mqtt_client_id, transport="tcp")
        if self._cert_required:
            self._client.tls_set()
        else:
            self._client.tls_set(cert_reqs=ssl.CERT_NONE)
        self._client.on_connect = self.on_connect
        self._client.on_disconnect = self.on_disconnect
        self._client.on_connect_fail = self.on_connect_fail
        self._client.on_message = self.on_message
        self._topic_handlers = None
        self._connect_handlers = []
        self._remote_chat = RemoteChat(self)
        self._zmq_handlers = {}
        self._client_metrics = {}
        self._connect_pattern = re.compile(r"connected from (.*?) as (d_[a-z0-9_-]+)", re.IGNORECASE)
        self._disconnect_pattern = re.compile(
            r"Client (d_[a-z0-9_-]+) (?:closed its connection|disconnected|has exceeded timeout)",
            re.IGNORECASE,
        )
        self._worker_queue = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self._device_init_lock = threading.Lock()
        self._device_init_futures = {}
        self._status_lock = threading.Lock()
        self._status = {
            "broker_connected": False,
            "started_at": self._timestamp(),
            "last_broker_connect": None,
            "last_broker_disconnect": None,
            "last_connect_error": None,
            "last_message": None,
            "last_message_topic": None,
            "last_device_activity": None,
            "last_device_id": None,
            "last_processing_error": None,
            "last_processing_error_at": None,
            "last_wake_command": None,
            "last_wake_device": None,
            "publish_failures": 0,
        }
        self.update_from_database()

    @staticmethod
    def _timestamp():
        return datetime.now(timezone.utc).isoformat()

    def _update_status(self, **values):
        with self._status_lock:
            self._status.update(values)

    def service_status(self):
        """Return a JSON-safe diagnostic snapshot without credentials or payloads."""
        with self._status_lock:
            result = dict(self._status)
        result.update({
            "mqtt_host": self._mqtt_endpoint,
            "mqtt_port": self._port,
            "tls_verify": self._cert_required,
            "connected_devices": self._robot_data.connected_list(),
            "devices": self._robot_data.connected_details(),
        })
        return result

    def _submit_worker(self, function, *args):
        """Submit background work and surface exceptions that Futures otherwise hide."""
        future = self._worker_queue.submit(function, *args)
        task_name = getattr(function, "__name__", str(function))

        def report_failure(completed):
            if completed.cancelled():
                return
            exception = completed.exception()
            if exception:
                logger.error(
                    "Background MQTT task %s failed",
                    task_name,
                    exc_info=(type(exception), exception, exception.__traceback__),
                )
                self._update_status(
                    last_processing_error=f"{task_name}: {exception}",
                    last_processing_error_at=self._timestamp(),
                )

        future.add_done_callback(report_failure)
        return future

    # Connect to the broker - the jwt stuff left in place, but isn't required
    def connect(self, start = False):
        jwt_token = self._robot.create_jwt(self._mqtt_project_id)
        self._client.username_pw_set(username='unknown', password=jwt_token)
        logger.info(f"Connecting to MQTT broker at {self._mqtt_endpoint}:{self._port}")
        # connect_async lets paho's network loop retry if the broker starts after
        # Django (or temporarily disappears).  The previous synchronous attempt
        # killed the supervisor thread permanently on the first failure.
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.connect_async(self._mqtt_endpoint, self._port, 60)
        if start:
            self.start()

    # For any external monitoring of connections to the broker
    def add_connect_handler(self, callback):
        self._connect_handlers.append(callback)

    # Bind a listener to a specific proto on the ZMQ topic
    def add_zmq_handler(self, protoname, callback):
        self._zmq_handlers[protoname] = callback

    # This is left-over client code, supervisor doesn't get a config
    def add_config_handler(self, callback):
        self.add_command_handler("config", callback)

    # This is left-over client code, supervisor doesn't rx commands
    def add_command_handler(self, topic, callback):
        if not self._topic_handlers:
            self._topic_handlers = dict()
            self._topic_handlers[topic] = [ callback ]
        elif topic in self._topic_handlers:
            self._topic_handlers[topic].append(callback)
        else:
            self._topic_handlers[topic] = [ callback ]

    # Callback when we connect to the mqtt broker, subscribe to everything we care about
    def on_connect(self, client, userdata, flags, rc):
        rc_value = int(rc)
        if rc_value != 0:
            message = mqtt.connack_string(rc_value)
            logger.error(f"MQTT connection rejected ({rc_value}): {message}")
            self._update_status(broker_connected=False, last_connect_error=message)
            return
        logger.info(f"Connected to MQTT broker at {self._mqtt_endpoint}:{self._port}")
        self._update_status(
            broker_connected=True,
            last_broker_connect=self._timestamp(),
            last_connect_error=None,
        )
        # The only two supported in IOT - commands for a wildcard of commands, config for our robot configuration
        client.subscribe('/devices/+/events/#')
        client.subscribe('/devices/+/state')
        # Subscriptions to monitor clients and broker logs
        client.subscribe('$SYS/broker/clients/#')
        client.subscribe('$SYS/broker/log/#')
        for ch in self._connect_handlers:
            ch(self, rc) 

    def on_connect_fail(self, client, userdata):
        message = f"Unable to reach {self._mqtt_endpoint}:{self._port}; retrying"
        logger.warning(message)
        self._update_status(broker_connected=False, last_connect_error=message)

    def on_disconnect(self, client, userdata, rc):
        rc_value = int(rc)
        message = None if rc_value == 0 else f"Unexpected disconnect (code {rc_value}); retrying"
        if message:
            logger.warning(message)
        else:
            logger.info("Disconnected from MQTT broker")
        self._update_status(
            broker_connected=False,
            last_broker_disconnect=self._timestamp(),
            last_connect_error=message,
        )

    # Entry point for ALL incoming messages, extract params about source and route
    def on_message(self, client, userdata, msg):
        try:
            self._update_status(last_message=self._timestamp(), last_message_topic=msg.topic)
            dec = msg.topic.split('/')
            if len(dec) >= 4 and dec[0] == "" and dec[1] == "devices":
                fromdevice = dec[2]
                basetype = dec[3]
                self._update_status(
                    last_device_activity=self._timestamp(),
                    last_device_id=fromdevice,
                )
                if basetype == "events" and len(dec) >= 5:
                    self.on_device_event(fromdevice, dec[4], msg)
                elif basetype == "state":
                    self.on_device_state(fromdevice, msg)
                else:
                    logger.debug(f"Rx unknown device topic: {msg.topic}")
            elif len(dec) >= 4 and dec[:3] == ["$SYS", "broker", "clients"]:
                self.on_client_metrics(dec[3], msg)
            elif len(dec) >= 4 and dec[:3] == ["$SYS", "broker", "log"]:
                self.on_sys_log_message(dec[3], msg)
            else:
                logger.debug(f"Rx unknown topic: {msg.topic}")
        except Exception:
            logger.exception("Error handling MQTT message on topic %s", msg.topic)
    

    # Handle messages FROM mosquitto syslog topic, looking for connect/disconnects
    def on_sys_log_message(self, basetype, msg):
        if basetype == "N": # Notifications
            line = msg.payload.decode('utf-8')
            match = self._connect_pattern.search(line)
            match2 = None if match else self._disconnect_pattern.search(line)
            if match:
                self.check_device_connect(match.group(2), match.group(1))
            elif match2:
                self._submit_worker(self.on_device_connect, match2.group(1), False)

    # Handles metrics from mosquitto
    def on_client_metrics(self, basetype, msg):
        try:
            self._client_metrics[basetype] = int(msg.payload.decode('utf-8'))
        except ValueError:
            logger.debug("Ignoring non-integer broker metric %s", msg.topic)

    # ALL EVENTS FROM-DEVICE ARRIVE HERE
    def on_device_event(self, device_id, eventname, msg):
        # Check the connection in case we missed this device connecting
        initializing = self.check_device_connect(device_id, "Event")
        if initializing:
            # MQTT callbacks and the DB initializer use different worker threads.
            # Defer this message until initialization completes to avoid serving
            # defaults or querying a MoxieDevice row that does not exist yet.
            initializing.add_done_callback(
                lambda future: self.on_device_event(device_id, eventname, msg)
                if future.result() else None
            )
            return
        if eventname == "remote-chat" or eventname == "remote-chat-staging":
            rcr = json.loads(msg.payload)
            if rcr.get('backend') == "data" and rcr.get('query',{}).get('query') == "modules":
                # REMOTE MODULES REQUEST
                req_id = rcr.get('event_id')
                # Let the remote chat module provide the modules data
                rc_modules = self._remote_chat.get_modules_info()
                logger.debug(f"Tx modules to: remote_chat: {rc_modules}")
                self.send_command_to_bot_json(device_id, 'remote_chat', { 'command': 'remote_chat', 'result': 0, 'event_id': req_id, 'query_data': rc_modules} )
            elif rcr.get('backend') == "router":
                # REMOTE CHAT CONVERSATION ENDPOINT
                self._remote_chat.handle_request(device_id, rcr, self._robot_data.get_volley_data(device_id))
        elif eventname == "client-service-activity-log":
            # Topic originally for reporting activities, but extended with subtopics
            csa = json.loads(msg.payload)
            if csa.get("subtopic") == "query":
                if csa.get("query") == "schedule":
                    # SCHEDULE REQUEST - Robot asking what schedule to follow this session
                    logger.debug("Rx Schedule request.")
                    req_id = csa.get('request_id')
                    self._submit_worker(self.provide_schedule, req_id, device_id)
                elif csa.get("query") == "mentor_behaviors":
                    # MENTOR BEHAVIOR REQUEST - Robot asking what user has done before
                    logger.debug("Rx MBH request.")
                    req_id = csa.get('request_id')
                    self._submit_worker(self.provide_mentor_behaviors, req_id, device_id)
                elif csa.get("query") == "license":
                    # ROBOT IS ASKING FOR ANY LICENSES IT CAN USE (e.g. google speech)
                    req_id = csa.get('request_id')
                    if _SHARE_GOOGLE_KEY and self._google_service_account:
                        logger.debug(f"Providing google speech credentials to {device_id}")
                        self.send_command_to_bot_json(device_id, 'query_result', 
                                                    { 'command': 'query_result', 'request_id': req_id, 'query': 'license',
                                                    'license_values': [ 
                                                        { 'id': 'google_speech', 'license': self._google_service_account}
                                                        ]
                                                        })
            elif 'mentor_behavior' in csa:
                # MENTOR BEHAVIOR REPORT - Robot informing what user has done
                self._submit_worker(self.ingest_mentor_behavior, device_id, csa['mentor_behavior'])
            elif csa.get("subtopic") == "telehealth":
                # ROBOT TELEHEALTH INTERFACE
                logger.info(f'Rx TELEHEALTH: {csa.get("message")}')
                th_state = csa["message"].get("state")
                if th_state:
                    self._robot_data.put_puppet_state(device_id, th_state)
        elif _PROVIDE_HTTP_TOKENS and eventname=="client-service-http-token":
            # There are no services to use them, but if enabled we respond with a 'notoken' access token
            logger.info(f"Sending HTTP TOKEN to device {device_id}")
            self.send_command_to_bot_json(device_id, 'http_token',
                                            { 'command': 'http_token', 'http_token': 'notoken'})
        elif eventname == "zmq":
            # ZMQ BRIDGE INCOMING
            colon_index = msg.payload.find(b':')
            protoname = msg.payload[:colon_index].decode('utf-8')
            protodata = msg.payload[colon_index + 1:]
            handler = self._zmq_handlers.get(protoname)
            if handler:
                handler.handle_zmq(device_id, protoname, protodata)
            # else:
            #     logger.debug(f'Unhandled RX ProtoBuf {protoname} over ZMQ Bridge')
        elif eventname == "device-logs":
            # These are per-client log messages
            logrec = json.loads(msg.payload)
            logger.debug(f'{device_id}[{logrec.get("tag")}] - {logrec.get("message")}')

    # NOTE: Called from worker thread pool
    def provide_schedule(self, req_id, device_id):
        schedule = self._robot_data.get_schedule(device_id)
        self.send_command_to_bot_json(device_id, 'query_result', { 'command': 'query_result', 'query': 'schedule', 'request_id': req_id, 'schedule': schedule} )

    # NOTE: Called from worker thread pool
    def ingest_mentor_behavior(self, device_id, mbh):
        self._robot_data.add_mbh(device_id, mbh)

    # NOTE: Called from worker thread pool
    def ingest_robot_state(self, device_id, statedata):
        self._robot_data.put_state(device_id, statedata)

    # NOTE: Called from worker thread pool
    def provide_mentor_behaviors(self, req_id, device_id):
        mbh = self._robot_data.get_mbh(device_id)
        logger.info(f'Providing {len(mbh)} MBH records to {device_id}')
        self.send_command_to_bot_json(device_id, 'query_result', { 'command': 'query_result', 'query': 'mentor_behaviors', 'request_id': req_id, 'mentor_behaviors': mbh} )

    # NOTE: Called from worker thread pool
    def on_device_connect(self, device_id, connected, ip_addr=None):
        if connected:
            logger.info(f'Moxie CONNECTED {device_id} from {ip_addr}')
            try:
                self._robot_data.db_connect(device_id)
                # Sleep to avoid sending sub/config before client is ready
                time.sleep(1.0)
                self.send_config_to_bot_json(device_id, self._robot_data.get_config(device_id))
                # subscribe to ZMQ STT
                sub = ProtoSubscribe()
                sub.protos.append('embodied.perception.audio.zmqSTTRequest')
                sub.timestamp = now_ms()
                logger.debug('Subscribed to ZMQ STT')
                self.send_zmq_to_bot(device_id, sub)
                return True
            except Exception:
                # Do not leave an empty cache entry marking a failed initialization
                # as online forever. A later state/event can now retry it.
                self._robot_data.abort_connect(device_id)
                logger.exception("Failed to initialize connected Moxie %s", device_id)
                return False
        else:
            self._robot_data.db_release(device_id)
            logger.info(f'Moxie DISCONNECTED {device_id}')
            return True

    # Fallback, we missed the connect message but robot is connected
    def check_device_connect(self, device_id, info="Missing"):
        new_future = None
        with self._device_init_lock:
            current = self._device_init_futures.get(device_id)
            if current and not current.done():
                return current
            if self._robot_data.connect_init_needed(device_id):
                logger.info(f"Unconnected robot {device_id} location {info}. Connecting now.")
                new_future = self._submit_worker(self.on_device_connect, device_id, True, info)
                self._device_init_futures[device_id] = new_future
        # Register outside the lock: add_done_callback executes immediately when a
        # fast failure already completed, and the callback takes the same lock.
        if new_future:
            new_future.add_done_callback(lambda completed: self._forget_init_future(device_id, completed))
            return new_future
        return None

    def _forget_init_future(self, device_id, completed):
        with self._device_init_lock:
            if self._device_init_futures.get(device_id) is completed:
                del self._device_init_futures[device_id]

    # Moxie reporting its own state information
    def on_device_state(self, device_id, msg):
        logger.debug(f"Rx STATE topic for device {device_id}")
        initializing = self.check_device_connect(device_id, "State")
        if initializing:
            initializing.add_done_callback(
                lambda future: self.on_device_state(device_id, msg) if future.result() else None
            )
            return
        self._submit_worker(self.ingest_robot_state, device_id, json.loads(msg.payload))

    # Callback when a moxie config has changed and may need to be provided
    def handle_config_updated(self, device):
        # Update if connected
        if self._robot_data.config_update_live(device):
            logger.info(f'Moxie device {device.device_id} updated, sending updated config.')
            self.send_config_to_bot_json(device.device_id, self._robot_data.get_config(device.device_id))
        else:
            logger.info(f'Moxie device {device.device_id} updated, but device offline')

    # For Robots using wake_button_enabled, wake them from screen off
    def send_wakeup_to_bot(self, device_id):
        if self._robot_data.device_online(device_id):
            result = self.send_command_to_bot_json(device_id, 'wakeup', {'command': 'wakeup'})
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self._update_status(
                    last_wake_command=self._timestamp(),
                    last_wake_device=device_id,
                )
                logger.info("Wake command queued for %s", device_id)
                return True
        return False

    # Send Moxie its configuration data
    def send_config_to_bot_json(self, device_id, payload: dict):
        return self._publish(f"/devices/{device_id}/config", json.dumps(payload))

    # Send a Command (JSON) to Moxie
    def send_command_to_bot_json(self, device_id, command, payload: dict):
        return self._publish(f"/devices/{device_id}/commands/{command}", json.dumps(payload))

    # Send a binary ZMQ message to Moxie
    def send_zmq_to_bot(self, device_id, msgobject):
        payload = (msgobject.DESCRIPTOR.full_name + ":").encode('utf-8') + msgobject.SerializeToString()
        return self._publish(f"/devices/{device_id}/commands/zmq", payload)

    def _publish(self, topic, payload):
        result = self._client.publish(topic, payload=payload)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("MQTT publish failed for %s: %s", topic, mqtt.error_string(result.rc))
            with self._status_lock:
                self._status["publish_failures"] += 1
        return result

    # Send Telehealth message to Moxie
    def send_telehealth(self, device_id, msg):
        self.send_command_to_bot_json(device_id, "telehealth", payload={ "command": "telehealth", "message": msg })

    # Send Telehealth - PLAY message to Moxie
    def send_telehealth_speech(self, device_id, speech:str, mood:str, intensity:float):
        markup = self._remote_chat.make_markup(speech, (mood, intensity))
        tmsg = { "action": "PLAY_OUTPUT", "output": { "text": speech, "markup": markup } }
        self.send_telehealth(device_id, tmsg)

    # Send Telehealth - INTERRUPT Moxie speaking
    def send_telehealth_interrupt(self, device_id):
        tmsg = { "action": "INTERRUPT" }
        self.send_telehealth(device_id, tmsg)

    def long_topic(self, topic_name):
        return "/devices/" + self._robot.device_id + "/events/" + topic_name

    def publish_as_json(self, topic, payload: dict):
        self._client.publish(self.long_topic(topic), payload=json.dumps(payload))

    def publish_canned(self, canned_data):
        if "topic" in canned_data:
            self.publish_as_json(canned_data["topic"], payload=canned_data["payload"])
        elif "subtopic" in canned_data["payload"]:
            self.publish_as_json("client-service-activity-log", payload=canned_data["payload"])
        else:
            logger.warning(f"Warning! Invalid canned message: {canned_data}")

    # Print out client metrics, called periodically in the background
    def print_metrics(self):
        logger.info(f"Client Metrics: {self._client_metrics}")

    # Start client connection loop
    def start(self):
        self._client.loop_start()

    # Stop client connection loop
    def stop(self):
        self._client.loop_stop()

    # Get's a chat session object for use in the web chat
    def get_web_session_for_module(self, device_id, module_id, content_id):
        sess = self._remote_chat.get_web_session_for_module(device_id, module_id, content_id)
        sess.set_auto_history(True)
        return sess
    
    # Check global commands for interactive web
    def get_web_session_global_response(self, speech):
        return self._remote_chat.get_web_session_global_response(speech)
    
    # Accessor to remote chat
    def remote_chat(self):
        return self._remote_chat

    # Accessor to robot data
    def robot_data(self):
        return self._robot_data

    # Reload records from the database
    def update_from_database(self):
        hive_config = HiveConfiguration.objects.filter(name="default").first()
        set_openai_key(hive_config.openai_api_key if hive_config else None)
        if hive_config:
            configure_ai(hive_config.chat_provider, hive_config.chat_base_url, hive_config.chat_model,
                         hive_config.stt_provider, hive_config.local_stt_model)
        self._google_service_account = hive_config.google_api_key if hive_config else None
        self._remote_chat.update_from_database()

    # Get the endppint / moxie relocate QR code to move a Moxie to this service
    def get_endpoint_qr_data(self):
        hiveconfig = HiveConfiguration.objects.filter(name="default").first()
        scfg = ServiceConfiguration2()
        scfg.gcp_project = self._mqtt_project_id
        scfg.mqtt_host = hiveconfig.external_host if hiveconfig and hiveconfig.external_host else self._mqtt_endpoint
        scfg.override_port = self._port
        scfg.disable_verify = not self._cert_required
        # Serialize to bytes, then bytes to base64 string
        scfg_base64 = base64.b64encode(scfg.SerializeToString()).decode('utf-8')
        # Now make QR debug object, just in JSON
        qr = { "debug": { "command": "om", "param": scfg_base64}}
        return json.dumps(qr)

    # Get a QR code for wifi credentials to show to Moxie
    def get_wifi_qr_data(self, ssid, password, band_id, hidden):
        wificreds = StartPairingQR()
        wificreds.wifi_only = True
        wificreds.ssid = ssid
        wificreds.password = password
        wificreds.is_hidden = hidden
        wificreds.band_select = int(band_id)
        # Pairing codes have two char header PA followed by a base64 coded serialized pairing proto
        wifi_base64 = "PA" + base64.b64encode(wificreds.SerializeToString()).decode('utf-8')
        return wifi_base64

# Instance method, disconnect and destroy
def cleanup_instance():
    global _MOXIE_SERVICE_INSTANCE
    if _MOXIE_SERVICE_INSTANCE:
        _MOXIE_SERVICE_INSTANCE._client.disconnect()
        _MOXIE_SERVICE_INSTANCE = None

# Instance method, accessor
def get_instance():
    global _MOXIE_SERVICE_INSTANCE
    return _MOXIE_SERVICE_INSTANCE

# Instance method, create singleton service
def create_service_instance(project_id, host, port, cert_required=True):
    global _MOXIE_SERVICE_INSTANCE
    if not _MOXIE_SERVICE_INSTANCE:
        creds = RobotCredentials(True)
        rbdata = RobotData()
        _MOXIE_SERVICE_INSTANCE = MoxieServer(creds, rbdata, project_id, host, port, cert_required)
        _MOXIE_SERVICE_INSTANCE.add_zmq_handler('embodied.perception.audio.zmqSTTRequest', STTHandler(_MOXIE_SERVICE_INSTANCE))
        _MOXIE_SERVICE_INSTANCE.connect(start=True)
    
    return _MOXIE_SERVICE_INSTANCE
    
if __name__ == "__main__":
    c = create_service_instance("openmoxie", "duranaki.com", 8883)
    while True:
        time.sleep(60)
        c.print_metrics()
