"""Self-made BK4/MSC vectors; never read a body, archive or USB descriptor."""
import copy
import hashlib
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from lutphoto import bk4, captureidentity as identity, capturemsc
from research.tests.test_capturemsc import model_response


SERIAL = b'\x01\x23\xab\xcd'


def snapshot_with_serial(raw=None, serial=SERIAL, *, index=0):
    raw = bk4.synthetic_snapshot() if raw is None else raw
    rows = [dict(image.records) for image in bk4.parse_snapshot(raw)]
    if serial is None:
        rows[index].pop(identity.SERIAL_PROPERTY, None)
    else:
        rows[index][identity.SERIAL_PROPERTY] = bk4.Property(0, serial, None, len(serial))
    return b'SELF-MADE IDENTITY\0' + bk4.fixture_image(rows[0]) + bytes(16) + bk4.fixture_image(rows[1])


class IdentityTests(unittest.TestCase):
    def decode(self, raw=None, **kw):
        return identity.from_snapshot(snapshot_with_serial() if raw is None else raw, model=identity.MODEL, **kw)

    def test_service_and_msc_encodings_match_without_faking_source(self):
        inquiry = bytes(8) + b'Sony    ' + bytes(20)
        for serial in (SERIAL, b'\0\xa1\xb2\xff', bytes(4), b'\xff'*4, b'1234'):
            with self.subTest(serial=serial):
                observed = self.decode(snapshot_with_serial(serial=serial))
                expected = capturemsc.decode_identity(inquiry, model_response(serial))
                self.assertEqual(observed['serial_sha256'], hashlib.sha256(serial.hex().encode('ascii')).hexdigest())
                self.assertNotEqual(observed['serial_sha256'], hashlib.sha256(serial).hexdigest())
                self.assertNotEqual(observed['serial_source'], expected['serial_source'])
                identity.require_match(observed, expected)
                self.assertEqual(set(observed), {'model', 'serial_source', 'serial_sha256'})

    def test_old_two_field_backup_binding_matches_without_mutation(self):
        observed = self.decode()
        expected = {'model': identity.MODEL, 'serial_sha256': hashlib.sha256(b'0123abcd').hexdigest()}
        before = copy.deepcopy((observed, expected))
        self.assertIsNone(identity.require_match(observed, expected))
        self.assertEqual((observed, expected), before)

    def test_other_body_rejected_and_error_does_not_leak_identity(self):
        observed = self.decode()
        expected = self.decode(snapshot_with_serial(serial=b'\x04\x03\x02\x01'))
        with self.assertRaises(ValueError) as raised:
            identity.require_match(observed, expected)
        for value in (observed['serial_sha256'], expected['serial_sha256'], SERIAL.hex()):
            self.assertNotIn(value, str(raised.exception))

    def test_wrong_model_rejected_before_snapshot_parsing(self):
        for model in (None, True, b'ILCE-7CM2', 'ILCE-7CR', 'ILCE-7CM2 ', 'ILCE-7CM2\0'):
            with patch.object(bk4, 'parse_snapshot', side_effect=AssertionError('No parsing')):
                with self.assertRaises(ValueError): identity.from_snapshot(b'', model=model)

    def test_missing_or_wrong_length_serial_rejected(self):
        for serial in (None, b'', b'123', b'12345'):
            with self.assertRaises(ValueError): self.decode(snapshot_with_serial(serial=serial))

    def test_second_image_is_never_searched_as_fallback(self):
        with self.assertRaises(ValueError): self.decode(snapshot_with_serial(index=1))

    def test_first_image_rule_is_explicit_even_if_second_has_same_property_id(self):
        raw = snapshot_with_serial(snapshot_with_serial(), b'\x99'*4, index=1)
        self.assertEqual(self.decode(raw), self.decode())

    def test_two_complete_valid_images_required(self):
        raw = snapshot_with_serial()
        first, second = bk4.parse_snapshot(raw)
        corrupt = bytearray(raw); corrupt[second.offset + 32] ^= 1
        cases = (raw[:first.offset + first.size], raw[:-1], bytes(corrupt), raw + raw[first.offset:first.offset + first.size])
        for value in cases:
            with self.assertRaises(ValueError): self.decode(value)

    def test_mutable_subclass_and_excessive_input_rejected(self):
        class Bytes(bytes): pass
        for raw in (None, bytearray(), memoryview(b''), Bytes(snapshot_with_serial())):
            with self.assertRaises(ValueError): identity.from_snapshot(raw,model=identity.MODEL)
        raw = snapshot_with_serial()
        with patch.object(bk4, 'MAX_SNAPSHOT', 512):
            with self.assertRaises(ValueError): self.decode(raw)

    def test_malformed_legacy_binding_or_unknown_source_rejected(self):
        observed = self.decode()
        for value in (None, {}, {'model': identity.MODEL}, observed | {'serial_sha256': 'A'*64},
                      observed | {'serial_sha256': True}, observed | {'serial_source': 'usb-product'},
                      observed | {'serial_source': None}, observed | {'model': 'ILCE-7CR'},
                      observed | {'port': [1, 2]}):
            for left, right in ((observed, value), (value, observed)):
                with self.assertRaises(ValueError): identity.require_match(left, right)

    def test_import_does_not_load_device_stack_or_add_cli(self):
        self.assertFalse(hasattr(identity, 'main'))
        code = ('import sys; from lutphoto import captureidentity; '
                'assert not any(n == "usb" or n.startswith("usb.") or n in '
                '("transport", "core", "macfl23.session", "numpy") for n in sys.modules)')
        run = subprocess.run([sys.executable, '-S', '-B', '-c', code],
                             cwd=Path(__file__).resolve().parents[2], capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == '__main__':
    unittest.main()
