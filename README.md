# Kinora

**Open-source, self-hosted prompt-to-video.** Type a prompt, get a clip, all running on your own machine or with your own API key.

- **Pluggable providers:** generate locally on your GPU, in the cloud, or with a no-GPU mock for development.
- **Zero-build frontend:** plain HTML/JS served by the backend. Clone and run.
- **Runs in a container:** with [apple/container](https://github.com/apple/container) on Apple silicon, or Docker anywhere.

> Status: early (v0.1). Generate single clips today; editing features (trim, join, audio) are on the roadmap.

## Providers

| Provider | Where it runs | Needs | Notes |
|---|---|---|---|
| `mock` | Anywhere | Nothing | Animated title card with your prompt. For development and CI. |
| `replicate` | Replicate's cloud GPUs | `REPLICATE_API_TOKEN` | Default model `lightricks/ltx-video`. Billed per run by Replicate. |
| `local` | Your GPU (Apple silicon or NVIDIA) | `pip install -e '.[local]'` | Runs [LTX-Video](https://huggingface.co/Lightricks/LTX-Video) via diffusers. Experimental on 16 GB Macs. |

> **Why can't `local` run in a container on a Mac?** Linux containers on macOS (both apple/container and Docker Desktop) run inside a lightweight VM that has no access to the Mac's GPU. Run Kinora natively on macOS if you want to use your Apple silicon GPU.

## Quick start (native, macOS / Linux)

```bash
git clone https://github.com/bharatpatel7/kinora.git
cd kinora
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
python -m kinora
```

Open http://127.0.0.1:8000 and generate with the **Mock** provider.

### Use a cloud GPU (Replicate)

```bash
export REPLICATE_API_TOKEN=r8_...
python -m kinora
```

### Use your own GPU

```bash
pip install -e '.[local]'
python -m kinora
```

The first run downloads the model weights (several GB). On a 16 GB Apple silicon Mac, start small: about 512×288 and 2–3 seconds.

## Run in a container

With **apple/container** (Apple silicon, macOS 26+):

```bash
container build --tag kinora --file Containerfile .
container run --rm -p 8000:8000 -e REPLICATE_API_TOKEN kinora
```

With **Docker**:

```bash
docker build -t kinora -f Containerfile .
docker run --rm -p 8000:8000 -e REPLICATE_API_TOKEN kinora
```

## Configuration

All settings are environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `KINORA_HOST` | `127.0.0.1` | Bind address (`0.0.0.0` in the container) |
| `KINORA_PORT` | `8000` | Port |
| `KINORA_OUTPUT_DIR` | `outputs` | Where generated `.mp4` files are written |
| `KINORA_PROVIDERS` | `mock,replicate,local` | Providers to enable |
| `KINORA_DEFAULT_PROVIDER` | `mock` | Provider selected by default |
| `KINORA_REPLICATE_MODEL` | `lightricks/ltx-video` | Replicate model (`owner/name`) |
| `KINORA_LOCAL_MODEL` | `Lightricks/LTX-Video` | Hugging Face model id for `local` |
| `REPLICATE_API_TOKEN` | – | Enables the `replicate` provider |

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/providers` | Providers and whether they're available |
| `POST` | `/api/jobs` | Start a generation: `{"prompt": "...", "provider": "mock", "seconds": 4}` |
| `GET` | `/api/jobs` | All jobs, newest first |
| `GET` | `/api/jobs/{id}` | One job: status, progress, and `video_url` when done |

Interactive docs at `/docs`.

## Adding a provider

Subclass `kinora.providers.base.Provider`, implement `generate(req, out_path, progress)` to write an `.mp4`, and register it in `kinora/providers/__init__.py`. Contributions for new backends (Wan, HunyuanVideo, MLX-native models, fal, Azure) are welcome.

## Roadmap

- [x] Prompt → clip with pluggable providers
- [ ] Persist job history across restarts
- [ ] Image → video
- [ ] Simple timeline: trim, join clips, add audio
- [ ] DaVinci Resolve plugin that talks to the Kinora API

## Development

```bash
pip install -e '.[dev]'
pytest
ruff check .
```

## License

[Apache-2.0](LICENSE). Generated videos are subject to the license of the model that produced them; check each model's terms before using output commercially.
