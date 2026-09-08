"""Run the actual adapter on a private bus with fake machine effects only."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

repo = Path(sys.argv[1])

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

core = load('clawosd_core', repo / 'm3/clawosd/clawosd_core.py')
fixtures = load('broker_test_fixtures', repo / 'm3/tests/test_clawosd.py')

if len(sys.argv) > 2 and sys.argv[2] == 'serve':
    import dbus
    import dbus.mainloop.glib
    import dbus.service
    from gi.repository import GLib
    root = Path(sys.argv[3])
    adapter = load('broker_adapter', repo / 'm3/clawosd/clawosd_service.py')
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.bus.BusConnection(f'unix:path={root}/bus')
    name = dbus.service.BusName(adapter.BUS_NAME, bus)
    service = adapter.Service.__new__(adapter.Service)
    service.bus = bus
    service.broker = core.Broker(config_path=root/'config.json', state_dir=root/'state',
        audit_path=root/'audit.jsonl', runner=fixtures.FakeRunner(), recovery=fixtures.FakeRecovery())
    dbus.service.Object.__init__(service, bus, adapter.OBJECT_PATH)
    GLib.MainLoop().run()
    sys.exit()

assert os.geteuid() == 0
with tempfile.TemporaryDirectory(prefix='clawos-bus-proof-') as tmp:
    root = Path(tmp)
    root.chmod(0o755)
    config = json.loads((repo/'m3/config/clawosd.json').read_text())
    (root/'config.json').write_text(json.dumps(config))
    (root/'bus.conf').write_text(f'''<busconfig><type>session</type>
<listen>unix:path={root}/bus</listen><auth>EXTERNAL</auth>
<policy context="default"><allow user="*"/><allow own="org.clawos.System"/>
<allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>''')
    bus = subprocess.Popen(['dbus-daemon', '--nofork', f'--config-file={root}/bus.conf'])
    server = None
    try:
        for _ in range(50):
            if (root/'bus').exists(): break
            time.sleep(.1)
        server = subprocess.Popen([sys.executable, __file__, str(repo), 'serve', str(root)])
        client = '''import dbus,json,sys
b=dbus.bus.BusConnection(sys.argv[1])
p=dbus.Interface(b.get_object('org.clawos.System','/org/clawos/System'),'org.clawos.System1')
print(getattr(p,sys.argv[2])(*sys.argv[3:]))
'''
        def call(user, method, *args):
            command = ['runuser','-u',user,'--',sys.executable,'-c',client,f'unix:path={root}/bus',method,*args]
            result = subprocess.run(command,capture_output=True,text=True,timeout=15)
            if result.returncode: raise RuntimeError(result.stderr)
            return json.loads(result.stdout)
        for attempt in range(50):
            try:
                assert call('nobody','GetStatus')['ok']
                break
            except RuntimeError:
                if attempt == 49: raise
                time.sleep(.1)
        params = json.dumps({'service':'sshd.service','operation':'stop'})
        for context in ('{}', '{"agentId":"main"}'):
            assert not call('nobody','PrepareAction','service.manage',params,context)['ok']
        assert not call('nobody','ListPending')['ok']
        prepared = call('clawos','PrepareAction','service.manage',params,'{}')
        assert prepared['ok'], prepared
        token = prepared['result']['token']
        assert not call('nobody','CommitAction',token)['ok']
        assert not call('nobody','CancelAction',token)['ok']
        assert call('clawos','ListPending')['result'][0]['token'] == token
        completed = call('clawos','CommitAction',token)
        assert completed['ok'] and completed['result']['state']=='complete', completed
        assert not call('clawos','CommitAction',token)['ok']
        print('PASS: real D-Bus UID enforcement; unrelated caller denied; separate owner CLI processes work; no real system actions')
    finally:
        if server:
            server.terminate()
            server.wait(timeout=10)
        bus.terminate()
        bus.wait(timeout=10)
