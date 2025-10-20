from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import hashlib
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Pietro&Yuri29'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sistema_emprestimos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    permissao = db.Column(db.String(20), default='funcionario')
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def set_senha(self, senha):
        self.senha_hash = hashlib.sha256(senha.encode()).hexdigest()

    def check_senha(self, senha):
        return self.senha_hash == hashlib.sha256(senha.encode()).hexdigest()

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cpf_cnpj = db.Column(db.String(20), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    endereco = db.Column(db.Text)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

class Notebook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(100), nullable=False)
    processador = db.Column(db.String(100))
    placa_video = db.Column(db.String(100))
    memoria_ram = db.Column(db.String(50))
    armazenamento = db.Column(db.String(50))
    numero_serie = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='disponivel')
    valor = db.Column(db.Float)
    data_aquisicao = db.Column(db.DateTime)
    cor = db.Column(db.String(50))
    tela = db.Column(db.String(50))
    sistema_operacional = db.Column(db.String(100))

class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    notebook_id = db.Column(db.Integer, db.ForeignKey('notebook.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_emprestimo = db.Column(db.DateTime, nullable=False)
    data_devolucao_prevista = db.Column(db.DateTime, nullable=False)
    data_devolucao_real = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='ativo')
    observacoes = db.Column(db.Text)
    
    cliente = db.relationship('Cliente', backref=db.backref('emprestimos', lazy=True))
    notebook = db.relationship('Notebook', backref=db.backref('emprestimos', lazy=True))
    usuario = db.relationship('Usuario', backref=db.backref('emprestimos', lazy=True))

class Comodato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crm = db.Column(db.String(50), unique=True, nullable=False)
    razao_social = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(20), nullable=False)
    destino = db.Column(db.String(200), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    processador = db.Column(db.String(100))
    placa_video = db.Column(db.String(100))
    cor = db.Column(db.String(50))
    tela = db.Column(db.String(50))
    memoria_ram = db.Column(db.String(50))
    armazenamento = db.Column(db.String(50))
    sistema_operacional = db.Column(db.String(100))
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    observacoes = db.Column(db.Text)

class Auditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    acao = db.Column(db.String(200), nullable=False)
    tabela_afetada = db.Column(db.String(50))
    registro_id = db.Column(db.Integer)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)
    detalhes = db.Column(db.Text)

# Funções auxiliares para CPF/CNPJ - CORRIGIDAS
def validar_cpf(cpf):
    """Valida CPF"""
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Calcula primeiro dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if digito1 != int(cpf[9]):
        return False
    
    # Calcula segundo dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return digito2 == int(cpf[10])

def validar_cnpj(cnpj):
    """Valida CNPJ"""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    if len(cnpj) != 14:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Calcula primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = 0
    for i in range(12):
        soma += int(cnpj[i]) * pesos1[i]
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if digito1 != int(cnpj[12]):
        return False
    
    # Calcula segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = 0
    for i in range(13):
        soma += int(cnpj[i]) * pesos2[i]
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return digito2 == int(cnpj[13])

def formatar_cpf_cnpj(numero):
    """Formata CPF ou CNPJ"""
    numero = re.sub(r'[^0-9]', '', numero)
    
    if len(numero) == 11:  # CPF
        return f'{numero[:3]}.{numero[3:6]}.{numero[6:9]}-{numero[9:]}'
    elif len(numero) == 14:  # CNPJ
        return f'{numero[:2]}.{numero[2:5]}.{numero[5:8]}/{numero[8:12]}-{numero[12:]}'
    else:
        return numero

def validar_cpf_cnpj(numero):
    """Valida CPF ou CNPJ"""
    numero = re.sub(r'[^0-9]', '', numero)
    
    if len(numero) == 11:
        return validar_cpf(numero)
    elif len(numero) == 14:
        return validar_cnpj(numero)
    else:
        return False

@app.context_processor
def inject_now():
    return {
        'now': datetime.utcnow(),
        'usuario_email': session.get('usuario_email', ''),
        'tema': session.get('tema', 'escuro')
    }

CSS_GLOBAL = '''
<style>
    :root {
        --avell-red: #e30613;
        --avell-dark: #1a1a1a;
        --avell-darker: #0d0d0d;
        --avell-light: #ffffff;
        --avell-silver: #f8f9fa;
        --text-primary: #333333;
        --text-secondary: #666666;
        --bg-primary: #ffffff;
        --bg-secondary: #f8f9fa;
        --border-color: #dee2e6;
    }

    [data-tema="escuro"] {
        --text-primary: #ffffff;
        --text-secondary: #cccccc;
        --bg-primary: #1a1a1a;
        --bg-secondary: #0d0d0d;
        --border-color: #333333;
    }

    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: var(--bg-secondary);
        color: var(--text-primary);
        transition: all 0.3s ease;
    }

    .avell-navbar {
        background: linear-gradient(135deg, var(--avell-darker) 0%, var(--avell-dark) 100%);
        border-bottom: 3px solid var(--avell-red);
    }

    .navbar-brand {
        color: var(--avell-light) !important;
        font-weight: bold;
        font-size: 1.3rem;
    }

    .btn-avell {
        background: var(--avell-red);
        color: white;
        border: none;
        font-weight: 600;
        transition: all 0.3s;
    }

    .btn-avell:hover {
        background: #c40510;
        color: white;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(227, 6, 19, 0.3);
    }

    .sidebar {
        background: linear-gradient(180deg, var(--avell-dark) 0%, var(--avell-darker) 100%);
        min-height: calc(100vh - 56px);
        padding: 0;
    }

    .sidebar-link {
        color: #ccc;
        text-decoration: none;
        display: block;
        padding: 15px 25px;
        border-bottom: 1px solid #333;
        transition: all 0.3s;
        font-weight: 500;
    }

    .sidebar-link:hover {
        color: var(--avell-light);
        background: rgba(227, 6, 19, 0.1);
        padding-left: 30px;
    }

    .sidebar-link.active {
        color: var(--avell-light);
        background: var(--avell-red);
        border-left: 4px solid var(--avell-light);
    }

    .card {
        border: 1px solid var(--border-color);
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        margin-bottom: 24px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        background: var(--bg-primary);
    }

    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    }

    .card-header {
        background: linear-gradient(135deg, var(--avell-dark) 0%, var(--avell-darker) 100%);
        color: var(--avell-light);
        font-weight: 600;
        border-radius: 12px 12px 0 0 !important;
        padding: 20px 25px;
        border: none;
    }

    .card-header i {
        color: var(--avell-red);
        margin-right: 8px;
    }

    .stats-card {
        text-align: center;
        padding: 30px 20px;
        border-radius: 12px;
        transition: all 0.3s ease;
        background: var(--bg-primary);
        color: var(--text-primary);
    }

    .stats-card:hover {
        transform: translateY(-8px);
    }

    .stats-number {
        font-size: 3rem;
        font-weight: 700;
        color: var(--avell-red);
        margin-bottom: 5px;
        line-height: 1;
    }

    .stats-label {
        font-size: 0.9rem;
        color: var(--text-secondary);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .main-content {
        padding: 30px;
        min-height: calc(100vh - 56px);
        background: var(--bg-secondary);
    }

    .table {
        background: var(--bg-primary);
        color: var(--text-primary);
    }

    .table th {
        background: linear-gradient(135deg, var(--avell-dark) 0%, var(--avell-darker) 100%);
        color: var(--avell-light);
        font-weight: 600;
        border: none;
        padding: 15px;
    }

    .table td {
        border-color: var(--border-color);
        padding: 15px;
        vertical-align: middle;
        color: var(--text-primary);
    }

    .table-hover tbody tr:hover {
        background-color: rgba(227, 6, 19, 0.05);
    }

    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: var(--bg-primary);
        border-radius: 16px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }

    .login-logo {
        text-align: center;
        margin-bottom: 30px;
        color: var(--avell-red);
    }

    .badge-disponivel { background: #28a745; color: white; }
    .badge-emprestado { background: #dc3545; color: white; }
    .badge-manutencao { background: #ffc107; color: black; }
    .badge-ativo { background: #28a745; color: white; }
    .badge-finalizado { background: #6c757d; color: white; }
    .badge-atrasado { background: #dc3545; color: white; }

    .notebook-card {
        transition: all 0.3s ease;
    }

    .notebook-card:hover {
        transform: translateY(-5px);
    }

    .comodato-card {
        border-left: 4px solid var(--avell-red);
    }

    .valor-destaque {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--avell-red);
    }

    .form-control, .form-select {
        background: var(--bg-primary);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
    }

    .form-control:focus, .form-select:focus {
        background: var(--bg-primary);
        color: var(--text-primary);
        border-color: var(--avell-red);
        box-shadow: 0 0 0 0.2rem rgba(227, 6, 19, 0.25);
    }

    .form-label {
        color: var(--text-primary);
        font-weight: 500;
    }

    .text-muted {
        color: var(--text-secondary) !important;
    }

    .btn-toggle-tema {
        background: transparent;
        border: 2px solid var(--avell-red);
        color: var(--avell-red);
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s;
        margin-left: 10px;
    }

    .btn-toggle-tema:hover {
        background: var(--avell-red);
        color: white;
        transform: rotate(180deg);
    }

    .invalid-feedback {
        display: block;
    }

    .cpf-cnpj-valido {
        border-color: #28a745 !important;
        box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25) !important;
    }

    .cpf-cnpj-invalido {
        border-color: #dc3545 !important;
        box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25) !important;
    }

    .email-valido {
        border-color: #28a745 !important;
        box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25) !important;
    }

    .email-invalido {
        border-color: #dc3545 !important;
        box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25) !important;
    }

    .telefone-valido {
        border-color: #28a745 !important;
        box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25) !important;
    }

    .telefone-invalido {
        border-color: #dc3545 !important;
        box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25) !important;
    }

    .modal-content {
        background: var(--bg-primary);
        color: var(--text-primary);
    }

    .modal-header {
        border-bottom: 1px solid var(--border-color);
    }

    .modal-footer {
        border-top: 1px solid var(--border-color);
    }

    .ddi-select {
        max-width: 120px;
    }

    /* Estilos específicos para tabelas no tema escuro */
    [data-tema="escuro"] .table {
        background: var(--bg-primary);
        color: var(--text-primary);
        border-color: var(--border-color);
    }

    [data-tema="escuro"] .table th {
        background: linear-gradient(135deg, var(--avell-dark) 0%, var(--avell-darker) 100%);
        color: var(--avell-light);
        border-color: var(--border-color);
    }

    [data-tema="escuro"] .table td {
        background: var(--bg-primary);
        color: var(--text-primary);
        border-color: var(--border-color);
    }

    [data-tema="escuro"] .table-bordered {
        border: 1px solid var(--border-color);
    }

    [data-tema="escuro"] .table-bordered th,
    [data-tema="escuro"] .table-bordered td {
        border: 1px solid var(--border-color);
    }

    /* CORREÇÃO: Garantir que textos nos cards sejam visíveis no tema escuro */
    [data-tema="escuro"] .card-body,
    [data-tema="escuro"] .card-body div,
    [data-tema="escuro"] .card-body p,
    [data-tema="escuro"] .card-body span,
    [data-tema="escuro"] .card-body strong {
        color: var(--text-primary) !important;
    }

    [data-tema="escuro"] .card-body small.text-muted {
        color: var(--text-secondary) !important;
    }

    /* Especificamente para os cards de notebook */
    [data-tema="escuro"] .notebook-card .card-body,
    [data-tema="escuro"] .notebook-card .card-body div,
    [data-tema="escuro"] .notebook-card .card-body p {
        color: var(--text-primary) !important;
    }

    [data-tema="escuro"] .notebook-card .text-muted {
        color: #8a8a8a !important;
    }

    /* Garantir que badges mantenham suas cores */
    [data-tema="escuro"] .badge {
        color: white !important;
    }

    [data-tema="escuro"] .badge.bg-warning {
        color: black !important;
    }

    [data-tema="escuro"] .badge.bg-secondary {
        color: white !important;
    }

    /* Garantir que textos coloridos sejam visíveis no tema escuro */
    [data-tema="escuro"] .text-success {
        color: #28a745 !important;
    }

    [data-tema="escuro"] .text-info {
        color: #17a2b8 !important;
    }

    [data-tema="escuro"] .text-primary {
        color: #007bff !important;
    }

    [data-tema="escuro"] .text-warning {
        color: #ffc107 !important;
    }

    [data-tema="escuro"] .text-secondary {
        color: #6c757d !important;
    }

    [data-tema="escuro"] .text-danger {
        color: #dc3545 !important;
    }

    /* Estilo para a barra de progresso no tema escuro */
    [data-tema="escuro"] .progress {
        background-color: var(--bg-secondary);
    }

    [data-tema="escuro"] .progress-bar {
        background-color: var(--avell-red);
    }

    /* Estilos para textos de ajuda no tema escuro */
    [data-tema="escuro"] .form-text {
        color: #8a8a8a !important;
    }

    [data-tema="escuro"] .form-control::placeholder {
        color: #8a8a8a;
    }

    [data-tema="escuro"] .form-control {
        color: var(--text-primary);
    }

    [data-tema="escuro"] .form-control:focus {
        color: var(--text-primary);
    }

    [data-tema="escuro"] .form-select {
        color: var(--text-primary);
    }

    [data-tema="escuro"] .form-select:focus {
        color: var(--text-primary);
    }

    /* Estilos para exemplos nos campos */
    .form-text-example {
        font-size: 0.875em;
        color: #6c757d;
        margin-top: 0.25rem;
        font-style: italic;
    }

    [data-tema="escuro"] .form-text-example {
        color: #8a8a8a;
    }

    /* Estilos para títulos de seção */
    .section-title {
        color: var(--avell-red);
        font-weight: 600;
        border-bottom: 2px solid var(--avell-red);
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }

    /* CORREÇÃO: Garantir que fontes monospace sejam visíveis */
    [data-tema="escuro"] .font-monospace {
        color: var(--text-primary) !important;
    }

    /* CORREÇÃO: Garantir que textos em listas sejam visíveis */
    [data-tema="escuro"] .list-group-item {
        background-color: var(--bg-primary);
        color: var(--text-primary);
        border-color: var(--border-color);
    }

    [data-tema="escuro"] .list-group-item h6 {
        color: var(--text-primary) !important;
    }

    /* CORREÇÃO: Garantir que valores em destaque sejam visíveis */
    [data-tema="escuro"] .valor-destaque {
        color: var(--avell-red) !important;
    }

    /* CORREÇÃO: Garantir que textos de status sejam visíveis */
    [data-tema="escuro"] .text-success,
    [data-tema="escuro"] .text-danger,
    [data-tema="escuro"] .text-warning {
        opacity: 1 !important;
    }
</style>
'''

