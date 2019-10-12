from setuptools import setup

setup(name='yahoo_fantasy_bot',
      version='0.0.1',
      description='A bot that can act as a manager in a Yahoo! fantasy league',
      url='http://github.com/spilchen/yahoo_fantasy_bot',
      author='Matt Spilchen',
      author_email='matt.spilchen@gmail.com',
      license='MIT',
      packages=['yahoo_fantasy_bot'],
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
