# План внедрения голосовых сообщений

## Обзор

Документ описывает план добавления функциональности обработки голосовых сообщений в Telegram бота Nergal. Пользователи смогут надиктовывать голосовые сообщения, которые будут транскрибироваться в текст и обрабатываться существующей логикой диалога.

## Архитектура

```
[Voice Message] → [Telegram Bot] → [Download Audio] → [STT Provider] → [Text Transcription] → [Dialog Manager] → [Response]
```

## Необходимые компоненты

### 1. STT (Speech-to-Text) провайдер

Для транскрибации голосовых сообщений необходимо выбрать и интегрировать STT сервис. Рассматриваемые варианты:

| Провайдер | Плюсы | Минусы | Стоимость |
|-----------|-------|--------|-----------|
| **OpenAI Whisper API** | Высокое качество, поддержка множества языков включая русский | Требует API ключ OpenAI | $0.006/минута |
| **Google Cloud Speech-to-Text** | Отличное качество, хорошая поддержка русского | Сложная настройка, требует GCP аккаунт | $0.006-0.009/минута |
| **Groq Whisper** | Очень быстрый, совместим с OpenAI API | Меньше моделей | Бесплатно (с ограничениями) |
| **Local Whisper** | Бесплатно, приватность, не требует интернета | Требует ресурсов сервера | Бесплатно (GPU опционально) |
| **Faster-Whisper** | Быстрее обычного Whisper, меньше памяти | Те же требования | Бесплатно |

**Рекомендация:** OpenAI Whisper API как основной провайдер (простота интеграции), с поддержкой Local Whisper для экономии и приватности.

## Локальный Whisper

Да, Whisper можно развернуть на том же сервере где работает бот. Есть несколько вариантов:

### Вариант 1: Официальный OpenAI Whisper

```bash
pip install openai-whisper
```

```python
import whisper

model = whisper.load_model("base")  # tiny, base, small, medium, large
result = model.transcribe("audio.mp3", language="ru")
print(result["text"])
```

### Вариант 2: Faster-Whisper (рекомендуется)

Более быстрая и эффективная реализация на CTranslate2:
```bash
pip install faster-whisper
```

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.mp3", language="ru")
text = "".join([segment.text for segment in segments])
```

### Требования к железу

| Модель | VRAM (GPU) | RAM (CPU) | Скорость | Качество |
|--------|------------|-----------|----------|----------|
| tiny | ~1 GB | ~1 GB | Очень быстро | Базовое |
| base | ~1 GB | ~1 GB | Быстро | Хорошее |
| small | ~2 GB | ~2 GB | Средне | Хорошее |
| medium | ~5 GB | ~5 GB | Медленно | Отличное |
| large-v3 | ~10 GB | ~10 GB | Очень медленно | Лучшее |

**Рекомендация для CPU сервера:** Модель `base` или `small` с `int8` квантованием - хорошее качество русского языка при приемлемой скорости.

**Рекомендация для GPU сервера:** Модель `medium` - отличный баланс качества и скорости.

### Docker поддержка

Добавить в [`Dockerfile`](Dockerfile):
```dockerfile
# Для CPU версии
RUN pip install faster-whisper

