import json
from typing import Any



def get_prompt_arguments(
    prompt: Any,
) -> list[Any]:
    """
    Return the argument metadata advertised for one MCP prompt.

    A prompt may accept:

    - no arguments
    - optional arguments
    - required arguments
    - a mixture of required and optional arguments

    MCP SDK prompt metadata normally exposes these through:

        prompt.arguments

    A missing or null arguments field means that the prompt accepts no
    arguments.
    """

    arguments = getattr(
        prompt,
        "arguments",
        None,
    )

    if arguments is None:
        return []

    try:
        return list(arguments)

    except TypeError as exc:
        raise AssertionError(
            "The prompt's argument metadata is not iterable."
        ) from exc



def parse_json_resource_text(resource_text: str) -> Any:
    """
    Parse resource text as JSON.

    Parameters
    ----------
    resource_text:
        The textual resource body returned by the MCP server.

    Returns
    -------
    Any
        The corresponding Python object, commonly a dictionary or list.

    Raises
    ------
    ValueError
        Raised with a clearer message when the returned text is not valid
        JSON.

    Why parse the resource?
    -----------------------
    Printing raw JSON proves that text was returned.

    Parsing it proves something stronger:

        the resource is valid JSON that a Python application can use.

    That distinction matters because the resource advertises the MIME type
    application/json.
    """

    try:
        return json.loads(resource_text)

    except json.JSONDecodeError as error:
        raise ValueError(
            "The resource advertised JSON content, but the returned "
            "text was not valid JSON."
        ) from error


