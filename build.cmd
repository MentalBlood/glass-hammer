rd /s /q dist
rd /s /q src\glass_hammer.egg-info
py -m build -n && ^
pip install --force-reinstall dist\glass_hammer-1.1-py3-none-any.whl