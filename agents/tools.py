import os

def list_directory(path: str) -> str:
    entries = os.listdir(path)
    formatted = []
    for entry in entries:
        entry_path = os.path.join(path, entry)
        prefix = "[DIR]" if os.path.isdir(entry_path) else "[FILE]"
        formatted.append(f"{prefix} {entry}")
    return "\n".join(formatted)


def get_folder_structure(path: str) -> dict:
    def walk_dir(current_path):
        structure = {"name": os.path.basename(current_path), "path": current_path}
        if os.path.isdir(current_path):
            structure["type"] = "directory"
            children = []
            try:
                entries = sorted(os.listdir(current_path))
                for entry in entries:
                    entry_path = os.path.join(current_path, entry)
                    try:
                        children.append(walk_dir(entry_path))
                    except Exception as e:
                        children.append({"name": entry, "path": entry_path, "type": "error", "error": str(e)})
            except Exception as e:
                structure["error"] = str(e)
                structure["children"] = []
            else:
                structure["children"] = children
        else:
            structure["type"] = "file"
        return structure
    return walk_dir(path)

