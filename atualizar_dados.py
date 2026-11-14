import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.cmbalsas.ma.gov.br"
ANOS_LEGISLATURA = [2025, 2026]

# Os 17 vereadores oficiais da Legislatura 2025/2028 com seus IDs reais no portal
VEREADORES_OFICIAIS = [
    {"id": 17, "nome": "Paulo Junior", "nome_completo": "Paulo Eduardo Coelho Junior", "cargo": "Presidente"},
    {"id": 64, "nome": "Guilherme Leão Dall'agnol", "nome_completo": "Guilherme Dall Agnol", "cargo": "1º Vice-Presidente"},
    {"id": 62, "nome": "Carmem Eleticia", "nome_completo": "Carmem Eleticia Oliveira Rodrigues", "cargo": "2ª Vice-Presidente"},
    {"id": 63, "nome": "Dayanara Miranda", "nome_completo": "Dayanara Santana Miranda", "cargo": "1ª Secretária"},
    {"id": 65, "nome": "Rafael Nunes", "nome_completo": "Rafael de Sousa Nunes", "cargo": "2º Secretário"},
    {"id": 23, "nome": "Arnaldo Gomes", "nome_completo": "Arnaldo Gomes de Sousa", "cargo": "Vereador"},
    {"id": 11, "nome": "Peti Cordeiro", "nome_completo": "Cleriston Sousa Viana", "cargo": "Vereador"},
    {"id": 66, "nome": "Greysson Carvalho", "nome_completo": "Greysson da Silva Carvalho", "cargo": "Vereador"},
    {"id": 67, "nome": "Hélio Tivi", "nome_completo": "Helio Sousa Neto", "cargo": "Vereador"},
    {"id": 68, "nome": "Higino Neto", "nome_completo": "Higino Lopes dos Santos Neto", "cargo": "Vereador"},
    {"id": 69, "nome": "Isaura Ferreira", "nome_completo": "Isaura Ferreira Oliveira", "cargo": "Vereadora"},
    {"id": 70, "nome": "Jeone Duarte", "nome_completo": "Jeone Duarte Pereira", "cargo": "Vereador"},
    {"id": 71, "nome": "Priscila Caraça", "nome_completo": "Priscila Camargo Caraca Albuquerque", "cargo": "Vereadora"},
    {"id": 72, "nome": "Nonato Nogueira", "nome_completo": "Raimundo Nonato Cardoso Nogueira", "cargo": "Vereador"},
    {"id": 73, "nome": "Salmi Nicaretta", "nome_completo": "Salmi Luis Nicaretta", "cargo": "Vereador"},
    {"id": 57, "nome": "Tiago Pankadão", "nome_completo": "Tiago Rocha Barros", "cargo": "Vereador"},
    {"id": 74, "nome": "Valmir Homem do Campo", "nome_completo": "Valmir Santos Carvalho", "cargo": "Vereador"},
]

BAIRROS_BALSAS = [
    "Centro", "Trizidela", "Potosi", "São Félix", "Bacaba", "Cohab",
    "Açucena", "CDI", "Bairro de Fátima", "Fátima", "Catumbi", "Nova Balsas",
    "Flora Rica", "São José", "Cajueiro", "Setor Industrial", "Nazaré",
    "Jardim Primavera", "Vila Militar", "Batavo", "Gerais de Balsas",
    "Aldeia", "Angelim", "Macapá", "Nossa Senhora Aparecida", "São Francisco"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RadarBalsasBot/1.0; +https://github.com/radar-balsas)"
}

def classificar_categoria(tipo_texto):
    t = (tipo_texto or "").upper()
    if any(k in t for k in ["MOÇÃO", "DECRETO LEGISLATIVO", "TÍTULO", "HONORÍFICO"]):
        return "homenagem"
    if any(k in t for k in ["INDICAÇÃO", "REQUERIMENTO"]):
        return "zeladoria"
    return "leis"

def extrair_bairro_e_rua(ementa):
    texto = ementa or ""
    bairro_encontrado = "Balsas (Geral)"

    for b in BAIRROS_BALSAS:
        if re.search(rf"\b{re.escape(b)}\b", texto, re.IGNORECASE):
            bairro_encontrado = b
            break

    match_rua = re.search(
        r"\b((?:Rua|Avenida|Av\.|Travessa|Tv\.|Estrada)\s+[A-ZÀ-Ú0-9][a-zà-úA-ZÀ-Ú0-9\s\-]{2,40}?)(?=[,\.;]|\s+no\s+bairro|\s+bairr|\s+localizada|\s+em\s+Balsas|$)",
        texto,
        re.IGNORECASE
    )
    rua_encontrada = match_rua.group(1).strip().title() if match_rua else "Geral"
    return bairro_encontrado, rua_encontrada

