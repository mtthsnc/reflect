import json
import os
import shutil
import subprocess


def graphify_catchup():
    home = os.path.expanduser("~")
    cfg_path = os.path.join(home, ".claude", "reflection", "config.json")
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return
    if not cfg.get("graph", {}).get("graphify_enabled", False):
        return
    if not shutil.which("graphify"):
        return
    memories = os.path.join(home, ".claude", "reflection", "store", "memories")
    graph_json = os.path.join(memories, "graphify-out", "graph.json")
    adapter = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graphify_adapter.py")
    try:
        subprocess.run(["graphify", memories, "--update"], timeout=600,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if os.path.exists(graph_json):
            subprocess.run(["python3", adapter, graph_json], timeout=120,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        return


if __name__ == "__main__":
    graphify_catchup()
