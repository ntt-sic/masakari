#!/usr/bin/env python
import os
from setuptools import setup

# Since masakari-controller does not own its own repo
# it can not derives the version of a package from the git tags.
# Therfore, we use PBR_VERSION=1.2.3
# to sikp all version calculation logics in pbr.

os.environ["PBR_VERSION"] = "1.2.3"

setup(
    setup_requires=['pbr'],
    pbr=True,
)
