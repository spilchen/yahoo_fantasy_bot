from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='yahoo_fantasy_bot',
      version='1.0.0',
      description='A bot that can act as a manager in a Yahoo! fantasy league',
      long_description=readme(),
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
      install_requires=['yahoo_fantasy_api>=2.4.1', 'baseball_scraper>=0.4.9',
                        'docopt', 'yahoo_oauth', 'nhl_scraper>=0.0.3',
                        'baseball_id>=0.1.0', 'progressbar', 'jinja2'],
      python_requires='>=3',
      include_package_data=True,
      zip_safe=True,
      scripts=['scripts/ybot', 'scripts/ybot_setup'])
