"""Setup module for python-onyx."""
from pathlib import Path

from setuptools import find_packages, setup

PROJECT_DIR = Path(__file__).parent.resolve()
README_FILE = PROJECT_DIR / "README.md"
VERSION = "0.0.01"


setup(
    name="python-onyx",
    version=VERSION,
    url="https://github.com/jeffmikels/obsidian_onyx_python",
    download_url="https://github.com/jeffmikels/obsidian_onyx_python",
    author="Jeff Mikels",
    author_email="jeffmikels@gmail.com",
    description="Python wrapper for Obsidian Onyx Telnet API",
    long_description=README_FILE.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["test*.*", "test"]),
    python_requires=">=3.6",
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Home Automation",
    ],
)