# Template Base - CORRIGIDO SIMPLES
def render_base(content, active_page='dashboard'):
    tema_atual = session.get('tema', 'escuro')
    
    # Links da sidebar
    links = [
        {'url': '/dashboard', 'icon': 'fa-tachometer-alt', 'text': 'Dashboard', 'page': 'dashboard'},
        {'url': '/clientes', 'icon': 'fa-users', 'text': 'Clientes', 'page': 'clientes'},
        {'url': '/notebooks', 'icon': 'fa-laptop', 'text': 'Notebooks', 'page': 'notebooks'},
        {'url': '/emprestimos', 'icon': 'fa-exchange-alt', 'text': 'Empréstimos', 'page': 'emprestimos'},
        {'url': '/comodatos', 'icon': 'fa-file-contract', 'text': 'Comodatos', 'page': 'comodatos'},
        {'url': '/relatorios', 'icon': 'fa-chart-bar', 'text': 'Relatórios', 'page': 'relatorios'},
    ]
    
    # Adicionar link de usuários apenas para admin
    if session.get('usuario_email') == 'pietro.admin':
        links.append({'url': '/usuarios', 'icon': 'fa-user-shield', 'text': 'Gerenciar Usuários', 'page': 'usuarios'})
    
    # Gerar HTML dos links
    sidebar_links = ''
    for link in links:
        is_active = 'active' if active_page == link['page'] else ''
        sidebar_links += f'''
        <a href="{link['url']}" class="sidebar-link {is_active}">
            <i class="fas {link['icon']} me-2"></i> {link['text']}
        </a>
        '''
    
    return f'''
<!DOCTYPE html>
<html lang="pt-BR" data-tema="{tema_atual}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema Avell - Empréstimos</title>
    <link rel="icon" type="image/png" href="/static/avell.png">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {CSS_GLOBAL}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark avell-navbar">
        <div class="container-fluid">
            <a class="navbar-brand d-flex align-items-center" href="/dashboard">
                <img src="/static/avell.png" alt="Avell Logo" height="32" class="me-2">
                Sistema Avell
            </a>
            <div class="navbar-nav ms-auto">
                <form method="POST" action="/toggle-tema" class="d-inline">
                    <button type="submit" class="btn-toggle-tema" title="Alternar tema">
                        <i class="fas fa-{'sun' if tema_atual == 'escuro' else 'moon'}"></i>
                    </button>
                </form>
                <div class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                        <i class="fas fa-user me-1"></i> {session.get('usuario_nome', 'Usuário')}
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="/logout"><i class="fas fa-sign-out-alt me-2"></i> Sair</a></li>
                    </ul>
                </div>
            </div>
        </div>
    </nav>

    <div class="container-fluid">
        <div class="row">
            <nav class="col-md-2 d-none d-md-block sidebar">
                <div class="sidebar-sticky">
                    {sidebar_links}
                </div>
            </nav>

            <main class="col-md-10 ms-sm-auto px-4 main-content">
                {content}
            </main>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</body>
</html>
'''

