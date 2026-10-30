# WordPress distribuído com Docker e Locust

Ambiente acadêmico dos Trabalhos 2 e 3: MySQL 5.7, três WordPress 5.4.2/PHP 7.2/Apache, Nginx 1.19 e Locust 2.31.8. O banco usa volume nomeado; os WordPress compartilham `./wordpress`. O Compose original e os dados foram preservados.

## Uso

Configure `.env` a partir de `.env.example`, mantendo as senhas fora do Git. Inicie com `docker compose up -d`. WordPress: http://localhost:8080 ; Locust: http://localhost:8089 . Não execute `docker compose down -v` para encerrar: isso remove o volume do banco.

## Trabalho 3

Posts criados em 30/10/2026: imagem ~1 MB (`/?p=6`), texto 400 KiB (`/?p=7`) e imagem ~300 KB (`/?p=9`). IDs, tamanhos, URLs e hashes estão em `locust/posts.json`. As imagens são PNGs de pixels sintéticos, sem dados pessoais; os tamanhos correspondem a conteúdo de imagem real, sem preenchimento artificial de arquivo.

O script Locust valida HTTP 200, conteúdo do post e a integridade de cada imagem. Cada visita acessa o HTML e o PNG original, com espera aleatória de 1–3 segundos. O host de conexão é `http://nginx`; o cabeçalho `Host: localhost:8080` preserva a URL pública do WordPress. A variável `SCENARIO` seleciona `imagem-1mb`, `texto-400kb` ou `imagem-300kb` (padrão: imagem-1mb).

Matriz autorizada: 3 posts × 1/2/3 instâncias ativas × 5/10/20 usuários, 60 segundos por combinação, subida de 1 usuário por segundo. Os exemplos 10/100/1000 do PDF não são obrigatórios. Os testes são sequenciais e geram resultados reais; não substituem medições de capacidade máxima.

Execute `python scripts/trabalho3/run_matrix.py --smoke` para validação leve ou `python scripts/trabalho3/run_matrix.py` para a matriz. O script verifica que a interface Locust não está executando carga, ajusta o upstream do Nginx, para instâncias excedentes, verifica o número de upstreams e restaura o Nginx original e os três WordPress no bloco `finally`. Evite editar o Nginx durante o teste. Após interrupção externa que mate o Python, confira a configuração e inicie as três instâncias antes de recarregar o Nginx.

Proteção: interrompe diante de erro do Locust, ausência de requisições, taxa de falhas acima de 5% ou p95 acima de 10 segundos. CSVs, HTML, console, parâmetros e amostras de recursos ficam em `docs/trabalho3/smoke-*` e `docs/trabalho3/matrix-*`. `COMPLETE` marca somente matrizes concluídas. O tempo de subida faz parte dos 60 segundos. Não há repetições ou intervalo de confiança; a execução é exploratória.

Gere tabelas e gráficos com `python scripts/trabalho3/report.py` (requer matplotlib). O relatório distingue HTTP/s de páginas/s: os cenários de imagem têm dois pedidos por visita. Os relatórios HTML completos e logs continuam no disco, mas são omitidos do Git para evitar duplicação volumosa; CSVs e resumos são a evidência versionável.

## Preservação e histórico

Antes dos posts, foi feito backup privado do banco e dos arquivos de configuração, fora deste repositório, na pasta `work/private` da conversa Codex. A senha e o dump SQL não devem ser publicados. Os posts anteriores foram preservados. Os arquivos do Trabalho 2 em `docs/prints` não foram alterados. Já havia modificações locais em `docker-compose.yml` e um Locust não rastreado; não foram descartadas.

Scripts de preparação em `scripts/trabalho3/setup_posts.php` e imagens em `docs/trabalho3/fixtures` documentam os conteúdos. A preparação recusa slugs existentes para evitar duplicação; não a execute novamente sem revisar. O script PHP foi executado dentro do WordPress após copiar as imagens para `/tmp`.

Commit sugerido: `feat: adiciona cenarios Locust e resultados do Trabalho 3`. Revise `git status --short` e `git diff` antes de selecionar arquivos. Revise separadamente a alteração pré-existente do Compose. Nenhum commit ou push foi feito automaticamente.

## Resultados coletados

[Relatório completo, tabela e gráficos](docs/trabalho3/matrix-20261030T184828Z/RELATORIO.md). Os CSVs originais e os relatórios HTML estão nas pastas de cada combinação.
