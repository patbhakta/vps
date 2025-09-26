This Pipecat configuration provides a complete conversational AI setup with the following features:
Core Components:

Pipecat: Main conversational AI service
Redis: Session management and caching
PostgreSQL: Optional conversation storage
Tailscale: Secure networking

Key Features Configured:

Multi-provider AI: OpenAI, Anthropic, Google, Azure support
Text-to-Speech: OpenAI TTS, ElevenLabs, Azure TTS options
Speech-to-Text: OpenAI Whisper, Deepgram, Azure STT options
WebRTC: Real-time audio/video communication
Voice Activity Detection: Smart conversation flow
Session Management: Redis-backed sessions with timeout

Important Setup Steps:

Create required directories:

bashmkdir -p ./tailscale-pipecat/state
mkdir -p ./config

Update critical values in .env:

OPENAI_API_KEY - Your OpenAI API key
REDIS_PASSWORD - Secure Redis password
POSTGRES_PASSWORD - Secure PostgreSQL password
Configure your preferred TTS/STT providers


Optional configuration files in ./config/:

Bot personality configs
Custom voice settings
Conversation templates



Key Configuration Options:

AI Models: Defaults to GPT-4o, easily switchable
Voice: Default OpenAI "alloy" voice, customizable
Audio: 16kHz mono audio with noise suppression
Sessions: 30-minute timeout, max 10 concurrent
Security: CORS enabled, optional API key auth

Access Points:

Main API: http://pipecat-on-advin:8080
WebSocket: ws://pipecat-on-advin:8080/ws
Metrics: http://pipecat-on-advin:9090 (if enabled)

Performance Notes:

Configured for moderate load (4 worker threads)
Audio optimized for real-time conversation
Redis caching for fast session retrieval
Optional PostgreSQL for conversation history

Make sure to set your API keys and passwords before deploying!