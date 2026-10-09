# Painel Marginal: actualização automática com o Metricool

Todas as segundas-feiras de manhã, o painel lê os dados do Metricool, agrupa as
publicações por programa e publica a página actualizada, sem exportar nem importar nada.

## O que está aqui
- `atualizar_painel.py`: lê a API do Metricool (Facebook, Instagram, Reels, TikTok), agrupa por programa e gera `saida/index.html`.
- `template.html`: o painel (visual Marginal). Não é preciso mexer.
- `.github/workflows/atualizar.yml`: agenda a execução semanal no GitHub.

## Passo 1: dados do Metricool (2 minutos)
No Metricool: **Definições da conta > API**. Copie:
- o **token** (é uma palavra-passe: não o partilhe nem o escreva em emails);
- o **userId** da conta.
O **blogId** da marca radio_marginal é `5972668` (o número da marca no Metricool).

## Passo 2: testar no seu computador (recomendado, 5 minutos)
Precisa de Python 3 instalado. Num terminal, na pasta destes ficheiros:

    # Windows (PowerShell)
    $env:METRICOOL_TOKEN="O_SEU_TOKEN"; $env:METRICOOL_USER_ID="O_SEU_USER_ID"
    python atualizar_painel.py --debug

    # Mac / Linux
    METRICOOL_TOKEN=O_SEU_TOKEN METRICOOL_USER_ID=O_SEU_USER_ID python3 atualizar_painel.py --debug

O `--debug` mostra, para cada rede, quantas publicações leu e os nomes dos campos.
No fim abra `saida/index.html`. **Se alguma rede aparecer "FALHOU" ou com 0
publicações, envie o texto que apareceu no terminal (sem o token) e o script é ajustado.**
O script foi escrito a partir da documentação pública da API e testado com uma
API simulada; a primeira execução real é que confirma os nomes dos campos.

## Passo 3: automatizar (GitHub, gratuito)
1. Crie um repositório no GitHub e envie estes ficheiros (incluindo a pasta `.github`).
2. **Settings > Secrets and variables > Actions > New repository secret**, crie:
   `METRICOOL_TOKEN`, `METRICOOL_USER_ID`, `METRICOOL_BLOG_ID` (= 5972668).
3. **Settings > Pages > Source: GitHub Actions**.
4. Separador **Actions > Atualizar painel Marginal > Run workflow** para a 1.ª vez.
   O endereço do painel aparece no fim da execução.
A partir daí corre sozinho todas as segundas-feiras às 07:00 (hora de Luanda).

## Atenção: privacidade
As páginas do GitHub Pages são **públicas** para quem tiver o link. Se não quiser isso:
- publique `saida/index.html` num alojamento com palavra-passe (Cloudflare Pages com Access, Netlify, SharePoint ou servidor da empresa), ou
- use só o passo 2 e envie o ficheiro gerado ao board.
O script também corre em qualquer servidor com um agendamento semanal, por exemplo
`0 7 * * 1 python3 /caminho/atualizar_painel.py`.

## Ajustes
- **Novo programa:** acrescente uma linha na lista `PROGRAMAS` do script.
- **Desporto sem o nome do programa:** as palavras estão em `DESPORTO`.
- **Seguidores:** o script tenta obter os totais pela API; se não conseguir, usa o último valor conhecido (e avisa).
- **Alcance no Facebook:** a Meta deixou de fornecer o alcance único por publicação (desde 15/06/2026), por isso pode aparecer a zero; use "Views".
- **Período:** o painel mostra por omissão os últimos 7 dias completos; os dados vão de 1 de Maio de 2026 até ontem.