# Для GPU версии (требует nvidia-docker)
# RUN pip install faster-whisper && ...
```

### Преимущества локального Whisper

1. **Бесплатно** - нет затрат на API
2. **Приватность** - аудио не покидает сервер
3. **Без интернета** - работает оффлайн
4. **Нет ограничений** на длину аудио

### Недостатки

1. **Ресурсы сервера** - требуется RAM/VRAM
2. **Задержка** - на CPU может быть 5-30 секунд на минуту аудио
3. **Сложность** - больше компонентов для поддержки

### 2. Форматы аудио

Telegram отправляет голосовые сообщения в формате OGG/OGA (Opus codec). Большинство STT сервисов требуют конвертации в:
- MP3
- WAV
- FLAC
- M4A

**Необходимая библиотека:** `pydub` + `ffmpeg` для конвертации аудио

## Этапы реализации

### Этап 1: Подготовка инфраструктуры

#### 1.1 Обновление зависимостей

Добавить в `pyproject.toml`:
```toml
dependencies = [
    # ... существующие зависимости
    "openai>=1.0.0",       # Для Whisper API (опционально)
    "faster-whisper>=1.0.0",  # Для локального Whisper (опционально)
    "pydub>=0.25.0",       # Для конвертации аудио
]
```

**Примечание:** Можно установить только один из провайдеров - `openai` для API или `faster-whisper` для локального использования.

Системные требования:
- `ffmpeg` должен быть установлен на сервере

#### 1.2 Добавление настроек STT

Создать класс настроек в [`src/nergal/config.py`](src/nergal/config.py):

```python
class STTSettings(BaseSettings):
    """Speech-to-Text provider settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="STT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    enabled: bool = Field(default=True, description="Enable voice message processing")
    provider: str = Field(default="local", description="STT provider (openai, local, groq)")
    api_key: str = Field(default="", description="API key for STT provider (not needed for local)")
    model: str = Field(default="base", description="STT model to use (whisper-1 for API, base/small/medium for local)")
    language: str = Field(default="ru", description="Language code for transcription")
    max_file_size_mb: int = Field(default=25, description="Maximum audio file size in MB")
    # Local Whisper settings
    device: str = Field(default="cpu", description="Device for local Whisper (cpu, cuda)")
    compute_type: str = Field(default="int8", description="Compute type for local Whisper (int8, float16, float32)")
```

### Этап 2: Создание модуля STT

#### 2.1 Структура файлов

```
src/nergal/stt/
├── __init__.py          # Экспорт
├── base.py              # Базовый класс провайдера
├── factory.py           # Фабрика создания провайдера
└── providers/
    ├── __init__.py
    ├── openai_whisper.py # OpenAI Whisper API реализация
    ├── local_whisper.py  # Local Whisper (faster-whisper)
    └── groq_whisper.py   # Groq Whisper реализация (опционально)
```

#### 2.2 Базовый класс провайдера

```python
# src/nergal/stt/base.py
from abc import ABC, abstractmethod
from typing import BinaryIO


class BaseSTTProvider(ABC):
    """Abstract base class for STT providers."""
    
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
        """Transcribe audio data to text.
        
        Args:
            audio_data: Audio file-like object
            language: Language code for transcription
            
        Returns:
            Transcribed text
        """
        pass
```

#### 2.3 OpenAI Whisper провайдер

```python
# src/nergal/stt/providers/openai_whisper.py
from openai import AsyncOpenAI
from typing import BinaryIO

from nergal.stt.base import BaseSTTProvider


class OpenAIWhisperProvider(BaseSTTProvider):
    """OpenAI Whisper API STT provider."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        base_url: str | None = None,
    ):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
    
    @property
    def provider_name(self) -> str:
        return "openai_whisper"
    
    async def transcribe(
        self,
        audio_data: BinaryIO,
        language: str = "ru",
    ) -> str:
        response = await self._client.audio.transcriptions.create(
            model=self._model,
            file=audio_data,
            language=language,
        )
        return response.text
```

#### 2.4 Local Whisper провайдер (faster-whisper)

```python
# src/nergal/stt/providers/local_whisper.py
import asyncio
from typing import BinaryIO

from faster_whisper import WhisperModel

from nergal.stt.base import BaseSTTProvider


