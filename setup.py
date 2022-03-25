from setuptools import setup

setup(
    name='discord_karaoke',
    version='0.0.5',
    description='Discord karaoke bot',
    url='https://github.com/artemetr/discord-karaoke-bot',
    author='Артем Широких <@artemetr>',
    author_email='job@artemetr.ru',
    license='MIT',
    packages=['discord_karaoke', 'discord_karaoke.src', 'discord_karaoke.src.decorators'],
    install_requires=['discord.py>=1.7.3'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: MacOS X',
        'Environment :: Web Environment',
        'Environment :: Win32 (MS Windows)',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
    ],
)
