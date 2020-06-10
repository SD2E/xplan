import subprocess

from setuptools import setup, find_packages
import sys
from setuptools.command.install import install
from setuptools.command.develop import develop
import os


def pip_install(url):
    subprocess.check_output([sys.executable, '-m', 'pip', 'install', url])

def override_run(cls):
    """
    Decorator to override the run method for a setup command to use the custom python
    linux version if the platform is linux
    """
    orig_run = cls.run

    def new_run(self):
        """
        Use the github link to a forked branch of pydoe that
        fixes python3 issues
        """

        orig_run(self)
        #pip_install('git+https://gitlab.sd2e.org/dbryce/xplan_models')

        ## Setup solvers in pysmt
        os.system("pysmt-install --z3 --confirm-agreement")
        os.system("export PYSMT_CYTON=0")
        PYSMT_CYTHON = 0



    cls.run = new_run
    return cls

@override_run
class CustomInstallCommand(install):
    pass

@override_run
class CustomDevelopCommand(develop):
    pass

cmdclass = {'develop': CustomDevelopCommand,
            'install': CustomInstallCommand}


setup(name='xplan_design',
      version='0.1',
      description='XPlan Experiment Design Component',
      url='http://gitlab.sd2e.org/xplan2/components/xplan_design',
      author='Dan Bryce',
      author_email='dbryce@sift.net',
      license='MIT',
      packages=find_packages('src'),
      package_dir={'':'src'},
      install_requires=[
                      "pytest-runner",
                      "pandas",
                      "pysmt"
      ],
      tests_require=["pytest"],
      cmdclass=cmdclass
      )

