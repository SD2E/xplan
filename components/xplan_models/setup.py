from setuptools import setup, find_packages

setup(name='xplan_models',
      version='0.1',
      description='XPlan model representations',
      url='https://gitlab.sd2e.org/dbryce/xplan_models',
      author='Dan Bryce',
      author_email='dbryce@sift.net',
      license='MIT',
      packages=find_packages('src'),
      package_dir={'':'src'},
      install_requires=["matplotlib",
                        "seaborn"],
      zip_safe=False)

