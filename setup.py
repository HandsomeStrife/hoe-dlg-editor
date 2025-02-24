from setuptools import setup, find_packages

setup(
    name="dlg_editor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'prompt_toolkit>=3.0.0',
        'rich>=10.0.0',
        'chardet>=4.0.0',
    ],
    entry_points={
        'console_scripts': [
            'dlg-editor=src.main:main',
        ],
    },
) 