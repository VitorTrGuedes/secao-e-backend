FROM python:3.14-slim

# Evita a criação de arquivos .pyc e força saída direta nos logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \ 
build-essential \ 
libpq-dev \ 
&& rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do projeto4
COPY . .

# Expõe a porta do Django
EXPOSE 8000

# Executa as migrações e sobe o servidor com Gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn backend.wsgi:application --bind 0.0.0.0:8000"]