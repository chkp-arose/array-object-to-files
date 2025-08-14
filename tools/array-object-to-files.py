import json
import logging
from typing import Any, Dict, Generator, List, Union

from pydantic import BaseModel, Field, ValidationError
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)

class ToolParameters(BaseModel):
    # 'any' in the manifest means this can be list/dict/string at runtime
    objects: Union[List[Dict[str, Any]], Dict[str, Any], str]

class ArrayObjectToFilesTool(Tool):
    """
    Pass-through: Accepts Array[Object] already Dify-file-shaped and returns Array[File] unchanged.
    """

    def _invoke(self, tool_parameters: Dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        if "objects" not in tool_parameters:
            yield self.create_text_message("No 'objects' provided. Please pass an Array[Object].")
            return

        try:
            params = ToolParameters(**tool_parameters)
        except ValidationError as e:
            yield self.create_text_message(f"Invalid parameters: {e}")
            return

        objs = self._coerce_to_list_of_dicts(params.objects)

        if not objs:
            yield self.create_text_message("Empty 'objects' array after coercion.")
            return

        # Optional: log sanity check; no mutation
        for i, o in enumerate(objs):
            if o.get("dify_model_identity") != "__dify__file__":
                logger.debug("Item %s lacks dify_model_identity='__dify__file__' (passing through anyway).", i)

        # Preferred path
        try:
            yield self.create_files_message(objs)
            return
        except AttributeError:
            pass

        # Fallbacks
        try:
            for o in objs:
                yield self.create_file_message(o)
            return
        except AttributeError:
            pass

        yield self.create_json_message({"files": objs})

    def _coerce_to_list_of_dicts(self, val: Union[List[Dict[str, Any]], Dict[str, Any], str]) -> List[Dict[str, Any]]:
        # Already a list of objects
        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]
        # Sometimes users pass a single object
        if isinstance(val, dict):
            return [val]
        # If it’s a Jinja-rendered JSON string, parse it
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return [x for x in parsed if isinstance(x, dict)]
                if isinstance(parsed, dict):
                    return [parsed]
            except Exception:
                logger.debug("objects is a plain string, not JSON; cannot coerce.")
        return []