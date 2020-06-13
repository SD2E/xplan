from setuptools import setup, find_packages

setup(name='xplan_submit',
      version='0.1',
      description='Xplan Subroutine Coordination',
      url='http://gitlab.sd2e.org/xplan2/components/xplan_coordinate',
      author='Dan Bryce',
      author_email='dbryce@sift.net',
      license='MIT',
      packages=find_packages('src'),
      package_dir={'':'src'},
      install_requires=[],
      tests_require=["pytest"],
      zip_safe=False)