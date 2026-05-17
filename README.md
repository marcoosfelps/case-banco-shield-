# 🛡️ Banco Shield vs Hidra — Pipeline de Dados & Dashboard de Inteligência

Case técnico de Engenharia e Análise de Dados com pipeline medalhão (Bronze → Silver → Gold) e dashboard interativo para análise competitiva entre o **Banco Shield** e a **Hidra** no universo Marvel.

---

## 📋 Índice

1. [Visão Geral](#-visão-geral)
2. [Arquitetura](#️-arquitetura)
3. [Estrutura do Projeto](#-estrutura-do-projeto)
4. [Como Rodar](#-como-rodar)
5. [Regras de Qualidade](#-regras-de-qualidade)
6. [Stack](#️-stack)
7. [Documentação Técnica](#-documentação-técnica)

---

## 📊 Visão Geral

O projeto processa **6.000 contratos financeiros** ao longo de 2025, aplicando regras de qualidade de dados, análises de negócio e gerando um dashboard HTML completo — tudo a partir de um único comando.

**Destaques:**
- 6.000 contratos | 5.908 válidos após limpeza (1,5% de inválidos)
- 20 grafias incorretas do nome do banco corrigidas automaticamente
- Shield lidera em volume de contratos e saldo de carteira
- Hidra domina o segmento de Seguros (51,8% de share)
- 514 contratos com saldo em aberto > valor financiado — sinalizados para revisão

---

## 🏗️ Arquitetura

```
CSV (raw) → Bronze → Silver → Gold → Dashboard HTML
```

| Camada | Responsabilidade |
|--------|-----------------|
| **Bronze** | Ingestão dos CSVs no DuckDB com metadados de rastreabilidade |
| **Silver** | Limpeza, tipagem e validação de regras de negócio |
| **Gold** | Agregações analíticas exportadas em CSV e tabelas DuckDB |
| **Dashboard** | Visualização interativa gerada em HTML estático (Chart.js) |

---

## 📁 Estrutura do Projeto

```
.
├── main.py                        # Orquestrador do pipeline
├── requirements.txt
├── README.md
├── DOCUMENTATION.md               # Documentação técnica completa
├── config/
│   └── rules.json                 # Regras de qualidade externalizadas
├── data/
│   └── raw/                       # Dados de entrada
│       ├── fato_contratos.csv
│       ├── dim_produto.csv
│       ├── dim_localidade.csv
│       ├── dim_banco.csv
│       └── metadados.txt
├── src/
│   ├── bronze.py
│   ├── gold.py
│   ├── generate_dashboard.py
│   └── silver/
│       ├── engine.py
│       └── fato_contratos.py
├── notebooks/
│   └── eda.ipynb                  # Análise exploratória
└── dashboard/
    └── chart.umd.min.js
```

> `data/gold/`, `data/pipeline.duckdb` e `dashboard/index.html` são gerados pelo pipeline e estão no `.gitignore`.

---

## 🚀 Como Rodar

**Pré-requisitos:** Python 3.10+

```bash
# 1. Clone o repositório
git clone https://github.com/marcoosfelps/case-banco-shield-.git
cd case-banco-shield-

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute o pipeline completo
python main.py
```

Abra `dashboard/index.html` no navegador para visualizar os resultados.

---

## 🔍 Regras de Qualidade

Configuradas via `config/rules.json` e aplicadas pelo `src/silver/engine.py`:

- Integridade referencial (FK de produto, localidade e banco)
- Domínios válidos (banco, período, risk score)
- Campos obrigatórios e unicidade do `contract_id`
- Valores não-negativos (`financed_amount`, `outstanding_balance`)
- Regra cruzada: `delinquent_amount_30p` deve ser 0 quando `dpd < 30`
- Normalização automática de grafias inválidas do nome do banco

---

## 🛠️ Stack

**Python** · **DuckDB** · **Pandas** · **Chart.js** · **HTML/CSS**

---

> Documentação técnica completa em [DOCUMENTATION.md](DOCUMENTATION.md)