# Template Login - ATUALIZADO
def render_login():
    tema_atual = session.get('tema', 'escuro')
    return f'''
<!DOCTYPE html>
<html lang="pt-BR" data-tema="{tema_atual}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Sistema Avell</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {CSS_GLOBAL}
</head>
<body class="login-body">
    <div class="login-container">
        <div class="login-logo">
            <i class="fas fa-laptop-code fa-3x mb-3"></i>
            <h2>Sistema Avell</h2>
            <p class="text-muted">Gestão de Empréstimos</p>
        </div>

        <form method="POST" action="/login">
            <div class="mb-3">
                <label class="form-label">Email</label>
                <div class="input-group">
                    <span class="input-group-text"><i class="fas fa-user"></i></span>
                    <input type="text" name="email" class="form-control" placeholder="Digite seu email" required>
                </div>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Senha</label>
                <div class="input-group">
                    <span class="input-group-text"><i class="fas fa-lock"></i></span>
                    <input type="password" name="senha" class="form-control" placeholder="Digite sua senha" required>
                </div>
            </div>

            <button type="submit" class="btn btn-avell w-100 py-2">
                <i class="fas fa-sign-in-alt me-2"></i>Entrar no Sistema
            </button>
        </form>

        <div class="mt-4 text-center">
            <p class="text-muted">Sistema exclusivo para funcionários autorizados</p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

# Template Dashboard
def render_dashboard(total_clientes=0, total_notebooks=0, emprestimos_ativos=0, emprestimos_atrasados=0, proximas_devolucoes=None, total_comodatos=0, valor_total_comodatos=0):
    if proximas_devolucoes is None:
        proximas_devolucoes = []
    
    devolucoes_html = ''
    for emp in proximas_devolucoes:
        dias_restantes = (emp.data_devolucao_prevista.date() - datetime.now().date()).days
        status_cor = 'text-danger' if dias_restantes < 0 else 'text-muted'
        texto_dias = f'{dias_restantes} dias atrás' if dias_restantes < 0 else f'{dias_restantes} dias'
        
        devolucoes_html += f'''
        <div class="list-group-item">
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">{emp.cliente.nome}</h6>
                <small class="{status_cor}">{texto_dias}</small>
            </div>
            <p class="mb-1 small">{emp.notebook.modelo}</p>
            <small class="text-muted">Devolução: {emp.data_devolucao_prevista.strftime('%d/%m/%Y')}</small>
        </div>
        '''
    
    content = f'''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Dashboard</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <a href="/emprestimos/novo" class="btn btn-avell me-2">
                <i class="fas fa-plus me-1"></i> Novo Empréstimo
            </a>
        </div>
    </div>

    <!-- Stats Cards -->
    <div class="row">
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{total_notebooks}</div>
                <div class="stats-label">Notebooks Cadastrados</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{emprestimos_ativos}</div>
                <div class="stats-label">Empréstimos Ativos</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{total_clientes}</div>
                <div class="stats-label">Total de Clientes</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{total_comodatos}</div>
                <div class="stats-label">Contratos Comodato</div>
            </div>
        </div>
    </div>

    <div class="row mt-4">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-chart-line me-2"></i> Empréstimos - Últimos 6 Meses
                </div>
                <div class="card-body">
                    <canvas id="graficoEmprestimos" height="100"></canvas>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            {f'<div class="card mb-4"><div class="card-header"><i class="fas fa-clock me-2"></i> Próximas Devoluções</div><div class="card-body p-0"><div class="list-group list-group-flush">' + devolucoes_html + '</div></div></div>' if proximas_devolucoes else ''}
            
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-info-circle me-2"></i> Sistema Avell
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <strong>Status:</strong>
                        {'<span class="badge bg-warning">Configuração Inicial</span><p class="small text-muted mt-1">Comece cadastrando clientes e notebooks</p>' if total_clientes == 0 and total_notebooks == 0 else '<span class="badge bg-success">Operacional</span>'}
                    </div>
                    
                    <div class="mb-3">
                        <strong>Valor Total em Comodatos:</strong>
                        <div class="valor-destaque">R$ {valor_total_comodatos:,.2f}</div>
                    </div>
                    
                    <div class="d-grid gap-2">
                        <a href="/clientes/novo" class="btn btn-avell btn-sm">
                            <i class="fas fa-user-plus me-1"></i> Novo Cliente
                        </a>
                        <a href="/notebooks/novo" class="btn btn-outline-secondary btn-sm">
                            <i class="fas fa-laptop me-1"></i> Cadastrar Notebook
                        </a>
                        <a href="/comodatos/novo" class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-file-contract me-1"></i> Novo Comodato
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const data = {{
                labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                datasets: [{{
                    label: 'Empréstimos',
                    data: [12, 15, 8, 11, 14, 10],
                    backgroundColor: '#e30613'
                }}]
            }};
            
            const ctx = document.getElementById('graficoEmprestimos').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: data,
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ display: false }}
                    }}
                }}
            }});
        }});
    </script>
    '''
    
    return render_base(content, 'dashboard')

# Template Clientes
def render_clientes(clientes=None):
    if clientes is None:
        clientes = []
    
    clientes_html = ''
    for cliente in clientes:
        clientes_html += f'''
        <tr>
            <td><strong>{cliente.nome}</strong></td>
            <td>{cliente.cpf_cnpj}</td>
            <td>{cliente.telefone or 'Não informado'}</td>
            <td>{cliente.email or 'Não informado'}</td>
            <td>{cliente.data_cadastro.strftime('%d/%m/%Y')}</td>
            <td><span class="badge bg-primary">{len(cliente.emprestimos)}</span></td>
        </tr>
        '''
    
    content = f'''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Clientes</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <a href="/clientes/novo" class="btn btn-avell">
                <i class="fas fa-plus me-1"></i> Novo Cliente
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <i class="fas fa-users me-2"></i> Lista de Clientes
        </div>
        <div class="card-body">
            {'<div class="table-responsive"><table class="table table-striped table-hover"><thead><tr><th>Nome</th><th>CPF/CNPJ</th><th>Telefone</th><th>Email</th><th>Data Cadastro</th><th>Empréstimos</th></tr></thead><tbody>' + clientes_html + '</tbody></table></div>' if clientes else '<div class="text-center py-5"><i class="fas fa-users fa-3x text-muted mb-3"></i><h5 class="text-muted">Nenhum cliente cadastrado</h5><a href="/clientes/novo" class="btn btn-avell mt-2"><i class="fas fa-plus me-1"></i> Cadastrar Primeiro Cliente</a></div>'}
        </div>
    </div>

    <!-- Estatísticas -->
    <div class="row mt-4">
        <div class="col-md-4">
            <div class="card stats-card">
                <div class="stats-number">{len(clientes)}</div>
                <div class="stats-label">Total de Clientes</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stats-card">
                <div class="stats-number">{sum(len(cliente.emprestimos) for cliente in clientes)}</div>
                <div class="stats-label">Total de Empréstimos</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stats-card">
                <div class="stats-number">{len([c for c in clientes if c.email])}</div>
                <div class="stats-label">Com Email</div>
            </div>
        </div>
    </div>
    '''
    
    return render_base(content, 'clientes')

# Template Form Cliente - ATUALIZADO COM EXEMPLOS NOS CAMPOS
def render_form_cliente():
    content = f'''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Novo Cliente</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <a href="/clientes" class="btn btn-outline-secondary">
                <i class="fas fa-arrow-left me-1"></i> Voltar
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <i class="fas fa-user-plus me-2"></i> Dados do Cliente
        </div>
        <div class="card-body">
            <form method="POST" id="formCliente" class="needs-validation" novalidate>
                <div class="row">
                    <div class="col-md-8 mb-3">
                        <label for="nome" class="form-label">Nome Completo *</label>
                        <input type="text" class="form-control" id="nome" name="nome" 
                               placeholder="Ex: João Silva Santos" required>
                    </div>
                    
                    <div class="col-md-4 mb-3">
                        <label for="cpf_cnpj" class="form-label">CPF/CNPJ *</label>
                        <input type="text" class="form-control" id="cpf_cnpj" name="cpf_cnpj" 
                               placeholder="000.000.000-00 ou 00.000.000/0000-00" required>
                        <div class="valid-feedback">
                            CPF/CNPJ válido!
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="telefone" class="form-label">Telefone</label>
                        <div class="input-group">
                            <select class="form-select ddi-select" id="ddi" name="ddi">
                                <option value="+55">+55 (BR)</option>
                                <option value="+1">+1 (EUA)</option>
                                <option value="+54">+54 (ARG)</option>
                                <option value="+56">+56 (CHL)</option>
                                <option value="+598">+598 (URU)</option>
                                <option value="+595">+595 (PAR)</option>
                                <option value="+51">+51 (PER)</option>
                                <option value="+57">+57 (COL)</option>
                                <option value="+52">+52 (MEX)</option>
                            </select>
                            <input type="text" class="form-control" id="telefone" name="telefone" placeholder="(11) 99999-9999">
                        </div>
                        <div class="valid-feedback">
                            Telefone válido!
                        </div>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control" id="email" name="email" placeholder="exemplo@dominio.com">
                        <div class="valid-feedback">
                            Email válido!
                        </div>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="endereco" class="form-label">Endereço</label>
                    <textarea class="form-control" id="endereco" name="endereco" rows="3" 
                              placeholder="Ex: Rua das Flores, 123 - Centro - São Paulo/SP"></textarea>
                </div>
                
                <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                    <a href="/clientes" class="btn btn-secondary me-md-2">Cancelar</a>
                    <button type="submit" class="btn btn-avell" id="btnSubmit">Cadastrar Cliente</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const cpfCnpjInput = document.getElementById('cpf_cnpj');
            const emailInput = document.getElementById('email');
            const telefoneInput = document.getElementById('telefone');
            const ddiSelect = document.getElementById('ddi');
            const form = document.getElementById('formCliente');
            const btnSubmit = document.getElementById('btnSubmit');
            
            // Função para formatar CPF/CNPJ
            function formatarCPFCNPJ(valor) {{
                const numeros = valor.replace(/\\D/g, '');
                
                if (numeros.length <= 11) {{
                    return numeros.replace(/(\\d{{3}})(\\d)/, '$1.$2')
                                 .replace(/(\\d{{3}})(\\d)/, '$1.$2')
                                 .replace(/(\\d{{3}})(\\d{{1,2}})$/, '$1-$2');
                }} else {{
                    return numeros.replace(/^(\\d{{2}})(\\d)/, '$1.$2')
                                 .replace(/^(\\d{{2}})\\.(\\d{{3}})(\\d)/, '$1.$2.$3')
                                 .replace(/\\.(\\d{{3}})(\\d)/, '.$1/$2')
                                 .replace(/(\\d{{4}})(\\d)/, '$1-$2');
                }}
            }}
            
            // Função para validar CPF/CNPJ
            function validarCPFCNPJ(valor) {{
                const numeros = valor.replace(/\\D/g, '');
                
                if (numeros.length === 11) {{
                    return validarCPF(numeros);
                }} else if (numeros.length === 14) {{
                    return validarCNPJ(numeros);
                }}
                return false;
            }}
            
            // Função para validar CPF
            function validarCPF(cpf) {{
                if (cpf.length !== 11 || /^(\\d)\\1{{10}}$/.test(cpf)) return false;
                
                let soma = 0;
                for (let i = 0; i < 9; i++) {{
                    soma += parseInt(cpf.charAt(i)) * (10 - i);
                }}
                let resto = soma % 11;
                let digito1 = resto < 2 ? 0 : 11 - resto;
                
                if (digito1 !== parseInt(cpf.charAt(9))) return false;
                
                soma = 0;
                for (let i = 0; i < 10; i++) {{
                    soma += parseInt(cpf.charAt(i)) * (11 - i);
                }}
                resto = soma % 11;
                let digito2 = resto < 2 ? 0 : 11 - resto;
                
                return digito2 === parseInt(cpf.charAt(10));
            }}
            
            // Função para validar CNPJ
            function validarCNPJ(cnpj) {{
                if (cnpj.length !== 14 || /^(\\d)\\1{{13}}$/.test(cnpj)) return false;
                
                let tamanho = cnpj.length - 2;
                let numeros = cnpj.substring(0, tamanho);
                let digitos = cnpj.substring(tamanho);
                let soma = 0;
                let pos = tamanho - 7;
                
                for (let i = tamanho; i >= 1; i--) {{
                    soma += numeros.charAt(tamanho - i) * pos--;
                    if (pos < 2) pos = 9;
                }}
                
                let resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
                if (resultado !== parseInt(digitos.charAt(0))) return false;
                
                tamanho = tamanho + 1;
                numeros = cnpj.substring(0, tamanho);
                soma = 0;
                pos = tamanho - 7;
                
                for (let i = tamanho; i >= 1; i--) {{
                    soma += numeros.charAt(tamanho - i) * pos--;
                    if (pos < 2) pos = 9;
                }}
                
                resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
                return resultado === parseInt(digitos.charAt(1));
            }}
            
            // Função para formatar telefone baseado no DDI
            function formatarTelefone(valor, ddi) {{
                const numeros = valor.replace(/\\D/g, '');
                
                if (ddi === '+55') {{
                    // Formatação brasileira: (11) 99999-9999
                    if (numeros.length <= 10) {{
                        return numeros.replace(/(\\d{{2}})(\\d)/, '($1) $2')
                                     .replace(/(\\d{{4}})(\\d)/, '$1-$2');
                    }} else {{
                        return numeros.replace(/(\\d{{2}})(\\d)/, '($1) $2')
                                     .replace(/(\\d{{5}})(\\d)/, '$1-$2');
                    }}
                }} else {{
                    // Formatação internacional simples
                    return numeros.replace(/(\\d{{3}})(\\d)/, '$1 $2')
                                 .replace(/(\\d{{3}})(\\d)/, '$1 $2')
                                 .replace(/(\\d{{4}})$/, '$1');
                }}
            }}
            
            // Função para validar email
            function validarEmail(email) {{
                if (!email) return true; // Email é opcional
                const regex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
                return regex.test(email) && email.includes('@') && email.split('@')[1].includes('.');
            }}
            
            // Função para validar telefone
            function validarTelefone(telefone) {{
                if (!telefone) return true; // Telefone é opcional
                const numeros = telefone.replace(/\\D/g, '');
                return numeros.length >= 10;
            }}
            
            // Event listener para CPF/CNPJ
            cpfCnpjInput.addEventListener('input', function(e) {{
                const valor = e.target.value;
                const valorFormatado = formatarCPFCNPJ(valor);
                
                if (valorFormatado !== valor) {{
                    e.target.value = valorFormatado;
                }}
                
                const isValid = validarCPFCNPJ(valorFormatado);
                
                if (valorFormatado && !isValid) {{
                    e.target.classList.add('cpf-cnpj-invalido');
                    e.target.classList.remove('cpf-cnpj-valido');
                    e.target.classList.add('is-invalid');
                    e.target.classList.remove('is-valid');
                }} else if (valorFormatado && isValid) {{
                    e.target.classList.add('cpf-cnpj-valido');
                    e.target.classList.remove('cpf-cnpj-invalido');
                    e.target.classList.add('is-valid');
                    e.target.classList.remove('is-invalid');
                }} else {{
                    e.target.classList.remove('cpf-cnpj-valido', 'cpf-cnpj-invalido', 'is-valid', 'is-invalid');
                }}
                
                validarFormulario();
            }});
            
            // Event listener para email
            emailInput.addEventListener('input', function(e) {{
                const valor = e.target.value;
                const isValid = validarEmail(valor);
                
                if (valor && !isValid) {{
                    e.target.classList.add('email-invalido');
                    e.target.classList.remove('email-valido');
                    e.target.classList.add('is-invalid');
                    e.target.classList.remove('is-valid');
                }} else if (valor && isValid) {{
                    e.target.classList.add('email-valido');
                    e.target.classList.remove('email-invalido');
                    e.target.classList.add('is-valid');
                    e.target.classList.remove('is-invalid');
                }} else {{
                    e.target.classList.remove('email-valido', 'email-invalido', 'is-valid', 'is-invalid');
                }}
                
                validarFormulario();
            }});
            
            // Event listener para telefone
            telefoneInput.addEventListener('input', function(e) {{
                const valor = e.target.value;
                const ddi = ddiSelect.value;
                const valorFormatado = formatarTelefone(valor, ddi);
                
                if (valorFormatado !== valor) {{
                    e.target.value = valorFormatado;
                }}
                
                const isValid = validarTelefone(valorFormatado);
                
                if (valor && !isValid) {{
                    e.target.classList.add('telefone-invalido');
                    e.target.classList.remove('telefone-valido');
                    e.target.classList.add('is-invalid');
                    e.target.classList.remove('is-valid');
                }} else if (valor && isValid) {{
                    e.target.classList.add('telefone-valido');
                    e.target.classList.remove('telefone-invalido');
                    e.target.classList.add('is-valid');
                    e.target.classList.remove('is-invalid');
                }} else {{
                    e.target.classList.remove('telefone-valido', 'telefone-invalido', 'is-valid', 'is-invalid');
                }}
                
                validarFormulario();
            }});
            
            // Event listener para DDI
            ddiSelect.addEventListener('change', function() {{
                const telefone = telefoneInput.value;
                if (telefone) {{
                    const ddi = this.value;
                    const valorFormatado = formatarTelefone(telefone.replace(/\\D/g, ''), ddi);
                    telefoneInput.value = valorFormatado;
                }}
            }});
            
            // Função para validar todo o formulário
            function validarFormulario() {{
                const nome = document.getElementById('nome').value;
                const cpfCnpj = cpfCnpjInput.value;
                const email = emailInput.value;
                const telefone = telefoneInput.value;
                
                const nomeValido = nome.trim() !== '';
                const cpfCnpjValido = validarCPFCNPJ(cpfCnpj);
                const emailValido = validarEmail(email);
                const telefoneValido = validarTelefone(telefone);
                
                btnSubmit.disabled = !(nomeValido && cpfCnpjValido && emailValido && telefoneValido);
            }}
            
            // Validação no submit
            form.addEventListener('submit', function(e) {{
                const nome = document.getElementById('nome').value;
                const cpfCnpjValue = cpfCnpjInput.value;
                const emailValue = emailInput.value;
                const telefoneValue = telefoneInput.value;
                
                let isValid = true;
                
                // Validar nome
                if (!nome.trim()) {{
                    document.getElementById('nome').classList.add('is-invalid');
                    isValid = false;
                }}
                
                // Validar CPF/CNPJ
                if (!validarCPFCNPJ(cpfCnpjValue)) {{
                    cpfCnpjInput.classList.add('is-invalid');
                    isValid = false;
                }}
                
                // Validar email
                if (emailValue && !validarEmail(emailValue)) {{
                    emailInput.classList.add('is-invalid');
                    isValid = false;
                }}
                
                // Validar telefone
                if (telefoneValue && !validarTelefone(telefoneValue)) {{
                    telefoneInput.classList.add('is-invalid');
                    isValid = false;
                }}
                
                if (!isValid) {{
                    e.preventDefault();
                    alert('Por favor, corrija os campos destacados em vermelho antes de enviar o formulário.');
                }}
            }});
            
            // Validação inicial
            validarFormulario();
            
            // Focar no campo de nome ao carregar a página
            document.getElementById('nome').focus();
        }});
    </script>
    '''
    
    return render_base(content, 'clientes')

# Template Notebooks
def render_notebooks(notebooks=None):
    if notebooks is None:
        notebooks = []
    
    notebooks_html = ''
    for notebook in notebooks:
        status_badge = f'<span class="badge badge-{notebook.status}">{notebook.status.title()}</span>'
        valor_str = f'R$ {notebook.valor:,.2f}' if notebook.valor else 'Não informado'
        notebooks_html += f'''
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="card notebook-card h-100">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span class="fw-bold">{notebook.modelo}</span>
                    {status_badge}
                </div>
                <div class="card-body">
                    <div class="mb-2">
                        <small class="text-muted">Processador:</small>
                        <div>{notebook.processador or 'Não informado'}</div>
                    </div>
                    
                    <div class="mb-2">
                        <small class="text-muted">Placa de Vídeo:</small>
                        <div>{notebook.placa_video or 'Não informado'}</div>
                    </div>
                    
                    <div class="row mb-2">
                        <div class="col-6">
                            <small class="text-muted">RAM:</small>
                            <div>{notebook.memoria_ram or 'Não informado'}</div>
                        </div>
                        <div class="col-6">
                            <small class="text-muted">Armazenamento:</small>
                            <div>{notebook.armazenamento or 'Não informado'}</div>
                        </div>
                    </div>
                    
                    <div class="mb-2">
                        <small class="text-muted">Nº Série:</small>
                        <div class="font-monospace small">{notebook.numero_serie}</div>
                    </div>
                    
                    <div class="mb-2">
                        <small class="text-muted">Valor:</small>
                        <div class="fw-bold text-success">{valor_str}</div>
                    </div>
                    
                    <div class="mb-3">
                        <small class="text-muted">Histórico:</small>
                        <div>
                            <span class="badge bg-secondary">{len(notebook.emprestimos)} empréstimos</span>
                        </div>
                    </div>
                </div>
                <div class="card-footer bg-transparent">
                    <small class="text-{'success' if notebook.status == 'disponivel' else 'danger' if notebook.status == 'emprestado' else 'warning'}">
                        <i class="fas fa-{'check-circle' if notebook.status == 'disponivel' else 'exclamation-circle' if notebook.status == 'emprestado' else 'tools'} me-1"></i>
                        {notebook.status.title()}
                    </small>
                </div>
            </div>
        </div>
        '''
    
    # Estatísticas
    total = len(notebooks)
    disponiveis = len([n for n in notebooks if n.status == 'disponivel'])
    emprestados = len([n for n in notebooks if n.status == 'emprestado'])
    manutencao = len([n for n in notebooks if n.status == 'manutencao'])
    valor_total = sum(n.valor or 0 for n in notebooks)
    
    content = f'''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Notebooks</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <a href="/notebooks/novo" class="btn btn-avell">
                <i class="fas fa-plus me-1"></i> Novo Notebook
            </a>
        </div>
    </div>

    <!-- Estatísticas -->
    <div class="row">
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{total}</div>
                <div class="stats-label">Total de Notebooks</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{disponiveis}</div>
                <div class="stats-label">Disponíveis</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{emprestados}</div>
                <div class="stats-label">Emprestados</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">R$ {valor_total:,.2f}</div>
                <div class="stats-label">Valor Total</div>
            </div>
        </div>
    </div>

    <div class="row mt-4">
        {notebooks_html if notebooks else '<div class="col-12"><div class="card"><div class="card-body text-center py-5"><i class="fas fa-laptop fa-3x text-muted mb-3"></i><h5 class="text-muted">Nenhum notebook cadastrado</h5><a href="/notebooks/novo" class="btn btn-avell"><i class="fas fa-plus me-1"></i> Cadastrar Notebook</a></div></div></div>'}
    </div>
    '''
    
    return render_base(content, 'notebooks')

# Template Empréstimos
def render_emprestimos(emprestimos=None, status='todos'):
    if emprestimos is None:
        emprestimos = []
    
    emprestimos_html = ''
    for emp in emprestimos:
        if emp.status == 'ativo':
            if emp.data_devolucao_prevista < datetime.now():
                status_badge = '<span class="badge badge-atrasado">Atrasado</span>'
            else:
                status_badge = '<span class="badge badge-ativo">Ativo</span>'
            acoes = f'''
            <form method="POST" action="/emprestimos/{emp.id}/devolver" class="d-inline">
                <button type="submit" class="btn btn-success btn-sm" onclick="return confirm('Confirmar devolução do notebook?')">
                    <i class="fas fa-check"></i> Devolver
                </button>
            </form>
            '''
        else:
            status_badge = '<span class="badge badge-finalizado">Finalizado</span>'
            acoes = '<span class="text-muted">Finalizado</span>'
        
        emprestimos_html += f'''
        <tr>
            <td>
                <strong>{emp.cliente.nome}</strong>
                <br><small class="text-muted">{emp.cliente.cpf_cnpj}</small>
            </td>
            <td>
                {emp.notebook.modelo}
                <br><small class="text-muted">{emp.notebook.numero_serie}</small>
            </td>
            <td>{emp.data_emprestimo.strftime('%d/%m/%Y')}</td>
            <td>
                {emp.data_devolucao_prevista.strftime('%d/%m/%Y')}
                {('<br><small class="text-danger">Atrasado</small>' if emp.status == 'ativo' and emp.data_devolucao_prevista < datetime.now() else '')}
            </td>
            <td>{status_badge}</td>
            <td>{emp.usuario.nome}</td>
            <td>{acoes}</td>
        </tr>
        '''
    
    # Filtros
    filtros_html = f'''
    <div class="btn-group mb-3" role="group">
        <a href="/emprestimos?status=todos" class="btn btn-outline-secondary {'active' if status == 'todos' else ''}">Todos</a>
        <a href="/emprestimos?status=ativos" class="btn btn-outline-secondary {'active' if status == 'ativos' else ''}">Ativos</a>
        <a href="/emprestimos?status=atrasados" class="btn btn-outline-secondary {'active' if status == 'atrasados' else ''}">Atrasados</a>
        <a href="/emprestimos?status=finalizados" class="btn btn-outline-secondary {'active' if status == 'finalizados' else ''}">Finalizados</a>
    </div>
    '''
    
    # Estatísticas
    ativos = len([e for e in emprestimos if e.status == 'ativo'])
    atrasados = len([e for e in emprestimos if e.status == 'ativo' and e.data_devolucao_prevista < datetime.now()])
    finalizados = len([e for e in emprestimos if e.status == 'finalizado'])
    
    content = f'''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Empréstimos</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <a href="/emprestimos/novo" class="btn btn-avell">
                <i class="fas fa-plus me-1"></i> Novo Empréstimo
            </a>
        </div>
    </div>

    {filtros_html}

    <!-- Estatísticas -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{len(emprestimos)}</div>
                <div class="stats-label">Total</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{ativos}</div>
                <div class="stats-label">Ativos</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{atrasados}</div>
                <div class="stats-label">Atrasados</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{finalizados}</div>
                <div class="stats-label">Finalizados</div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <i class="fas fa-exchange-alt me-2"></i> 
            {'Todos os Empréstimos' if status == 'todos' else 
             'Empréstimos Ativos' if status == 'ativos' else 
             'Empréstimos Atrasados' if status == 'atrasados' else 
             'Empréstimos Finalizados'}
        </div>
        <div class="card-body">
            {'<div class="table-responsive"><table class="table table-striped table-hover"><thead><tr><th>Cliente</th><th>Notebook</th><th>Data Empréstimo</th><th>Previsão Devolução</th><th>Status</th><th>Responsável</th><th>Ações</th></tr></thead><tbody>' + emprestimos_html + '</tbody></table></div>' if emprestimos else '<div class="text-center py-5"><i class="fas fa-exchange-alt fa-3x text-muted mb-3"></i><h5 class="text-muted">Nenhum empréstimo encontrado</h5><a href="/emprestimos/novo" class="btn btn-avell mt-2"><i class="fas fa-plus me-1"></i> Realizar Primeiro Empréstimo</a></div>'}
        </div>
    </div>
    '''
    
    return render_base(content, 'emprestimos')

# Template Comodatos
def render_comodatos(comodatos=None):
    if comodatos is None:
        comodatos = []
    
    comodatos_html = ''
    for comodato in comodatos:
        comodatos_html += f'''
        <div class="col-md-6 mb-4">
            <div class="card comodato-card h-100">
                <div class="card-header">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="fw-bold">{comodato.razao_social}</span>
                        <span class="badge bg-primary">{comodato.quantidade} unidades</span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row mb-2">
                        <div class="col-6">
                            <small class="text-muted">CRM:</small>
                            <div class="fw-bold">{comodato.crm}</div>
                        </div>
                        <div class="col-6">
                            <small class="text-muted">CNPJ:</small>
                            <div>{comodato.cnpj}</div>
                        </div>
                    </div>
                    
                    <div class="mb-2">
                        <small class="text-muted">Destino:</small>
                        <div>{comodato.destino}</div>
                    </div>
                    
                    <div class="mb-2">
                        <small class="text-muted">Modelo:</small>
                        <div class="fw-bold">{comodato.modelo}</div>
                    </div>
                    
                    <div class="row mb-2">
                        <div class="col-6">
                            <small class="text-muted">Processador:</small>
                            <div>{comodato.processador}</div>
                        </div>
                        <div class="col-6">
                            <small class="text-muted">Placa de Vídeo:</small>
                            <div>{comodato.placa_video}</div>
                        </div>
                    </div>
                    
                    <div class="row mb-3">
                        <div class="col-6">
                            <small class="text-muted">RAM:</small>
                            <div>{comodato.memoria_ram}</div>
                        </div>
                        <div class="col-6">
                            <small class="text-muted">Armazenamento:</small>
                            <div>{comodato.armazenamento}</div>
                        </div>
                    </div>
                    
                    <div class="border-top pt-2">
                        <div class="row">
                            <div class="col-6">
                                <small class="text-muted">Valor Unitário:</small>
                                <div class="fw-bold text-success">R$ {comodato.valor_unitario:,.2f}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">Valor Total:</small>
                                <div class="fw-bold valor-destaque">R$ {comodato.valor_total:,.2f}</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="card-footer bg-transparent">
                    <small class="text-muted">
                        <i class="fas fa-calendar me-1"></i>
                        Criado em: {comodato.data_criacao.strftime('%d/%m/%Y')}
                    </small>
                </div>
            </div>
        </div>
        '''
    
    # Estatísticas
    total_comodatos = len(comodatos)
    total_unidades = sum(c.quantidade for c in comodatos)
    valor_total = sum(c.valor_total for c in comodatos)
    
    content = f'''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Comodatos</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <a href="/comodatos/novo" class="btn btn-avell">
                <i class="fas fa-plus me-1"></i> Novo Comodato
            </a>
        </div>
    </div>

    <!-- Estatísticas -->
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="card stats-card">
                <div class="stats-number">{total_comodatos}</div>
                <div class="stats-label">Contratos</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stats-card">
                <div class="stats-number">{total_unidades}</div>
                <div class="stats-label">Total de Unidades</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stats-card">
                <div class="stats-number">R$ {valor_total:,.2f}</div>
                <div class="stats-label">Valor Total</div>
            </div>
        </div>
    </div>

    <div class="row">
        {comodatos_html if comodatos else '<div class="col-12"><div class="card"><div class="card-body text-center py-5"><i class="fas fa-file-contract fa-3x text-muted mb-3"></i><h5 class="text-muted">Nenhum contrato de comodato cadastrado</h5><a href="/comodatos/novo" class="btn btn-avell mt-2"><i class="fas fa-plus me-1"></i> Cadastrar Primeiro Comodato</a></div></div></div>'}
    </div>
    '''
    
    return render_base(content, 'comodatos')

# Template Form Comodato - ATUALIZADO COM EXEMPLOS E COR VERMELHA
def render_form_comodato():
    content = '''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Novo Comodato</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <a href="/comodatos" class="btn btn-outline-secondary">
                <i class="fas fa-arrow-left me-1"></i> Voltar
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <i class="fas fa-file-contract me-2"></i> Dados do Comodato
        </div>
        <div class="card-body">
            <form method="POST" class="needs-validation" novalidate>
                <h5 class="section-title">Dados da Empresa</h5>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="crm" class="form-label">CRM *</label>
                        <input type="text" class="form-control" id="crm" name="crm" 
                               placeholder="Ex: CRM/SP 123456" required>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="razao_social" class="form-label">Razão Social *</label>
                        <input type="text" class="form-control" id="razao_social" name="razao_social" 
                               placeholder="Ex: Hospital São Paulo Ltda" required>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="cnpj" class="form-label">CNPJ *</label>
                        <input type="text" class="form-control" id="cnpj" name="cnpj" 
                               placeholder="Ex: 12.345.678/0001-90" required>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="destino" class="form-label">Destino *</label>
                        <input type="text" class="form-control" id="destino" name="destino" 
                               placeholder="Ex: Setor de Radiologia" required>
                    </div>
                </div>

                <h5 class="section-title mt-4">Especificações do Produto</h5>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="modelo" class="form-label">Modelo *</label>
                        <input type="text" class="form-control" id="modelo" name="modelo" 
                               placeholder="Ex: Avell A62 MUV" required>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="processador" class="form-label">Processador *</label>
                        <input type="text" class="form-control" id="processador" name="processador" 
                               placeholder="Ex: Intel Core i7-13700H" required>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="placa_video" class="form-label">Placa de Vídeo *</label>
                        <input type="text" class="form-control" id="placa_video" name="placa_video" 
                               placeholder="Ex: NVIDIA GeForce RTX 4060" required>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="cor" class="form-label">Cor</label>
                        <input type="text" class="form-control" id="cor" name="cor" 
                               placeholder="Ex: Preto Fosco">
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="tela" class="form-label">Tela</label>
                        <input type="text" class="form-control" id="tela" name="tela" 
                               placeholder="Ex: 15.6'' FHD 144Hz">
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="memoria_ram" class="form-label">Memória RAM *</label>
                        <input type="text" class="form-control" id="memoria_ram" name="memoria_ram" 
                               placeholder="Ex: 16GB DDR5" required>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="armazenamento" class="form-label">Armazenamento *</label>
                        <input type="text" class="form-control" id="armazenamento" name="armazenamento" 
                               placeholder="Ex: 1TB SSD NVMe" required>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="sistema_operacional" class="form-label">Sistema Operacional</label>
                        <input type="text" class="form-control" id="sistema_operacional" name="sistema_operacional" 
                              placeholder="Ex: Windows 11 Pro">
                    </div>
                </div>

                <h5 class="section-title mt-4">Quantidade e Valores</h5>
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label for="quantidade" class="form-label">Quantidade *</label>
                        <input type="number" class="form-control" id="quantidade" name="quantidade" 
                               min="1" placeholder="Ex: 5" required>
                    </div>
                    
                    <div class="col-md-4 mb-3">
                        <label for="valor_unitario" class="form-label">Valor Unitário (R$) *</label>
                        <input type="number" class="form-control" id="valor_unitario" name="valor_unitario" 
                               step="0.01" min="0" placeholder="Ex: 5999.99" required>
                    </div>
                    
                    <div class="col-md-4 mb-3">
                        <label for="valor_total" class="form-label">Valor Total (R$) *</label>
                        <input type="number" class="form-control" id="valor_total" name="valor_total" 
                               step="0.01" min="0" readonly placeholder="Será calculado automaticamente">
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="observacoes" class="form-label">Observações</label>
                    <textarea class="form-control" id="observacoes" name="observacoes" rows="3" 
                              placeholder="Ex: Equipamento para uso exclusivo no setor de diagnóstico por imagem..."></textarea>
                </div>
                
                <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                    <a href="/comodatos" class="btn btn-secondary me-md-2">Cancelar</a>
                    <button type="submit" class="btn btn-avell">Cadastrar Comodato</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const quantidade = document.getElementById('quantidade');
            const valorUnitario = document.getElementById('valor_unitario');
            const valorTotal = document.getElementById('valor_total');
            
            function calcularTotal() {
                const qtd = parseInt(quantidade.value) || 0;
                const unitario = parseFloat(valorUnitario.value) || 0;
                valorTotal.value = (qtd * unitario).toFixed(2);
            }
            
            quantidade.addEventListener('input', calcularTotal);
            valorUnitario.addEventListener('input', calcularTotal);

            // Formatação automática do CNPJ
            const cnpjInput = document.getElementById('cnpj');
            cnpjInput.addEventListener('input', function(e) {
                let value = e.target.value.replace(/\\D/g, '');
                
                if (value.length <= 14) {
                    value = value.replace(/^(\\d{2})(\\d)/, '$1.$2')
                                 .replace(/^(\\d{2})\\.(\\d{3})(\\d)/, '$1.$2.$3')
                                 .replace(/\\.(\\d{3})(\\d)/, '.$1/$2')
                                 .replace(/(\\d{4})(\\d)/, '$1-$2');
                }
                
                e.target.value = value;
            });

            // Focar no primeiro campo
            document.getElementById('crm').focus();
        });
    </script>
    '''
    
    return render_base(content, 'comodatos')

# Template Relatórios
def render_relatorios(emprestimos_mes=0, clientes_ativos=0, notebooks_emprestados=0, total_comodatos=0, valor_total_comodatos=0):
    content = f'''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Relatórios</h1>
    </div>

    <!-- Estatísticas Principais -->
    <div class="row">
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{emprestimos_mes}</div>
                <div class="stats-label">Empréstimos Este Mês</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{clientes_ativos}</div>
                <div class="stats-label">Clientes com Empréstimos Ativos</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">{notebooks_emprestados}</div>
                <div class="stats-label">Notebooks Emprestados</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stats-card">
                <div class="stats-number">R$ {valor_total_comodatos:,.2f}</div>
                <div class="stats-label">Valor em Comodatos</div>
            </div>
        </div>
    </div>

    <div class="row mt-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-chart-pie me-2"></i> Status dos Notebooks
                </div>
                <div class="card-body">
                    <canvas id="graficoStatus" height="200"></canvas>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-chart-bar me-2"></i> Empréstimos por Mês (2024)
                </div>
                <div class="card-body">
                    <canvas id="graficoMensal" height="200"></canvas>
                </div>
            </div>
        </div>
    </div>

    <div class="row mt-4">
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-table me-2"></i> Resumo do Mês Atual
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th>Período</th>
                                    <th>Novos Empréstimos</th>
                                    <th>Devoluções</th>
                                    <th>Clientes Novos</th>
                                    <th>Notebooks Novos</th>
                                    <th>Comodatos Ativos</th>
                                    <th>Taxa de Ocupação</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>{datetime.now().strftime("%B %Y").title()}</td>
                                    <td class="text-success fw-bold">{emprestimos_mes}</td>
                                    <td class="text-info">-</td>
                                    <td class="text-primary">-</td>
                                    <td class="text-warning">-</td>
                                    <td class="text-secondary">{total_comodatos}</td>
                                    <td>
                                        <div class="progress">
                                            <div class="progress-bar bg-success" style="width: 75%">75%</div>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Gráfico de Status dos Notebooks
            const ctxStatus = document.getElementById('graficoStatus').getContext('2d');
            new Chart(ctxStatus, {{
                type: 'doughnut',
                data: {{
                    labels: ['Disponíveis', 'Emprestados', 'Manutenção'],
                    datasets: [{{
                        data: [8, 2, 1],
                        backgroundColor: ['#28a745', '#dc3545', '#ffc107']
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }}
                    }}
                }}
            }});

            // Gráfico Mensal
            const ctxMensal = document.getElementById('graficoMensal').getContext('2d');
            new Chart(ctxMensal, {{
                type: 'bar',
                data: {{
                    labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
                    datasets: [{{
                        label: 'Empréstimos',
                        data: [12, 15, 8, 11, 14, 10, 13, 9, 7, 0, 0, 0],
                        backgroundColor: '#e30613'
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
        }});
    </script>
    '''
    
    return render_base(content, 'relatorios')

# Template Form Notebook - ATUALIZADO COM EXEMPLOS
def render_form_notebook():
    content = '''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Novo Notebook</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <a href="/notebooks" class="btn btn-outline-secondary">
                <i class="fas fa-arrow-left me-1"></i> Voltar
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <i class="fas fa-laptop me-2"></i> Especificações do Notebook
        </div>
        <div class="card-body">
            <form method="POST" class="needs-validation" novalidate>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="modelo" class="form-label">Modelo *</label>
                        <input type="text" class="form-control" id="modelo" name="modelo" 
                               placeholder="Ex: Avell A62 MUV" required>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="numero_serie" class="form-label">Número de Série *</label>
                        <input type="text" class="form-control" id="numero_serie" name="numero_serie" 
                               placeholder="Ex: SN2024AVL001" required>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="processador" class="form-label">Processador</label>
                        <input type="text" class="form-control" id="processador" name="processador" 
                               placeholder="Ex: Intel Core i7-13700H">
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="placa_video" class="form-label">Placa de Vídeo</label>
                        <input type="text" class="form-control" id="placa_video" name="placa_video" 
                               placeholder="Ex: NVIDIA GeForce RTX 4060">
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="memoria_ram" class="form-label">Memória RAM</label>
                        <input type="text" class="form-control" id="memoria_ram" name="memoria_ram" 
                               placeholder="Ex: 16GB DDR5">
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="armazenamento" class="form-label">Armazenamento</label>
                        <input type="text" class="form-control" id="armazenamento" name="armazenamento" 
                               placeholder="Ex: 1TB SSD NVMe">
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label for="cor" class="form-label">Cor</label>
                        <input type="text" class="form-control" id="cor" name="cor" 
                               placeholder="Ex: Preto Fosco">
                    </div>
                    
                    <div class="col-md-4 mb-3">
                        <label for="tela" class="form-label">Tela</label>
                        <input type="text" class="form-control" id="tela" name="tela" 
                               placeholder="Ex: 15.6'' FHD 144Hz">
                    </div>
                    
                    <div class="col-md-4 mb-3">
                        <label for="sistema_operacional" class="form-label">Sistema Operacional</label>
                        <input type="text" class="form-control" id="sistema_operacional" name="sistema_operacional" 
                               placeholder="Ex: Windows 11 Pro">
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="valor" class="form-label">Valor (R$)</label>
                        <input type="number" class="form-control" id="valor" name="valor" step="0.01" min="0" 
                               placeholder="Ex: 5999.99">
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="data_aquisicao" class="form-label">Data de Aquisição</label>
                        <input type="date" class="form-control" id="data_aquisicao" name="data_aquisicao">
                    </div>
                </div>
                
                <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                    <a href="/notebooks" class="btn btn-secondary me-md-2">Cancelar</a>
                    <button type="submit" class="btn btn-avell">Cadastrar Notebook</button>
                </div>
            </form>
        </div>
    </div>
    '''
    
    return render_base(content, 'notebooks')

# Template Form Empréstimo
def render_form_emprestimo(clientes=None, notebooks=None):
    if clientes is None:
        clientes = []
    if notebooks is None:
        notebooks = []
    
    clientes_options = ''.join([f'<option value="{c.id}">{c.nome} - {c.cpf_cnpj}</option>' for c in clientes])
    notebooks_options = ''.join([f'<option value="{n.id}">{n.modelo} - {n.numero_serie}</option>' for n in notebooks])
    
    hoje = datetime.now().strftime('%Y-%m-%d')
    trinta_dias = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    content = f'''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Novo Empréstimo</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <a href="/emprestimos" class="btn btn-outline-secondary">
                <i class="fas fa-arrow-left me-1"></i> Voltar
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <i class="fas fa-handshake me-2"></i> Dados do Empréstimo
        </div>
        <div class="card-body">
            <form method="POST" class="needs-validation" novalidate>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="cliente_id" class="form-label">Cliente *</label>
                        <select class="form-select" id="cliente_id" name="cliente_id" required>
                            <option value="">Selecione um cliente...</option>
                            {clientes_options}
                        </select>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="notebook_id" class="form-label">Notebook *</label>
                        <select class="form-select" id="notebook_id" name="notebook_id" required>
                            <option value="">Selecione um notebook...</option>
                            {notebooks_options}
                        </select>
                        {'<div class="text-warning small mt-1"><i class="fas fa-exclamation-triangle me-1"></i>Nenhum notebook disponível no momento.</div>' if not notebooks else ''}
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="data_emprestimo" class="form-label">Data do Empréstimo *</label>
                        <input type="date" class="form-control" id="data_emprestimo" name="data_emprestimo" value="{hoje}" required>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="data_devolucao_prevista" class="form-label">Previsão de Devolução *</label>
                        <input type="date" class="form-control" id="data_devolucao_prevista" name="data_devolucao_prevista" value="{trinta_dias}" required>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="observacoes" class="form-label">Observações</label>
                    <textarea class="form-control" id="observacoes" name="observacoes" rows="3" placeholder="Observações sobre o empréstimo..."></textarea>
                </div>
                
                <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                    <a href="/emprestimos" class="btn btn-secondary me-md-2">Cancelar</a>
                    <button type="submit" class="btn btn-avell" {'disabled' if not notebooks else ''}>Realizar Empréstimo</button>
                </div>
            </form>
        </div>
    </div>
    '''
    
    return render_base(content, 'emprestimos')

def render_usuarios(usuarios=None):
    if usuarios is None:
        usuarios = []
    
    usuarios_html = ''
    for usuario in usuarios:
        if usuario.email == 'pietro.admin':
            continue
            
        status_badge = '<span class="badge bg-success">Ativo</span>' if usuario.ativo else '<span class="badge bg-danger">Inativo</span>'
        permissao_badge = '<span class="badge bg-primary">Admin</span>' if usuario.permissao == 'admin' else '<span class="badge bg-secondary">Funcionário</span>'
        
        usuarios_html += f'''
        <tr>
            <td>
                <strong>{usuario.nome}</strong>
                <br><small class="text-muted">{usuario.email}</small>
            </td>
            <td>{permissao_badge}</td>
            <td>{status_badge}</td>
            <td>{usuario.data_criacao.strftime('%d/%m/%Y')}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button type="button" class="btn btn-outline-warning" data-bs-toggle="modal" data-bs-target="#modalEditarUsuario" onclick="carregarUsuario({usuario.id}, '{usuario.nome}', '{usuario.email}', '{usuario.permissao}', {str(usuario.ativo).lower()})">
                        <i class="fas fa-edit"></i>
                    </button>
                    {'<button type="button" class="btn btn-outline-danger" onclick="desativarUsuario(' + str(usuario.id) + ')"><i class="fas fa-ban"></i></button>' if usuario.ativo else '<button type="button" class="btn btn-outline-success" onclick="ativarUsuario(' + str(usuario.id) + ')"><i class="fas fa-check"></i></button>'}
                </div>
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
        <h1 class="h2">Gerenciar Usuários</h1>
        <div class="btn-toolbar mb-2 mb-md-0">
            <button type="button" class="btn btn-avell" data-bs-toggle="modal" data-bs-target="#modalNovoUsuario">
                <i class="fas fa-plus me-1"></i> Novo Usuário
            </button>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <i class="fas fa-users-cog me-2"></i> Usuários do Sistema
        </div>
        <div class="card-body">
            {'<div class="table-responsive"><table class="table table-striped table-hover"><thead><tr><th>Usuário</th><th>Permissão</th><th>Status</th><th>Data Criação</th><th>Ações</th></tr></thead><tbody>' + usuarios_html + '</tbody></table></div>' if usuarios else '<div class="text-center py-5"><i class="fas fa-users fa-3x text-muted mb-3"></i><p class="text-muted">Nenhum usuário cadastrado</p></div>'}
        </div>
    </div>

    <!-- Modal Novo Usuário -->
    <div class="modal fade" id="modalNovoUsuario" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Novo Usuário</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/usuarios">
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Nome Completo *</label>
                            <input type="text" class="form-control" name="nome" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Email *</label>
                            <input type="email" class="form-control" name="email" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Senha *</label>
                            <input type="password" class="form-control" name="senha" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Permissão</label>
                            <select class="form-select" name="permissao">
                                <option value="funcionario">Funcionário</option>
                                <option value="admin">Administrador</option>
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="submit" class="btn btn-avell">Criar Usuário</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Modal Editar Usuário -->
    <div class="modal fade" id="modalEditarUsuario" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Editar Usuário</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/usuarios/editar" id="formEditarUsuario">
                    <input type="hidden" name="usuario_id" id="editar_usuario_id">
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Nome Completo *</label>
                            <input type="text" class="form-control" name="nome" id="editar_nome" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Email *</label>
                            <input type="email" class="form-control" name="email" id="editar_email" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Nova Senha (deixe em branco para manter a atual)</label>
                            <input type="password" class="form-control" name="senha" id="editar_senha" placeholder="Digite nova senha...">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Permissão</label>
                            <select class="form-select" name="permissao" id="editar_permissao">
                                <option value="funcionario">Funcionário</option>
                                <option value="admin">Administrador</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="ativo" id="editar_ativo" value="1">
                                <label class="form-check-label" for="editar_ativo">
                                    Usuário Ativo
                                </label>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="submit" class="btn btn-avell">Salvar Alterações</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script>
        function carregarUsuario(id, nome, email, permissao, ativo) {{
            document.getElementById('editar_usuario_id').value = id;
            document.getElementById('editar_nome').value = nome;
            document.getElementById('editar_email').value = email;
            document.getElementById('editar_permissao').value = permissao;
            document.getElementById('editar_ativo').checked = ativo;
            document.getElementById('editar_senha').value = '';
        }}
        
        function desativarUsuario(id) {{
            if (confirm('Tem certeza que deseja desativar este usuário?')) {{
                window.location.href = '/usuarios/desativar/' + id;
            }}
        }}
        
        function ativarUsuario(id) {{
            if (confirm('Tem certeza que deseja ativar este usuário?')) {{
                window.location.href = '/usuarios/ativar/' + id;
            }}
        }}
    </script>
    '''
    
    return render_base(content, 'usuarios')

# Rotas de Autenticação
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        usuario = Usuario.query.filter_by(email=email, ativo=True).first()
        
        if usuario and usuario.check_senha(senha):
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            session['usuario_permissao'] = usuario.permissao
            session['usuario_email'] = usuario.email
            
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha incorretos!', 'danger')
    
    return render_login()

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

@app.route('/toggle-tema', methods=['POST'])
def toggle_tema():
    tema_atual = session.get('tema', 'escuro')
    session['tema'] = 'claro' if tema_atual == 'escuro' else 'escuro'
    return redirect(request.referrer or '/dashboard')

# Rotas Principais
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    total_clientes = Cliente.query.count()
    total_notebooks = Notebook.query.count()
    emprestimos_ativos = Emprestimo.query.filter_by(status='ativo').count()
    emprestimos_atrasados = Emprestimo.query.filter(
        Emprestimo.status == 'ativo',
        Emprestimo.data_devolucao_prevista < datetime.now()
    ).count()
    
    proximas_devolucoes = Emprestimo.query.filter_by(status='ativo')\
        .order_by(Emprestimo.data_devolucao_prevista.asc())\
        .limit(5)\
        .all()
    
    total_comodatos = Comodato.query.count()
    valor_total_comodatos = sum(c.valor_total for c in Comodato.query.all())
    
    return render_dashboard(total_clientes, total_notebooks, emprestimos_ativos, emprestimos_atrasados, proximas_devolucoes, total_comodatos, valor_total_comodatos)

@app.route('/clientes')
def clientes():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    clientes = Cliente.query.all()
    return render_clientes(clientes)

@app.route('/clientes/novo', methods=['GET', 'POST'])
def novo_cliente():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Validar CPF/CNPJ
            cpf_cnpj = request.form['cpf_cnpj']
            if not validar_cpf_cnpj(cpf_cnpj):
                flash('CPF ou CNPJ inválido!', 'danger')
                return render_form_cliente()
            
            # Validar email se fornecido
            email = request.form['email']
            if email and not ('@' in email and '.' in email.split('@')[1]):
                flash('Email inválido! Deve conter @ e domínio.', 'danger')
                return render_form_cliente()
            
            # Formatar CPF/CNPJ
            cpf_cnpj_formatado = formatar_cpf_cnpj(cpf_cnpj)
            
            # Combinar DDI com telefone
            ddi = request.form.get('ddi', '+55')
            telefone = request.form['telefone']
            telefone_completo = f"{ddi} {telefone}" if telefone else None
            
            cliente = Cliente(
                nome=request.form['nome'],
                cpf_cnpj=cpf_cnpj_formatado,
                telefone=telefone_completo,
                email=email if email else None,
                endereco=request.form['endereco']
            )
            db.session.add(cliente)
            db.session.commit()
            flash('Cliente cadastrado com sucesso!', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')
    
    return render_form_cliente()

@app.route('/notebooks')
def notebooks():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    notebooks = Notebook.query.all()
    return render_notebooks(notebooks)

@app.route('/notebooks/novo', methods=['GET', 'POST'])
def novo_notebook():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            notebook = Notebook(
                modelo=request.form['modelo'],
                processador=request.form['processador'],
                placa_video=request.form['placa_video'],
                memoria_ram=request.form['memoria_ram'],
                armazenamento=request.form['armazenamento'],
                numero_serie=request.form['numero_serie'],
                cor=request.form['cor'],
                tela=request.form['tela'],
                sistema_operacional=request.form['sistema_operacional'],
                valor=float(request.form['valor']) if request.form['valor'] else None,
                data_aquisicao=datetime.strptime(request.form['data_aquisicao'], '%Y-%m-%d') if request.form['data_aquisicao'] else None
            )
            db.session.add(notebook)
            db.session.commit()
            flash('Notebook cadastrado com sucesso!', 'success')
            return redirect(url_for('notebooks'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')
    
    return render_form_notebook()

@app.route('/emprestimos')
def emprestimos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    status = request.args.get('status', 'todos')
    
    query = Emprestimo.query
    
    if status == 'ativos':
        query = query.filter_by(status='ativo')
    elif status == 'finalizados':
        query = query.filter_by(status='finalizado')
    elif status == 'atrasados':
        query = query.filter(
            Emprestimo.status == 'ativo',
            Emprestimo.data_devolucao_prevista < datetime.now()
        )
    
    emprestimos = query.order_by(Emprestimo.data_emprestimo.desc()).all()
    return render_emprestimos(emprestimos, status)

@app.route('/emprestimos/novo', methods=['GET', 'POST'])
def novo_emprestimo():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            emprestimo = Emprestimo(
                cliente_id=int(request.form['cliente_id']),
                notebook_id=int(request.form['notebook_id']),
                usuario_id=session['usuario_id'],
                data_emprestimo=datetime.strptime(request.form['data_emprestimo'], '%Y-%m-%d'),
                data_devolucao_prevista=datetime.strptime(request.form['data_devolucao_prevista'], '%Y-%m-%d'),
                observacoes=request.form['observacoes']
            )
            
            # Atualizar status do notebook
            notebook = Notebook.query.get(int(request.form['notebook_id']))
            notebook.status = 'emprestado'
            
            db.session.add(emprestimo)
            db.session.commit()
            
            flash('Empréstimo realizado com sucesso!', 'success')
            return redirect(url_for('emprestimos'))
            
        except Exception as e:
            flash(f'Erro ao realizar empréstimo: {str(e)}', 'danger')
    
    clientes = Cliente.query.all()
    notebooks = Notebook.query.filter_by(status='disponivel').all()
    return render_form_emprestimo(clientes, notebooks)

@app.route('/emprestimos/<int:id>/devolver', methods=['POST'])
def devolver_emprestimo(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    try:
        emprestimo = Emprestimo.query.get_or_404(id)
        emprestimo.status = 'finalizado'
        emprestimo.data_devolucao_real = datetime.now()
        
        # Liberar notebook
        notebook = Notebook.query.get(emprestimo.notebook_id)
        notebook.status = 'disponivel'
        
        db.session.commit()
        
        flash('Devolução registrada com sucesso!', 'success')
        
    except Exception as e:
        flash(f'Erro ao registrar devolução: {str(e)}', 'danger')
    
    return redirect(url_for('emprestimos'))

# Rotas para Comodatos
@app.route('/comodatos')
def comodatos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    comodatos = Comodato.query.all()
    return render_comodatos(comodatos)

@app.route('/comodatos/novo', methods=['GET', 'POST'])
def novo_comodato():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            comodato = Comodato(
                crm=request.form['crm'],
                razao_social=request.form['razao_social'],
                cnpj=request.form['cnpj'],
                destino=request.form['destino'],
                modelo=request.form['modelo'],
                processador=request.form['processador'],
                placa_video=request.form['placa_video'],
                cor=request.form['cor'],
                tela=request.form['tela'],
                memoria_ram=request.form['memoria_ram'],
                armazenamento=request.form['armazenamento'],
                sistema_operacional=request.form['sistema_operacional'],
                quantidade=int(request.form['quantidade']),
                valor_unitario=float(request.form['valor_unitario']),
                valor_total=float(request.form['valor_total']),
                observacoes=request.form['observacoes']
            )
            db.session.add(comodato)
            db.session.commit()
            flash('Comodato cadastrado com sucesso!', 'success')
            return redirect(url_for('comodatos'))
        except Exception as e:
            flash(f'Erro ao cadastrar comodato: {str(e)}', 'danger')
    
    return render_form_comodato()

@app.route('/relatorios')
def relatorios():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Dados para relatórios
    emprestimos_mes = Emprestimo.query.filter(
        Emprestimo.data_emprestimo >= datetime.now().replace(day=1)
    ).count()
    
    clientes_ativos = db.session.query(Emprestimo.cliente_id)\
        .filter(Emprestimo.status == 'ativo')\
        .distinct()\
        .count()
    
    notebooks_emprestados = Notebook.query.filter_by(status='emprestado').count()
    
    total_comodatos = Comodato.query.count()
    valor_total_comodatos = sum(c.valor_total for c in Comodato.query.all())
    
    return render_relatorios(emprestimos_mes, clientes_ativos, notebooks_emprestados, total_comodatos, valor_total_comodatos)

@app.route('/usuarios')
def usuarios():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Apenas pietro.admin pode acessar
    if session.get('usuario_email') != 'pietro.admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('dashboard'))
    
    usuarios = Usuario.query.all()
    return render_usuarios(usuarios)

@app.route('/usuarios', methods=['POST'])
def criar_usuario():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Apenas pietro.admin pode criar usuários
    if session.get('usuario_email') != 'pietro.admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        permissao = request.form['permissao']
        
        if Usuario.query.filter_by(email=email).first():
            flash('Já existe um usuário com este email!', 'danger')
            return redirect(url_for('usuarios'))
        
        usuario = Usuario(
            nome=nome,
            email=email,
            permissao=permissao
        )
        usuario.set_senha(senha)
        
        db.session.add(usuario)
        db.session.commit()
        
        flash('Usuário criado com sucesso!', 'success')
        
    except Exception as e:
        flash(f'Erro ao criar usuário: {str(e)}', 'danger')
    
    return redirect(url_for('usuarios'))

@app.route('/usuarios/editar', methods=['POST'])
def editar_usuario():
    if 'usuario_id' not in session or session.get('usuario_email') != 'pietro.admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        usuario_id = request.form['usuario_id']
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        permissao = request.form['permissao']
        ativo = 'ativo' in request.form
        
        usuario = Usuario.query.get_or_404(usuario_id)
        
        # Não permitir editar o pietro.admin
        if usuario.email == 'pietro.admin':
            flash('Não é possível editar o administrador principal!', 'danger')
            return redirect(url_for('usuarios'))
        
        # Verificar se o email já existe em outro usuário
        if email != usuario.email and Usuario.query.filter_by(email=email).first():
            flash('Já existe um usuário com este email!', 'danger')
            return redirect(url_for('usuarios'))
        
        usuario.nome = nome
        usuario.email = email
        usuario.permissao = permissao
        usuario.ativo = ativo
        
        # Atualizar senha apenas se fornecida
        if senha:
            usuario.set_senha(senha)
        
        db.session.commit()
        
        flash('Usuário atualizado com sucesso!', 'success')
        
    except Exception as e:
        flash(f'Erro ao editar usuário: {str(e)}', 'danger')
    
    return redirect(url_for('usuarios'))

@app.route('/usuarios/desativar/<int:id>')
def desativar_usuario(id):
    if 'usuario_id' not in session or session.get('usuario_email') != 'pietro.admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        usuario = Usuario.query.get_or_404(id)
        
        # Não permitir desativar o pietro.admin
        if usuario.email == 'pietro.admin':
            flash('Não é possível desativar o administrador principal!', 'danger')
            return redirect(url_for('usuarios'))
        
        usuario.ativo = False
        db.session.commit()
        flash('Usuário desativado com sucesso!', 'success')
        
    except Exception as e:
        flash(f'Erro ao desativar usuário: {str(e)}', 'danger')
    
    return redirect(url_for('usuarios'))

@app.route('/usuarios/ativar/<int:id>')
def ativar_usuario(id):
    if 'usuario_id' not in session or session.get('usuario_email') != 'pietro.admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        usuario = Usuario.query.get_or_404(id)
        usuario.ativo = True
        db.session.commit()
        flash('Usuário ativado com sucesso!', 'success')
        
    except Exception as e:
        flash(f'Erro ao ativar usuário: {str(e)}', 'danger')
    
    return redirect(url_for('usuarios'))

# Função para criar usuário admin
def criar_admin():
    if not Usuario.query.filter_by(email='pietro.admin').first():
        admin = Usuario(
            nome='Pietro Admin',
            email='pietro.admin',
            permissao='admin'
        )
        admin.set_senha('Pietro&Yuri29')
        db.session.add(admin)
        db.session.commit()
        print("✅ Administrador principal criado!")
        print("👤 Email: pietro.admin")
        print("🔑 Senha: Pietro&Yuri29")

# Inicialização do sistema - CORRIGIDA
def init_database():
    with app.app_context():
        try:
            print("🔄 Iniciando criação do banco de dados...")
            
            # ✅ FORÇAR criação das tabelas
            db.create_all()
            print("✅ Tabelas criadas com sucesso!")
            
            # ✅ Verificar se as tabelas foram criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tabelas no banco: {tables}")
            
            # ✅ Só então criar admin
            criar_admin()
            
            print("🎉 Banco de dados inicializado com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro durante inicialização: {e}")
            import traceback
            traceback.print_exc()

# Inicializar o banco quando o app iniciar
init_database()

if __name__ == '__main__':
    # ⚠️ APENAS para desenvolvimento
    app.run(host='0.0.0.0', port=5000, debug=True)



