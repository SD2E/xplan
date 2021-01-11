import subprocess

from setuptools import setup, find_packages
import sys
from setuptools.command.install import install
from setuptools.command.develop import develop
import os


def pip_install(url):
    subprocess.check_output([sys.executable, '-m', 'pip', 'install', url])

def _post_install():
    #pip_install('git+https://gitlab.sd2e.org/dbryce/xplan_models')
    pip_install("git+https://github.com/SD2E/synbiohub_adapter.git")
    ## Setup solvers in pysmt
    pip_install("pysmt")
    print("Installing z3...")
    os.system("pysmt-install --z3 --confirm-agreement")
    os.system("export PYSMT_CYTHON=0")
    #PYSMT_CYTHON = 0


setup(name='xplan_design',
      version='0.1',
      description='XPlan Experiment Design Component',
      url='http://gitlab.sd2e.org/xplan2/components/xplan_design',
      author='Dan Bryce',
      author_email='dbryce@sift.net',
      license='MIT',
      packages=find_packages('src'),
      package_dir={'':'src'},
      install_requires=["fsspec",
                        "pandas",
                        "pysbol",
                        "pysmt",
                        "transcriptic"
                        ],
      tests_require=["pytest"],
      zip_safe=False
      )

_post_install()