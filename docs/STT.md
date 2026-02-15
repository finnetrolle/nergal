# Speech-to-Text (STT) Module

This document describes the architecture, configuration, and usage of the Speech-to-Text module in Nergal.

## Overview

The STT module enables voice message processing in the Telegram bot. It transcribes audio messages (voice notes) sent by users into text, which is then processed by the dialog manager like regular text messages.

### Key Features

- **Local Whisper Processing**: Uses `faster-whisper` (CTranslate2) for efficient local transcription
- **No External API Required**: Runs entirely on your infrastructure
- **Multi-language Support**: Configurable language for transcription
- **Audio Duration Limits**: Configurable maximum audio length to prevent resource exhaustion
- **Automatic Format Conversion**: Handles Telegram's OGG/Opus format transparently
- **GPU Support**: Optional CUDA acceleration for faster processing
- **Metrics & Monitoring**: Built-in Prometheus metrics for observability

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Telegram Voice Message                      │
│                         (OGG/Opus format)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         handle_voice()                           │
│                     (src/nergal/main.py)                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      convert_ogg_to_wav()                        │
│                (src/nergal/stt/audio_utils.py)                   │
│                                                                  │
│  • Downloads OGG audio from Telegram                            │
│  • Converts to WAV (16kHz mono)                                 │
│  • Validates duration limits                                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LocalWhisperProvider                          │
│          (src/nergal/stt/providers/local_whisper.py)             │
│                                                                  │
│  • Lazy-loads Whisper model                                     │
│  • Runs transcription in thread pool                            │
│  • Applies VAD (Voice Activity Detection)                       │
│  • Returns transcribed text                                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Dialog Manager                             │
│              (src/nergal/dialog/manager.py)                      │
│                                                                  │
│  • Processes transcribed text as regular message                │
│  • Generates AI response                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Base Provider (`src/nergal/stt/base.py`)

Abstract base class that defines the STT provider interface:

```python
class BaseSTTProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the STT provider."""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_data: BinaryIO,
        language: str = "ru",
    ) -> str:
        """Transcribe audio data to text."""
        pass
```

### Local Whisper Provider (`src/nergal/stt/providers/local_whisper.py`)

The primary STT implementation using `faster-whisper`:

- **Lazy Loading**: Model is loaded on first use to save memory
- **Thread Pool Execution**: Runs blocking transcription in executor
- **VAD Filter**: Voice Activity Detection to skip silence
- **Timeout Protection**: Configurable timeout to prevent hanging

### Audio Utilities (`src/nergal/stt/audio_utils.py`)

Handles audio format conversion:

```python
def convert_ogg_to_wav(
    ogg_data: bytes | bytearray,
    max_duration_seconds: int | None = None,
) -> tuple[BytesIO, float]:
    """Convert OGG audio (Telegram format) to WAV."""
```

