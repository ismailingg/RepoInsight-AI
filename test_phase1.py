from backend.core.cloner import ingest_repo

# Test on a small public repo
files = ingest_repo("https://github.com/pallets/flask")

print(f"\n✓ Found {len(files)} files")
print("\nFirst 5 files:")
for f in files[:5]:
    print(f"  {f['relative_path']} ({f['language']})")