"""Execucao serial; restaura Nginx e as tres instancias inclusive em erro."""
import argparse
import csv
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(r'C:\faculdade\trabalho-wordpress')
BASE = ROOT / 'docs' / 'trabalho3'
BASE.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('--smoke', action='store_true')
args = parser.parse_args()
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT = BASE / (('smoke-' if args.smoke else 'matrix-') + STAMP)
OUT.mkdir()
ORIGINAL = (ROOT / 'nginx.conf').read_bytes()
(OUT / 'nginx-original.conf').write_bytes(ORIGINAL)
MANIFEST = json.loads((ROOT / 'locust' / 'posts.json').read_text())

def dc(*items, timeout=90):
    p = subprocess.run(['docker', 'compose', *items], cwd=ROOT, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError('docker compose ' + ' '.join(items[:3]) + ': ' + p.stderr.decode(errors='replace')[-1500:])
    return p.stdout.decode(errors='replace')

def topology(n):
    dc('start', *['wordpress'+str(i) for i in range(1, n+1)])
    config = ORIGINAL.decode()
    for i in range(n+1, 4):
        config = config.replace('        server wordpress'+str(i)+':80;', '')
    (ROOT / 'nginx.conf').write_bytes(config.encode())
    dc('exec', '-T', 'nginx', 'nginx', '-t')
    dc('exec', '-T', 'nginx', 'nginx', '-s', 'reload')
    time.sleep(3)
    if n < 3:
        dc('stop', *['wordpress'+str(i) for i in range(n+1,4)])
    time.sleep(2)
    # Uma conexao nova por pedido permite observar todos os membros round-robin.
    upstreams = set()
    for _ in range(12):
        with urlopen('http://localhost:8080/?p='+str(MANIFEST['imagem-1mb']['id']), timeout=20) as response:
            if response.status != 200:
                raise RuntimeError('Preflight HTTP falhou')
            upstreams.add(response.headers.get('X-Upstream'))
            response.read()
    if None in upstreams or len(upstreams) != n:
        raise RuntimeError('Upstreams observados '+repr(upstreams)+'; esperado '+str(n))
    (OUT / ('topology-'+str(n)+'.json')).write_text(json.dumps({'instances':n,'upstreams':sorted(upstreams),'compose_ps':dc('ps')} ,indent=2))
    print('TOPOLOGIA VALIDADA: '+str(n)+' instancia(s), '+repr(sorted(upstreams)), flush=True)

def execute(n, scenario, users, seconds):
    name = f'i{n}-{scenario}-u{users}'
    folder = OUT / name
    folder.mkdir()
    cmd = ['docker','compose','run','--rm','--no-deps','-e','SCENARIO='+scenario,
           '-v',str(folder)+':/results','locust','-f','/mnt/locust/locustfile.py',
           '--host=http://nginx','--headless','--users',str(users),'--spawn-rate','1',
           '--run-time',str(seconds)+'s','--stop-timeout','20','--csv=/results/locust',
           '--csv-full-history','--html=/results/report.html','--exit-code-on-error','1']
    meta = {'instances':n,'scenario':scenario,'users':users,'duration_seconds':seconds,
            'spawn_rate':1,'wait_seconds':[1,3],'started_utc':datetime.now(timezone.utc).isoformat(),
            'warmup':'12 HTML requests per topology; no separate statistical warmup',
            'command':cmd}
    print('INICIO '+name,flush=True)
    with (folder/'console.log').open('w',encoding='utf-8') as log:
        process = subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic()+seconds+100
            with (folder/'resources.jsonl').open('w',encoding='utf-8') as resource:
                while process.poll() is None:
                    if time.monotonic()>deadline:
                        raise RuntimeError('Prazo excedido em '+name)
                    sample = subprocess.run(['docker','stats','--no-stream','--format','{{json .}}',
                        *['trabalho-wordpress-'+x+'-1' for x in ['mysql','nginx']+['wordpress'+str(i) for i in range(1,n+1)]]],
                        capture_output=True,text=True,timeout=15)
                    resource.write(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'stats':sample.stdout.splitlines()})+'\n')
                    resource.flush()
                    time.sleep(5)
        finally:
            if process.poll() is None:
                process.terminate()
                subprocess.run(['docker','compose','stop','locust'],cwd=ROOT,capture_output=True)
    meta['returncode']=process.returncode
    meta['finished_utc']=datetime.now(timezone.utc).isoformat()
    (folder/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    if process.returncode != 0:
        raise RuntimeError('Locust falhou em '+name+'; consultar console.log')
    with (folder/'locust_stats.csv').open(encoding='utf-8-sig') as f:
        aggregate=next(r for r in csv.DictReader(f) if r['Name']=='Aggregated')
    count=int(aggregate['Request Count'])
    failures=int(aggregate['Failure Count'])
    print('FIM '+name+': '+str(count)+' requisicoes, '+str(failures)+' falhas; media '+aggregate['Average Response Time']+' ms',flush=True)
    if not count or failures/max(count,1)>0.05 or float(aggregate['95%'])>10000:
        raise RuntimeError('Limite de protecao: sem requisicoes, >5% falhas ou p95 >10s; interrompendo matriz')

try:
    state=json.load(urlopen('http://localhost:8089/stats/requests',timeout=10))
    if state.get('state') not in ['ready','stopped']:
        raise RuntimeError('Locust da interface esta ativo; nao executar cargas concorrentes')
    (OUT/'environment.json').write_text(json.dumps({'platform':platform.platform(),'utc':STAMP,'manifest':MANIFEST,'original_compose_ps':dc('ps')},indent=2))
    for n in ([3] if args.smoke else [1,2,3]):
        topology(n)
        for scenario in MANIFEST:
            for users in ([1] if args.smoke else [5,10,20]):
                execute(n,scenario,users,10 if args.smoke else 60)
                time.sleep(3)
    (OUT/'COMPLETE').write_text('All planned runs completed.\n')
finally:
    dc('start','wordpress1','wordpress2','wordpress3')
    (ROOT/'nginx.conf').write_bytes(ORIGINAL)
    dc('exec','-T','nginx','nginx','-t')
    dc('exec','-T','nginx','nginx','-s','reload')
    print('RESTAURADO: configuracao original e tres instancias. Resultados: '+str(OUT),flush=True)
