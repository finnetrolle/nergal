# stt_lib - Speech-to-Text Library

A reusable Python library for transcribing audio to text using various STT providers. Designed to be independent and easily integrated into any application.

## Features

- 🎙️ **Multiple providers**: Local Whisper, OpenAI (extensible)
- 🔧 **Flexible configuration**: Environment variables or programmatic
- 📦 **Zero external dependencies**: Only depends on STT provider libraries
- 🎯 **Clean API**: Simple async interface
- 🌍 **Multi-format support**: OGG, WAV, MP3, FLAC conversion

## Installation

The library is currently part of the Nergal monorepo. Install Nergal to get stt_lib:

```bash
pip install nergal
```

Or install from source:

```bash
uv sync
```

## Quick Start

```python
import asyncio
from stt_lib import create_stt_provider, convert_ogg_to_wav

async def main():
    # Create provider
    stt = create_stt_provider(provider_type="local", model="base")
    stt.preload_model()  # Optional: pre-load model

    # Convert audio (if needed)
    with open("voice.ogg", "rb") as f:
        ogg_bytes = f.read()

    wav_audio, duration = convert_ogg_to_wav(ogg_bytes, max_duration_seconds=60)

    # Transcribe
    text = await stt.transcribe(wav_audio, language="ru")
    print(text)

asyncio.run(main())
```

## Configuration

### Via Environment Variables

Set environment variables with `STT_` prefix:

```bash
export STT_PROVIDER=local
export STT_MODEL=base
export STT_DEVICE=cpu
export STT_COMPUTE_TYPE=int8
export STT_TIMEOUT=60.0
export STT_MAX_DURATION=60
```

### Programmatically

```python
from stt_lib import STTConfig, create_stt_provider

config = STTConfig(
    provider="local",
    model="base",
    device="cpu",
    timeout=60.0,
    max_duration=60,
)

stt = create_stt_provider(config)
```

## API Reference

### `create_stt_provider()`

Create an STT provider instance.

```python
from stt_lib import create_stt_provider

# Using individual parameters
stt = create_stt_provider(
    provider_type="local",
    model="base",
    device="cpu",
    compute_type="int8",
    timeout=60.0,
)

# Using config object
from stt_lib import STTConfig
config = STTConfig(provider="local", model="base")
stt = create_stt_provider(config)
```

**Parameters:**
- `config` (optional): `STTConfig` object with all settings
- `provider_type` (optional): "local" or "openai" (default: "local")
- `model` (optional): Model name (default: "base")
- `device` (optional): "cpu" or "cuda" (default: "cpu")
- `compute_type` (optional): "int8", "float16", "float32" (default: "int8")
- `api_key` (optional): API key for cloud providers
- `timeout` (optional): Timeout in seconds (default: 60.0)

**Returns:** `BaseSTTProvider` instance

### `BaseSTTProvider`

Abstract base class for all STT providers.

```python
from stt_lib import BaseSTTProvider

class MyProvider(BaseSTTProvider):
    @property
    def provider_name(self) -> str:
        return "my_provider"

    async def transcribe(self, audio_data, language="ru") -> str:
        # Implementation here
        return "transcribed text"
```

**Methods:**
- `provider_name` (property): Name of the provider
- `preload_model()`: Pre-load the model (optional)
- `transcribe(audio_data, language)`: Transcribe audio to text

### `convert_ogg_to_wav()`

Convert OGG audio to WAV format.

```python
from stt_lib import convert_ogg_to_wav

with open("voice.ogg", "rb") as f:
    ogg_bytes = f.read()

wav_audio, duration = convert_ogg_to_wav(
    ogg_bytes,
    max_duration_seconds=60,
    sample_rate=16000,
    channels=1,
)
```

**Parameters:**
- `ogg_data`: Raw OGG/Opus bytes
- `max_duration_seconds` (optional): Maximum allowed duration
- `sample_rate` (optional): Target sample rate (default: 16000)
- `channels` (optional): Number of channels (default: 1)

