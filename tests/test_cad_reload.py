"""Run under xvfb-run. Swap two CAD revisions while the same live session spins."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


def run(binary,rom,base,revised,log_path):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for source in (base,revised):
            # Hardlink if both reside on the same volume. Never edit the files.
            for_copy = os.link if source.stat().st_dev == root.stat().st_dev else shutil.copyfile
            shutil.copytree(source,root/source.name,copy_function=for_copy)
        def point(revision):
            scratch = root/'next.json'
            scratch.write_text(json.dumps(dict(schema_version=1,asset_revision=revision)))
            scratch.replace(root/'current.json')
        point(base.name)
        with log_path.open('w') as log:
            env = dict(os.environ,SDL_AUDIODRIVER='dummy',XDG_DATA_HOME=str(root/'prefs'))
            proc = subprocess.Popen(['stdbuf','-oL','-eL',binary,rom,'--live','--cad-assets',root,
                                     '--auto-start','--bench-preset','--window-frames','1200',
                                     '--frame-delay-ms','8'],stdout=log,stderr=subprocess.STDOUT,env=env)
            def wait(action):
                deadline = time.monotonic()+35
                while time.monotonic()<deadline and proc.poll() is None:
                    result = action()
                    if result: return result
                    time.sleep(.08)
                raise AssertionError(log_path.read_text()[-1400:])
            def xdo(*args):
                return subprocess.run(['xdotool',*args],capture_output=True,text=True).stdout.strip()
            try:
                win = wait(lambda: xdo('search','--name',r'^SEVEL 3D CAD \| LIVE').splitlines())
                win = win[-1]
                def phase():
                    name = xdo('getwindowname',win)
                    match = re.search(r'LIVE ([-\d.]+) deg',name)
                    return float(match[1]) if match else 0.
                first = wait(phase)
                for revision,token in [(revised.name,'reload=ready revision='+revised.name),
                                       ('0'*64,'reload=rejected active='+revised.name),
                                       (base.name,'reload=ready revision='+base.name)]:
                    point(revision)
                    xdo('key','--window',win,'F5')
                    wait(lambda: token in log_path.read_text())
                last = phase()
                assert last > first and log_path.read_text().count('preview_ready=1') == 1,(first,last)
                print(f'PASS hot reload, rejected missing package, rollback; continuous LIVE {first} -> {last} deg')
            finally:
                proc.terminate()
                proc.wait(timeout=10)


if __name__ == '__main__':
    run(*(Path(arg).resolve() for arg in sys.argv[1:]))
