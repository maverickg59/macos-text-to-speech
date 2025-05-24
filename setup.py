from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ottotone",
    version="0.0.1",
    author="Christopher White",
    author_email="chris@chriswhite.rocks",
    description="Ottotone is a lightweight STT App designed for productive dictation without interrupting workflow.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/maverickg59/ottotone",
    packages=find_packages(),
    install_requires=[
        "rumps>=0.4.0",
        "sounddevice>=0.4.6",
        "numpy>=1.24.0",
        "faster-whisper>=0.9.0",
        "pyperclip>=1.8.2",
        "appdirs>=1.4.4",
        "pynput>=1.7.6",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "ottotone=ottotone.app:main",
        ],
    },
)
