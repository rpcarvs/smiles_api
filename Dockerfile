FROM mcr.microsoft.com/azure-functions/python:4-python3.11-slim

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true 

RUN apt update && apt install -y \
    openssh-client \
    git \
    supervisor \
    openbabel \
    libopenbabel-dev

# no root for the api
COPY . /home/site/wwwroot
WORKDIR /home/site/wwwroot

RUN pip install -r requirements.txt --no-cache --no-cache-dir
RUN mv supervisord.conf /etc/supervisor/supervisord.conf
RUN apt remove git -y && apt autoremove -y && apt autoclean -y

# Expose the port that the app will run on
EXPOSE 80

ENTRYPOINT ["supervisord"]
