#!/usr/bin/env python3
"""
Atualiza o painel por programa da Marginal 104.1 FM com dados reais do Metricool.

Uso:
    python atualizar_painel.py            # gera saida/index.html
    python atualizar_painel.py --debug    # mostra os campos que a API devolve (1.ª execução)

Variáveis de ambiente:
    METRICOOL_TOKEN     token da API (Metricool > Definições da conta > API)
    METRICOOL_USER_ID   userId da conta (mesma página)
    METRICOOL_BLOG_ID   id da marca "radio_marginal" (por omissão 5972668)
Só usa a biblioteca padrão do Python (sem instalar nada).
"""
import datetime as dt
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("METRICOOL_BASE", "https://app.metricool.com/api")
TOKEN = os.environ.get("METRICOOL_TOKEN", "")
USER_ID = os.environ.get("METRICOOL_USER_ID", "")
BLOG_ID = os.environ.get("METRICOOL_BLOG_ID", "5972668")
DEBUG = "--debug" in sys.argv

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "saida")
INICIO = dt.date(2026, 5, 1)          # primeiro dia do painel
LUANDA = dt.timedelta(hours=1)        # Africa/Luanda = UTC+1

# Seguidores usados se a API não os devolver (actualize quando quiser)
SEGUIDORES_PADRAO = {"fb": 36705, "ig": 6141, "tt": 7475}

# ---------------------------------------------------------------------------
# PROGRAMAS: (nome, etiqueta, padrão). O padrão procura o nome do programa no
# texto da publicação, sem acentos, espaços ou pontuação (apanha também #hashtags).
# Para acrescentar um programa, basta acrescentar uma linha aqui.
# ---------------------------------------------------------------------------
PROGRAMAS = [
    ("Ponto & Contraponto", "Debate", r"pontoecontraponto|pontocontraponto"),
    ("Fórum Marginal", "Justiça e sociedade", r"forummarginal"),
    ("Expansão em Directo", "Economia", r"expansaoemdirecto|expansaoemdirect"),
    ("Conversa Aberta", "Entrevista", r"conversaaberta"),
    ("NJ às Terças", "Novo Jornal na rádio", r"njastercas|taljornalnaradio|novojornalnaradio"),
    ("Desporto Marginal", "Desporto", r"desportomarginal"),
    ("Mutamba", "Cultura e música", r"mutamba"),
    ("Radar Diplomático", "Internacional", r"radardiplomatico"),
    ("Fórmula de Sucesso", "Carreira e empreendedorismo", r"formuladesucesso"),
    ("Billboard", "Música", r"billboard"),
    ("Valor do Kumbu", "Economia e finanças", r"valordokumbu|valordokumbo"),
    ("Elas em Foco", "Sociedade", r"elasemfoco"),
]
RESTO = ("Notícias", "Restantes publicações")
TOTAL = ("Total da rádio", "Todas as publicações")
# Publicações de desporto sem o nome do programa vão para o Desporto Marginal
DESPORTO = re.compile(r"\b(futebol|petro|girabola|atletas?|desportiv[oa]s?)\b")
IDX_DESPORTO = 5

REDES = ("fb", "ig", "tt")
METRICAS = ("vis", "rch", "int", "seg", "n")


def sem_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t or "")) if unicodedata.category(c) != "Mn")


def classificar(texto):
    n = sem_acentos(texto).lower()
    compacto = re.sub(r"[^a-z0-9]", "", n)
    melhor, pos = None, 10**9
    for i, (_, _, padrao) in enumerate(PROGRAMAS):
        m = re.search(padrao, compacto)
        if m and m.start() < pos:
            melhor, pos = i, m.start()
    if melhor is not None:
        return melhor
    if DESPORTO.search(n):
        return IDX_DESPORTO
    return len(PROGRAMAS)  # Notícias


