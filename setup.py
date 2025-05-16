
from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# This setup.py is kept for backwards compatibility
# Modern Python packaging relies primarily on pyproject.toml
setup(
    name="blackforest",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.31.0",
        "pydantic>=2.0.0",
    ],
    author="Black Forest Labs",
    author_email="support@blackforestlabs.ai",
    description="Python client for Black Forest Labs API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/black-forest-labs/blackforest",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    package_data={'': ['py.typed']},  # For type hints support
    project_urls={
        'Homepage': 'https://github.com/black-forest-labs/blackforest',
        'Source': 'https://github.com/black-forest-labs/blackforest',
        'Documentation': 'https://blackforestlabs.ai/docs',
    },
)
