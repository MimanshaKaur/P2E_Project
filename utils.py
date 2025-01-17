import os
import wave
import json
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment  
from fpdf import FPDF

class CustomPDF(FPDF):
    def header(self):
        # Add a logo
        logo_path = "static/p2e_logo.png"  # Replace with your logo path
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 10, 33)  # (x, y, width)

        # Add the app title
        self.ln(12)
        self.set_font("Arial", style="B", size=20)
        self.cell(0, 10, "Podcast to Ebook Converter", align="C", ln=True)
        self.ln(10)

    def footer(self):
        # Add the footer with page number
        self.set_y(-15)
        self.set_font("Arial", size=10)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_ebook(text, audio_file, author_name=None, is_preview=False):
    # Create an instance of the CustomPDF class
    pdf = CustomPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    def draw_black_margin():
        pdf.set_draw_color(0, 0, 0)  # Black color
        pdf.set_line_width(1)       # Line thickness
        pdf.rect(5, 5, 200, 287)    # Rectangle (x, y, width, height)

    # Add the starting page
    pdf.add_page()
    draw_black_margin()
    pdf.set_font("Arial", style="B", size=25)

    # Add file name (center-aligned)
    file_name = os.path.basename(audio_file).replace(".mp3", "").upper()
    pdf.cell(0, 50, f"File Name: {file_name}", ln=True, align="C")

    # Add author name (center-aligned)
    if author_name:
        pdf.cell(0, 10, f"Author: {author_name}", ln=True, align="C")

    # Add custom message
    pdf.ln(20)
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, "Transcription starts on the next page.", ln=True, align="C")

    # Add transcription page
    pdf.add_page()
    draw_black_margin()
    pdf.set_font("Arial", size=12)

    # Add transcription text
    lines = text.split('\n')
    for line in lines:
        pdf.multi_cell(0, 10, line)

    # Save the PDF
    folder = "static/previews" if is_preview else "static/output"
    os.makedirs(folder, exist_ok=True)
    pdf_file = os.path.basename(audio_file).replace(".mp3", ".pdf")
    pdf_path = os.path.join(folder, pdf_file)
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