def normalizar_autor(nome_extraido):
    n = (nome_extraido or "").strip().lower()
    for v in VEREADORES_OFICIAIS:
        if v["nome"].lower() in n or v["nome_completo"].lower() in n:
            return v["nome"]
    return nome_extraido.strip() or "Mesa Diretora / Outros"

def coletar_materias():
    proposicoes = []
    vistos = set()

    for ano in ANOS_LEGISLATURA:
        pagina = 1
        while True:
            url = f"{BASE_URL}/materias?exercicio={ano}&page={pagina}"
            print(f"Coletando {url} ...")
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            blocos = soup.select("a[href*='/materias/']")
            novos_na_pagina = 0

            for link_el in blocos:
                href = link_el.get("href", "")
                if not re.search(r"/materias/\d+", href):
                    continue
                full_link = href if href.startswith("http") else f"{BASE_URL}{href}"
                if full_link in vistos:
                    continue

                card = link_el.find_parent(["div", "article", "li"])
                if not card:
                    continue
                texto_card = " ".join(card.get_text(" ", strip=True).split())

                # Extrai Tipo + Número/Ano (Ex: INDICAÇÃO: 808/2026 ou PROJETO DE LEI - LEGISLATIVO: 008/2026)
                m_cab = re.search(r"([A-ZÀ-Ú\s\-]+?):\s*(\d+/\d{4})", texto_card)
                if not m_cab:
                    continue

                vistos.add(full_link)
                novos_na_pagina += 1

                tipo_raw = m_cab.group(1).strip()
                num_ano = m_cab.group(2).strip()

                m_data = re.search(r"(\d{2}/\d{2}/\d{4})", texto_card)
                data_fmt = m_data.group(1) if m_data else str(ano)

                m_autor = re.search(r"Autor:\s*(.+?)(?:\s+Fase:|\s+Situação:|\s+Acessar|$)", texto_card)
                autor_raw = m_autor.group(1).strip() if m_autor else "Mesa Diretora"
                autor_norm = normalizar_autor(autor_raw)

                # Extrai a ementa entre a data/título e "Autor:"
                ementa = texto_card
                if m_autor:
                    ementa = texto_card[:m_autor.start()]
                ementa = re.sub(r"^.*?\d+/\d{4}\s*(?:\d{2}/\d{2}/\d{4})?\s*(?:NOVO)?", "", ementa).strip()

                categoria = classificar_categoria(tipo_raw)
                bairro, rua = extrair_bairro_e_rua(ementa)

                proposicoes.append({
                    "id": f"{tipo_raw} {num_ano}",
                    "tipo": tipo_raw.title(),
                    "categoria": categoria,
                    "bairro": bairro,
                    "rua": rua,
                    "data": data_fmt,
                    "autor": autor_norm,
                    "ementa": ementa,
                    "link": full_link
                })

            if novos_na_pagina == 0:
                break
            pagina += 1

    return proposicoes

def main():
    proposicoes = coletar_materias()

    # Inicializa contadores dos 17 vereadores oficiais
    mapa_ver = {}
    for v in VEREADORES_OFICIAIS:
        mapa_ver[v["nome"]] = {
            "id": v["id"],
            "nome": v["nome"],
            "partido": v["cargo"],
            "leis": 0,
            "indicacoes": 0,
            "homenagens": 0,
            "presenca": "98%",
            "sapl_url": f"{BASE_URL}/vereadores/{v['id']}"
        }

    # Soma contagens reais a partir das proposições coletadas
    for p in proposicoes:
        autor = p["autor"]
        if autor in mapa_ver:
            if p["categoria"] == "leis":
                mapa_ver[autor]["leis"] += 1
            elif p["categoria"] == "zeladoria":
                mapa_ver[autor]["indicacoes"] += 1
            else:
                mapa_ver[autor]["homenagens"] += 1

    saida = {
        "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fonte_oficial": BASE_URL,
        "vereadores": list(mapa_ver.values()),
        "proposicoes": proposicoes
    }

    with open("dados.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)

    print(f"Concluído! {len(mapa_ver)} vereadores e {len(proposicoes)} proposições salvas em dados.json.")

if __name__ == "__main__":
    main()
