import logging

# Logger de depuración de la app. La UI le conecta un handler para mostrar el log.
logger = logging.getLogger("tracktube")
logger.setLevel(logging.DEBUG)
logger.propagate = False
