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

Notícias e críticas são cadastradas manualmente pelo painel `/admin/`, no modelo `Article`, escolhendo o tipo `Notícia` ou `Crítica`. A API de artigos é somente de leitura. Para importar notícias automaticamente pelos feeds RSS configurados, execute `python manage.py buscar_noticias`; quando o feed publica o corpo completo, o importador preserva sua formatação e imagens, sanitiza o HTML antes da exibição e mantém um link para a matéria original. Se o feed fornecer apenas um resumo, esse resumo é exibido com o link para a fonte. Notícias automáticas existentes também são atualizadas sem alterar publicações manuais. Se algum feed estiver indisponível, os outros acessíveis ainda são importados e a falha da fonte é registrada; a execução só falha quando todos os feeds estiverem inacessíveis. A conexão definida em `DATABASE_URL` precisa estar válida.

O GitHub Actions executa a importação RSS uma vez por dia às 07:10 no horário de Brasília (UTC−3). O agendador usa UTC, portanto o workflow está configurado para 10:10 UTC. Para habilitar a execução, cadastre a connection string do PostgreSQL como segredo `DATABASE_URL` em **Settings → Secrets and variables → Actions**. O GitHub pode iniciar tarefas agendadas alguns minutos depois do horário configurado.

Para atualizar as notícias manualmente em caso de falha:
1. Abra o repositório no GitHub e vá até a aba **Actions**.
2. Na lista de workflows, selecione **Importar notícias RSS**.
3. Clique em **Run workflow**, mantenha a branch `main` selecionada e confirme em **Run workflow**.
4. Abra a execução criada e aguarde o job `importar-noticias` terminar. Confira se as etapas **Verificar configuração do banco** e **Importar notícias dos feeds RSS** ficaram verdes.
5. Se a execução falhar, abra a etapa vermelha para ver o erro. Confirme que o segredo `DATABASE_URL` está configurado em **Settings → Secrets and variables → Actions** e tente novamente.

Após uma execução bem-sucedida, a API passa a servir as notícias importadas. Atualize o site para buscar a lista atualizada.

| Método | Endpoint | Descrição | Autenticação |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/articles/` | Lista todas as notícias e análises publicadas | Pública |
| `GET` | `/api/articles/{slug}/` | Detalhes de um post específico + comentários aprovados | Pública |
| `POST` | `/api/comments/` | Envia comentário para o e-mail informado confirmar (Rate Limit: 5/min) | Pública |
| `POST` | `/api/comments/confirm/` | Confirma o e-mail e publica o comentário; link válido por 24 horas e uso único | Pública |
| `POST` | `/api/suggestions/` | Envio de sugestão de próxima crítica (Rate Limit: 5/min) | Pública |
| `GET/POST` | `/admin/` | Painel Administrativo com 2FA | Superuser + TOTP |
| `GET/POST` | `/recuperar-senha/` | Fluxo de recuperação de senha por e-mail | Pública |

Comentários novos só aparecem depois da confirmação do e-mail. O endereço fica privado, não é incluído nas respostas públicas da API e pode ser consultado no painel administrativo. No `/admin/`, filtre comentários por status, desmarque `is_approved` para ocultá-los ou use a ação de exclusão para removê-los.

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
ALLOWED_HOSTS=localhost,127.0.0.1
PASSWORD_RESET_DOMAIN=localhost:8000
PASSWORD_RESET_USE_HTTPS=False

No Render, o hostname da aplicação é incluído automaticamente por meio da variável
`RENDER_EXTERNAL_HOSTNAME`. Para um domínio personalizado, adicione-o à variável
`ALLOWED_HOSTS`, separado por vírgulas.

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
FRONTEND_URL (URL pública do frontend, usada no link de confirmação de comentários)
RESEND_API_KEY (chave da API do Resend para enviar os e-mails de confirmação)

O remetente definido em `DEFAULT_FROM_EMAIL` também precisa estar verificado no Resend.

👤 Autor
Desenvolvido por Vitor Guedes.
Críticas, notícias e sugestões sobre o universo do Cinema, Animes e Séries!
