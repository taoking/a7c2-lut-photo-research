"""Read-only service snapshot identity, with no USB or session capability.

QAQLeonard 3.0.3 service_identity and ma1co BK4 provenance: round 75 and
ACKNOWLEDGEMENTS.md. The first valid image is an upstream positional rule,
not independent proof of AP/CP roles, freshness or physical body identity.
"""
import hashlib
import re

from . import bk4

MODEL = 'ILCE-7CM2'
SERIAL_PROPERTY = 0x00e70003
SERVICE_SOURCE = 'sony-service-bk4-00e70003'
MSC_SOURCE = 'sony-get-camera-info'


def from_snapshot(raw, *, model):
    """Decode a complete dual-image snapshot; never search other images for ID.

    The caller must establish the model from its owned device observation.
    This pure decoder cannot establish where the supplied bytes came from.
    """
    if type(model) is not str or model != MODEL:
        raise ValueError('Supported observed model required')
    if type(raw) is not bytes:
        raise ValueError('Immutable complete snapshot required')
    images = bk4.parse_snapshot(raw)
    serial = images[0].records.get(SERIAL_PROPERTY)
    if serial is None or len(serial.data) != 4:
        raise ValueError('First snapshot image lacks the four-byte identity property')
    # Legacy getCameraInfo hashes lowercase hex text, including leading zeros.
    # Hashing raw bytes, uppercasing or converting to an integer breaks binding.
    return {'model': model, 'serial_source': SERVICE_SOURCE,
            'serial_sha256': hashlib.sha256(serial.data.hex().encode('ascii')).hexdigest()}


def require_match(observed, expected):
    """Compare explicit identities without relabelling their observation source.

    Accept the old upstream two-field binding or this project's explicit source
    field. Callers must separately check location, version and full programs.
    No existing backup is loaded, modified or adopted by this function.
    """
    for value in (observed, expected):
        if (type(value) is not dict
                or set(value) not in ({'model', 'serial_sha256'}, {'model', 'serial_sha256', 'serial_source'})
                or type(value['model']) is not str or value['model'] != MODEL
                or type(value['serial_sha256']) is not str
                or re.fullmatch('[0-9a-f]{64}', value['serial_sha256']) is None
                or 'serial_source' in value and (type(value['serial_source']) is not str
                    or value['serial_source'] not in (MSC_SOURCE, SERVICE_SOURCE))):
            raise ValueError('Explicit supported identity binding required')
    if observed['serial_sha256'] != expected['serial_sha256']:
        raise ValueError('Snapshot and expected body identities differ')
