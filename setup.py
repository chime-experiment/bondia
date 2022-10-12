#!/usr/bin/python3.8
"""
bondia

CHIME Daily Validation
"""

import setuptools
import versioneer

# Load the PEP508 formatted requirements from the requirements.txt file. Needs
# pip version > 19.0
with open("requirements.txt", "r") as fh:
    requires = fh.readlines()

# Now for the regular setuptools-y stuff
setuptools.setup(
    name="bondia",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="The CHIME Collaboration",
    author_email="lgray@phas.ubc.ca",
    description="CHIME Daily Validation",
    packages=setuptools.find_packages(),
    scripts=["bondia/scripts/bondia-server"],
    license="GPL v3.0",
    url="http://github.com/chime-experiment/bondia",
    install_requires=requires,
    package_data={
        "bondia.templates": ["material.html", "mwc.html", "mdl.html", "mdl_tabs.html"],
        "bondia": ["login.html"],
        "bondia.scripts": [
            "val_preprocess.py",
            "val_preprocess.sbatch",
            "val_preprocess.sh",
        ],
    },
    include_package_data=True,
)
