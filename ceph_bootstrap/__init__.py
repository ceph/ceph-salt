import logging
import logging.config
import signal
import sys
import time

import click
import pkg_resources

from .config_shell import run_config_cmdline, run_config_shell
from .exceptions import CephBootstrapException
from .terminal_utils import check_root_privileges, PrettyPrinter as PP
from .deploy import CephSaltExecutor


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
        PP.pl_red(str(ex))
        sys.exit(1)


@click.group()
@click.option('-l', '--log-level', default='info',
              type=click.Choice(["info", "error", "debug", "silent"]),
              help="set log level (default: info)")
@click.option('--log-file', default='/var/log/ceph-bootstrap.log',
              type=click.Path(dir_okay=False),
              help="the file path for the log to be stored")
@click.version_option(pkg_resources.get_distribution('ceph-bootstrap'), message="%(version)s")
@check_root_privileges
def cli(log_level, log_file):
    _setup_logging(log_level, log_file)


@cli.command(name='config')
@click.argument('config_args', nargs=-1, type=click.UNPROCESSED, required=False)
def config_shell(config_args):
    """
    Starts ceph-bootstrap configuration shell
    """
    if config_args:
        if not run_config_cmdline(" ".join(config_args)):
            sys.exit(1)
    else:
        if not run_config_shell():
            sys.exit(1)


@cli.command(name='deploy')
@click.option('-n', '--non-interactive', is_flag=True, default=False,
              help='Run deploy in non-interactive mode')
@click.argument('minion_id', required=False)
def deploy(non_interactive, minion_id):
    """
    Runs ceph-salt formula and shows real-time progress
    """
    executor = CephSaltExecutor(not non_interactive, minion_id)
    retcode = executor.run()
    sys.exit(retcode)


if __name__ == '__main__':
    ceph_bootstrap_main()
