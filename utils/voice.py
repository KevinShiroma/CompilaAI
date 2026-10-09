import os
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger("instabot")

def converter_para_wav(audio_input_path: str) -> str:
    """Converte qualquer formato de áudio (.oga, .ogg, .m4a, .mp3) para WAV PCM 16kHz mono para o Azure Speech SDK."""
    import av
    import wave

    wav_path = audio_input_path + ".wav"
    container = av.open(audio_input_path)
    stream = container.streams.audio[0]
    resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
    
    with wave.open(wav_path, 'wb') as wav_out:
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)
        wav_out.setframerate(16000)
        for frame in container.decode(stream):
            for resampled_frame in resampler.resample(frame):
                wav_out.writeframes(resampled_frame.to_ndarray().tobytes())
    return wav_path

def transcrever_audio(audio_file_path: str) -> Optional[str]:
    """Transcreve arquivo de áudio utilizando o Azure Cognitive Services Speech SDK."""
    load_dotenv(override=True)
    speech_key = os.getenv("AZURE_SPEECH_KEY", "").strip()
    speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus2").strip()

    if not speech_key:
        logger.warning("AZURE_SPEECH_KEY não configurada no .env. Pulando transcrição de áudio.")
        return None

    wav_path = None
    try:
        wav_path = converter_para_wav(audio_file_path)
        
        import azure.cognitiveservices.speech as speechsdk
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        speech_config.speech_recognition_language = "pt-BR"
        
        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        
        result = speech_recognizer.recognize_once_async().get()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            logger.info(f"[Azure Speech SDK] Transcrição bem-sucedida: '{result.text}'")
            return result.text
        else:
            logger.warning(f"Azure Speech SDK não reconheceu fala clara (Razão: {result.reason})")
            return None
    except Exception as e:
        logger.error(f"Erro ao transcrever áudio com Azure Speech: {e}")
        return None
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass
