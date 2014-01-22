from setuptools import setup
import os.path


HERE = os.path.dirname(__file__)

with open(os.path.join(HERE, 'README.md')) as f:
    ldesc = f.read()

setup(
        name='heat-standalone-auth-secretkey',
        version='0.1',
        author='sjmc7',
        packages=['heat_secretkey'],
        license='MIT',
        description=('Authentication plugin for heat server (standalone) '
            'allowing api access/secret key to be sent by client'),
        long_description=ldesc,
        platforms='POSIX',
        url='https://github.com/sjmc7/heat-standalone-auth-secretkey',
        )
