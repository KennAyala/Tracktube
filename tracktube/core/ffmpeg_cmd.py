from tracktube.core import presets
from tracktube.core.fit_modes import DEFAULT_BLUR, build_filter_graph


def build_command(ffmpeg_exe, image, audio, output, aspect_ratio, short_side, fps, fit_mode,
                  background="ninguno", background_image=None, shadow=False, margin=0,
                  transparent=False, darkness=0, blur=DEFAULT_BLUR):
    """Arma el comando de FFmpeg con las características recomendadas por YouTube."""
    width, height = presets.get_dimensions(aspect_ratio, short_side)
    bitrate = presets.get_video_bitrate_kbps(short_side, fps)

    # Sin imagen de fondo, "personalizado" equivale a no tener fondo
    if background == "personalizado" and not background_image:
        background = "ninguno"
    use_background_image = fit_mode == "ajustar" and background == "personalizado"

    command = [
        ffmpeg_exe, "-hide_banner", "-loglevel", "info", "-y",
        # La imagen entra a 1 fps; el filtro `fps` la repite al final
        "-loop", "1", "-framerate", "1", "-i", str(image),
        "-i", str(audio),
    ]
    if use_background_image:
        command += ["-loop", "1", "-framerate", "1", "-i", str(background_image)]

    command += [
        "-filter_complex",
        build_filter_graph(fit_mode, width, height, fps, background, shadow, margin,
                           transparent, darkness, blur),
        "-map", "[v]", "-map", "1:a",
        # Video: H.264 High, progresivo, 2 B-frames, GOP cerrado, CABAC, BT.709
        "-c:v", "libx264", "-profile:v", "high", "-bf", "2",
        "-g", str(presets.get_gop(fps)), "-flags", "+cgop", "-coder", "1",
        "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-b:v", f"{bitrate}k", "-maxrate", f"{bitrate}k", "-bufsize", f"{bitrate * 2}k",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        # Audio: AAC-LC estéreo 48 kHz
        "-c:a", "aac", "-b:a", f"{presets.AUDIO_BITRATE_KBPS}k",
        "-ar", str(presets.AUDIO_SAMPLE_RATE), "-ac", "2",
        "-shortest", "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",
        str(output),
    ]
    return command
