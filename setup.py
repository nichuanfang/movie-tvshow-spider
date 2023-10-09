from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    readme = f.read()

setup(
    name='movie tvshow spider',
    version='0.1.2',
    author='jaychouzzz',
    author_email='f18326186224@gmail.com',
    # 项目主页
    url='https://github.com/nichuanfang/movie-tvshow-spider',
    # 描述
    description='movie and tvshow spider for alidrive',
    long_description_content_type='text/markdown',
    long_description=readme,
    # 包含哪些文件夹
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'aligo==6.1.8',
        'loguru==0.7.0',
        'requests==2.27.1'
    ],
    python_requires='>=3.8',
    zip_safe=False,
)

    