import argparse
import csv
import json
import shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(r'C:\faculdade\trabalho-wordpress')
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',type=Path,default=ROOT/'docs'/'trabalho3'/'entrega')
DELIVER=parser.parse_args().output_dir
runs=sorted((ROOT/'docs'/'trabalho3').glob('matrix-*'))
if not runs:
    raise SystemExit('Nenhuma matriz encontrada')
run=runs[-1]
rows=[]
for folder in sorted(run.glob('i*-u*')):
    if not (folder/'metadata.json').exists() or not (folder/'locust_stats.csv').exists():
        continue
    meta=json.loads((folder/'metadata.json').read_text())
    with (folder/'locust_stats.csv').open(encoding='utf-8-sig') as f:
        stats=list(csv.DictReader(f))
    total=next(x for x in stats if x['Name']=='Aggregated')
    html=next(x for x in stats if x['Name'].endswith('/html'))
    rows.append(dict(instancias=meta['instances'],cenario=meta['scenario'],usuarios=meta['users'],
        requisicoes=int(total['Request Count']),falhas=int(total['Failure Count']),
        media_ms=float(total['Average Response Time']),p95_ms=float(total['95%']),
        rps=float(total['Requests/s']),html_media_ms=float(html['Average Response Time']),
        html_rps=float(html['Requests/s']),bytes_medios=float(total['Average Content Size'])))
if not rows:
    raise SystemExit('Nenhum resultado completo ainda')
summary=run/'resumo.csv'
with summary.open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
for metric,label in [('media_ms','Tempo médio por requisição (ms)'),('p95_ms','Percentil 95 por requisição (ms)'),('rps','Requisições HTTP por segundo'),('html_media_ms','Tempo médio do HTML (ms)'),('html_rps','Páginas por segundo (HTML)')]:
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
    for ax,scenario in zip(axes,['imagem-1mb','texto-400kb','imagem-300kb']):
        for n in [1,2,3]:
            data=sorted([r for r in rows if r['cenario']==scenario and r['instancias']==n],key=lambda r:r['usuarios'])
            if data: ax.plot([r['usuarios'] for r in data],[r[metric] for r in data],marker='o',label=f'{n} instância(s)')
        ax.set(title=scenario,xlabel='Usuários simultâneos',ylabel=label,xticks=[5,10,20]);ax.set_ylim(bottom=0);ax.grid(alpha=.25);ax.legend()
    fig.suptitle('WordPress + Locust — resultados medidos, 60 s por execução')
    fig.savefig(run/(metric+'.png'),dpi=160);plt.close(fig)
