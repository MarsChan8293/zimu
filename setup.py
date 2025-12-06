from setuptools import setup

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='zimu',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='Download subtitles from samfunny.com for media files',
    long_description='Download subtitles from samfunny.com for media files',
    long_description_content_type='text/plain',
    url='https://github.com/yourusername/zimu',
    packages=['samfunny'],
    package_dir={'': 'src'},
    py_modules=['cli'],
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'zimu = cli:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