# ---------------------------------------------------------------------------
# Chamadas à API
# ---------------------------------------------------------------------------
def chamar(caminho, params):
    q = {"userId": USER_ID, "blogId": BLOG_ID, "timezone": "Africa/Luanda"}
    q.update(params)
    url = BASE + caminho + "?" + urllib.parse.urlencode(q)
    pedido = urllib.request.Request(url, headers={"X-Mc-Auth": TOKEN, "Accept": "application/json"})
    ultimo = None
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(pedido, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            ultimo = "HTTP %s %s" % (e.code, e.reason)
            if e.code in (401, 403):
                break
        except Exception as e:  # rede, JSON, etc.
            ultimo = repr(e)
        time.sleep(2 * (tentativa + 1))
    raise RuntimeError(ultimo)


def lista(resp):
    """Extrai a lista de publicações, seja uma lista simples ou {"data": [...]}."""
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for k in ("data", "rows", "posts", "items", "result"):
            if isinstance(resp.get(k), list):
                return resp[k]
        for v in resp.values():
            if isinstance(v, list):
                return v
    return []


def primeiro_que_funciona(nome, tentativas):
    """Usa o primeiro endereço que devolve publicações; se vierem vazios, tenta o seguinte."""
    erros, vazio = [], False
    for caminho, params in tentativas:
        try:
            itens = lista(chamar(caminho, params))
        except Exception as e:
            erros.append("%s -> %s" % (caminho, e))
            continue
        print("  %-14s %-34s %d publicações" % (nome, caminho, len(itens)))
        if itens:
            print("    campos:", ", ".join(sorted(itens[0].keys())) if isinstance(itens[0], dict) else type(itens[0]))
            if DEBUG:
                print("    exemplo:", json.dumps(itens[0], ensure_ascii=False)[:600])
            return itens
        vazio = True
    if vazio:
        return []
    print("  %-14s FALHOU:" % nome)
    for e in erros:
        print("    ", e)
    return None


# ---------------------------------------------------------------------------
# Leitura tolerante dos campos
# ---------------------------------------------------------------------------
def numero(r, *chaves):
    for k in chaves:
        v = r.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.replace(",", "."))
            except ValueError:
                pass
    return 0.0


def texto(r, *chaves):
    for k in chaves:
        v = r.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def data_da_publicacao(r):
    """Devolve a data (hora de Luanda) de uma publicação, ou None."""
    for k in ("created", "timestamp", "createTime", "publishedAt", "date", "publicationDate"):
        v = r.get(k)
        if v is None:
            continue
        if isinstance(v, dict):
            v = v.get("dateTime") or v.get("date")
            if v is None:
                continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            seg = v / 1000.0 if v > 1e11 else float(v)
            return (dt.datetime.fromtimestamp(seg, dt.timezone.utc) + LUANDA).date()
        s = str(v).strip()
        if re.fullmatch(r"\d{10,13}", s):
            seg = int(s) / 1000.0 if len(s) > 10 else int(s)
            return (dt.datetime.fromtimestamp(seg, dt.timezone.utc) + LUANDA).date()
        m = re.match(r"(\d{4})-?(\d{2})-?(\d{2})", s)
        if m:
            try:
                return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
    return None


def ler_fb(r):
    t = texto(r, "text", "message", "content")
    vis = max(numero(r, "impressions"), numero(r, "views"), numero(r, "videoViews"))
    rch = max(numero(r, "impressionsUnique"), numero(r, "totalMediaViewUnique"), numero(r, "reach"))
    inter = numero(r, "comments") + numero(r, "reactions", "likes") + numero(r, "shares")
    tipo = "Vídeo" if numero(r, "videoViews") > 0 else "Foto"
    return t, vis, rch, inter, 0.0, tipo


def ler_fb_reel(r):
    t = texto(r, "description", "content", "text")
    vis = max(numero(r, "videoViews"), numero(r, "blueReelsPlayCount"), numero(r, "views"))
    rch = numero(r, "impressionsUnique", "postImpressionsUnique", "reach")
    inter = numero(r, "likes", "postVideoReactions") + numero(r, "actions", "postVideoSocialActions")
    return t, vis, rch, inter, 0.0, "Reel"


def ler_ig_post(r):
    t = texto(r, "content", "caption", "text")
    vis = numero(r, "views", "impressions", "videoViews")
    rch = numero(r, "reach")
    inter = numero(r, "interactions")
    if not inter:
        inter = numero(r, "likes") + numero(r, "comments") + numero(r, "shares") + numero(r, "saved")
    return t, vis, rch, inter, numero(r, "follows", "newFollowers"), "Foto"


def ler_ig_reel(r):
    t, vis, rch, inter, seg, _ = ler_ig_post(r)
    return t, vis, rch, inter, seg, "Reel"


def ler_tt(r):
    t = texto(r, "videoDescription", "title", "description")
    vis = numero(r, "viewCount", "views")
    rch = numero(r, "reach")
    inter = numero(r, "likeCount", "likes") + numero(r, "commentCount", "comments") + numero(r, "shareCount", "shares")
    return t, vis, rch, inter, 0.0, "Vídeo"