- Converts OGG/Opus (Telegram's format) to WAV
- Resamples to 16kHz mono (optimal for Whisper)
- Validates audio duration limits
- Returns `AudioTooLongError` if duration exceeds limit

### Factory (`src/nergal/stt/factory.py`)

Creates STT provider instances based on configuration:

```python
def create_stt_provider(
    provider_type: Literal["local", "openai"] = "local",
    model: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    api_key: str | None = None,
    timeout: float = 60.0,
) -> BaseSTTProvider:
```

## Configuration

### Environment Variables

All STT settings are prefixed with `STT_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `STT_ENABLED` | `true` | Enable/disable voice message processing |
| `STT_PROVIDER` | `local` | Provider type (`local` or `openai`) |
| `STT_MODEL` | `base` | Whisper model size |
| `STT_LANGUAGE` | `ru` | Language code for transcription |
| `STT_MAX_DURATION_SECONDS` | `60` | Maximum audio duration (seconds) |
| `STT_DEVICE` | `cpu` | Device (`cpu` or `cuda`) |
| `STT_COMPUTE_TYPE` | `int8` | Compute type (`int8`, `float16`, `float32`) |
| `STT_TIMEOUT` | `60.0` | Transcription timeout (seconds) |

### Model Sizes

| Model | RAM Usage | Speed | Quality | Recommended For |
|-------|-----------|-------|---------|-----------------|
| `tiny` | ~1 GB | Fastest | Lowest | Testing, limited resources |
| `base` | ~1 GB | Fast | Good | **CPU (recommended)** |
| `small` | ~2 GB | Medium | Better | CPU with more RAM |
| `medium` | ~5 GB | Slow | High | GPU |
| `large-v3` | ~10 GB | Slowest | Best | GPU, highest quality needed |

### Compute Types

| Type | Description | Recommended For |
|------|-------------|-----------------|
| `int8` | 8-bit quantization | **CPU (recommended)** |
| `float16` | 16-bit float | GPU with tensor cores |
| `float32` | 32-bit float | GPU, maximum precision |

### Example Configuration

```env
# Enable voice messages
STT_ENABLED=true

# Use local Whisper (no API key needed)
STT_PROVIDER=local

# Use base model - good balance for CPU
STT_MODEL=base

# Transcribe in Russian
STT_LANGUAGE=ru

# Limit to 1 minute voice messages
STT_MAX_DURATION_SECONDS=60

# Run on CPU with int8 quantization
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8

# Timeout after 60 seconds
STT_TIMEOUT=60.0
```

### GPU Configuration

For systems with NVIDIA GPU:

```env
STT_DEVICE=cuda
STT_COMPUTE_TYPE=float16
STT_MODEL=small    # or medium/large-v3 for better quality
```

## Usage in Code

### Basic Usage

```python
from nergal.stt import create_stt_provider, convert_ogg_to_wav

# Create provider
stt = create_stt_provider(
    provider_type="local",
    model="base",
    device="cpu",
    compute_type="int8",
)

# Convert audio
wav_audio, duration = convert_ogg_to_wav(
    ogg_bytes,
    max_duration_seconds=60,
)

# Transcribe
text = await stt.transcribe(wav_audio, language="ru")
```

### Integration with Telegram Bot

The STT module is integrated in [`main.py`](../src/nergal/main.py):

```python
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages."""
    # Get STT provider
    stt = app.stt_provider
    
    # Download voice message
    voice = update.message.voice
    new_file = await voice.get_file()
    audio_bytes = await new_file.download_as_bytearray()
    
    # Convert OGG to WAV
    wav_audio, duration = convert_ogg_to_wav(
        bytes(audio_bytes),
        max_duration_seconds=settings.stt.max_duration_seconds,
    )
    
    # Transcribe
    transcription = await stt.transcribe(
        wav_audio,
        language=settings.stt.language,
    )
    
    # Process through dialog manager
    response = await dialog_manager.process_message(
        user_id=user_id,
        message_text=transcription,
        user_info=user_info,
    )
```

## Monitoring

### Prometheus Metrics

The STT module exposes the following metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `bot_stt_requests_total` | Counter | Total STT requests by provider and status |
| `bot_stt_duration_seconds` | Histogram | Time spent on STT processing |
| `bot_stt_audio_duration_seconds` | Histogram | Duration of processed audio |

### Using Metrics

```python
from nergal.monitoring import track_stt_request

async def transcribe_with_metrics(audio, provider):
    async with track_stt_request(
        provider="local_whisper",
        audio_duration=30.0,
    ):
        return await stt.transcribe(audio)
```

### Health Checks

STT health is checked via the health endpoint:

```python
from nergal.monitoring.health import check_stt_health

health = await check_stt_health(stt_provider)
# Returns:
# - HEALTHY: STT disabled or provider ready
# - DEGRADED: Provider exists but error accessing
```

## Performance Considerations

### CPU vs GPU

| Aspect | CPU | GPU |
|--------|-----|-----|
| Setup | Simple | Requires CUDA |
| Latency | 5-30s per minute | 1-5s per minute |
| Cost | No extra hardware | GPU required |
| Model Size | tiny/base recommended | small/medium/large |

### Optimization Tips

1. **Use appropriate model size**: `base` is usually sufficient for CPU
2. **Enable VAD**: Voice Activity Detection skips silence (enabled by default)
3. **Set reasonable duration limits**: 60 seconds is a good default
4. **Use int8 quantization on CPU**: Significantly faster with minimal quality loss
5. **Configure timeout**: Prevent long-running transcriptions from blocking

### Resource Usage

| Model | CPU Usage | RAM | Transcription Time (30s audio) |
|-------|-----------|-----|-------------------------------|
| tiny | 100% | ~1 GB | ~3-5s |
| base | 100% | ~1 GB | ~5-10s |
| small | 100% | ~2 GB | ~10-20s |
| medium | 100% | ~5 GB | ~20-40s |

*Times are approximate for modern CPU with int8 quantization*

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `AudioTooLongError` | Audio exceeds `max_duration_seconds` | Increase limit or trim audio |
| `ValueError: Invalid OGG audio` | Corrupted or invalid audio | Check audio format |
| `RuntimeError: Transcription failed` | Whisper model error | Check logs, try different model |
| `asyncio.TimeoutError` | Transcription exceeded timeout | Increase `STT_TIMEOUT` |

### Error Handling Example

```python
from nergal.stt import AudioTooLongError

try:
    wav_audio, duration = convert_ogg_to_wav(
        audio_bytes,
        max_duration_seconds=60,
    )
    text = await stt.transcribe(wav_audio)
except AudioTooLongError as e:
    await message.reply_text(
        f"Voice message too long: {e.duration_seconds:.0f}s "
        f"(max: {e.max_seconds}s)"
    )
except ValueError as e:
    await message.reply_text("Could not process audio format")
except RuntimeError as e:
    await message.reply_text(f"Transcription failed: {e}")
except asyncio.TimeoutError:
    await message.reply_text("Transcription timed out")
```

## Dependencies

The STT module requires:

```toml
[dependencies]
faster-whisper = ">=1.0.0"  # CTranslate2-based Whisper
pydub = ">=0.25.0"          # Audio processing
```

System dependencies:
- **ffmpeg**: Required by pydub for audio conversion
  ```bash
  # Ubuntu/Debian
  sudo apt-get install ffmpeg
  
  # macOS
  brew install ffmpeg
  ```

## Extending STT

### Adding a New Provider

1. Create a new provider class implementing [`BaseSTTProvider`](../src/nergal/stt/base.py):

```python
# src/nergal/stt/providers/my_provider.py
from nergal.stt.base import BaseSTTProvider

class MySTTProvider(BaseSTTProvider):
    @property
    def provider_name(self) -> str:
        return "my_provider"
    
    async def transcribe(
        self,
        audio_data: BinaryIO,
        language: str = "ru",
    ) -> str:
        # Implementation here
        pass
```

2. Update the factory in [`factory.py`](../src/nergal/stt/factory.py):

```python
from nergal.stt.providers.my_provider import MySTTProvider

def create_stt_provider(...):
    if provider_type == "my_provider":
        return MySTTProvider(...)
```

3. Add configuration in [`config.py`](../src/nergal/config.py) if needed.

## Troubleshooting

### Model Download Issues

Whisper models are downloaded on first use. If download fails:

1. Check internet connection
2. Set `XDG_CACHE_HOME` or `HUGGINGFACE_HUB_CACHE` for custom cache location
3. Pre-download models: `python -c "from faster_whisper import WhisperModel; WhisperModel('base')"`

### Memory Issues

If you encounter OOM (Out of Memory) errors:

1. Use a smaller model (`tiny` or `base`)
2. Ensure no other processes are using GPU memory
3. Reduce `STT_MAX_DURATION_SECONDS` to process shorter audio

### Slow Transcription

If transcription is too slow:

1. Use `int8` compute type on CPU
2. Use a smaller model
3. Consider GPU acceleration
4. Reduce audio duration limit

### Audio Format Errors

If audio conversion fails:

1. Ensure ffmpeg is installed
2. Check the audio file is valid OGG/Opus
3. Try with a different voice message

## Related Documentation

- [Configuration Reference](../.env.example) - All environment variables
- [Monitoring Guide](./MONITORING.md) - Observability setup
- [Deployment Guide](./DEPLOYMENT.md) - Production deployment
