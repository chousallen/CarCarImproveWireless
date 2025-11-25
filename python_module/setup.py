"""Setup script for bt_bridge package"""

from setuptools import setup, find_packages

with open("IMPLEMENTATION_NOTES.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bt_bridge",
    version="0.1.0",
    author="CarCar Team",
    description="Python module for ESP32 BLE Bridge communication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "pyserial>=3.5",
        "bleak>=0.21.0",
    ],
)
