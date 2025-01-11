"""Clean up recovery files, keeping latest for each source playlist."""

import os
import json
from collections import defaultdict


def cleanup_recovery_files(directory="data/recovery"):
    """Clean up recovery files, keeping latest for each source playlist."""
    if not os.path.exists(directory):
        print("Recovery directory not found:", directory)
        return

    # Group files by source playlist ID
    playlist_files = defaultdict(list)

    # Find all recovery files
    for filename in os.listdir(directory):
        if filename.startswith("recovery_") and filename.endswith(".json"):
            try:
                # Read the file to get source playlist ID
                with open(os.path.join(directory, filename), "r") as f:
                    data = json.load(f)
                    source_id = data["source_playlist_id"]
                    playlist_files[source_id].append(filename)
            except (json.JSONDecodeError, KeyError, IOError):
                print(f"Skipping invalid file: {filename}")
                continue

    # For each playlist, keep only the latest file
    files_to_delete = []
    for source_id, filenames in playlist_files.items():
        # Sort files by timestamp (which is part of the filename)
        sorted_files = sorted(filenames, key=lambda x: x.split("_")[-1].split(".")[0])
        # Keep the latest, mark others for deletion
        files_to_delete.extend(sorted_files[:-1])

    # Delete old files
    deleted_count = 0
    for filename in files_to_delete:
        try:
            os.remove(os.path.join(directory, filename))
            deleted_count += 1
        except OSError as e:
            print(f"Failed to delete {filename}: {e}")

    print("\nCleanup complete:")
    print(f"- Found {len(playlist_files)} source playlists")
    print(f"- Deleted {deleted_count} old recovery files")
    print(f"- Kept {len(playlist_files)} latest files")


if __name__ == "__main__":
    cleanup_recovery_files()
