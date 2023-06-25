from setuptools import setup, find_packages

setup(
    name='research-agents',
    version='0.1.0',
    author='Research agents hackathon team',
    author_email='sam@qxcv.net',
    description="Automates research entirely; literally AGI",
    url='https://github.com/qxcv/research-agents/',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'BeautifulSoup4==4.12.2',
        'requests==2.31.0',
        'langchain[openai,anthropic]==0.0.214',
        'jupyter==1.0.0',
        'anthropic==0.2.10',
        'openai==0.27.8',
        'fuzzywuzzy[speedup]==0.18.0',
        'html2text==2020.1.16',
        'Markdown==3.4.3',
        'bleach==6.0.0',
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
    ],
    python_requires='>=3.10',
)
