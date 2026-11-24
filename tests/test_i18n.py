from tracktube import i18n


def test_ambos_idiomas_tienen_las_mismas_claves():
    assert set(i18n.STRINGS["en"]) == set(i18n.STRINGS["es"])


def test_ingles_es_el_idioma_por_defecto():
    assert i18n.DEFAULT_LANGUAGE == "en"
    assert list(i18n.LANGUAGES) == ["en", "es"]


def test_tr_cambia_con_el_idioma():
    i18n.set_language("es")
    assert i18n.tr("slot.image") == "Carátula"
    assert i18n.tr("slot.audio_info", duration="1:00", format="MP3", bitrate="320 kbps",
                   bit_depth="—") == (
        "Duración: 1:00 · Formato: MP3\nBitrate: 320 kbps · Profundidad de bits: —")
    i18n.set_language("en")
    assert i18n.tr("slot.image") == "Album art"
    assert i18n.tr("slot.audio") == "Audio track"


def test_relacion_de_aspecto_en_espanol():
    i18n.set_language("es")
    assert i18n.tr("settings.ratio") == "Relación de aspecto"
    assert "relación de aspecto horizontal" in i18n.tr("warning.short_hint")
    assert "aspect ratio" not in i18n.tr("warning.short_hint").lower()
    i18n.set_language("en")
    assert i18n.tr("settings.ratio") == "Aspect ratio"  # en inglés no cambia


def test_idioma_desconocido_vuelve_al_defecto():
    i18n.set_language("fr")
    assert i18n.get_language() == "en"
