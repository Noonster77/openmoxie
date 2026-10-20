"""Wire helpers for Moxie's built-in image-captioning gate.

Protocol field numbers and the safe event-driven arming sequence are adapted
from AppleMelonOrange/sidecar-for-openmoxie (MIT).  Encoding these two tiny
proto3 messages directly keeps OpenMoxie's protobuf 4.x runtime compatible
with the Sidecar research, whose generated files currently require 7.x.
"""

LOGGING_NAME = b'embodied.logging.LoggingStateUpdate:'
ENABLE_NAME = b'embodied.robotbrain.EnableICModule:'
POWERSTATE_PREFIX = b'embodied.power.PowerStatePB:'
POWER_RUNNING = 3


def _varint(value):
    value = int(value)
    output = bytearray()
    while value > 0x7f:
        output.append((value & 0x7f) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)


def logging_state_payload(timestamp_ms, enabled=True):
    policy = 2 if enabled else 1
    # state=1, timestamp=4 (uint64), upload_policy=7
    body = b'\x08' + _varint(policy) + b'\x20' + _varint(timestamp_ms)
    body += b'\x38' + _varint(policy)
    return LOGGING_NAME + body


def enable_ic_payload(timestamp_ms, enabled=True):
    # timestamp=1 (uint64), run=2 (bool). Proto3 omits false/default fields.
    body = b'\x08' + _varint(timestamp_ms)
    if enabled:
        body += b'\x10\x01'
    return ENABLE_NAME + body


def vision_gate_payloads(timestamp_ms, enabled=True):
    return (
        logging_state_payload(timestamp_ms, enabled),
        enable_ic_payload(timestamp_ms, enabled),
    )


def parse_power_state(payload):
    """Return PowerStatePB.state (field 2), or None for unrelated/bad data."""
    try:
        if not payload.startswith(POWERSTATE_PREFIX):
            return None
        data = payload[len(POWERSTATE_PREFIX):]
        offset = 0
        while offset < len(data):
            tag = data[offset]
            offset += 1
            field, wire_type = tag >> 3, tag & 7
            if wire_type != 0:
                return None
            value = 0
            shift = 0
            while offset < len(data):
                byte = data[offset]
                offset += 1
                value |= (byte & 0x7f) << shift
                if not byte & 0x80:
                    break
                shift += 7
                if shift > 63:
                    return None
            else:
                return None
            if field == 2:
                return value
        return None
    except (AttributeError, IndexError, TypeError):
        return None
