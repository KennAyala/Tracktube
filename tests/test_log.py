from tracktube.log import logger
from tracktube.ui.log_panel import QtLogHandler


def capture():
    handler = QtLogHandler()
    received = []
    handler.emitter.message.connect(received.append)
    logger.addHandler(handler)
    return handler, received


def test_handler_reenvia_los_mensajes_con_formato():
    handler, received = capture()
    try:
        logger.info("hola %s", "mundo")
    finally:
        logger.removeHandler(handler)
    assert len(received) == 1
    assert "[INFO] hola mundo" in received[0]
