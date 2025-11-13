"""Export data model schema to Arrows JSON format for visualization."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_schema():
    """Load the data model schema."""
    schema_path = Path(__file__).parent.parent / 'data' / 'schema' / 'data_model.json'
    with open(schema_path, 'r') as f:
        return json.load(f)

def create_arrows_json(schema):
    """Convert schema to Arrows JSON format."""
    arrows = {
        "nodes": [],
        "relationships": []
    }
    
    # Convert nodes to Arrows format
    node_positions = {}
    x_start = 100
    y_start = 100
    x_spacing = 300
    y_spacing = 200
    cols = 3
    
    for idx, node in enumerate(schema['nodes']):
        col = idx % cols
        row = idx // cols
        
        # Create property string
        props = []
        for prop in node['properties']:
            prop_name = prop['name']
            prop_type = prop.get('type', 'STRING')
            if prop_name == node['key_property']['name']:
                props.append(f"{prop_name}: {prop_type} (key)")
            else:
                props.append(f"{prop_name}: {prop_type}")
        
        arrows_node = {
            "id": f"n{idx}",
            "position": {
                "x": x_start + col * x_spacing,
                "y": y_start + row * y_spacing
            },
            "caption": node['label'],
            "labels": [node['label']],
            "properties": {
                node['key_property']['name']: f"{node['key_property']['name']} (key)"
            },
            "propertyList": props
        }
        
        arrows["nodes"].append(arrows_node)
        node_positions[node['label']] = f"n{idx}"
    
    # Convert relationships to Arrows format
    rel_idx = 0
    for rel in schema['relationships']:
        start_label = rel['start_node_label']
        end_label = rel['end_node_label']
        
        if start_label in node_positions and end_label in node_positions:
            arrows_rel = {
                "id": f"r{rel_idx}",
                "type": rel['type'],
                "startNodeId": node_positions[start_label],
                "endNodeId": node_positions[end_label],
                "properties": {},
                "propertyList": []
            }
            arrows["relationships"].append(arrows_rel)
            rel_idx += 1
    
    return arrows

if __name__ == '__main__':
    schema = load_schema()
    arrows_json = create_arrows_json(schema)
    
    output_path = Path(__file__).parent.parent / 'data' / 'schema' / 'data_model_arrows.json'
    with open(output_path, 'w') as f:
        json.dump(arrows_json, f, indent=2)
    
    print(f"✓ Arrows JSON exported to: {output_path}")
    print(f"\nTo visualize:")
    print(f"1. Go to https://arrows.app/")
    print(f"2. Click 'Open' and paste the contents of {output_path}")
    print(f"\nOr use the JSON directly:")
    print(json.dumps(arrows_json, indent=2))

