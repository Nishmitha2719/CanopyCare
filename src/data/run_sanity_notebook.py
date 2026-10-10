"""Execute the sanity notebook with this exact Python environment."""
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager


def main() -> None:
    root=Path(__file__).resolve().parents[2]
    path=root/"notebooks/01_collection_sanity.ipynb"
    nb=nbformat.read(path,as_version=4)
    manager=KernelManager(kernel_name="python3")
    manager.kernel_spec.argv=[sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"]
    NotebookClient(nb,km=manager,timeout=600,resources={"metadata":{"path":str(root)}}).execute()
    nbformat.write(nb,path)
    print("Executed",path)

if __name__=="__main__":main()
