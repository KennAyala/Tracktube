import pytest

from tracktube.core import presets


@pytest.mark.parametrize("ratio", list(presets.ASPECT_RATIOS))
@pytest.mark.parametrize("short_side", presets.RESOLUTIONS)
def test_dimensiones_pares_y_lado_corto(ratio, short_side):
    width, height = presets.get_dimensions(ratio, short_side)
    assert width % 2 == 0 and height % 2 == 0
    assert min(width, height) == short_side


def test_dimensiones_conocidas():
    assert presets.get_dimensions("16:9", 1080) == (1920, 1080)
    assert presets.get_dimensions("16:9", 480) == (854, 480)
    assert presets.get_dimensions("16:9", 2160) == (3840, 2160)
    assert presets.get_dimensions("9:16", 1080) == (1080, 1920)
    assert presets.get_dimensions("4:3", 1080) == (1440, 1080)
    assert presets.get_dimensions("5:4", 1080) == (1350, 1080)
    assert presets.get_dimensions("1:1", 720) == (720, 720)
    assert presets.get_dimensions("4:5", 1080) == (1080, 1350)


def test_orientacion_invierte_el_ratio():
    assert presets.get_aspect_ratio("16:9", False) == "16:9"
    assert presets.get_aspect_ratio("16:9", True) == "9:16"
    assert presets.get_aspect_ratio("4:3", True) == "3:4"
    assert presets.get_aspect_ratio("5:4", True) == "4:5"
    assert presets.get_aspect_ratio("1:1", True) == "1:1"
    for base in presets.BASE_ASPECT_RATIOS:
        for vertical in (False, True):
            assert presets.get_aspect_ratio(base, vertical) in presets.ASPECT_RATIOS


def test_posible_short():
    # 3:00 o menos y no horizontal -> posible Short
    assert presets.may_be_short(180, "9:16")
    assert presets.may_be_short(59.4, "3:4")
    assert presets.may_be_short(120, "1:1")
    assert presets.may_be_short(180.4, "4:5")  # se muestra como 3:00
    # horizontal, más de 3:00 o sin audio -> no
    assert not presets.may_be_short(120, "16:9")
    assert not presets.may_be_short(120, "4:3")
    assert not presets.may_be_short(181, "9:16")
    assert not presets.may_be_short(300, "1:1")
    assert not presets.may_be_short(0, "9:16")


def test_bitrate_segun_fps():
    assert presets.get_video_bitrate_kbps(1080, 30) == 8000
    assert presets.get_video_bitrate_kbps(1080, 60) == 12000
    assert presets.get_video_bitrate_kbps(2160, 24) == 40000
    assert presets.get_video_bitrate_kbps(480, 1) == 2500


def test_gop():
    assert [presets.get_gop(f) for f in presets.FPS_OPTIONS] == [1, 7, 12, 15, 30]


def test_default_fps_es_60():
    assert presets.DEFAULT_FPS == 60
