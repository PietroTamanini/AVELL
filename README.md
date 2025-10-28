# 🚀 Sistema Avell: Gestão Inteligente de Ativos (Empréstimos & Comodatos) 📈

> Uma solução web completa e robusta construída em Python/Flask para centralizar o controle total de notebooks, clientes e o ciclo de vida de empréstimos e comodatos, garantindo rastreabilidade e segurança máxima dos ativos da Avell.

---

## ✨ Destaques & Funcionalidades (O que o sistema faz?)

O **Sistema Avell** atua como o seu centro de comando para gestão de T.I., transformando a logística de ativos em um processo eficiente e auditável.

* **📊 Dashboard Gerencial:** Obtenha uma visão instantânea com estatísticas vitais sobre o status dos seus ativos (disponíveis, emprestados, em comodato, etc.).
* **💻 Gestão Completa de Entidades:** Cadastros detalhados de **Notebooks** e **Clientes**, incluindo especificações técnicas e histórico de movimentação.
* **✅ Controle de Operações:** Módulos separados e otimizados para gerenciar **Empréstimos** (curto prazo) e **Comodatos** (longo prazo).
* **🔒 Segurança de Dados:** Validações rigorosas em tempo real (CPF/CNPJ, E-mail) para garantir a integridade de cada registro.
* **📜 Relatórios e Auditoria:** Geração de relatórios e gráficos para facilitar a conformidade e a auditoria de todos os movimentos.
* **⚙️ Usabilidade Moderna:** Interface de usuário com **Tema Claro/Escuro** e design unificado para uma experiência agradável.

---

## 🛠️ Stack Tecnológico

| Categoria | Tecnologia | Detalhes |
| :--- | :--- | :--- |
| **Backend** | Python 3+ | Linguagem de programação principal. |
| **Framework** | **Flask** | Micro-framework web leve e poderoso. |
| **Banco de Dados** | **SQLAlchemy** / SQLite | Mapeamento Objeto-Relacional (ORM) usando um banco de dados local. |
| **Segurança** | **Hash SHA256** | Proteção de senhas. |

---

## ⚙️ Primeiros Passos: Instalação Rápida

Para rodar o sistema localmente, siga estes passos:

### 1. Preparação do Ambiente

```bash
# ⬇️ Clonar o repositório
git clone (https://github.com/PietroTamanini/AVELL.git)
cd AVELL

# 🐍 Criar e ativar o ambiente virtual
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows0

# 📦 Instalar as bibliotecas necessárias
pip install Flask Flask-SQLAlchemy

# ▶️ Inicializar o sistema
python app.py

#🔑 Credenciais Padrão (Administrador)
| Usuário (E-mail) | Senha |
| admin  | admin |
