# search_docnum

A small placeholder project used for demonstration purposes.

## Local development

Create a virtual environment with Python 3.12 or newer and install the project
in editable mode to ensure dependencies are resolved exactly as the container
does:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\\Scripts\\activate
pip install --upgrade pip
pip install -e .
python -m search_docnum
```

## Running with Docker

The repository ships with a ready-to-use Dockerfile and Docker Compose setup.
They install all Python dependencies declared in `pyproject.toml`, so the image
behaves the same regardless of whether you run it on Linux or Windows.

### Build and run with Docker directly

```bash
docker build -t search-docnum .
docker run --rm search-docnum
```

### Build and run with Docker Compose

```bash
docker compose up --build
```

The Compose file mounts the project directory into the container. This allows
you to edit the source code locally and rerun `docker compose up` without
rebuilding the image unless dependencies change.