**Returns:** Tuple of `(BytesIO, float)` - WAV audio and duration in seconds

### `STTConfig`

Configuration class for STT providers.

```python
from stt_lib import STTConfig

config = STTConfig(
    provider="local",
    model="base",
    device="cpu",
    compute_type="int8",
    timeout=60.0,
    max_duration=60,
)
```

**Attributes:**
- `provider`: Provider type ("local", "openai")
- `model`: Model name
- `device`: Device ("cpu", "cuda")
- `compute_type`: Compute type ("int8", "float16", "float32")
- `api_key`: API key for cloud providers
- `timeout`: Timeout in seconds
- `max_duration`: Maximum audio duration in seconds

## Providers

### Local Whisper

Runs Whisper locally using faster-whisper (CTranslate2 optimized).

```python
from stt_lib import LocalWhisperProvider

stt = LocalWhisperProvider(
    model="base",  # tiny, base, small, medium, large-v3
    device="cpu",   # cpu or cuda
    compute_type="int8",  # int8 for CPU, float16 for GPU
    timeout=60.0,
)
```

**Supported models:**
- `tiny` - Fastest, lowest accuracy
- `base` - Good balance (default)
- `small` - Better accuracy
- `medium` - High accuracy
- `large-v3` - Best accuracy, slowest

## Exceptions

```python
from stt_lib import STTError, AudioTooLongError, STTConnectionError

try:
    text = await stt.transcribe(audio_data)
except AudioTooLongError as e:
    print(f"Audio too long: {e.duration_seconds}s > {e.max_seconds}s")
except STTConnectionError as e:
    print(f"Connection error: {e.message}")
except STTError as e:
    print(f"STT error: {e.message}")
```

## Usage Examples

### Basic transcription

```python
from stt_lib import create_stt_provider

stt = create_stt_provider()

with open("audio.wav", "rb") as f:
    text = await stt.transcribe(f, language="ru")
    print(text)
```

### With Telegram voice messages

```python
from stt_lib import create_stt_provider, convert_ogg_to_wav

stt = create_stt_provider()

# Download Telegram voice message
# voice_file = await voice.get_file()
# audio_bytes = await voice_file.download_as_bytearray()

# Convert OGG to WAV
wav_audio, duration = convert_ogg_to_wav(audio_bytes, max_duration_seconds=60)

# Transcribe
text = await stt.transcribe(wav_audio, language="ru")
```

### Pre-loading model

```python
from stt_lib import create_stt_provider

# Create and pre-load model at startup
stt = create_stt_provider()
stt.preload_model()  # Loads model now

# Later transcriptions will be faster
text = await stt.transcribe(audio_data)
```

## Project Structure

```
src/stt_lib/
├── __init__.py          # Public API
├── base.py             # BaseSTTProvider
├── factory.py          # create_stt_provider()
├── config.py           # STTConfig
├── audio.py           # Audio conversion utilities
├── exceptions.py       # STT exceptions
└── providers/
    ├── __init__.py
    └── local_whisper.py  # Local Whisper provider
```

## Dependencies

- `faster-whisper` >= 1.0.0 - For local Whisper
- `pydub` >= 0.25.0 - For audio conversion
- `pydantic-settings` >= 2.7.0 - For configuration

## Contributing

To add a new provider:

1. Create a provider class implementing `BaseSTTProvider`
2. Add it to `src/stt_lib/providers/`
3. Update `factory.py` to support the new provider

Example:

```python
# src/stt_lib/providers/my_provider.py
from stt_lib.base import BaseSTTProvider

class MySTTProvider(BaseSTTProvider):
    @property
    def provider_name(self) -> str:
        return "my_provider"

    async def transcribe(self, audio_data, language="ru") -> str:
        # Your implementation
        return "transcribed text"
```

## License

MIT License
