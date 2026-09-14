# Build from the repository root:
#   docker build -f demo/Dockerfile -t rocketflag-python-demo .
#   docker run --rm rocketflag-python-demo
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE.md ./
COPY src ./src
COPY demo/demo.py ./demo.py

RUN pip install --no-cache-dir .

CMD ["python", "demo.py"]
