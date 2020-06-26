import logging


class LoggingUtil:
    log_file = None

    @classmethod
    def setup_logging(cls, log_level, log_file):
        """
        Logging configuration
        """
        cls.log_file = log_file
        if log_level == "silent":
            return

        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
                },
            },
            'handlers': {
                'file': {
                    'level': log_level.upper(),
                    'filename': log_file,
                    'class': 'logging.FileHandler',
                    'formatter': 'standard'
                },
            },
            'loggers': {
                '': {
                    'handlers': ['file'],
                    'level': log_level.upper(),
                    'propagate': True,
                }
            }
        })
