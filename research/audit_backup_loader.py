"""Audit fixed host transport/backup sources without importing device code."""
import argparse
import ast
import json
from pathlib import Path
import sys
import zipfile

from lutphoto.io import write_bytes_new
from lutphoto.workercontracts import ROOT, load_sources


def audit(archive):
    pin, sources = load_sources(archive, inventory=ROOT / 'research/upstream-backup-loader.lock.json')
    # Syntax-check only. Transport/USB and the parser's setters are never imported.
    for name, raw in sources.items():
        if name.endswith('.py'): ast.parse(raw, filename=name)
    return {'schema': 'a7c2-backup-loader-source-audit-result/1', 'commit': pin['commit'],
            'archive_sha256': pin['archive_sha256'], 'verified_source_files': len(sources),
            'host_chain': {'temporary_file_limit_bytes': 65536, 'path_command': 15, 'upload_command': 16,
                           'trigger_filename': 'libJit.so', 'staged_readback_before_trigger': True,
                           'request_readback_when_present': True, 'decode_result_before_cleanup': True,
                           'trigger_or_main_result_exception_marks_session_unknown': True,
                           'extras_and_cleanup_are_outside_that_exception_guard': True,
                           'cleanup_requires_expected_contents': True},
            'body_interface': {'normal_USB_serial_hash_bound_outside_BK4': True,
                               'BK4_order_proves_chip_role': False, 'BK4_header_id1_is_body_serial': False,
                               'BK4_checksum_proves_body_identity': False},
            'reviewed_host_chain_proves_Sony_ELF_mapping_BSS_permissions_or_lifetime': False,
            'NOR_CP_boot_loading_is_Jiritsu_plugin_loading_proof': False,
            'archive_Python_imported_or_executed': False, 'camera_operations_enabled': False,
            'camera_loader_abi_verified': False, 'body_binding_verified': False,
            'physical_validation_verified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if Path(args.output).exists() or Path(args.output).is_symlink(): raise ValueError('Output exists')
        result = audit(args.archive)
        write_bytes_new(args.output, (json.dumps(result, indent=2, allow_nan=False) + '\n').encode())
        print('Source audit completed; Sony loader implementation and body proof remain unverified')
        return 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print('Source audit rejected: ' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
