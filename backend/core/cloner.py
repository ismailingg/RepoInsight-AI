import git
import tempfile
import os
from backend.config import TEMP_REPOS_PATH, MAX_FILES_PER_REPO
from backend.utils.blocklist import BLOCKLIST_DIRS, BLOCKLIST_EXTS, CODE_EXTENSIONS

def clone_repo(github_url: str, token: str = None) -> str:
    """Clone repo into temp dir, return path."""
    tmp_dir = tempfile.mkdtemp(dir=TEMP_REPOS_PATH)
    
    if token:
        url = github_url.replace("https://", f"https://{token}@")
    else:
        url = github_url
    
    git.Repo.clone_from(url, tmp_dir)
    return tmp_dir

def walk_repo(repo_path: str) -> list[dict]:
    """Walk repo and return filtered source file list."""
    results = []
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in BLOCKLIST_DIRS]
        
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in CODE_EXTENSIONS or ext in BLOCKLIST_EXTS:
                continue
            
            full_path = os.path.join(root, fname)
            
            if os.path.islink(full_path):
                print(f"[WARN] Skipping symlink: {full_path}")
                continue
            
            results.append({
                "path": full_path,
                "relative_path": os.path.relpath(full_path, repo_path),
                "language": ext.lstrip("."),
                "last_modified": os.path.getmtime(full_path)
            })
            
            if len(results) >= MAX_FILES_PER_REPO:
                print(f"[WARN] File cap of {MAX_FILES_PER_REPO} reached.")
                return results
    
    return results

def ingest_repo(github_url: str, token: str = None) -> list[dict]:
    """Main Phase 1 entry point."""
    repo_path = clone_repo(github_url, token)
    files = walk_repo(repo_path)
    print(f"✓ Found {len(files)} source files.")
    return files