# ---------------------------------------------------------------------------
# Seguidores (melhor esforço: se a API não responder, usa o último valor conhecido)
# ---------------------------------------------------------------------------
def e_data(s):
    return isinstance(s, str) and re.match(r"^(\d{8}(\d{6})?|\d{4}-\d{2}-\d{2})", s) is not None


def ultimo_valor(obj):
    pontos = []

    def andar(o):
        if isinstance(o, list):
            if len(o) == 2 and any(e_data(str(x)) for x in o):
                d = next(str(x) for x in o if e_data(str(x)))
                v = next((x for x in o if str(x) != d), None)
                try:
                    pontos.append((re.sub(r"\D", "", d)[:14], float(v)))
                except (TypeError, ValueError):
                    pass
            else:
                for x in o:
                    andar(x)
        elif isinstance(o, dict):
            d = next((str(o[k]) for k in ("dateTime", "datetime", "date", "day") if k in o and e_data(str(o[k]))), None)
            v = next((o[k] for k in ("value", "count", "followers", "total") if isinstance(o.get(k), (int, float))), None)
            if d and v is not None:
                pontos.append((re.sub(r"\D", "", d)[:14], float(v)))
            else:
                for x in o.values():
                    andar(x)

    andar(obj)
    return max(pontos)[1] if pontos else None


def seguidores(ate, anteriores):
    ini, fim = (ate - dt.timedelta(days=10)), ate
    s8 = lambda d: d.strftime("%Y%m%d")
    iso = lambda d, h: d.strftime("%Y-%m-%d") + h
    tent = {
        "fb": [("/stats/timeline/fbFollowers", {"start": s8(ini), "end": s8(fim)}),
               ("/stats/timeling/fbFollowers", {"start": s8(ini), "end": s8(fim)})],
        "ig": [("/stats/timeline/igFollowers", {"start": s8(ini), "end": s8(fim)}),
               ("/stats/timeling/igFollowers", {"start": s8(ini), "end": s8(fim)}),
               ("/stats/timeline/followers", {"start": s8(ini), "end": s8(fim), "subject": "account", "network": "instagram"}),
               ("/v2/analytics/timelines", {"network": "instagram", "subject": "account", "metric": "followers",
                                            "from": iso(ini, "T00:00:00"), "to": iso(fim, "T23:59:59")})],
        "tt": [("/v2/analytics/timelines", {"network": "tiktok", "subject": "account", "metric": "followers_count",
                                            "from": iso(ini, "T00:00:00"), "to": iso(fim, "T23:59:59")})],
    }
    res, obtidos = {}, {}
    for rede, opcoes in tent.items():
        valor = None
        for caminho, params in opcoes:
            try:
                valor = ultimo_valor(chamar(caminho, params))
            except Exception:
                valor = None
            if valor:
                break
        obtidos[rede] = bool(valor)
        if valor:
            res[rede] = int(round(valor))
        else:
            res[rede] = anteriores.get(rede, SEGUIDORES_PADRAO[rede])
            print("  aviso: seguidores de %s não obtidos pela API; a usar %s" % (rede, res[rede]))
    return res, obtidos


