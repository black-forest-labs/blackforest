from setuptools import setup, find_packages

setup(
    name="bfl",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
    ],
    author="Black Forest Labs",
    author_email="saksham@blackforestlabs.io",  # Update this
    description="Python client for Black Forest Labs API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/black-forest-labs/bfl",  # Update this
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
) 