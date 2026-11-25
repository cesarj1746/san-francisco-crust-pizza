# -*- mode: python ; coding: utf-8 -*-
# Compilación:  python -m PyInstaller --noconfirm SanFranciscoCrustPizza.spec
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = [("app.py", "."), ("sfcp", "sfcp"), ("vistas", "vistas"), ("datos_iniciales", "datos_iniciales"),
         (".streamlit", ".streamlit"), ("recursos", "recursos")]
datas += collect_data_files("streamlit")
datas += collect_data_files("plotly")
for pkg in ["streamlit", "pandas", "numpy", "plotly", "openpyxl", "pyarrow", "altair", "packaging",
            "python-calamine"]:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

hidden = (collect_submodules("streamlit") + collect_submodules("sfcp") + collect_submodules("vistas")
          + collect_submodules("plotly.graph_objects") + collect_submodules("plotly.express")
          + collect_submodules("plotly.io") + collect_submodules("python_calamine")
          + ["openpyxl", "openpyxl.cell._writer", "tkinter", "tkinter.messagebox", "pyarrow.vendored.version"])

a = Analysis(["launcher.py"], pathex=["."], binaries=[], datas=datas, hiddenimports=hidden,
             hookspath=[], runtime_hooks=[], excludes=["matplotlib", "IPython", "pytest", "scipy", "PyQt5", "PySide6"],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SanFranciscoCrustPizza", debug=False,
          strip=False, upx=False, console=False, icon="recursos/icono.ico",
          version=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="SanFranciscoCrustPizza")
