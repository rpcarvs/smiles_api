FROM python:3.12-slim-bookworm

RUN apt update && apt install -y \
    openssh-client \
    git \
    openbabel \
    libopenbabel-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache --no-cache-dir

WORKDIR /var/task
COPY app/ ./app/
ENV PYTHONPATH=/var/task

#for local testing
# ADD aws-lambda-rie /usr/local/bin/aws-lambda-rie
# RUN chmod +x /usr/local/bin/aws-lambda-rie
# ENTRYPOINT ["/usr/local/bin/aws-lambda-rie", "python", "-m", "awslambdaric"]

ENTRYPOINT ["python", "-m", "awslambdaric"]
CMD ["app.smiles_api.lambda_handler"]