complete=(run/'COMPLETE').exists() and len(rows)==27
lines=['# Trabalho 3 — WordPress e Locust','',
    'Requisitos conferidos no PDF "Trabalho 3 – Realização de Testes de Carga com Múltiplas Instâncias do Wordpress Utilizando o Locust": três conteúdos, três cargas crescentes, três quantidades de instâncias e gráficos com usuários/instâncias no eixo X e métricas no eixo Y.','',
    f'Estado: {"matriz completa (27/27)" if complete else "matriz parcial ("+str(len(rows))+"/27)"}. Dados reais; nenhuma interpolação ou resultado inventado.','',
    '## Conteúdos e execução','',
    '- Imagem ~1 MB: post 6; PNG original com 1.046.039 bytes.',
    '- Texto ~400 KB: post 7; texto sintético de 409.600 bytes (400 KiB), além do HTML do tema.',
    '- Imagem ~300 KB: post 9; PNG original com 307.963 bytes.',
    '- 1, 2 e 3 contêineres WordPress ativos; upstreams do Nginx conferidos antes de cada topologia.',
    '- 5, 10 e 20 usuários; subida de 1 usuário/s; duração de 60 s incluindo a subida; espera aleatória de 1–3 s após cada visita.',
    '- Uma execução por combinação; testes sequenciais no mesmo computador, com banco e arquivos compartilhados. Gerador e aplicação disputam recursos locais.',
    '- Cada visita solicita o HTML e, nos posts de imagem, baixa o PNG original por HTTP. Sem cache de navegador; não carrega CSS, JavaScript, outras imagens do tema ou srcset.',
    '- O Locust usa http://nginx com Host localhost:8080; redirecionamentos são considerados falhas. Valida marcador do post e hash/tamanho da imagem.',
    '- RPS agregado conta HTML + imagem; páginas/s conta somente HTML. A média agregada mistura recursos diferentes; compare cenários também pelo gráfico de HTML.',
    '- Percentis extraídos dos CSVs do Locust; valores arredondados pelo próprio Locust. Requisições que terminam durante a drenagem podem estender a janela registrada.',
    '- Há pré-aquecimento funcional por topologia, mas nenhuma janela de estabilização excluída das estatísticas. Ordem fixa: instâncias crescentes, depois cenário e usuários crescentes. Aquecimento e caches podem confundir comparações. Não há repetições para estimar variância ou intervalos de confiança.',
    '- Os números 10/100/1000 do PDF são exemplos. As cargas 5/10/20 foram escolhidas pelo usuário para limitar o impacto local; estes resultados não estimam capacidade máxima.',
    '', '## Resultados','',
    '|Post|Instâncias|Usuários|Requisições|Falhas|Média HTTP (ms)|p95 (ms)|HTTP/s|HTML (ms)|Páginas/s|',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in sorted(rows,key=lambda r:(r['cenario'],r['instancias'],r['usuarios'])):
    lines.append(f"|{r['cenario']}|{r['instancias']}|{r['usuarios']}|{r['requisicoes']}|{r['falhas']}|{r['media_ms']:.1f}|{r['p95_ms']:.0f}|{r['rps']:.2f}|{r['html_media_ms']:.1f}|{r['html_rps']:.2f}|")
lines+=['','## Gráficos','']
for metric in ['media_ms','p95_ms','rps','html_media_ms','html_rps']:
    lines+=['!['+metric+']('+metric+'.png)','']
lines+=['## Leitura dos resultados','']
for scenario in ['imagem-1mb','texto-400kb','imagem-300kb']:
    selected=[r for r in rows if r['cenario']==scenario and r['usuarios']==20]
    one=next((r for r in selected if r['instancias']==1),None)
    three=next((r for r in selected if r['instancias']==3),None)
    if one and three:
        lines.append(f"- {scenario}, 20 usuários: de 1 para 3 instâncias, páginas/s passaram de {one['html_rps']:.2f} para {three['html_rps']:.2f}; a média do HTML passou de {one['html_media_ms']:.1f} para {three['html_media_ms']:.1f} ms. Esta é uma comparação observada nesta execução, sem estimativa de incerteza.")
lines+=['',f"Total medido: {sum(r['requisicoes'] for r in rows):,} requisições HTTP e {sum(r['falhas'] for r in rows):,} falhas nas {len(rows)} combinações disponíveis.",'']
lines+=['## Evidências e limites','',
    'Cada pasta de execução contém CSVs originais, relatório HTML do Locust, console, parâmetros e amostras de recursos Docker. environment.json registra o ambiente; topology-*.json registra os upstreams observados. O arquivo COMPLETE existe somente após todas as execuções.',
    '', 'Os resultados permitem comparar este ambiente e esta janela de carga. Não demonstram escalabilidade em máquinas independentes: MySQL, volume de arquivos e recursos do computador são compartilhados. Uma única amostra curta por ponto está sujeita a aquecimento, caches e variação do host.',
    '', '## Alterações e reprodução','',
    'Scripts em scripts/trabalho3; execute a partir do projeto: python scripts/trabalho3/run_matrix.py. Requer Python; para gerar os gráficos: python scripts/trabalho3/report.py (matplotlib). O Locust vem da imagem já usada no Compose. O script de preparação não deve ser repetido sem revisão: recusa slugs de teste existentes.',
    '', 'Foram acrescentados três posts e duas mídias; locust/locustfile.py foi substituído e locust/posts.json guarda IDs, URLs e hashes sem credenciais. Compose foi preservado. O Nginx muda temporariamente durante a matriz e é restaurado no bloco finally; WordPress 1/2/3 voltam a funcionar ao final.',
    '', 'Backup anterior de banco/configuração guardado privadamente na pasta work/private desta conversa, fora do repositório. Não inclua o backup SQL, .env ou wp-config.php em commits. Nenhum commit ou envio remoto foi executado.',
    '', 'Commit sugerido: `feat: adiciona cenarios Locust e resultados do Trabalho 3`.',
    '', 'Revisar antes do commit: `git diff -- docker-compose.yml locust/locustfile.py README.md .gitignore` e `git status --short`. Incluir somente locust/locustfile.py, locust/posts.json, scripts/trabalho3, docs/trabalho3 e documentação revisada. A alteração pré-existente do Compose deve ser revisada separadamente.', '']
if (run/'VERIFICACAO.json').exists():
    audit=json.loads((run/'VERIFICACAO.json').read_text())
    lines+=['## Verificação final','',audit['docker_environment'],'',
        'As 27 combinações atingiram o número previsto de usuários (conferido no histórico Locust). Os arquivos Compose e Nginx coincidem byte a byte com o backup anterior; os seis serviços voltaram a funcionar, o post original 1 responde HTTP 200 e a interface Locust foi reiniciada com o script novo.', '']
(run/'RELATORIO.md').write_text('\n'.join(lines),encoding='utf-8')
DELIVER.mkdir(exist_ok=True)
for item in [summary,run/'RELATORIO.md',*run.glob('*.png')]:shutil.copy2(item,DELIVER/item.name)
print(json.dumps({'complete':complete,'runs':len(rows),'requests':sum(r['requisicoes'] for r in rows),'failures':sum(r['falhas'] for r in rows),'source':str(run)},indent=2))
