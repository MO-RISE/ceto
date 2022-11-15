from setuptools import find_packages, setup

# Package meta-data.
NAME = "ceto"
DESCRIPTION = "A Python package for analyzing vessel data."
URL = "https://github.com/rise-mo/ceto"
EMAIL = "luis.sanchez-heres@ri.se"
AUTHOR = "Maritime Operations - RISE"
REQUIRES_PYTHON = ">=3.8.0"
VERSION = "0.1.0"

# Trove classifiers (i.e. metadata) for package discovery.
# Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
TROVE_CLASSIFIERS = [
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "License :: OSI Approved :: Apache Software License",
]

# Import README.md to as 'long_description'
with open("README.md", encoding="utf-8") as f:
    long_description = "\n" + f.read()

# Import requirements.txt to populate 'install_requires'
with open("requirements.txt", encoding="utf-8") as f:
    requirements = f.readlines()

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    install_requires=[req for req in requirements if req[:2] != "# "],
    include_package_data=True,
    license="Apache License 2.0",
    classifiers=TROVE_CLASSIFIERS,
)
