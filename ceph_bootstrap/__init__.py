import logging
import logging.config
import sys

import click
import pkg_resources

from .config_shell import run_config_cmdline, run_config_shell
from .exceptions import CephBootstrapException

logger = logging.getLogger(__name__)


def _setup_logging(log_level, log_file):
    """
    Logging configuration
    """
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


def ceph_bootstrap_main():
    try:
        # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
        cli(prog_name='ceph-bootstrap')
    except CephBootstrapException as ex:
        logger.exception(ex)
        click.echo(str(ex))


@click.group()
@click.option('-l', '--log-level', default='info',
              type=click.Choice(["info", "error", "debug", "silent"]),
              help="set log level (default: info)")
@click.option('--log-file', default='/var/log/ceph-bootstrap.log',
              type=click.Path(dir_okay=False),
              help="the file path for the log to be stored")
@click.version_option(pkg_resources.get_distribution('ceph-bootstrap'), message="%(version)s")
def cli(log_level, log_file):
    _setup_logging(log_level, log_file)


@cli.command(name='config')
@click.option('-a', '--advanced', is_flag=True, default=False,
              help='Enable all features')
@click.argument('config_args', nargs=-1, type=click.UNPROCESSED, required=False)
def config_shell(advanced, config_args):
    """
    Starts ceph-bootstrap configuration shell
    """
    if config_args:
        run_config_cmdline(advanced, " ".join(config_args))
    else:
        run_config_shell(advanced)


if __name__ == '__main__':
    ceph_bootstrap_main()
