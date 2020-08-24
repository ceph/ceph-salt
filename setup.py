# -*- coding: utf-8 -*-
import os
import re
from setuptools import setup


def get_version_from_spec():
    this_dir = os.path.dirname(__file__)
    with open(os.path.join(this_dir, 'ceph-salt.spec'), 'r') as file:
        while True:
            line = file.readline()
            if not line:
                return 'unknown'
            ver_match = re.match(r'^Version:\s+(\d.*)', line)
            if ver_match:
                return ver_match[1]


setup(
    version=get_version_from_spec(),
    )
