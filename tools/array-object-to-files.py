import logging
from typing import Any, Dict, Generator, List

from pydantic import BaseModel, Field

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)


class ToolParameters(BaseModel):
    objects: List[Dict[str, Any]] = Field(default_factory=list)


class ArrayObjectToFilesTool(Tool):
    """
    Pass-through: Accepts Array[Object] that is already Dify file-shaped and
    returns it as Array[File] with zero modification.
    """

    def _invoke(self, tool_parameters: Dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        if "objects" not in tool_parameters:
            yield self.create_text_message("No 'objects' provided. Please pass an Array[Object].")
            return

        params = ToolParameters(**tool_parameters)
        objs = params.objects or []

        if not objs:
            yield self.create_text_message("Empty 'objects' array.")
            return

        # Optional: sanity check (logs only)
        for i, o in enumerate(objs):
            if o.get("dify_model_identity") != "__dify__file__":
                logger.debug("Item %s lacks dify_model_identity='__dify__file__' (passing through anyway).", i)

        # Try the standard files message path first.
        try:
            yield self.create_files_message(objs)
            return
        except AttributeError:
            pass

        # Fallback: emit one file per message
        try:
            for o in objs:
                yield self.create_file_message(o)
            return
        except AttributeError:
            pass

        # Final fallback: JSON wrapper
        yield self.create_json_message({"files": objs})