class LocalWhisperProvider(BaseSTTProvider):
    """Local Whisper STT provider using faster-whisper."""
    
    def __init__(
        self,
        model: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self._model_name = model
        self._device = device
        self._compute_type = compute_type
        self._model: WhisperModel | None = None
    
    @property
    def provider_name(self) -> str:
        return "local_whisper"
    
    def _get_model(self) -> WhisperModel:
        """Lazy load model to save memory."""
        if self._model is None:
            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model
    
    async def transcribe(
        self,
        audio_data: BinaryIO,
        language: str = "ru",
    ) -> str:
        """Transcribe audio using local Whisper model."""
        loop = asyncio.get_event_loop()
        
        # Run in thread pool to avoid blocking
        def _transcribe() -> str:
            model = self._get_model()
            segments, info = model.transcribe(
                audio_data,
                language=language,
                beam_size=5,
            )
            return "".join(segment.text for segment in segments)
        
        return await loop.run_in_executor(None, _transcribe)
```

### Этап 3: Обработка голосовых сообщений в боте

#### 3.1 Добавление обработчика в main.py

```python
# Добавить новый обработчик для голосовых сообщений
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages."""
    if not (update.message and update.message.voice):
        return
    
    # 1. Получить информацию о голосовом сообщении
    voice = update.message.voice
    
    # 2. Скачать файл
    new_file = await voice.get_file()
    audio_bytes = await new_file.download_as_bytearray()
    
    # 3. Конвертировать формат (OGG -> MP3/WAV)
    audio_converted = convert_audio(audio_bytes)
    
    # 4. Транскрибировать
    stt_provider = get_stt_provider()  # Создать через фабрику
    transcription = await stt_provider.transcribe(audio_converted)
    
    # 5. Обработать как обычное текстовое сообщение
    # ... использовать существующую логику handle_message
```

#### 3.2 Регистрация обработчика

```python
# В функции main()
application.add_handler(MessageHandler(filters.VOICE, handle_voice))
```

#### 3.3 Утилита конвертации аудио

```python
# src/nergal/stt/audio_utils.py
from io import BytesIO
from pydub import AudioSegment


def convert_ogg_to_mp3(ogg_data: bytes) -> BytesIO:
    """Convert OGG audio data to MP3 format.
    
    Args:
        ogg_data: Raw OGG audio bytes
        
    Returns:
        BytesIO object containing MP3 audio
    """
    # Load OGG audio
    audio = AudioSegment.from_ogg(BytesIO(ogg_data))
    
    # Export to MP3
    output = BytesIO()
    audio.export(output, format="mp3")
    output.seek(0)
    
    return output
```

### Этап 4: Интеграция с DialogManager

Модифицировать [`handle_voice`](src/nergal/main.py) для использования существующего [`DialogManager`](src/nergal/dialog/manager.py):

```python
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... код загрузки и транскрибации ...
    
    # Отправить статус "печатает..."
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # Использовать существующий DialogManager
    app = BotApplication.get_instance()
    result = await app.dialog_manager.process_message(
        user_id=user_id,
        message=transcription,
        user_info=user_info,
    )
    
    await update.message.reply_text(result.response)
```

## Конфигурация

### Переменные окружения (.env)

#### Вариант 1: Локальный Whisper (рекомендуется для экономии)

```env
# STT Settings - Local Whisper
STT_ENABLED=true
STT_PROVIDER=local
STT_MODEL=base          # tiny, base, small, medium, large-v3
STT_LANGUAGE=ru
STT_MAX_FILE_SIZE_MB=25
STT_DEVICE=cpu          # cpu или cuda (если есть GPU)
STT_COMPUTE_TYPE=int8   # int8 для CPU, float16 для GPU
```

#### Вариант 2: OpenAI Whisper API

```env
# STT Settings - OpenAI API
STT_ENABLED=true
STT_PROVIDER=openai
STT_API_KEY=your-openai-api-key
STT_MODEL=whisper-1
STT_LANGUAGE=ru
STT_MAX_FILE_SIZE_MB=25
```

## Обработка ошибок

Необходимо обработать следующие сценарии:
1. **Файл слишком большой** - уведомить пользователя об ограничении
2. **Ошибка транскрибации** - предложить отправить текстом
3. **Пустая транскрипция** - запросить повторить сообщение
4. **STT сервис недоступен** - graceful degradation

```python
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # ... обработка ...
    except FileTooLargeError:
        await update.message.reply_text(
            "Голосовое сообщение слишком длинное. "
            f"Максимум {settings.stt.max_file_size_mb} МБ. "
            "Пожалуйста, запишите короче или напишите текстом."
        )
    except TranscriptionError as e:
        await update.message.reply_text(
            "Не удалось распознать голосовое сообщение. "
            "Пожалуйста, напишите текстом."
        )
```

## Оптимизации (опционально)

### Кэширование транскрипций
Для предотвращения повторной обработки одного и того же сообщения:
```python
# Использовать file_unique_id как ключ кэша
cache_key = f"voice:{update.message.voice.file_unique_id}"
```

### Асинхронная обработка
Для длинных сообщений можно отправить промежуточный ответ:
```python
await update.message.reply_text("Обрабатываю голосовое сообщение...")
# ... транскрибация ...
await update.message.reply_text(response)  # Или edit предыдущего
```

## Тестирование

### Unit тесты
- Тест конвертации аудио форматов
- Тест мокирования STT провайдера
- Тест обработки ошибок

### Integration тесты
- Полный цикл обработки голосового сообщения
- Тест с реальным API (опционально)

## Оценка трудозатрат

| Этап | Время |
|------|-------|
| Настройка конфигурации | 1 час |
| Создание STT модуля | 2-3 часа |
| Обработчик голосовых сообщений | 2 часа |
| Конвертация аудио | 1 час |
| Обработка ошибок | 1 час |
| Тестирование | 2 часа |
| **Итого** | **9-10 часов** |

## Приоритет реализации

1. **Высокий приоритет:**
   - Базовая структура STT модуля
   - OpenAI Whisper провайдер
   - Обработчик голосовых сообщений
   - Базовая обработка ошибок

2. **Средний приоритет:**
   - Альтернативные провайдеры (Groq)
   - Оптимизации (кэширование)

3. **Низкий приоритет:**
   - Local Whisper поддержка
   - Расширенная аналитика

## Следующие шаги

1. Выбрать STT провайдер (рекомендуется OpenAI Whisper)
2. Добавить необходимые зависимости
3. Создать модуль STT с базовой структурой
4. Реализовать OpenAI Whisper провайдер
5. Добавить обработчик голосовых сообщений в main.py
6. Протестировать функциональность
7. Добавить обработку ошибок и оптимизации
