FROM python:3.12
WORKDIR /code
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash
RUN apt update && apt install --no-install-recommends -y git-lfs
# CMD ["fastapi", "run", "server.py", "--port", "8000"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
