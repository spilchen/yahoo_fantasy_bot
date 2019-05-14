from setuptools import setup

setup(name='yahoo_baseball_assistant',
      version='0.0.1',
      description='Helpers to aid machine learning in Yahoo! fantasy baseball',
      url='http://github.com/spilchen/yahoo_baseball_assistant',
      author='Matt Spilchen',
      author_email='matt.spilchen@gmail.com',
      license='MIT',
      packages=['yahoo_baseball_assistant'],
      setup_requires=["pytest-runner"],
      tests_require=["pytest"],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.5',
      ],
      install_requires=['yahoo_fantasy_api', 'baseball_scraper'],
      python_requires='>=3',
      zip_safe=True)
