from setuptools import find_packages, setup

with open("readme.md") as f:
    long_description = f.read()

setup(
    name="srcompy",
    version="0.1",
    description="python libray for the speedrun.com API",
    package_dir={"": "srcompy"},
    packages=find_packages(where="srcompy"),
    long_description=long_description,
    author="Green-Bat",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.12.1",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=["requests >= 2.23.3"],
    python_requires=">=3.10",
)
