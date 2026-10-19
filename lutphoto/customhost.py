"""N3 host compiler probes. Never loads or executes generated target code."""
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

from .io import write_bytes_new

PROBE = b'static volatile unsigned long value; void _init(void) { value = 7; }\n'
TARGET = 'aarch64-linux-gnu'


def inspect_elf(raw, *, shared):
    from elftools.elf.elffile import ELFFile
    if not raw or len(raw) > 65536:
        raise ValueError('Probe ELF exceeds the 64 KiB bound')
    elf = ELFFile(io.BytesIO(raw))
    if elf.elfclass != 64 or not elf.little_endian or elf['e_machine'] != 'EM_AARCH64' or elf['e_type'] != ('ET_DYN' if shared else 'ET_REL'):
        raise ValueError('Wrong probe ELF architecture/type')
    result = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
              'machine': elf['e_machine'], 'type': elf['e_type']}
    if shared:
        dynamic, symbols = elf.get_section_by_name('.dynamic'), elf.get_section_by_name('.dynsym')
        if dynamic is None or symbols is None:
            raise ValueError('Missing dynamic metadata')
        tags = list(dynamic.iter_tags())
        if not any(t.entry.d_tag == 'DT_INIT' for t in tags) or any(t.entry.d_tag == 'DT_NEEDED' for t in tags):
            raise ValueError('Probe init/dependency contract differs')
        if any(s.name and s['st_shndx'] == 'SHN_UNDEF' for s in symbols.iter_symbols()):
            raise ValueError('Probe has unresolved external symbols')
        count = 0
        for section in elf.iter_sections():
            if section['sh_type'] == 'SHT_RELA':
                for relocation in section.iter_relocations():
                    if relocation['r_info_type'] != 1027 or relocation['r_info_sym'] != 0:
                        raise ValueError('Unsupported probe relocation')
                    count += 1
        result.update(init_present=True, needed_libraries=0, relative_relocations=count)
    return result


def compiler_command(kind):
    if kind == 'zig':
        try:
            version = importlib.metadata.version('ziglang')
        except importlib.metadata.PackageNotFoundError:
            return None
        if version != '0.13.0':
            raise ValueError('Only the audited ziglang==0.13.0 probe is supported')
        return [sys.executable, '-m', 'ziglang']
    found = shutil.which('clang')
    return [found] if found else None


def inspect_host(kind='zig', *, compile_probe=False):
    if kind not in ('zig', 'clang'):
        raise ValueError('Choose zig or clang')
    command = compiler_command(kind)
    report = {'schema': 'a7c2-custom-host-probe/1', 'host_system': platform.system(),
              'host_machine': platform.machine(), 'host_version': platform.mac_ver()[0] if platform.system() == 'Darwin' else platform.release(),
              'compiler': kind, 'available': command is not None, 'target': TARGET,
              'probe_source_sha256': hashlib.sha256(PROBE).hexdigest(),
              'probe': {'attempted': False, 'passed': False},
              'generated_target_executed': False, 'camera_operations_enabled': False,
              'real_worker_build_verified': False, 'camera_install_supported': False}
    if command is None:
        report['probe']['reason'] = 'audited compiler unavailable'
        return report
    version = subprocess.run(command+(['version'] if kind == 'zig' else ['--version']),
                             capture_output=True, timeout=15, check=True)
    report['compiler_version'] = version.stdout.decode('utf-8', errors='replace').splitlines()[0][:200]
    if not compile_probe:
        return report
    with tempfile.TemporaryDirectory(prefix='a7c2-host-probe-') as temporary:
        folder = Path(temporary)
        source, output = folder/'probe.c', folder/'probe.elf'
        source.write_bytes(PROBE)
        flags = ['-target', TARGET, '-fPIC', '-O2', '-ffreestanding', '-fno-builtin',
                 '-fno-stack-protector', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-nostdlib', '-g0']
        if kind == 'zig':
            flags += ['-shared', '-Wl,--strip-debug', '-Wl,--no-undefined', '-Wl,-Bsymbolic', '-Wl,-z,noexecstack']
        else:
            flags += ['-c']
        env = os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR'] = str(folder/'global-cache')
        env['ZIG_LOCAL_CACHE_DIR'] = str(folder/'local-cache')
        try:
            result = subprocess.run(command+(['cc'] if kind == 'zig' else [])+flags+['-o', str(output), str(source)],
                                    env=env, capture_output=True, timeout=45)
        except subprocess.TimeoutExpired:
            report['probe'] = {'attempted': True, 'passed': False, 'reason': 'compile timeout'}
            return report
        report['probe'] = {'attempted': True, 'passed': False, 'returncode': result.returncode,
                           'diagnostic_sha256': hashlib.sha256(result.stderr).hexdigest()}
        if result.returncode:
            report['probe']['reason'] = 'compiler rejected the bounded probe; raw diagnostics omitted'
            return report
        with output.open('rb') as stream:
            raw = stream.read(65537)
        report['probe'].update(inspect_elf(raw, shared=kind == 'zig'), passed=True)
        report['probe']['scope'] = 'neutral shared ELF only' if kind == 'zig' else 'object compilation only; ELF linker not verified'
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', choices=('zig', 'clang'), default='zig')
    parser.add_argument('--compile-probe', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output and (args.output.exists() or args.output.is_symlink()):
            raise ValueError('Output already exists')
        report = inspect_host(args.compiler, compile_probe=args.compile_probe)
        raw = (json.dumps(report, indent=2, allow_nan=False)+'\n').encode()
        if args.output:
            write_bytes_new(args.output, raw)
        print(raw.decode(), end='')
        return 0
    except (ValueError, OSError, ImportError, subprocess.SubprocessError) as e:
        # Do not put compiler commands, temporary paths or raw stderr in shareable output.
        print('STOPPED: host probe '+type(e).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
