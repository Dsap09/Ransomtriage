from setuptools import setup, find_packages

setup(
    name="ransomtriage",
    version="1.0.0",
    description="Automated Execution Chain Analyzer for Windows Forensics",
    author="First Responder & CSIRT",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "ransomtriage": ["templates/*.html", "templates/*"],
    },
    install_requires=[
        "pandas>=1.3.0",
        "plotly>=5.0.0",
        "jinja2>=3.0.0",
        "tqdm>=4.60.0",
        "python-registry>=1.3.1",
    ],
    entry_points={
        "console_scripts": [
            "ransomtriage = ransomtriage.cli:main",
        ],
    },
    python_requires=">=3.9",
)
