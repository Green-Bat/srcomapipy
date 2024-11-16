from setuptools import find_packages, setup

with open("readme.md") as f:
    long_description = f.read()

setup(
    name="srcomapipy",
    version="0.3.0",
    description="python libray for the speedrun.com API",
    packages=find_packages(),
    long_description_content_type="text/markdown",
    long_description=long_description,
    author="Green-Bat",
    url="https://github.com/Green-Bat/srcompy",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=["requests >= 2.23.3"],
    python_requires=">=3.10",
)
