"""
Setup script for FontEase
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="FontEase",
    version="1.0.0",
    author="Ahmed Hawass",
    author_email="example@example.com",
    description="Change your windows font with easy steps",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/FontEase",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Environment :: Win32 (MS Windows)",
        "Topic :: Desktop Environment :: Window Managers",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    package_data={
        "": ["assets/*.ico"],
    },
    entry_points={
        "console_scripts": [
            "FontEase=src.main:main",
        ],
    },
)