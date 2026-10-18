#!/usr/bin/env python3
from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-whatsapp",
    version="1.0.0",
    description="Send WhatsApp messages through the WhatsApp Mac app, as a CLI or MCP server",
    url="https://github.com/mhdibrahimcn/CLI-Anything",
    license="MIT",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    python_requires=">=3.10",
    install_requires=["click>=8.1,<9.0", "mcp>=1.2,<2"],
    extras_require={"dev": ["pytest>=7"]},
    entry_points={"console_scripts": ["cli-anything-whatsapp=cli_anything.whatsapp.whatsapp_cli:main"]},
    package_data={"cli_anything.whatsapp": ["skills/*.md"]},
    classifiers=["Operating System :: MacOS :: MacOS X", "License :: OSI Approved :: MIT License"],
)
