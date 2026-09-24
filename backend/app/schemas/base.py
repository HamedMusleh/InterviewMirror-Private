from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    """
    Shared base model for schemas that are sent to Azure OpenAI
    Structured Outputs (`response_format={"type": "json_schema", ...}`).

    Azure OpenAI's Structured Outputs feature requires every nested
    object in the JSON schema to disallow additional properties, so
    every nested model used in such a schema should inherit from this
    base instead of `pydantic.BaseModel` directly. This does not add,
    remove, or rename any fields - it only sets `extra="forbid"`.
    """

    model_config = ConfigDict(extra="forbid")
