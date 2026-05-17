import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SC = "#4f9cf9"; HC = "#f05252"
SC2 = "#4f9cf944"; HC2 = "#f0525244"
GOLD_C = "#f5a623"

def j(o): return json.dumps(o, ensure_ascii=False)

def main():
    GOLD = BASE_DIR / "data" / "gold"
    OUT  = BASE_DIR / "dashboard" / "index.html"
    OUT.parent.mkdir(exist_ok=True)

    carteira   = pd.read_csv(GOLD / "carteira_banco_mes.csv")
    produtos   = pd.read_csv(GOLD / "produtos_mais_vendidos.csv")
    localidade = pd.read_csv(GOLD / "inadimplencia_localidade.csv")
    share      = pd.read_csv(GOLD / "share_mercado.csv")
    qualidade  = pd.read_csv(GOLD / "qualidade_dados.csv")
    oport_vuln = pd.read_csv(GOLD / "ataque_vulneravel.csv")
    oport_rec  = pd.read_csv(GOLD / "ataque_recuperar.csv")

    def inad(bank):
        d = produtos[produtos.bank == bank]
        s, i = d.saldo_total.sum(), d.saldo_inadimplente.sum()
        return round(i / s * 100, 2) if s else 0

    def qual_pct(bank):
        r = qualidade[qualidade.bank == bank]
        return round((1 - r.iloc[0].pct_invalido) * 100, 1) if not r.empty else 100.0

    ks = dict(
        sc=int(carteira[carteira.bank=="Banco Shield"].contratos.sum()),
        hc=int(carteira[carteira.bank=="Hidra"].contratos.sum()),
        ss=round(carteira[carteira.bank=="Banco Shield"].saldo_total.sum()/1e6, 2),
        hs=round(carteira[carteira.bank=="Hidra"].saldo_total.sum()/1e6, 2),
        si=inad("Banco Shield"), hi=inad("Hidra"),
        sq=qual_pct("Banco Shield"), hq=qual_pct("Hidra"),
    )

    meses = sorted(carteira.ano_mes.unique().tolist())
    ml = [str(m)[4:]+"/"+str(m)[2:4] for m in meses]

    def serie(bank, col, scale=1):
        return [round(float(carteira[(carteira.ano_mes==m)&(carteira.bank==bank)][col].sum())/scale, 3) for m in meses]

    ev_labels = j(ml)
    ev_ss = j(serie("Banco Shield","saldo_total",1e6))
    ev_hs = j(serie("Hidra","saldo_total",1e6))
    ev_sc = j(serie("Banco Shield","contratos"))
    ev_hc = j(serie("Hidra","contratos"))

    seg = share[share.category == "Seguro"].iloc[0]
    seg_hidra_pct = round(float(seg.share_hidra) * 100, 1)
    seg_shield_pct = round(float(seg.share_shield) * 100, 1)

    sh_cat = j(share.category.tolist())
    sh_s   = j(share.share_shield.mul(100).round(1).tolist())
    sh_h   = j(share.share_hidra.mul(100).round(1).tolist())
    sh_cs  = j(share.contratos_shield.tolist())
    sh_ch  = j(share.contratos_hidra.tolist())

    tp = produtos[produtos.saldo_total>0].sort_values("indice_inadimplencia",ascending=False).head(12)
    rp_n   = j((tp.product_name+" ("+tp.bank.str.replace("Banco Shield","Shield")+")").tolist())
    rp_v   = j(tp.indice_inadimplencia.mul(100).round(2).tolist())
    rp_col = j([SC if b=="Banco Shield" else HC for b in tp.bank])

    tl = localidade[localidade.saldo_total>0].sort_values("indice_inadimplencia",ascending=False).head(12)
    rl_n   = j((tl.location_name+" ("+tl.bank.str.replace("Banco Shield","Shield")+")").tolist())
    rl_v   = j(tl.indice_inadimplencia.mul(100).round(2).tolist())
    rl_col = j([SC if b=="Banco Shield" else HC for b in tl.bank])

    qm = qualidade[qualidade.bank.isin(["Banco Shield","Hidra"])]
    ec = ["err_id_duplicado","err_periodo_invalido","err_produto_fk","err_localidade_fk","err_valor_negativo"]
    el = ["ID Duplicado","Periodo Invalido","Produto FK","Localidade FK","Valor Negativo"]
    qd_l = j(el)
    qd_s = j([int(qm[qm.bank=="Banco Shield"][c].sum()) for c in ec])
    qd_h = j([int(qm[qm.bank=="Hidra"][c].sum()) for c in ec])

    import duckdb as _duckdb
    _con = _duckdb.connect(str(BASE_DIR / "data" / "pipeline.duckdb"))
    grafias_corrigidas = _con.execute("SELECT COUNT(*) FROM silver_fato_contratos WHERE _fixed_bank = true").fetchone()[0]
    _con.close()
    shield_row = qm[qm.bank == "Banco Shield"].iloc[0]
    hidra_row  = qm[qm.bank == "Hidra"].iloc[0]

    atencao_balance = pd.read_csv(GOLD / "atencao_balance.csv")
    bgf_total   = len(atencao_balance)
    bgf_shield  = len(atencao_balance[atencao_balance.bank == "Banco Shield"])
    bgf_hidra   = len(atencao_balance[atencao_balance.bank == "Hidra"])
    bgf_media_s = round(atencao_balance[atencao_balance.bank == "Banco Shield"]["diferenca"].mean(), 2)
    bgf_media_h = round(atencao_balance[atencao_balance.bank == "Hidra"]["diferenca"].mean(), 2)
    bgf_adim_s  = round((atencao_balance[atencao_balance.bank == "Banco Shield"]["dpd"] == 0).mean() * 100, 1)
    bgf_adim_h  = round((atencao_balance[atencao_balance.bank == "Hidra"]["dpd"] == 0).mean() * 100, 1)

    qual_rows = ""
    for _, row in qualidade.iterrows():
        pct = round(row.pct_invalido*100, 1)
        badge = f'<span class="badge-ok">{pct}%</span>' if pct < 5 else f'<span class="badge-warn">{pct}%</span>'
        qual_rows += f"<tr><td><b>{row.bank}</b></td><td>{int(row.total)}</td><td>{int(row.err_id_duplicado)}</td><td>{int(row.err_periodo_invalido)}</td><td>{int(row.err_produto_fk)}</td><td>{int(row.err_localidade_fk)}</td><td>{int(row.err_valor_negativo)}</td><td>{badge}</td></tr>"

    # vulneravel: Hidra fraca (risco/inad alto)
    ov = oport_vuln
    ov_label = j((ov.location_name + " Ã— " + ov.product_name).tolist())
    ov_score  = j(ov.score_vulnerabilidade.round(3).tolist())
    ov_ri     = j(ov.risk_hidra.round(3).tolist())

    # recuperar: Hidra forte, Shield fraco
    or_ = oport_rec
    or_label = j((or_.location_name + " Ã— " + or_.product_name).tolist())
    or_score  = j(or_.score_recuperacao.round(3).tolist())
    or_sh     = j(or_.share_hidra.mul(100).round(1).tolist())
    or_ss     = j(or_.share_shield.mul(100).round(1).tolist())

    shield_svg = """<svg viewBox="0 0 100 110" width="36" height="36" xmlns="http://www.w3.org/2000/svg">
  <path d="M50 5 L95 25 L95 60 Q95 90 50 105 Q5 90 5 60 L5 25 Z" fill="#1a2744" stroke="#4f9cf9" stroke-width="3"/>
  <path d="M50 18 L82 33 L82 60 Q82 80 50 92 Q18 80 18 60 L18 33 Z" fill="none" stroke="#4f9cf9" stroke-width="1.5" opacity=".5"/>
  <text x="50" y="68" text-anchor="middle" font-size="38" font-weight="bold" fill="#4f9cf9" font-family="Arial">S</text>
</svg>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>S.H.I.E.L.D. Intelligence Dashboard</title>
<script src="chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#050505;
  --surface:#0d0d0d;
  --surface2:#141414;
  --border:#2a2a2a;
  --text:#c8c8c8;
  --muted:#555;
  --shield:{SC};
  --hidra:{HC};
  --gold:{GOLD_C};
}}
body{{font-family:'Share Tech Mono',monospace;background:var(--bg);color:var(--text);display:flex;min-height:100vh;overflow-x:hidden}}

/* SIDEBAR */
aside{{
  width:220px;min-width:220px;background:var(--surface);border-right:1px solid var(--border);
  display:flex;flex-direction:column;position:fixed;top:0;left:0;height:100vh;z-index:10;
}}
.logo{{padding:20px 16px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}}
.logo-text h2{{font-size:.85rem;font-weight:700;color:#fff;letter-spacing:3px}}
.logo-text p{{font-size:.65rem;color:var(--muted);margin-top:1px;letter-spacing:1px}}
.nav-section{{padding:16px 12px 4px;font-size:.6rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted)}}
nav a{{
  display:flex;align-items:center;gap:10px;padding:9px 16px;margin:2px 8px;
  border-radius:4px;cursor:pointer;font-size:.78rem;color:var(--muted);
  text-decoration:none;transition:.15s;border:none;background:none;width:calc(100% - 16px);text-align:left;
  letter-spacing:.5px;
}}
nav a:hover{{background:var(--surface2);color:var(--text)}}
nav a.active{{background:var(--surface2);color:#fff;border-left:2px solid #fff}}
.nav-icon{{font-size:1rem;width:20px;text-align:center}}
.sidebar-footer{{margin-top:auto;padding:16px;border-top:1px solid var(--border);font-size:.65rem;color:var(--muted);text-align:center;letter-spacing:.5px}}
.threat-level{{margin-top:8px;padding:6px 10px;background:#0a0a0a;border-radius:2px;border:1px solid #333}}
.threat-level span{{color:#fff;font-weight:600;font-size:.7rem;letter-spacing:1px}}

/* MAIN */
main{{margin-left:220px;flex:1;display:flex;flex-direction:column;min-height:100vh}}
.topbar{{
  padding:14px 28px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  background:var(--surface);position:sticky;top:0;z-index:5;
}}
.topbar h1{{font-size:1rem;font-weight:400;color:#fff;letter-spacing:2px;text-transform:uppercase}}
.topbar p{{font-size:.68rem;color:var(--muted);letter-spacing:.5px}}
.status-dot{{width:8px;height:8px;border-radius:50%;background:#22c55e;display:inline-block;margin-right:6px;box-shadow:0 0 6px #22c55e}}
.badge-live{{font-size:.65rem;color:#22c55e;background:#22c55e18;padding:3px 8px;border-radius:2px;border:1px solid #22c55e44;letter-spacing:1px}}

.page{{display:none;padding:24px 28px;flex:1}}
.page.active{{display:block}}

/* GRID */
.g{{display:grid;gap:14px;margin-bottom:18px}}
.g4{{grid-template-columns:repeat(4,1fr)}}
.g2{{grid-template-columns:1fr 1fr}}

/* CARDS */
.card{{
  background:var(--surface);border:1px solid var(--border);border-radius:2px;padding:18px;
  position:relative;overflow:hidden;
}}
.card::before{{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:var(--border);
}}
.card.red::before{{background:var(--hidra)}}
.card.gold::before{{background:var(--gold)}}
.ct{{font-size:.6rem;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:10px}}
.kr{{display:flex;gap:20px;align-items:flex-end}}
.kv{{font-size:1.65rem;font-weight:400;line-height:1}}
.ks{{font-size:.65rem;color:var(--muted);margin-bottom:3px;letter-spacing:1px}}
.bl{{color:var(--shield)}}.rd{{color:var(--hidra)}}.gd{{color:var(--gold)}}
.delta{{font-size:.68rem;margin-top:4px;color:var(--muted)}}
.delta.up{{color:#22c55e}}.delta.down{{color:var(--hidra)}}

/* CHARTS */
.chart{{background:var(--surface);border:1px solid var(--border);border-radius:2px;padding:18px}}
.chart-title{{font-size:.75rem;font-weight:400;color:#fff;margin-bottom:4px;letter-spacing:1px;text-transform:uppercase}}
.chart-sub{{font-size:.63rem;color:var(--muted);margin-bottom:14px;letter-spacing:.5px}}

/* TABLE */
table{{width:100%;border-collapse:collapse;font-size:.78rem}}
th{{text-align:left;padding:10px 12px;color:var(--muted);border-bottom:1px solid var(--border);font-weight:400;font-size:.65rem;text-transform:uppercase;letter-spacing:1px}}
td{{padding:10px 12px;border-bottom:1px solid var(--border)}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:var(--surface2)}}
.badge-ok{{background:#22c55e18;color:#22c55e;padding:2px 8px;border-radius:2px;font-size:.68rem;border:1px solid #22c55e33;white-space:nowrap}}
.badge-warn{{background:#f5a62318;color:var(--gold);padding:2px 8px;border-radius:2px;font-size:.68rem;border:1px solid #f5a62333;white-space:nowrap}}

/* SECTION LABEL */
.sl{{font-size:.6rem;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:10px;display:flex;align-items:center;gap:8px}}
.sl::after{{content:'';flex:1;height:1px;background:var(--border)}}

/* INSIGHT BOX */
.insight{{background:var(--surface);border:1px solid var(--border);border-left:2px solid #fff;border-radius:2px;padding:14px 16px;margin-bottom:18px;font-size:.78rem;line-height:1.7;letter-spacing:.3px}}
.insight strong{{color:#fff}}
.insight .tag{{display:inline-block;background:var(--surface2);color:#fff;font-size:.6rem;padding:2px 8px;border-radius:2px;margin-right:6px;font-weight:400;letter-spacing:2px;border:1px solid var(--border)}}

/* SPLASH SCREEN */
#splash{{
  position:fixed;inset:0;background:#000;z-index:9999;
  display:flex;align-items:center;justify-content:center;
  flex-direction:column;
}}
#splash::after{{
  content:'';position:absolute;inset:0;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(255,255,255,.015) 2px,rgba(255,255,255,.015) 4px);
  pointer-events:none;
}}
#splash-inner{{text-align:center;display:flex;flex-direction:column;align-items:center;gap:20px}}
#splash-logo{{opacity:0;animation:fadeIn .8s ease .3s forwards}}
#splash-logo svg{{filter:drop-shadow(0 0 20px rgba(255,255,255,.3))}}
#splash-title{{
  font-family:'Share Tech Mono',monospace;font-size:2rem;color:#fff;
  letter-spacing:8px;opacity:0;animation:fadeIn .6s ease 1s forwards;
}}
#splash-sub{{
  font-family:'Share Tech Mono',monospace;font-size:.65rem;color:#555;
  letter-spacing:4px;opacity:0;animation:fadeIn .6s ease 1.4s forwards;
}}
#splash-bar-wrap{{
  width:280px;height:2px;background:#1a1a1a;border:1px solid #333;
  opacity:0;animation:fadeIn .4s ease 1.8s forwards;overflow:hidden;
}}
#splash-bar{{height:100%;width:0;background:#fff;animation:loadBar 1.5s ease 2s forwards}}
#splash-status{{
  font-family:'Share Tech Mono',monospace;font-size:.65rem;color:#444;
  letter-spacing:2px;opacity:0;animation:fadeIn .4s ease 1.8s forwards;
}}
@keyframes fadeIn{{to{{opacity:1}}}}
@keyframes loadBar{{to{{width:100%}}}}


</style>
</head>
<body>

<!-- SIDEBAR -->
<aside>
  <div class="logo">
    {shield_svg}
    <div class="logo-text">
      <h2>S.H.I.E.L.D.</h2>
      <p>Analytics Division</p>
    </div>
  </div>
  <div class="nav-section">InteligÃªncia</div>
  <nav>
    <a class="active" onclick="go(0)" id="nav0"><span class="nav-icon">&#x1F4CA;</span> VisÃ£o Geral</a>
    <a onclick="go(1)" id="nav1"><span class="nav-icon">&#x1F3AF;</span> Share de Mercado</a>
    <a onclick="go(2)" id="nav2"><span class="nav-icon">&#x26A0;&#xFE0F;</span> Risco & InadimplÃªncia</a>
    <a onclick="go(3)" id="nav3"><span class="nav-icon">&#x1F6E1;&#xFE0F;</span> Qualidade de Dados</a>
    <a onclick="go(4)" id="nav4"><span class="nav-icon">&#x1F3AF;</span> Onde Atacar</a>
  </nav>
  <div class="sidebar-footer">
    <div>Dados: Janâ€“Dez 2025</div>
    <div class="threat-level">NÃ­vel de AmeaÃ§a<br><span>&#9632; HIDRA ATIVA</span></div>
  </div>
</aside>

<!-- MAIN -->
<main>
  <div class="topbar">
    <div>
      <h1>Central de InteligÃªncia Financeira</h1>
      <p>MissÃ£o: conter a expansÃ£o da Hidra nos mercados financeiros</p>
    </div>
    <div><span class="status-dot"></span><span class="badge-live">OPERACIONAL</span></div>
  </div>

  <!-- PAGE 0: VisÃ£o Geral -->
  <div class="page active" id="p0">
    <div class="insight">
      <span class="tag">BRIEFING</span> O Banco Shield opera <strong>{ks['sc']:,} contratos</strong> com carteira de <strong>R${ks['ss']}M</strong>, superando a Hidra em volume. InadimplÃªncia sob controle em <strong>{ks['si']}%</strong> vs {ks['hi']}% da Hidra. Qualidade dos dados: <strong>{ks['sq']}%</strong> de registros vÃ¡lidos.
    </div>
    <div class="sl">Indicadores Operacionais</div>
    <div class="g g3" style="grid-template-columns:repeat(3,1fr)">
      <div class="card">
        <div class="ct">Contratos Ativos</div>
        <div class="kr">
          <div><div class="ks bl">Shield</div><div class="kv bl">{ks['sc']:,}</div></div>
          <div><div class="ks rd">Hidra</div><div class="kv rd">{ks['hc']:,}</div></div>
        </div>
        <div class="delta up">&#x25B2; Shield lidera por {ks['sc']-ks['hc']:,} contratos</div>
      </div>
      <div class="card">
        <div class="ct">Saldo da Carteira</div>
        <div class="kr">
          <div><div class="ks bl">Shield</div><div class="kv bl">R${ks['ss']}M</div></div>
          <div><div class="ks rd">Hidra</div><div class="kv rd">R${ks['hs']}M</div></div>
        </div>
        <div class="delta up">&#x25B2; +R${round(ks['ss']-ks['hs'],2)}M de vantagem</div>
      </div>
      <div class="card {'red' if ks['si'] > ks['hi'] else ''}">
        <div class="ct">InadimplÃªncia 30+ DPD</div>
        <div class="kr">
          <div><div class="ks bl">Shield</div><div class="kv bl">{ks['si']}%</div></div>
          <div><div class="ks rd">Hidra</div><div class="kv rd">{ks['hi']}%</div></div>
        </div>
        <div class="delta {'down' if ks['si'] > ks['hi'] else 'up'}">{'&#x25BC; Shield com maior risco' if ks['si'] > ks['hi'] else '&#x25B2; Shield com menor risco'}</div>
      </div>
    </div>
    <div class="sl">EvoluÃ§Ã£o da Carteira â€” 2025</div>
    <div class="g g2">
      <div class="chart">
        <div class="chart-title">Saldo Total por MÃªs (R$ M)</div>
        <div class="chart-sub">ExposiÃ§Ã£o financeira acumulada â€” Shield vs Hidra</div>
        <canvas id="ev-saldo"></canvas>
      </div>
      <div class="chart">
        <div class="chart-title">Novos Contratos por MÃªs</div>
        <div class="chart-sub">Volume de originaÃ§Ã£o mensal comparado</div>
        <canvas id="ev-cont"></canvas>
      </div>
    </div>
  </div>

  <!-- PAGE 1: Share -->
  <div class="page" id="p1">
    <div class="insight">
      <span class="tag">ALERTA</span> A Hidra domina o segmento de <strong>Seguros ({seg_hidra_pct}%)</strong>. Shield lidera em Financiamento, EmprÃ©stimo e Conta. Oportunidade: atacar o nicho de Seguros onde a Hidra avanÃ§a.
    </div>
    <div class="sl">Disputa por TerritÃ³rio</div>
    <div class="g g2">
      <div class="chart">
        <div class="chart-title">Share de Contratos por Categoria (%)</div>
        <div class="chart-sub">ParticipaÃ§Ã£o relativa â€” quem domina cada segmento</div>
        <canvas id="share"></canvas>
      </div>
      <div class="chart">
        <div class="chart-title">Volume Absoluto por Categoria</div>
        <div class="chart-sub">Total de contratos â€” onde estÃ¡ o maior campo de batalha</div>
        <canvas id="vol-cat"></canvas>
      </div>
    </div>
  </div>

  <!-- PAGE 2: Risco -->
  <div class="page" id="p2">
    <div class="insight">
      <span class="tag">AMEAÃ‡A</span> ConsÃ³rcio Xandar (Hidra) lidera inadimplÃªncia com <strong>2.19%</strong>. SÃ£o Paulo e Wakanda sÃ£o as localidades de maior risco para o Shield. Risk score mÃ©dio da Hidra (~0.14) Ã© 55% maior que o Shield (~0.09).
    </div>
    <div class="sl">Mapa de Risco Operacional</div>
    <div class="g g2">
      <div class="chart">
        <div class="chart-title">Top Produtos â€” Ãndice de InadimplÃªncia (%)</div>
        <div class="chart-sub">Azul = Shield Â· Vermelho = Hidra</div>
        <canvas id="rp" style="max-height:400px"></canvas>
      </div>
      <div class="chart">
        <div class="chart-title">Top Localidades â€” Ãndice de InadimplÃªncia (%)</div>
        <div class="chart-sub">ConcentraÃ§Ã£o geogrÃ¡fica de risco</div>
        <canvas id="rl" style="max-height:400px"></canvas>
      </div>
    </div>
  </div>

  <!-- PAGE 3: Qualidade -->
  <div class="page" id="p3">
    <div class="insight">
      <span class="tag">GOVERNANÃ‡A</span> <strong>{grafias_corrigidas} registros</strong> com nome de banco invÃ¡lido foram corrigidos automaticamente. Shield: <strong>{int(shield_row.err_id_duplicado)} IDs duplicados</strong>, {int(shield_row.err_periodo_invalido)} perÃ­odos fora do range. Hidra: <strong>{int(hidra_row.err_periodo_invalido)} perÃ­odos invÃ¡lidos</strong>, {int(hidra_row.err_produto_fk)} FKs de produto quebradas.
    </div>
    <div class="sl">Controles de Qualidade</div>
    <div class="g g4">
      <div class="card gold">
        <div class="ct">Nomes Corrigidos</div>
        <div class="kr"><div><div class="kv gd">{grafias_corrigidas}</div><div class="ks" style="margin-top:4px">registros normalizados</div></div></div>
      </div>
      <div class="card">
        <div class="ct">IDs Duplicados</div>
        <div class="kr">
          <div><div class="ks bl">Shield</div><div class="kv bl">{int(shield_row.err_id_duplicado)}</div></div>
          <div><div class="ks rd">Hidra</div><div class="kv rd">{int(hidra_row.err_id_duplicado)}</div></div>
        </div>
      </div>
      <div class="card">
        <div class="ct">PerÃ­odo InvÃ¡lido</div>
        <div class="kr">
          <div><div class="ks bl">Shield</div><div class="kv bl">{int(shield_row.err_periodo_invalido)}</div></div>
          <div><div class="ks rd">Hidra</div><div class="kv rd">{int(hidra_row.err_periodo_invalido)}</div></div>
        </div>
      </div>
      <div class="card">
        <div class="ct">FK Quebrada (Produto)</div>
        <div class="kr">
          <div><div class="ks bl">Shield</div><div class="kv bl">{int(shield_row.err_produto_fk)}</div></div>
          <div><div class="ks rd">Hidra</div><div class="kv rd">{int(hidra_row.err_produto_fk)}</div></div>
        </div>
      </div>
    </div>
    <div class="insight" style="border-color:#f5a62344;background:linear-gradient(135deg,#1a150a,#2a1f0a);margin-bottom:18px">
      <span class="tag" style="background:#3a2a10;color:{GOLD_C}">PONTO DE ATENÃ‡ÃƒO</span>
      <strong style="color:{GOLD_C}">{bgf_total} contratos</strong> apresentam saldo em aberto maior que o valor financiado no mÃªs â€”
      <strong style="color:{SC}">{bgf_shield} no Shield</strong> (diferenÃ§a mÃ©dia R$ {bgf_media_s:,.2f}) e
      <strong style="color:{HC}">{bgf_hidra} na Hidra</strong> (diferenÃ§a mÃ©dia R$ {bgf_media_h:,.2f}).
      Desses contratos, <strong style="color:{GOLD_C}">{bgf_adim_s}% dos casos Shield</strong> e <strong style="color:{GOLD_C}">{bgf_adim_h}% dos casos Hidra</strong> sÃ£o adimplentes (dpd = 0),
      o que indica que a diferenÃ§a provavelmente nÃ£o Ã© decorrente de juros por inadimplÃªncia.
      Os registros foram mantidos na base. Recomenda-se validaÃ§Ã£o com a Ã¡rea de negÃ³cio.
    </div>
    <div class="g g2">
      <div class="chart">
        <div class="chart-title">Erros por Tipo de Regra</div>
        <div class="chart-sub">Quantidade de registros com violaÃ§Ã£o por categoria</div>
        <canvas id="qd"></canvas>
      </div>
      <div class="chart">
        <div class="chart-title">RelatÃ³rio de Integridade por Banco</div>
        <div class="chart-sub">VisÃ£o consolidada das anomalias detectadas no pipeline</div>
        <table>
          <thead><tr><th>Banco</th><th>Total</th><th>ID Dup</th><th>PerÃ­odo</th><th>Prod FK</th><th>Local FK</th><th>Valor Neg</th><th>Status</th></tr></thead>
          <tbody>{qual_rows}</tbody>
        </table>
      </div>
    </div>
  </div>
  <!-- PAGE 4: Onde Atacar -->
  <div class="page" id="p4">
    <div class="insight">
      <span class="tag">MISSÃƒO</span> Duas frentes de ataque identificadas: nichos onde a <strong>Hidra estÃ¡ vulnerÃ¡vel</strong> (risco alto, carteira deteriorando) e nichos onde a <strong>Hidra domina e o Shield estÃ¡ perdendo terreno</strong> â€” prioridade estratÃ©gica de recuperaÃ§Ã£o.
    </div>
    <div class="sl">Frente 1 â€” Hidra VulnerÃ¡vel (entrar agora com baixo risco)</div>
    <div class="g g2">
      <div class="chart">
        <div class="chart-title">Score de Vulnerabilidade da Hidra</div>
        <div class="chart-sub">Risco alto + inadimplÃªncia alta = janela de entrada para o Shield</div>
        <canvas id="ov-score" style="max-height:220px"></canvas>
      </div>
      <div class="chart">
        <div class="chart-title">Risk Score da Hidra nesses Nichos</div>
        <div class="chart-sub">Quanto maior, mais a carteira da Hidra estÃ¡ deteriorada</div>
        <canvas id="ov-risk" style="max-height:220px"></canvas>
      </div>
    </div>
    <div class="sl">Frente 2 â€” Recuperar TerritÃ³rio (Shield perdendo para a Hidra)</div>
    <div class="g g2">
      <div class="chart">
        <div class="chart-title">Score de RecuperaÃ§Ã£o de Mercado</div>
        <div class="chart-sub">Hidra forte + Shield fraco = territÃ³rio a reconquistar</div>
        <canvas id="or-score" style="max-height:220px"></canvas>
      </div>
      <div class="chart">
        <div class="chart-title">Share Hidra vs Shield nesses Nichos (%)</div>
        <div class="chart-sub">DistÃ¢ncia a recuperar em cada nicho estratÃ©gico</div>
        <canvas id="or-share" style="max-height:220px"></canvas>
      </div>
    </div>
  </div>
</main>

<!-- SPLASH SCREEN -->
<div id="splash">
  <div id="splash-inner">
    <div id="splash-logo">
      <svg viewBox="0 0 100 110" width="120" height="120" xmlns="http://www.w3.org/2000/svg">
        <path d="M50 5 L95 25 L95 60 Q95 90 50 105 Q5 90 5 60 L5 25 Z" fill="#000" stroke="#fff" stroke-width="2"/>
        <path d="M50 18 L82 33 L82 60 Q82 80 50 92 Q18 80 18 60 L18 33 Z" fill="none" stroke="#555" stroke-width="1"/>
        <text x="50" y="68" text-anchor="middle" font-size="38" font-weight="bold" fill="#fff" font-family="Arial">S</text>
      </svg>
    </div>
    <div id="splash-title">S.H.I.E.L.D.</div>
    <div id="splash-sub">STRATEGIC HOMELAND INTERVENTION</div>
    <div id="splash-bar-wrap"><div id="splash-bar"></div></div>
    <div id="splash-status">INITIALIZING...</div>
  </div>
</div>

<script>
Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = '#1e2d4a';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;

var SC='{SC}', HC='{HC}', SC2='{SC2}', HC2='{HC2}';
var built = {{}};

function go(i) {{
  document.querySelectorAll('.page').forEach(function(p,idx){{ p.classList.toggle('active',idx===i); }});
  document.querySelectorAll('nav a').forEach(function(a,idx){{ a.classList.toggle('active',idx===i); }});
  if(!built[i]){{ buildPage(i); built[i]=true; }}
}}

function hbar(labels, datasets, pct) {{
  return {{type:'bar', data:{{labels:labels,datasets:datasets}}, options:{{
    responsive:true, indexAxis:'y',
    plugins:{{legend:{{labels:{{color:'#94a3b8',font:{{size:11}}}}}}}},
    scales:{{
      x:{{grid:{{color:'#1e2d4a'}},ticks:{{color:'#64748b',callback:pct?function(v){{return v+'%';}}:null}}}},
      y:{{grid:{{display:false}},ticks:{{color:'#94a3b8',font:{{size:10}}}}}}
    }}
  }}}};
}}

function buildPage(i) {{
  if(i===0) {{
    new Chart(document.getElementById('ev-saldo').getContext('2d'), {{type:'line', data:{{
      labels:{ev_labels},
      datasets:[
        {{label:'Shield',data:{ev_ss},borderColor:SC,backgroundColor:SC2,fill:true,tension:.4,pointRadius:4,pointBackgroundColor:SC}},
        {{label:'Hidra', data:{ev_hs},borderColor:HC,backgroundColor:HC2,fill:true,tension:.4,pointRadius:4,pointBackgroundColor:HC}}
      ]}}, options:{{responsive:true,
        plugins:{{legend:{{labels:{{color:'#94a3b8'}}}}}},
        scales:{{
          x:{{grid:{{color:'#1e2d4a'}},ticks:{{color:'#64748b'}}}},
          y:{{grid:{{color:'#1e2d4a'}},ticks:{{color:'#64748b',callback:function(v){{return 'R$'+v+'M';}}}}}}
        }}
    }}}});
    new Chart(document.getElementById('ev-cont').getContext('2d'), {{type:'bar', data:{{
      labels:{ev_labels},
      datasets:[
        {{label:'Shield',data:{ev_sc},backgroundColor:SC2,borderColor:SC,borderWidth:1,borderRadius:4}},
        {{label:'Hidra', data:{ev_hc},backgroundColor:HC2,borderColor:HC,borderWidth:1,borderRadius:4}}
      ]}}, options:{{responsive:true,
        plugins:{{legend:{{labels:{{color:'#94a3b8'}}}}}},
        scales:{{
          x:{{grid:{{color:'#1e2d4a'}},ticks:{{color:'#64748b'}}}},
          y:{{grid:{{color:'#1e2d4a'}},ticks:{{color:'#64748b'}}}}
        }}
    }}}});
  }}
  if(i===1) {{
    new Chart(document.getElementById('share').getContext('2d'), {{type:'bar', data:{{
      labels:{sh_cat},
      datasets:[
        {{label:'Shield',data:{sh_s},backgroundColor:SC,borderRadius:4}},
        {{label:'Hidra', data:{sh_h},backgroundColor:HC,borderRadius:4}}
      ]}}, options:{{responsive:true, indexAxis:'y',
        plugins:{{legend:{{labels:{{color:'#94a3b8'}}}}}},
        scales:{{
          x:{{stacked:true,max:100,grid:{{color:'#1e2d4a'}},ticks:{{color:'#64748b',callback:function(v){{return v+'%';}}}}}},
          y:{{stacked:true,grid:{{display:false}},ticks:{{color:'#94a3b8'}}}}
        }}
    }}}});
    new Chart(document.getElementById('vol-cat').getContext('2d'), hbar({sh_cat}, [
      {{label:'Shield',data:{sh_cs},backgroundColor:SC,borderRadius:4}},
      {{label:'Hidra', data:{sh_ch},backgroundColor:HC,borderRadius:4}}
    ], false));
  }}
  if(i===2) {{
    new Chart(document.getElementById('rp').getContext('2d'), hbar({rp_n}, [
      {{label:'InadimplÃªncia %',data:{rp_v},backgroundColor:{rp_col},borderRadius:4}}
    ], true));
    new Chart(document.getElementById('rl').getContext('2d'), hbar({rl_n}, [
      {{label:'InadimplÃªncia %',data:{rl_v},backgroundColor:{rl_col},borderRadius:4}}
    ], true));
  }}
  if(i===3) {{
    new Chart(document.getElementById('qd').getContext('2d'), hbar({qd_l}, [
      {{label:'Shield',data:{qd_s},backgroundColor:SC,borderRadius:4}},
      {{label:'Hidra', data:{qd_h},backgroundColor:HC,borderRadius:4}}
    ], false));
  }}
  if(i===4) {{
    var ov_label={ov_label}, ov_score={ov_score}, ov_ri={ov_ri};
    var or_label={or_label}, or_score={or_score}, or_sh={or_sh}, or_ss={or_ss};
    new Chart(document.getElementById('ov-score').getContext('2d'), hbar(ov_label,[
      {{label:'Score Vulnerabilidade',data:ov_score,backgroundColor:'#22c55ecc',borderRadius:4}}
    ],false));
    new Chart(document.getElementById('ov-risk').getContext('2d'), hbar(ov_label,[
      {{label:'Risk Score Hidra',data:ov_ri,backgroundColor:HC,borderRadius:4}}
    ],false));
    new Chart(document.getElementById('or-score').getContext('2d'), hbar(or_label,[
      {{label:'Score Recuperacao',data:or_score,backgroundColor:'#f5a623cc',borderRadius:4}}
    ],false));
    new Chart(document.getElementById('or-share').getContext('2d'), hbar(or_label,[
      {{label:'Hidra %',data:or_sh,backgroundColor:HC,borderRadius:4}},
      {{label:'Shield %',data:or_ss,backgroundColor:SC,borderRadius:4}}
    ],true));
  }}
}}

// SPLASH
var splashMsgs = ['INITIALIZING...','LOADING INTEL...','DECRYPTING DATA...','ACCESS GRANTED'];
var si = 0;
var splashInterval = setInterval(function() {{
  si++;
  if(si < splashMsgs.length) {{
    document.getElementById('splash-status').textContent = splashMsgs[si];
  }} else {{
    clearInterval(splashInterval);
    setTimeout(function() {{
      var s = document.getElementById('splash');
      s.style.transition = 'opacity .6s ease';
      s.style.opacity = '0';
      setTimeout(function() {{ s.style.display = 'none'; }}, 600);
    }}, 400);
  }}
}}, 900);

buildPage(0);
</script>
</body>
</html>"""

    OUT.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado: {OUT}")

if __name__ == "__main__":
    main()

