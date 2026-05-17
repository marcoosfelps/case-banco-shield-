# 📖 Documentação Técnica — Banco Shield vs Hidra

## Sumário
1. [Pipeline de Dados](#1-pipeline-de-dados)
2. [Estrutura do Banco de Dados](#2-estrutura-do-banco-de-dados)
3. [Tabelas de Dimensão](#3-tabelas-de-dimensão)
4. [Dicionário de Colunas](#4-dicionário-de-colunas)
5. [KPIs e Métricas](#5-kpis-e-métricas)

---

## 1. Pipeline de Dados

O pipeline segue a **Arquitetura Medalhão** em três camadas, orquestradas pelo `main.py`:

```
data/raw/ (CSV)
    ↓
[Bronze] Ingestão bruta
    ↓
[Silver] Limpeza + Validação
    ↓
[Gold] Agregações analíticas
    ↓
[Dashboard] HTML interativo
```

### Camada Bronze — `src/bronze.py`
Responsável pela ingestão dos arquivos CSV brutos no DuckDB sem transformações.

- Lê os CSVs de `data/raw/` com todos os campos como `VARCHAR`
- Adiciona metadados de rastreabilidade: `_source_file` e `_ingested_at`
- Persiste as tabelas como `bronze_<tabela>` no DuckDB

### Camada Silver — `src/silver/engine.py`
Motor genérico de validação configurado via `config/rules.json`. Aplica as seguintes etapas em ordem:

| Etapa | Descrição |
|-------|-----------|
| Normalização por regex | Corrige grafias inválidas do campo `bank` (ex: `hydra` → `Hidra`) |
| Normalização textual | Strip + Title Case nos campos de texto |
| Cast de tipos | Converte colunas para os tipos corretos (int, float, string) |
| Campos obrigatórios | Sinaliza nulos em campos requeridos com `_err_<campo>_null` |
| Unicidade | Detecta duplicatas com `_err_<campo>_dup` |
| Chaves estrangeiras | Valida integridade referencial com `_err_<campo>_fk` |
| Regras de domínio | Valida enums e ranges com `_err_<campo>_domain` |
| Campos não-negativos | Sinaliza valores negativos com `_err_<campo>_negative` |
| Regras cruzadas | Valida condições entre colunas (ex: `delinquent_amount_30p` deve ser 0 quando `dpd < 30`) |
| Flag consolidada | `_is_valid = true` quando nenhum erro foi detectado |

Persiste as tabelas como `silver_<tabela>` no DuckDB.

### Camada Gold — `src/gold.py`
Executa queries analíticas sobre os dados válidos da Silver e exporta os resultados como tabelas DuckDB (`gold_<nome>`) e arquivos CSV em `data/gold/`.

### Dashboard — `src/generate_dashboard.py`
Lê os CSVs da Gold e gera `dashboard/index.html` — um dashboard HTML estático com Chart.js, sem dependência de servidor ou CDN externo.

---

## 2. Estrutura do Banco de Dados

O banco DuckDB (`data/pipeline.duckdb`) contém as seguintes tabelas após execução do pipeline:

### Camada Bronze
| Tabela | Descrição |
|--------|-----------|
| `bronze_fato_contratos` | Contratos brutos — todos os campos como VARCHAR |
| `bronze_dim_produto` | Dimensão de produtos bruta |
| `bronze_dim_localidade` | Dimensão de localidades bruta |
| `bronze_dim_banco` | Dimensão de bancos bruta |

### Camada Silver
| Tabela | Descrição |
|--------|-----------|
| `silver_fato_contratos` | Contratos com tipos corretos, flags de erro e `_is_valid` |
| `silver_dim_produto` | Produtos validados |
| `silver_dim_localidade` | Localidades validadas |
| `silver_dim_banco` | Bancos validados |

### Camada Gold
| Tabela | Descrição |
|--------|-----------|
| `gold_carteira_banco_mes` | Evolução mensal de contratos e saldo por banco |
| `gold_produtos_mais_vendidos` | Volume, saldo e inadimplência por produto e banco |
| `gold_inadimplencia_localidade` | Índice de inadimplência por localidade e banco |
| `gold_share_mercado` | Share de contratos e valor por categoria de produto |
| `gold_ataque_vulneravel` | Top 5 nichos onde a Hidra está com risco/inadimplência elevados |
| `gold_ataque_recuperar` | Top 5 nichos onde a Hidra domina e o Shield pode recuperar |
| `gold_atencao_balance` | Contratos com saldo em aberto maior que o valor financiado |
| `gold_qualidade_dados` | Resumo de erros de qualidade por banco |

---

## 3. Tabelas de Dimensão

### `dim_produto`
Catálogo dos produtos financeiros disponíveis no universo do case.

| product_id | product_name | category | tenor_months | base_rate_apr |
|---|---|---|---|---|
| Identificador único | Nome do produto | Categoria (Financiamento, Empréstimo, Seguro, Conta, Consórcio, Investimentos) | Prazo em meses | Taxa base anual (APR) |

### `dim_localidade`
Cidades e territórios onde os contratos foram originados.

| location_id | location_name | macro_region | risk_factor_region |
|---|---|---|---|
| Identificador único | Nome da localidade | Macro-região (Brasil, Europa, Galáxia etc.) | Fator de risco regional (0–10) |

### `dim_banco`
Instituições financeiras presentes no dataset.

| bank_id | bank_name |
|---|---|
| 1 | Banco Shield |
| 2 | Hidra |

---

## 4. Dicionário de Colunas

### `fato_contratos` (tabela principal)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `contract_id` | VARCHAR | Identificador único do contrato (PK lógica) |
| `ano_mes` | INT (AAAAMM) | Mês de referência do contrato (ex: 202501) |
| `bank` | VARCHAR | Instituição: `Banco Shield` ou `Hidra` |
| `product_id` | INT | FK → `dim_produto.product_id` |
| `location_id` | INT | FK → `dim_localidade.location_id` |
| `units` | INT | Quantidade de contratos no registro (1 por linha) |
| `financed_amount` | FLOAT | Valor financiado/contratado no mês (R$) |
| `outstanding_balance` | FLOAT | Saldo em aberto (R$) |
| `dpd` | INT | Days Past Due — dias em atraso (0 = adimplente) |
| `delinquent_amount_30p` | FLOAT | Valor em atraso para contratos com 30+ DPD (R$) |
| `risk_score` | FLOAT (0–1) | Score de risco sintético — quanto maior, mais risco |

### Colunas de Controle (Silver)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `_source_file` | VARCHAR | Nome do arquivo CSV de origem |
| `_ingested_at` | VARCHAR | Timestamp UTC de ingestão |
| `_fixed_bank` | BOOLEAN | `true` se a grafia do banco foi corrigida por regex |
| `_err_*_null` | BOOLEAN | Campo obrigatório com valor nulo |
| `_err_*_dup` | BOOLEAN | Valor duplicado em campo que deveria ser único |
| `_err_*_fk` | BOOLEAN | Valor não encontrado na tabela de dimensão referenciada |
| `_err_*_domain` | BOOLEAN | Valor fora do domínio permitido (enum ou range) |
| `_err_*_negative` | BOOLEAN | Valor negativo em campo que deve ser não-negativo |
| `_err_delinquent_30p` | BOOLEAN | `delinquent_amount_30p > 0` com `dpd < 30` (regra cruzada) |
| `_is_valid` | BOOLEAN | `true` quando nenhum erro foi detectado no registro |

### `gold_carteira_banco_mes`

| Coluna | Descrição |
|--------|-----------|
| `ano_mes` | Mês de referência |
| `bank` | Banco |
| `contratos` | Total de contratos válidos no mês |
| `total_financiado` | Soma dos valores financiados no mês (R$) |
| `saldo_total` | Soma do saldo em aberto no mês (R$) |

### `gold_produtos_mais_vendidos`

| Coluna | Descrição |
|--------|-----------|
| `bank` | Banco |
| `product_name` | Nome do produto |
| `category` | Categoria do produto |
| `contratos` | Total de contratos |
| `total_financiado` | Soma dos valores financiados (R$) |
| `saldo_total` | Soma do saldo em aberto (R$) |
| `saldo_inadimplente` | Soma do saldo inadimplente 30+ DPD (R$) |
| `indice_inadimplencia` | `saldo_inadimplente / saldo_total` |
| `risk_score_medio` | Média do risk score |

### `gold_share_mercado`

| Coluna | Descrição |
|--------|-----------|
| `category` | Categoria do produto |
| `contratos_shield` / `contratos_hidra` | Volume de contratos por banco |
| `contratos_total` | Total de contratos na categoria |
| `share_shield` / `share_hidra` | Participação relativa por número de contratos (0–1) |
| `financiado_shield` / `financiado_hidra` | Valor financiado por banco (R$) |
| `share_valor_shield` | Participação do Shield por valor financiado (0–1) |

### `gold_inadimplencia_localidade`

| Coluna | Descrição |
|--------|-----------|
| `location_name` | Nome da localidade |
| `macro_region` | Macro-região |
| `risk_factor_region` | Fator de risco regional (0–10) |
| `bank` | Banco |
| `contratos` | Total de contratos |
| `saldo_total` | Saldo em aberto (R$) |
| `saldo_inadimplente` | Saldo inadimplente 30+ DPD (R$) |
| `indice_inadimplencia` | `saldo_inadimplente / saldo_total` |

### `gold_ataque_vulneravel`

| Coluna | Descrição |
|--------|-----------|
| `location_name` / `product_name` / `category` | Identificação do nicho |
| `contratos_total` / `contratos_hidra` / `contratos_shield` | Volume por banco |
| `share_hidra` | Participação da Hidra no nicho |
| `risk_hidra` | Risk score médio da Hidra no nicho |
| `inad_hidra` | Índice de inadimplência da Hidra no nicho |
| `saldo_total` | Saldo total do nicho (R$) |
| `score_vulnerabilidade` | Score composto: `risk_hidra×0.5 + inad_hidra×10×0.3 + share_hidra×0.2` |

### `gold_ataque_recuperar`

| Coluna | Descrição |
|--------|-----------|
| `location_name` / `product_name` / `category` | Identificação do nicho |
| `share_hidra` / `share_shield` | Participação de cada banco |
| `saldo_total` | Saldo total do nicho (R$) |
| `score_recuperacao` | Score composto: `share_hidra×0.6 + (1 - share_shield)×0.4` |

### `gold_qualidade_dados`

| Coluna | Descrição |
|--------|-----------|
| `bank` | Banco |
| `total` | Total de registros |
| `err_id_duplicado` | Contratos com `contract_id` duplicado |
| `err_bank_invalido` | Registros com banco fora do domínio permitido |
| `err_periodo_invalido` | Registros com `ano_mes` fora do range 202501–202512 |
| `err_produto_fk` | Registros com `product_id` inexistente na dimensão |
| `err_localidade_fk` | Registros com `location_id` inexistente na dimensão |
| `err_valor_negativo` | Registros com `financed_amount` ou `outstanding_balance` negativos |
| `err_delinquent_30p` | Registros com `delinquent_amount_30p > 0` e `dpd < 30` |
| `err_risk_score` | Registros com `risk_score` fora do range 0–1 |
| `pct_invalido` | Percentual de registros inválidos (0–1) |

---

## 5. KPIs e Métricas

### Indicadores de Carteira

| KPI | Fórmula | Onde é calculado |
|-----|---------|-----------------|
| **Saldo Total** | `SUM(outstanding_balance)` | `gold_carteira_banco_mes` |
| **Total Financiado** | `SUM(financed_amount)` | `gold_carteira_banco_mes` |
| **Volume de Contratos** | `COUNT(*)` | `gold_carteira_banco_mes` |

### Indicadores de Risco

| KPI | Fórmula | Onde é calculado |
|-----|---------|-----------------|
| **Índice de Inadimplência** | `SUM(delinquent_amount_30p) / SUM(outstanding_balance)` | `gold_produtos_mais_vendidos`, `gold_inadimplencia_localidade` |
| **Risk Score Médio** | `AVG(risk_score)` | `gold_produtos_mais_vendidos` |
| **Saldo Inadimplente** | `SUM(delinquent_amount_30p)` onde `dpd >= 30` | `gold_produtos_mais_vendidos` |

### Indicadores de Mercado

| KPI | Fórmula | Onde é calculado |
|-----|---------|-----------------|
| **Share de Contratos** | `contratos_banco / contratos_total` | `gold_share_mercado` |
| **Share de Valor** | `financiado_banco / SUM(financiado_total)` | `gold_share_mercado` |

### Scores Estratégicos

| Score | Fórmula | Interpretação |
|-------|---------|---------------|
| **Vulnerabilidade da Hidra** | `risk_hidra × 0.5 + inad_hidra × 10 × 0.3 + share_hidra × 0.2` | Quanto maior, mais a carteira da Hidra está deteriorada — janela de entrada para o Shield |
| **Recuperação de Mercado** | `share_hidra × 0.6 + (1 - share_shield) × 0.4` | Quanto maior, mais urgente é a ação do Shield para reconquistar o nicho |

### Indicadores de Qualidade

| KPI | Fórmula | Onde é calculado |
|-----|---------|-----------------|
| **% Registros Inválidos** | `SUM(NOT _is_valid) / COUNT(*)` | `gold_qualidade_dados` |
| **Registros Corrigidos** | `SUM(_fixed_bank = true)` | `silver_fato_contratos` |
| **Contratos com Saldo > Financiado** | `COUNT(*) WHERE outstanding_balance > financed_amount` | `gold_atencao_balance` |
