import os
import json
import uuid
from typing import List, Dict, Any, Optional

PROJECTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects.json")

def _load_projects_data() -> List[Dict[str, Any]]:
    if not os.path.exists(PROJECTS_FILE):
        default_projects = [
            {
                "id": "proj_1",
                "name": "Project 1",
                "doc_ids": ["bb79e675-d9a7-490e-bb2d-bad755905102"] if os.path.exists(os.path.join(os.path.dirname(__file__), "temp_uploads", "machine-learning-and-deep-learning-notes.pdf")) else [],
                "created_at": "2026-09-24T12:00:00Z"
            },
            {
                "id": "proj_2",
                "name": "Project 2",
                "doc_ids": [],
                "created_at": "2026-09-24T12:01:00Z"
            },
            {
                "id": "proj_3",
                "name": "Project 3",
                "doc_ids": [],
                "created_at": "2026-09-24T12:02:00Z"
            }
        ]
        _save_projects_data(default_projects)
        return default_projects

    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading projects file: {e}")
        return []

def _save_projects_data(projects: List[Dict[str, Any]]) -> None:
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)

def list_projects() -> List[Dict[str, Any]]:
    """Return all projects."""
    return _load_projects_data()

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Get project by ID."""
    projects = _load_projects_data()
    for p in projects:
        if p["id"] == project_id:
            return p
    return None

def create_project(name: str) -> Dict[str, Any]:
    """Create a new project workspace."""
    projects = _load_projects_data()
    new_proj = {
        "id": f"proj_{uuid.uuid4().hex[:8]}",
        "name": name.strip() or f"Project {len(projects) + 1}",
        "doc_ids": [],
        "created_at": "2026-09-24T14:00:00Z"
    }
    projects.append(new_proj)
    _save_projects_data(projects)
    return new_proj

def add_doc_to_project(project_id: str, note_id: str) -> Dict[str, Any]:
    """Attach an uploaded document to a project."""
    projects = _load_projects_data()
    for p in projects:
        if p["id"] == project_id:
            if note_id not in p["doc_ids"]:
                p["doc_ids"].append(note_id)
            _save_projects_data(projects)
            return p
    # If project not found, add to first project
    if projects:
        if note_id not in projects[0]["doc_ids"]:
            projects[0]["doc_ids"].append(note_id)
        _save_projects_data(projects)
        return projects[0]
    return {}

def remove_doc_from_project(project_id: str, note_id: str) -> bool:
    """
    Soft-remove document from the project view.
    CRITICAL: Does NOT delete the document or chunks from Supabase,
    so knowledge is permanently preserved for all users.
    """
    projects = _load_projects_data()
    modified = False
    for p in projects:
        if p["id"] == project_id:
            if note_id in p["doc_ids"]:
                p["doc_ids"].remove(note_id)
                modified = True
    if modified:
        _save_projects_data(projects)
    return modified

def delete_project(project_id: str) -> bool:
    """
    Deletes a project workspace.
    NOTE: All documents and vector embeddings in Supabase permanently remain intact!
    """
    projects = _load_projects_data()
    initial_count = len(projects)
    projects = [p for p in projects if p["id"] != project_id]
    if len(projects) < initial_count:
        _save_projects_data(projects)
        return True
    return False
