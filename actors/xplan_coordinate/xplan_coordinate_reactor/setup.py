from setuptools import setup, find_packages

setup(name='xplan_coordinate_reactor',
      version='0.1',
      description='Xplan Coordinate Helpers',
      url='http://gitlab.sd2e.org/xplan2/actors/xplan_coordinate/xplan_coordinate_reactor',
      author='Jack Ladwig',
      author_email='jladwig@sift.net',
      license='MIT',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      package_data={'xplan_coordinate_reactor': [
          'messagetypes/schema/*.jsonschema'
      ]},
      install_requires=[],
      tests_require=["pytest"],
      zip_safe=False)
