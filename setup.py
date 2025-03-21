from setuptools import setup, find_packages

setup(
    name="blackforest",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
    ],
    author="Black Forest Labs",
    author_email="saksham@blackforestlabs.io",
    description="Python client for Black Forest Labs API",
    long_description=open("README.md").read(),
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
    entry_points={
        'console_scripts': [],
    },
    project_urls={
        'Source': 'https://github.com/black-forest-labs/blackforest',
    },
    provides=['blackforest'],
) 