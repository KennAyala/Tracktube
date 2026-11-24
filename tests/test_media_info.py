import wave

import pytest
from PIL import Image

from tracktube.core import media_info
from tracktube.core.media_info import get_audio_info, has_transparency


def test_detecta_canal_alfa():
    assert has_transparency(Image.new("RGBA", (4, 4), (255, 255, 255, 0)))
    assert has_transparency(Image.new("LA", (4, 4)))


def test_imagen_opaca_no_tiene_transparencia():
    assert not has_transparency(Image.new("RGB", (4, 4)))
    assert not has_transparency(Image.new("L", (4, 4)))


def test_detecta_transparencia_indexada_de_png(tmp_path):
    path = tmp_path / "indexed.png"
    image = Image.new("P", (4, 4), 0)
    image.putpalette([255, 255, 255] * 256)
    image.save(path, transparency=0)
    with Image.open(path) as saved:
        assert has_transparency(saved)


def make_wav(path, bits, seconds=2, rate=44100, channels=2):
    sample_width = bits // 8
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(rate)
        wav.writeframes(b"\x00" * sample_width * channels * rate * seconds)


@pytest.mark.parametrize("bits", [16, 24])
def test_info_de_un_wav(tmp_path, bits):
    path = tmp_path / "a.wav"
    make_wav(path, bits)
    info = get_audio_info(path)
    assert info.duration == pytest.approx(2, abs=0.05)
    assert info.format == "WAV"
    assert info.bit_depth == bits
    # bitrate = frecuencia x canales x bits
    assert info.bitrate == 44100 * 2 * bits


def test_info_de_un_flac(tmp_path):
    import subprocess

    from tracktube.core.exporter import get_ffmpeg_exe

    wav = tmp_path / "a.wav"
    flac = tmp_path / "a.flac"
    make_wav(wav, 16)
    subprocess.run([get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(wav), str(flac)],
                   check=True)
    info = get_audio_info(flac)
    assert info.format == "FLAC"
    assert info.bit_depth == 16
    assert info.duration == pytest.approx(2, abs=0.05)


@pytest.mark.parametrize("extension, codec, expected_format", [
    ("mp3", "libmp3lame", "MP3"),
    ("ogg", "libvorbis", "OGG Vorbis"),
])
def test_info_de_formatos_con_perdida_no_tiene_bit_depth(
        tmp_path, extension, codec, expected_format):
    import subprocess

    from tracktube.core.exporter import get_ffmpeg_exe

    wav = tmp_path / "a.wav"
    out = tmp_path / f"a.{extension}"
    make_wav(wav, 16)
    result = subprocess.run(
        [get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(wav), "-c:a", codec,
         "-b:a", "128k", str(out)], capture_output=True)
    if result.returncode != 0:
        pytest.skip(f"este FFmpeg no incluye {codec}")
    info = get_audio_info(out)
    assert info.format == expected_format
    assert info.bit_depth is None
    assert info.bitrate and 64_000 < info.bitrate < 200_000


def test_duracion_con_la_funcion_anterior(tmp_path):
    path = tmp_path / "a.wav"
    make_wav(path, 16)
    assert media_info.get_audio_duration(path) == pytest.approx(2, abs=0.05)


def test_archivo_que_no_es_audio(tmp_path):
    path = tmp_path / "no-es-audio.wav"
    path.write_bytes(b"esto no es un audio")
    with pytest.raises(ValueError):
        get_audio_info(path)
