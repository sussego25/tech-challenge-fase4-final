#!/usr/bin/env python
"""
Build script para empacotar a Lambda com suas dependencias.
Usado pelo Terraform (null_resource local-exec).
"""
import shutil
import subprocess
import sys
import os

# Caminhos relativos ao diretorio deste script (infra/lambda/)
script_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(script_dir, "..", ".."))

handler_src = os.path.join(root, "services", "lambda-functions", "order-handler")
shared_src  = os.path.join(root, "shared")
build_dir   = os.path.join(script_dir, "terraform", "build")

print(f"[build] handler : {handler_src}")
print(f"[build] shared  : {shared_src}")
print(f"[build] build   : {build_dir}")

# Limpa e recria o diretorio de build
shutil.rmtree(build_dir, ignore_errors=True)
os.makedirs(build_dir, exist_ok=True)

# Copia o handler
shutil.copytree(handler_src, build_dir, dirs_exist_ok=True)

# Copia contracts e libs do shared
shutil.copytree(os.path.join(shared_src, "contracts"), os.path.join(build_dir, "contracts"), dirs_exist_ok=True)
shutil.copytree(os.path.join(shared_src, "libs"),      os.path.join(build_dir, "libs"),      dirs_exist_ok=True)

# boto3/botocore NAO sao instalados aqui: o runtime Lambda Python 3.11
# ja os fornece. Inclui-los aumentaria o zip e poderia causar conflito de versao.

# Instala pydantic com wheels Linux/x86_64 para Python 3.11.
# pydantic_core contem extensao Rust compilada — precisa de wheel
# especifico para manylinux2014_x86_64 + cp311, independente do SO do runner.
subprocess.check_call([
    sys.executable, "-m", "pip", "install",
    "pydantic>=2.0",
    "-t", build_dir,
    "--platform", "manylinux2014_x86_64",
    "--python-version", "311",
    "--implementation", "cp",
    "--only-binary=:all:",
    "--upgrade",
    "--quiet"
])

print("[build] OK")
