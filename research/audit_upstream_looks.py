"""Verify the pinned v2.1 source package and compare the FL23 baseline.

Offline source audit only: no extraction, network, firmware execution or USB.
The separate research pin does not replace the installer's upstream lock.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

from lutphoto.io import write_bytes_new

ROOT=Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(archive, baseline_source):
    pin=json.loads((ROOT/'research/upstream-looktool.lock.json').read_text())
    if pin['schema']!='a7c2-upstream-looktool-audit/1' or pin['camera_integration_enabled'] is not False:
        raise ValueError('Expected the audit-only source pin')
    lock_raw=(ROOT/'upstream.lock.json').read_bytes()
    if sha(lock_raw)!=pin['baseline_lock_sha256']:
        raise ValueError('Installer baseline lock differs; review independently')
    baseline=json.loads(lock_raw)
    if baseline['commit']!=pin['baseline_commit']:
        raise ValueError('Baseline commit differs')
    if archive.stat().st_size!=pin['archive_bytes']:
        raise ValueError('Source package size differs')
    raw=archive.read_bytes()
    if sha(raw)!=pin['archive_sha256']:
        raise ValueError('Source package fingerprint differs')
    prefix='a7c2-tools-2.1/'
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        names=package.namelist()
        if len(names)!=len(set(names)) or any(
                not n.startswith(prefix) or '..' in Path(n).parts or Path(n).is_absolute() for n in names):
            raise ValueError('Unexpected or duplicate source package member')
        if sum(i.file_size for i in package.infolist())>20_000_000:
            raise ValueError('Source package exceeds the audit limit')
        for name,expected in pin['files'].items():
            data=package.read(prefix+name)
            blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if len(data)!=expected['bytes'] or sha(data)!=expected['sha256'] or blob!=expected['git_blob_sha1']:
                raise ValueError('Pinned source member differs: '+name)
        comparison={k:[] for k in ('byte_identical','line_ending_only','substantive_or_launcher','absent_at_same_relative_path')}
        for name,expected in baseline['files'].items():
            relative=Path(name).relative_to('a7c2_fl23_preview')
            source=baseline_source/relative
            if source.is_symlink() or source.stat().st_size>2_000_000:
                raise ValueError('Unexpected baseline source member: '+str(relative))
            original=source.read_bytes()
            if sha(original)!=expected:
                raise ValueError('Baseline source fingerprint differs: '+str(relative))
            member=prefix+'src/fl23/'+relative.as_posix()
            if member not in names:
                kind='absent_at_same_relative_path'
            else:
                current=package.read(member)
                if current==original:kind='byte_identical'
                elif current.replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'):kind='line_ending_only'
                else:kind='substantive_or_launcher'
            comparison[kind].append(relative.as_posix())
    return {
        'schema':'a7c2-upstream-looktool-audit-result/1',
        'release':{'tag':pin['tag'],'commit':pin['commit'],'published_at':pin['published_at']},
        'archive_sha256':pin['archive_sha256'],'verified_pinned_source_files':len(pin['files']),
        'baseline_commit':baseline['commit'],'verified_old_source_files':len(baseline['files']),
        'fl23_source_comparison':comparison,'comparison_counts':{k:len(v) for k,v in comparison.items()},
        'limits':['Source identity and file differences only; capability review is documented separately',
                  'Package blob identity does not establish camera safety or color accuracy',
                  'New looktool code and device assets are not integrated into the old installer'],
        'installer_baseline_lock_verified':True,'camera_commands_sent':False,
        'mac_custom_lut_install_verified':False,'actual_camera_color_accuracy_verified':False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--baseline-source',type=Path,default=ROOT/'.upstream/a7c2_fl23_preview')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        raw=(json.dumps(audit(args.archive,args.baseline_source),ensure_ascii=False,indent=2)+'\n').encode()
        write_bytes_new(args.output,raw);print(raw.decode(),end='');return 0
    except (ValueError,OSError,KeyError,zipfile.BadZipFile) as exc:
        p.exit(1,f'STOPPED: {exc}\n')


if __name__=='__main__':
    raise SystemExit(main())
