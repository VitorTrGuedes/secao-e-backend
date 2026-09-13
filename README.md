code
Markdown
# 🎬 Seção E — Backend API

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Django-6.x-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/Django_REST_Framework-3.x-red?style=for-the-badge&logo=django&logoColor=white" alt="DRF" />
  <img src="https://img.shields.io/badge/SQLite-Local-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/PostgreSQL-Produção-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Tests-100%25_Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests" />
</p>

> **API REST e Painel Administrativo do portal Seção E** — plataforma voltada para publicação de notícias, críticas e análises autorais sobre Cinema, Animes e Séries, com espaço interativo para a comunidade opinar e sugerir pautas.

---

## 📌 Funcionalidades Principais

- 📰 **Gestão de Conteúdo:** Publicação de Notícias e Críticas autorais com atribuição de notas (1 a 10), categorias e capas.
- 💬 **Opiniões dos Leitores:** Endpoint público para envio de comentários em tempo real, com sistema de aprovação e moderação via Django Admin.
- 💡 **Canal de Sugestões:** Coleta estruturada de indicações de obras feitas pelo público para futuras análises.
- 🛡️ **Segurança Avançada:**
  - **Autenticação em 2 Etapas (2FA/MFA):** Proteção do painel via TOTP (`django-otp`) integrado a apps como Google Authenticator.
  - **Anti-Spam (Rate Limiting):** Proteção de endpoints contra bots limitando requisições anônimas a 5 envios/minuto.
  - **Recuperação Segura de Senha:** Fluxo nativo de redefinição de credenciais por e-mail com tokens de uso único.
  - **Proteção CORS:** Comunicação controlada exclusivamente para as origens autorizadas do Frontend (Vite/React).
  - **Arquitetura 12-Factor:** Variáveis sensíveis e credenciais totalmente isoladas via `.env`.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** [Python 3.11+](https://www.python.org/)
- **Framework Web:** [Django](https://www.djangoproject.com/)
- **API Toolkit:** [Django REST Framework (DRF)](https://www.django-rest-framework.org/)
- **Segurança & 2FA:** [django-otp](https://django-otp-official.readthedocs.io/)
- **E-mails Transacionais:** [django-anymail](https://anymail.dev/) (Integrável com Brevo / Resend via HTTPS)
- **Containerização:** [Docker](https://www.docker.com/) & [Gunicorn](https://gunicorn.org/)
- **Testes Automatizados:** Django Test Runner & DRF `APITestCase`

---

## 📡 Endpoints da API

| Método | Endpoint | Descrição | Autenticação |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/articles/` | Lista todas as notícias e análises publicadas | Pública |
| `GET` | `/api/articles/{slug}/` | Detalhes de um post específico + comentários aprovados | Pública |
| `POST` | `/api/comments/` | Envio de nova opinião/comentário (Rate Limit: 5/min) | Pública |
| `POST` | `/api/suggestions/` | Envio de sugestão de próxima crítica (Rate Limit: 5/min) | Pública |
| `GET/POST` | `/admin/` | Painel administrativo com 2FA | Superuser + TOTP |
| `GET/POST` | `/recuperar-senha/` | Fluxo de recuperação de senha por e-mail | Pública |

---

## 🚀 Como Executar o Projeto Localmente

### Pré-requisitos
- Python 3.11 ou superior instalado
- Git configurado

### 1. Clonar o repositório
```bash
git clone https://github.com/VitorTrGuedes/secao-e-backend.git
cd secao-e-backend


2. Criar e ativar o Ambiente Virtual (venv)
No Windows (PowerShell):
code
Powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
No Linux / Mac / Git Bash:
code
Bash
python3 -m venv venv
source venv/bin/activate


3. Instalar as dependências
code
Bash
pip install -r requirements.txt

4. Configurar as Variáveis de Ambiente
Crie um arquivo .env na raiz do projeto (use o .env.example como base):
code
Env
SECRET_KEY=sua-chave-secreta-local-aqui
DEBUG=True


5. Executar as Migrações do Banco de Dados
code
Bash
python manage.py migrate


6. Criar o Usuário Administrador
code
Bash
python manage.py createsuperuser


7. Iniciar o Servidor
code
Bash
python manage.py runserver
Acesse a API em http://127.0.0.1:8000/api/articles/ e o painel em http://127.0.0.1:8000/admin/.
🧪 Como Rodar os Testes Automatizados
O projeto conta com uma suíte de testes cobrindo validações de modelos, listagem de artigos, envio de comentários, bloqueios de segurança e rate limiting:
code
Bash
python manage.py test core
🐳 Executando com Docker
Você pode subir toda a aplicação em container sem precisar configurar dependências locais do Python:
code
Bash


# Construir a imagem Docker
docker build -t secao-e-backend .


# Executar o container na porta 8000
docker run -p 8000:8000 --env-file .env secao-e-backend
☁️ Deploy em Produção (Render)
Crie um banco PostgreSQL gerenciado no Render.com.
Configure um Web Service conectado a este repositório.
Configure os comandos:
Build Command: pip install -r requirements.txt && python manage.py migrate
Start Command: gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
Adicione as variáveis de ambiente no dashboard do Render:
SECRET_KEY
DEBUG=False
DATABASE_URL (URL interna do PostgreSQL)
CORS_ALLOWED_ORIGINS (URL do frontend na Vercel)


👤 Autor
Desenvolvido por Vitor Guedes.
Críticas, notícias e sugestões sobre o universo do Cinema, Animes e Séries!
