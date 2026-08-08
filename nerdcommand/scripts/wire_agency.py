import os
import json
import yaml
from pathlib import Path

def convert_agency_to_manifests():
    base_dir = Path("/home/user/Super/nerdcommand")
    agency_dir = base_dir / "skills" / "agency"
    manifests_dir = base_dir / "agents" / "manifests"
    prompts_dir = base_dir / "agents" / "prompts"
    
    if not agency_dir.exists():
        print(f"Agency dir {agency_dir} not found.")
        return

    manifests_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)

    for md_file in agency_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        parts = content.split("---")
        if len(parts) < 3:
            continue
        
        try:
            frontmatter = yaml.safe_load(parts[1])
            body = "---".join(parts[2:]).strip()
        except Exception as e:
            print(f"Error parsing {md_file.name}: {e}")
            continue

        agent_id = md_file.stem.replace(" ", "-").lower()
        display_name = frontmatter.get("name", md_file.stem)
        purpose = frontmatter.get("description", "")
        
        # Manifest
        manifest = {
            "id": agent_id,
            "version": "1.0.0",
            "display_name": display_name,
            "purpose": purpose,
            "model_policy": "fast",
            "temperature": 0.3,
            "tools": ["web_search", "browser", "knowledge_search"],
            "permissions": ["read:web", "read:knowledge"],
            "input_schema": "Task",
            "output_schema": "TaskEnvelope",
            "requires_approval": False
        }
        
        # Write manifest
        manifest_path = manifests_dir / f"{agent_id}.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
            
        # Write prompt file
        prompt_path = prompts_dir / f"{agent_id}.txt"
        with open(prompt_path, "w") as f:
            f.write(body)
            
    print(f"Converted {len(list(agency_dir.glob('*.md')))} agency agents to manifests.")

if __name__ == "__main__":
    convert_agency_to_manifests()
