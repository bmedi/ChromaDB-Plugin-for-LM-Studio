import pyaudio
import wave
import os
import tempfile
import threading
import pyperclip
from faster_whisper import WhisperModel
import torch
import gc
import yaml
from termcolor import cprint

ENABLE_PRINT = True

def my_cprint(*args, **kwargs):
    if ENABLE_PRINT:
        filename = "voice_recorder_module.py"
        modified_message = f"{filename}: {args[0]}"
        cprint(modified_message, *args[1:], **kwargs)

class VoiceRecorder:
    def __init__(self, format=pyaudio.paInt16, channels=1, rate=44100, chunk=1024):
        my_cprint("VoiceRecorder __init__ is running.", 'green')
        self.format, self.channels, self.rate, self.chunk = format, channels, rate, chunk
        self.is_recording, self.frames = False, []

    def transcribe_audio(self, audio_file):
        my_cprint("transcribe_audio is running.", 'green')
        segments, _ = self.model.transcribe(audio_file)
        pyperclip.copy("\n".join([segment.text for segment in segments]))

    def record_audio(self):
        my_cprint("record_audio is running.", 'green')
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=self.format, channels=self.channels, rate=self.rate, input=True, frames_per_buffer=self.chunk)
            [self.frames.append(stream.read(self.chunk)) for _ in iter(lambda: self.is_recording, False)]
            stream.stop_stream()
            stream.close()
        finally:
            p.terminate()

    def save_audio(self):
        my_cprint("save_audio is running.", 'green')
        self.is_recording = False
        temp_filename = tempfile.mktemp(suffix=".wav")
        with wave.open(temp_filename, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b"".join(self.frames))
        
        def transcribe_and_cleanup():
            my_cprint("transcribe_and_cleanup is running.", 'green')
            self.transcribe_audio(temp_filename)
            os.remove(temp_filename)
            self.frames.clear()
            self.ReleaseTranscriber()

        threading.Thread(target=transcribe_and_cleanup).start()

    def start_recording(self):
        my_cprint("start_recording is running.", 'green')
        if not self.is_recording:
            with open("config.yaml", 'r') as stream:
                config_data = yaml.safe_load(stream)
            
            transcriber_config = config_data['transcriber']
            model_string = f"ctranslate2-4you/whisper-{transcriber_config['model']}-ct2-{transcriber_config['quant']}"
            
            print(f"Loaded device: {transcriber_config['device']}")
            print(f"Loaded model: {transcriber_config['model']}")
            print(f"Loaded quant: {transcriber_config['quant']}")
            
            self.model = WhisperModel(
                model_string,
                device=transcriber_config['device'],
                compute_type=transcriber_config['quant'],
                cpu_threads=8
            )
            my_cprint("Whisper model loaded.", 'green')
            
            self.is_recording = True
            threading.Thread(target=self.record_audio).start()

    def stop_recording(self):
        my_cprint("stop_recording is running.", 'green')
        self.save_audio()
        
    def ReleaseTranscriber(self):
        my_cprint("ReleaseTranscriber is running.", 'green')
        del self.model
        torch.cuda.empty_cache()
        gc.collect()
        my_cprint("Whisper model destroyed.", 'red')