import os
import wave
import json
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment  
from fpdf import FPDF
def generate_ebook(text, audio_file):
    # Create an instance of FPDF class
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    lines = text.split('\n')
    for line in lines:
        pdf.multi_cell(0, 10, line)
    pdf_file = os.path.basename(audio_file).replace(".mp3", ".pdf")
    pdf_path = os.path.join("static/output", pdf_file)
    pdf.output(pdf_path)
    return pdf_path

def generate_text_from_audio(file_path, model_path="vosk-model-small-en-us-0.15"):
    # Convert MP3 to WAV -  Audio file must be WAV format mono PCM
    audio = AudioSegment.from_file(file_path)
    wav_file = "temp.wav"
    audio.export(wav_file, format="wav", parameters=["-ac", "1"]) # Export as mono channel
    
    # Load the Vosk model
    if not os.path.exists(model_path):
        raise ValueError("Model not found. Please download the model and specify the correct path.")
    model = Model(model_path)

    # Open the WAV file
    with wave.open(wav_file, "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            raise ValueError("Audio file must be WAV format mono PCM.")

        # Initialize the recognizer
        rec = KaldiRecognizer(model, wf.getframerate())

        # Process audio and generate text
        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                results.append(result.get('text', ''))

        # Get the final result
        final_result = json.loads(rec.FinalResult())
        results.append(final_result.get('text', ''))

    # Combine the results
    transcription = ' '.join(results)

    # Clean up the temporary WAV file
    os.remove(wav_file)

    return transcription


if __name__ == "__main__":
    os.makedirs("static/output", exist_ok=True)
    file_path = "static/uploads/sample.mp3"
    text = generate_text_from_audio(file_path)
    print(text)
    if text:
        pdf_path = generate_ebook(text, file_path)
        print(f"PDF saved at: {pdf_path}")