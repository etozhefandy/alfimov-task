import os
from google.cloud import speech

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-key.json"

file_path = "test.ogg"  # имя твоего голосового файла

client = speech.SpeechClient()

with open(file_path, "rb") as audio_file:
    content = audio_file.read()

audio = speech.RecognitionAudio(content=content)

config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
    sample_rate_hertz=48000,
    language_code="ru-RU"
)

response = client.recognize(config=config, audio=audio)

for result in response.results:
    print("👉 Распознано:", result.alternatives[0].transcript)

