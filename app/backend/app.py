import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import soundfile as sf
import torchaudio
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import ffmpeg
import torch
import tempfile

app = Flask(__name__)
CORS(app, origins=["http://localhost:8000", "http://127.0.0.1:5500", "http://localhost:5500"])


UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Tăng giới hạn lên 500MB

logging.basicConfig(level=logging.DEBUG)

processor = WhisperProcessor.from_pretrained("hkab/whisper-base-vietnamese-finetuned")
model = WhisperForConditionalGeneration.from_pretrained("HoaDoan1710/checkpoint-whisper-9525")


device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
logging.info(f"Model loaded on {device}")

def extract_audio_from_video(video_path, audio_path):
    try:
        ffmpeg.input(video_path).output(audio_path, ac=1, ar=16000).run(overwrite_output=True)
        logging.info(f"Audio extracted from video: {audio_path}")
    except ffmpeg.Error as e:
        logging.error(f"Error extracting audio from video: {str(e)}")
        raise


def convert_mp3_to_wav(mp3_path, audio_path):
    try:
        ffmpeg.input(mp3_path).output(audio_path, ac=1, ar=16000).run(overwrite_output=True)
        logging.info(f"MP3 converted to WAV: {audio_path}")
    except ffmpeg.Error as e:
        logging.error(f"Error converting MP3 to WAV: {str(e)}")
        raise

def split_audio_into_chunks(waveform, sr, chunk_duration=10):
    chunk_samples = chunk_duration * sr  
    chunks = []

    # Chia thành các chunk
    total_samples = waveform.shape[0]
    for i in range(0, total_samples, chunk_samples):
        chunk = waveform[i:i+chunk_samples]
        chunks.append(chunk)
    
    logging.info(f"Audio split into {len(chunks)} chunks.")
    return chunks


def transcribe_chunk(waveform, sr):
    try:
        if sr != 16000:
            logging.info(f"Resampling audio from {sr} to 16000 Hz")
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
            waveform = resampler(waveform)

        input_features = processor(waveform.squeeze().numpy(), sampling_rate=16000, return_tensors="pt").input_features
        input_features = input_features.to(device)
        decoder_ids = processor.get_decoder_prompt_ids(language="vi", task="transcribe")
        predicted_ids = model.generate(input_features, forced_decoder_ids=decoder_ids)
        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]

        return transcription
    except Exception as e:
        logging.error(f"Error transcribing chunk: {str(e)}")
        raise


def transcribe_audio(audio_path):
    try:
        waveform, sr = sf.read(audio_path)
        chunks = split_audio_into_chunks(torch.tensor(waveform).float(), sr)

        transcription = ""
        for chunk in chunks:
    
            chunk_tensor = torch.tensor(chunk).float().unsqueeze(0)
            chunk_transcription = transcribe_chunk(chunk_tensor, sr)
            transcription += chunk_transcription + " "

        return transcription.strip()
    except Exception as e:
        logging.error(f"Transcription error: {str(e)}")
        raise

@app.route("/transcribe", methods=["POST"])
def transcribe():
    logging.info("Received request to /transcribe")
    if "file" not in request.files:
        logging.error("No file uploaded")
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    logging.info(f"Received file: {file.filename}, Size: {file.content_length} bytes")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as temp_file:
        file.save(temp_file.name)
        file_path = temp_file.name

    try:
        audio_path = file_path + ".wav"
        if file.filename.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
            extract_audio_from_video(file_path, audio_path)
        elif file.filename.lower().endswith(".mp3"):
            convert_mp3_to_wav(file_path, audio_path)
        else:
            audio_path = file_path

        transcription = transcribe_audio(audio_path)
        logging.info(f"Transcription generated: {transcription}")

        if not transcription:
            logging.error("No subtitles generated")
            return jsonify({"error": "No subtitles generated"}), 500

        for path in [file_path, audio_path]:
            if os.path.exists(path):
                os.remove(path)

        return jsonify({"text": transcription})

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        for path in [file_path, audio_path]:
            if os.path.exists(path):
                os.remove(path)
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/")
def serve_frontend():
    return send_from_directory("../frontend", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("../frontend", path)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