# ---------------------------------------------------------------------------
def main():
    if not TOKEN or not USER_ID:
        sys.exit("Faltam METRICOOL_TOKEN e/ou METRICOOL_USER_ID (veja o LEIA-ME).")

    agora = dt.datetime.now(dt.timezone.utc) + LUANDA
    hoje = agora.date()
    ate = hoje - dt.timedelta(days=1)               # último dia completo
    nd = (ate - INICIO).days + 1
    s8 = lambda d: d.strftime("%Y%m%d")
    a, b = INICIO.isoformat() + "T00:00:00", ate.isoformat() + "T23:59:59"
    v2 = {"from": a, "to": b}
    v1 = {"start": s8(INICIO), "end": s8(ate)}
    print("A ler o Metricool (marca %s) de %s a %s ..." % (BLOG_ID, INICIO, ate))

    fontes = [
        ("fb", ler_fb, primeiro_que_funciona("Facebook", [("/stats/facebook/posts", v1), ("/v2/analytics/posts/facebook", v2)])),
        ("fb", ler_fb_reel, primeiro_que_funciona("FB Reels", [("/v2/analytics/reels/facebook", v2), ("/stats/facebook/reels", v1)])),
        ("ig", ler_ig_post, primeiro_que_funciona("Instagram", [("/stats/instagram/posts", v1), ("/v2/analytics/posts/instagram", v2)])),
        ("ig", ler_ig_reel, primeiro_que_funciona("IG Reels", [("/stats/instagram/reels", v1), ("/v2/analytics/reels/instagram", v2)])),
        ("tt", ler_tt, primeiro_que_funciona("TikTok", [("/v2/analytics/posts/tiktok", v2)])),
    ]
    if all(f[2] is None for f in fontes):
        sys.exit("Nenhuma fonte respondeu. Verifique o token, o userId e o plano (a API exige Advanced ou Custom).")

    n_prog = len(PROGRAMAS) + 2
    nomes = [(p[0], p[1]) for p in PROGRAMAS] + [RESTO, TOTAL]
    D = [{"name": n, "tag": t, **{r: {m: [0] * nd for m in METRICAS} for r in REDES}} for n, t in nomes]
    TP, lidas, sem_data = [], {r: 0 for r in REDES}, 0

    for rede, ler, itens in fontes:
        for r in itens or []:
            if not isinstance(r, dict):
                continue
            dia = data_da_publicacao(r)
            if dia is None:
                sem_data += 1
                continue
            d = (dia - INICIO).days
            if not 0 <= d < nd:
                continue
            t, vis, rch, inter, seg, tipo = ler(r)
            idx = classificar(t)
            lidas[rede] += 1
            for k in (idx, n_prog - 1):
                o = D[k][rede]
                o["vis"][d] += vis
                o["rch"][d] += rch
                o["int"][d] += inter
                o["seg"][d] += seg
                o["n"][d] += 1
            TP.append({"d": d, "t": re.sub(r"\s+", " ", t)[:80], "v": int(vis), "n": rede, "tp": tipo})

    for p in D:
        for r in REDES:
            for m in METRICAS:
                p[r][m] = [int(round(x)) for x in p[r][m]]
    TP = sorted(TP, key=lambda x: -x["v"])[:300]

    dados_antes = {}
    try:
        with open(os.path.join(AQUI, "dados.json"), encoding="utf-8") as f:
            dados_antes = json.load(f).get("seguidores", {})
    except Exception:
        pass
    foll, seg_ok = seguidores(ate, dados_antes)

    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    subst = {
        "__D__": json.dumps(D, ensure_ascii=False, separators=(",", ":")),
        "__TP__": json.dumps(TP, ensure_ascii=False, separators=(",", ":")),
        "__FOLL__": json.dumps(foll),
        "__ND__": str(nd),
        "__ATE_ISO__": ate.isoformat(),
        "__ATE__": ate.strftime("%d/%m/%Y"),
        "__ATE_EXT__": "%d de %s de %d" % (ate.day, meses[ate.month - 1], ate.year),
        "__SEGDATA__": hoje.strftime("%d/%m/%Y"),
    }
    with open(os.path.join(AQUI, "template.html"), encoding="utf-8") as f:
        html = f.read()
    if all(seg_ok.values()):
        frase_seg = "seguidores a " + hoje.strftime("%d/%m/%Y")
    else:
        em_falta = ", ".join({"fb": "Facebook", "ig": "Instagram", "tt": "TikTok"}[r] for r in REDES if not seg_ok[r])
        frase_seg = "seguidores: " + em_falta + " = último valor conhecido (a API não o devolveu)"
    html = html.replace("seguidores a __SEGDATA__", frase_seg)
    html = html.replace("Dados reais das exportações do Facebook, Instagram e TikTok", "Dados reais do Metricool (API) do Facebook, Instagram e TikTok")
    for k, v in subst.items():
        html = html.replace(k, v)
    os.makedirs(SAIDA, exist_ok=True)
    with open(os.path.join(SAIDA, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    resumo = {
        "gerado_em": agora.strftime("%Y-%m-%d %H:%M"),
        "dados_ate": ate.isoformat(),
        "publicacoes_lidas": lidas,
        "sem_data": sem_data,
        "avulsas_noticias": sum(D[len(PROGRAMAS)][r]["n"][i] for r in REDES for i in range(nd)),
        "seguidores": foll,
        "seguidores_via_api": seg_ok,
    }
    with open(os.path.join(AQUI, "dados.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1)
    print("\nPronto: saida/index.html")
    print(json.dumps(resumo, ensure_ascii=False))


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
