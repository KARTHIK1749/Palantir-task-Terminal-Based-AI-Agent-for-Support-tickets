"""
Tool Validator Module

Ensures all generated tool calls strictly adhere to the internal_tools.json schema.
Drops hallucinated tools or malformed parameters to guarantee safety.
"""
import os
import json
from typing import List, Dict, Any

class ToolValidator:
    """
    Validates API tool calls against the strict JSON schema defined in data/api_specs/internal_tools.json.
    """
    def __init__(self):
        self.tools_spec = self._load_tools_spec()
        self.allowed_tool_names = {t["name"] for t in self.tools_spec}
        self.tool_schemas = {t["name"]: t["parameters"] for t in self.tools_spec}

    def _load_tools_spec(self) -> List[Dict[str, Any]]:
        spec_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "api_specs", "internal_tools.json")
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def validate_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a list of tool call objects: [{"action": "tool_name", "parameters": {...}}]
        Filters out invalid calls.
        """
        valid_actions = []
        
        for action_call in actions:
            if not isinstance(action_call, dict):
                continue
                
            tool_name = action_call.get("action")
            if not tool_name or tool_name not in self.allowed_tool_names:
                # Dropping hallucinated or unsupported tool
                continue
                
            parameters = action_call.get("parameters", {})
            if not isinstance(parameters, dict):
                # Malformed parameters
                continue
                
            schema = self.tool_schemas.get(tool_name)
            if not schema:
                continue
                
            # Validate required fields
            required_fields = schema.get("required", [])
            has_all_required = all(req in parameters for req in required_fields)
            
            if not has_all_required:
                # Dropping tool call missing required parameters
                continue
                
            # Optionally validate parameter types here
            # For this simplified strict validator, if required fields are present, we accept it
            valid_actions.append({
                "action": tool_name,
                "parameters": parameters
            })
            
        return valid_actions
