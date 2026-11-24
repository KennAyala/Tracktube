> **Note:** this project was created with the assistance of artificial intelligence (Claude, by Anthropic). The code and documentation were generated and reviewed together with a person. The logo was generated with ChatGPT.

<p align="center">
  <img src="assets/logo.svg" alt="Tracktube logo" width="140">
</p>

# Tracktube

A Python desktop app that turns **an image + an audio file into an MP4 video**, ready to upload to YouTube. It is built to export quickly, using the encoding settings recommended by YouTube.

Reference: [Recommended upload encoding settings](https://support.google.com/youtube/answer/1722171).

## Features

- Two simple inputs: **Audio track** (wav, flac, mp3, ogg, m4a, aac) and **Album art** (jpg, jpeg, png, bmp), in that order, with buttons to add, replace and delete, plus drag and drop.
- **Audio information:** the Audio track section shows the duration, format, bitrate and bit depth of the file (bit depth only applies to lossless formats such as WAV, FLAC and M4A with ALAC; it shows `—` for MP3, OGG, M4A with AAC and raw AAC). An `.m4a` file is reported as **M4A (AAC)** or **M4A (ALAC)** depending on its codec. Below it, an **Album art in metadata** line says **Yes (width × height)** in green when the file has an image in its tags, or **No** in red when it does not.
- **Audio preview:** a Play / Stop button to listen to the audio before exporting.
- **Image from the audio metadata:** when you load an audio file, Tracktube looks for an image in its tags (cover art in MP3 and WAV via ID3, FLAC pictures, OGG Vorbis / Opus, and the cover of M4A files). If there is one, a **Use metadata image** button appears in the Album art section; clicking it uses that image as the album art. It never replaces your image on its own.
- Live **preview** of the frame that will fill the whole video.
- **Export preview as image:** a button under the preview saves the frame as a **JPG** (default) or **PNG**. It is rendered at the video's resolution and aspect ratio, with the current fit, background, darkness, shadow and margin. The suggested file name is the current **File name** (for example `my-video.mp4` suggests `my-video.jpg`).
- **PNG transparency is preserved:** transparent areas show the selected background (black when there is none), because MP4 has no alpha channel. The shadow follows the album art silhouette.
- **Aspect ratios:** 1:1, 4:3, 5:4 and 16:9, with **horizontal** (default) and **vertical** orientation buttons (3:4, 4:5 and 9:16).
- **Resolutions:** 480p, 720p, 1080p, 1440p and 2160p (4K). Resolution is taken from the short side.
- **FPS:** Minimum (1), 15, 24, 30 and 60 (default).
- **Image fit:** Fit, Crop or Stretch.
- With *Fit*: **background** (none, blurred album art or a custom image), album art **shadow** and a **margin** that moves the album art away from the edge. A **negative margin** (down to -50 %) does the opposite: it enlarges the album art past the edges so it looks closer.
- **Background blur:** a percentage for how strong the blurred background is (50 % by default, 0 % means no blur). It is always visible and is enabled only with the *Blurred album art* background.
- **Background darkness:** a percentage that darkens the background (0 % leaves it as is, 100 % makes it black). It is always visible and is enabled only when a background is used; it never darkens the album art or its shadow.
- **Reset buttons (✕):** the blur, darkness and margin inputs each have a ✕ button that returns the input to its default value (blur 50 %, darkness 0 %, margin 0 %). The ✕ is only shown while the value is different from the default, and it keeps its space so the layout does not move.
- **Export folder** and **file name** are separate fields (default `exports/` and `{uuid}.mp4`). A button changes the folder, and a refresh button next to the file name generates a new UUID. The UUID changes every time the app opens and after each export; a file name you typed yourself is kept.
- Warns you before exporting if a video already exists at the chosen path and will be replaced.
- Progress bar with its status next to the Export button (Ready, Exporting… 45%, Done) and a cancel button.
- **YouTube Short warning** when the video lasts 3:00 or less and the aspect ratio is not horizontal.
- **Theme:** System (default, follows the Windows light/dark setting), Light or Dark, from the header.
- Interface in **English** (default) and **Spanish**.
- Remembers your settings (theme, language, options, export folder and file name) between sessions, in `user/conf.ini`.
- **Log** panel for debugging, opened from the button at the top of the window and shown on the side.

## Requirements

- Python 3.11 or newer (developed and tested with 3.11).
- Windows (see [Known limitations](#known-limitations)).
- FFmpeg does not need to be installed: the binary ships with the `imageio-ffmpeg` package.

Dependencies (see [requirements.txt](requirements.txt)): PySide6 6.8 or newer (it provides the interface, the audio preview and the light/dark theme), imageio-ffmpeg, mutagen, Pillow and pytest.

## Installation

```powershell
git clone https://github.com/KennAyala/tracktube.git
cd tracktube
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Why a virtual environment?

You need Python installed, but its libraries (PySide6, Pillow, ...) are not part of it. `python -m venv .venv` uses your Python to create a `.venv` folder with an isolated copy of it, and the install step puts the dependencies there so they do not mix with other projects. `.\.venv\Scripts\python.exe` is simply the Python inside that folder, so it can run the app without activating anything.

If you prefer, you can skip the virtual environment and install the dependencies in your own Python (`python -m pip install -r requirements.txt`), then run `python main.py`. You can also activate the environment first (`.\.venv\Scripts\Activate.ps1`) and use `python main.py`.

## Usage

```powershell
.\.venv\Scripts\python.exe main.py
```

Basic flow:

1. Add an audio file in **Audio track**, then an image in **Album art**. If the audio has an image in its tags, you can click **Use metadata image** instead of adding one.
2. Check the audio information and, if you want, listen to it with **Play**.
3. Choose aspect ratio, orientation, resolution, FPS and image fit.
4. Check the **Preview** (you can save it as an image with **Export preview as image**).
5. Confirm the export folder and file name and click **Export**.

## Exported video specifications

| Item | Value |
|---|---|
| Container | MP4 with `faststart` |
| Video | H.264 (`libx264`), High profile, progressive, 2 B-frames, closed GOP, CABAC |
| GOP | Half the frame rate (minimum 1) |
| Color | `yuv420p`, BT.709 |
| Audio | AAC-LC stereo, 48 kHz, 384 kbps |

Video bitrate (SDR) by resolution and frame rate:

| Resolution | Up to 30 fps | 48–60 fps |
|---|---|---|
| 480p | 2.5 Mbps | 4 Mbps |
| 720p | 5 Mbps | 7.5 Mbps |
| 1080p | 8 Mbps | 12 Mbps |
| 1440p | 16 Mbps | 24 Mbps |
| 2160p | 40 Mbps | 60 Mbps |

Dimensions are computed from the short side and rounded to even numbers (a `yuv420p` requirement). Examples at 1080p: 16:9 → 1920×1080, 4:3 → 1440×1080, 5:4 → 1350×1080, 1:1 → 1080×1080, 9:16 → 1080×1920.

## Saved settings

Your settings (theme, language, options, export folder and file name) are saved in `user/conf.ini`, next to the app. The `user/` folder is created automatically and is listed in `.gitignore`, so it is never committed. You can delete `user/conf.ini` to go back to the default settings.

If the saved file name is a UUID, a new UUID is assigned every time the app starts so the previous export is not overwritten; a name typed by hand is kept.

Settings saved by earlier versions (in the Windows registry) are not imported, except the old export path, which is split into folder and file name.

## Project structure

```
tracktube/
├─ main.py                  # entry point
├─ requirements.txt
├─ pytest.ini
├─ assets/                  # logo (logo.svg for docs, logo.png for the window icon)
├─ exports/                 # default export folder
├─ user/                    # created at runtime: conf.ini with your settings (git-ignored)
├─ tracktube/
│  ├─ config.py             # allowed extensions and base paths
│  ├─ settings.py           # user settings in user/conf.ini
│  ├─ i18n.py               # translations (en / es)
│  ├─ log.py                # debug logger
│  ├─ core/
│  │  ├─ presets.py         # ratios, resolutions, fps, bitrates
│  │  ├─ fit_modes.py       # image fit: FFmpeg filter + Pillow preview
│  │  ├─ ffmpeg_cmd.py      # builds the FFmpeg command
│  │  ├─ exporter.py        # runs FFmpeg, progress and cancellation
│  │  ├─ export_path.py     # default file name and folder + name join
│  │  ├─ image_export.py    # save the preview as JPG / PNG
│  │  └─ media_info.py      # audio info, image found in the audio tags and image validation
│  └─ ui/
│     ├─ main_window.py
│     ├─ file_slot.py       # file input (add, replace, delete)
│     ├─ audio_slot.py      # audio input with the Play / Stop preview
│     ├─ image_slot.py      # album art input with the "Use metadata image" button
│     ├─ theme.py           # system / light / dark theme
│     ├─ preview_widget.py
│     ├─ export_worker.py   # export thread
│     └─ log_panel.py       # log panel
└─ tests/
```

## QA and testing

### Automated tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

What they cover:

| File | Covers |
|---|---|
| `test_presets.py` | Even and correct dimensions per ratio and resolution, orientation, bitrates, GOP and the YouTube Short rule |
| `test_fit_modes.py` | FFmpeg filters and Pillow preview for each fit, background, shadow and margin |
| `test_exporter.py` | Real exports: checks H.264 High, `yuv420p`, BT.709, size, fps, AAC 48 kHz stereo, progress, cancellation and logging |
| `test_export_path.py` | Default file name, relative path resolution, `.mp4` extension and folder + name join |
| `test_main_window.py` | UI (headless): folder and file name fields, UUID renewal on start and after exporting, refresh button, overwrite confirmation, audio info, Play / Stop preview, theme selector, progress status |
| `test_m4a_and_aac.py` | `.m4a` (AAC and ALAC) and `.aac` support: accepted extensions, drag and drop, info (format, bitrate, bit depth), the cover of M4A files, the UI, and real exports from each format |
| `test_media_info.py` | Audio info for WAV, FLAC, MP3 and OGG (duration, format, bitrate, bit depth), the image embedded in the tags of real MP3, WAV, FLAC and OGG files, and transparency detection for PNG images |
| `test_image_export.py` | Choosing JPG or PNG from the extension or the dialog filter, and saving both formats |
| `test_cover_and_preview_export.py` | UI (headless): the "Use metadata image" button and the export of the preview as an image (format, size, current settings, suggested file name, cancel and errors) |
| `test_darkness_and_negative_margin.py` | Background darkness and negative margin in the FFmpeg filter, the preview and real exports (it measures the pixels of the exported video) |
| `test_blur_and_reset_buttons.py` | The blur percentage in the FFmpeg filter, the preview and a real export, and the UI: blur input state, and the ✕ buttons (shown only when the value changes, reset to the default, restored on start, stable layout) |
| `test_options_and_cover_label.py` | UI (headless): the darkness input (always visible, enabled only with a background), negative margin, and the "Album art in metadata" label with its colors and languages |
| `test_settings.py` | Settings saved in `user/conf.ini`, folder creation and `user/` in `.gitignore` |
| `test_theme.py` | Which color scheme each theme requests |
| `test_i18n.py` | Same keys in English and Spanish, default language |
| `test_log.py` | Message forwarding to the log panel |

### Manual checklist

- [ ] Add, replace and delete the image and the audio (with the buttons and by dragging).
- [ ] Loading an audio file with an image in its tags shows **Use metadata image**; one without it does not. Clicking it loads that image as the album art.
- [ ] **Export preview as image** is disabled without an image, opens a save dialog with JPG first (default) and PNG, and the saved file has the video's resolution.
- [ ] The **Album art in metadata** line shows **Yes (width × height)** in green for an audio with an image in its tags and **No** in red for one without, in both the light and dark themes.
- [ ] **Background darkness** is always visible; it is disabled with no background (or with Crop / Stretch) and enabled with a blurred or custom background, and a higher value gives a darker background in the preview and in the video.
- [ ] **Background blur** is always visible, enabled only with the *Blurred album art* background, 50 % by default, and a higher value gives a blurrier background in the preview and in the video.
- [ ] The margin accepts negative values and the album art gets bigger and closer.
- [ ] The ✕ buttons of blur, darkness and margin only appear when the value is not the default, reset it when clicked, and the other inputs do not move when they appear.
- [ ] **Export preview as image** suggests the same name as the **File name** field, with `.jpg`.
- [ ] The preview updates when changing ratio, orientation, fit, background, darkness, shadow and margin.
- [ ] A PNG with transparency shows the background through its transparent areas (no white box) in the thumbnail, the preview and the exported video.
- [ ] Switching to vertical renames the ratio selector entries to 3:4, 4:5 and 9:16.
- [ ] The ✕ button next to the margin resets it to 0.
- [ ] The Short warning shows for audio of 3:00 or less in 1:1 or vertical, and hides in horizontal or above 3:00.
- [ ] Switching between English and Spanish translates the whole interface.
- [ ] The Audio track section shows duration, format, bitrate and bit depth (`—` for the bit depth of MP3, OGG, M4A with AAC and raw AAC).
- [ ] `.m4a` (AAC and ALAC) and `.aac` files can be added with the button and by dragging, they play with **Play**, and they export to a video.
- [ ] **Play** plays the audio and becomes **Stop**; **Stop**, replacing or deleting the audio stops it.
- [ ] The theme selector offers System (first and default), Light and Dark, and the window changes right away, including the orientation icons.
- [ ] With the System theme, the app follows the Windows light/dark setting.
- [ ] Closing and reopening the app keeps the settings, and they are written to `user/conf.ini`.
- [ ] The export folder and file name are separate, and the refresh button sits next to the file name.
- [ ] The UUID in the file name changes when the app opens, after each export and when clicking the refresh button.
- [ ] Exporting to a path that already exists shows a warning with Replace and Cancel; Cancel leaves the file untouched.
- [ ] Export, cancel halfway, and export again; the status next to the Export button shows the percentage.
- [ ] Open the resulting MP4 and confirm it matches the preview.
- [ ] The **Log** button at the top opens the panel on the right, and it shows the FFmpeg command and progress.

## Known limitations

- Only tested on Windows. The code has no known Windows-only dependencies, but other systems have not been tried.
- Bitrate values are taken from YouTube's recommendations and should be checked against the official documentation from time to time.
- The Light and Dark themes use Qt's color scheme support, so they need PySide6 6.8 or newer; the System theme follows the Windows setting.
- The audio preview uses the system audio output, so it needs a working audio device.
- Images embedded in audio tags are detected in MP3, WAV, FLAC, OGG and M4A files (a raw `.aac` stream has no tags). The image is saved to a temporary folder that is deleted when you close the app.
- With 60 fps and high resolutions (for example 4K), encoding long audio files takes noticeably longer.
- There is no `.exe` packaging yet.

## License

To be defined.
