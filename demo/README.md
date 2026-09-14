# Python SDK demo

Evaluates a live RocketFlag (`01ecwHSL0eOCfy5ufzEP`) through this package.

From the repository root:

```bash
docker build -f demo/Dockerfile -t rocketflag-python-demo .
docker run --rm rocketflag-python-demo
```

Without Docker:

```bash
python -m pip install -e .
python demo/demo.py
```
