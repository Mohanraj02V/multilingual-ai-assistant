import time
import io
import asyncio
from faster_whisper import WhisperModel
import subprocess
import os

PHRASES = {
    "ta": "எங்கள் நிறுவனம் பற்றி சொல்லுங்கள்",
    "hi": "हमारी कंपनी के बारे में बताइए",
    "te": "మా కంపెనీ వివరాలు చెప్పండి",
    "ml": "ഞങ്ങളുടെ കമ്പനിയെക്കുറിച്ച് പറയുക",
    "kn": "ನಮ್ಮ ಕಂಪನಿಯ ಬಗ್ಗೆ ಹೇಳಿ",
    "es": "Háblame de nuestra empresa",
    "en": "Tell me about our company",
}

def synthesize_audio(text, lang):
    import edge_tts
    output_file = f"temp_{lang}.wav"
    # edge-tts maps
    voice_map = {
        "ta": "ta-IN-PallaviNeural",
        "hi": "hi-IN-SwaraNeural",
        "te": "te-IN-ShrutiNeural",
        "ml": "ml-IN-SobhanaNeural",
        "kn": "kn-IN-SapnaNeural",
        "es": "es-ES-ElviraNeural",
        "en": "en-US-AriaNeural",
    }
    voice = voice_map.get(lang, "en-US-AriaNeural")
    asyncio.run(edge_tts.Communicate(text, voice).save(output_file))
    
    with open(output_file, "rb") as f:
        data = f.read()
    os.remove(output_file)
    return data

def main():
    try:
        import edge_tts
    except ImportError:
        subprocess.check_call(["pip", "install", "edge-tts"])
        import edge_tts
    
    print("Loading model (small, cpu, int8)...")
    model = WhisperModel("small", device="cpu", compute_type="int8", download_root="./data/whisper-model")
    
    # generate audios
    print("Synthesizing test audios...")
    audios = {}
    for lang, text in PHRASES.items():
        audios[lang] = synthesize_audio(text, lang)
        
    print(f"{'Lang':<5} | {'Beam':<5} | {'Time (s)':<10} | {'Transcript'}")
    print("-" * 80)
    
    for beam in [1, 2, 5]:
        for lang, text in PHRASES.items():
            audio_bytes = audios[lang]
            
            # warmup once per beam
            if lang == "ta":
                _ = list(model.transcribe(io.BytesIO(audio_bytes), beam_size=beam, vad_filter=True)[0])
                
            t0 = time.time()
            segments, info = model.transcribe(io.BytesIO(audio_bytes), beam_size=beam, vad_filter=True)
            res = "".join([s.text for s in segments]).strip()
            dur = time.time() - t0
            print(f"{lang:<5} | {beam:<5} | {dur:<10.3f} | {res}")

if __name__ == "__main__":
    main()
