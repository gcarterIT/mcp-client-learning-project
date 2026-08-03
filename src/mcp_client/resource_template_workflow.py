"""
MCP resource-template workflow
==============================

This module owns the complete deterministic resource-template workflow
used by the learning client.

Responsibilities
----------------
- locate the advertised product resource template
- read and parse the inventory resource
- select deterministic product IDs
- expand the product URI template
- read the expanded product resources
- display resource metadata and returned content
- verify product-resource results

This module does not own:

- MCP connection lifecycle
- capability discovery
- tools
- static application configuration
- prompts
- application startup orchestration
"""

from typing import Any

from mcp import ClientSession

from mcp_client.formatters import (
    display_resource_read_result,
    display_resource_template_metadata,
    get_mime_type,
    get_resource_text,
    get_uri_template,
)

from mcp_client.validation import (
    parse_json_resource_text,
)


def find_resource_template(
    templates_result: Any,
    expected_uri_template: str,
) -> Any | None:
    """
    Find one advertised resource template by its exact URI pattern.

    Parameters
    ----------
    templates_result:
        The result returned by session.list_resource_templates().

    expected_uri_template:
        The URI pattern to locate, such as:

            inventory://products/{product_id}

    Returns
    -------
    Any | None
        The matching template metadata object, or None when no matching
        template was advertised.
    """

    templates = getattr(
        templates_result,
        "resourceTemplates",
        None,
    )

    # Some SDK models may expose the Python-friendly field name.
    if templates is None:
        templates = getattr(
            templates_result,
            "resource_templates",
            None,
        )

    if templates is None:
        templates = []

    for template in templates:
        actual_uri_template = get_uri_template(template)

        if actual_uri_template == expected_uri_template:
            return template

    return None


def expand_product_resource_template(
    uri_template: str,
    product_id: str,
) -> str:
    """
    Replace the {product_id} placeholder with a concrete product ID.

    Parameters
    ----------
    uri_template:
        The discovered resource URI pattern.

    product_id:
        The concrete product identifier to insert.

    Returns
    -------
    str
        A completed resource URI, such as:

            inventory://products/P100

    Raises
    ------
    ValueError
        When the required placeholder is missing, the product ID is invalid,
        or unresolved placeholders remain after expansion.
    """

    placeholder = "{product_id}"

    if placeholder not in uri_template:
        raise ValueError(
            "The resource template does not contain the required "
            f"placeholder: {placeholder}"
        )

    if not isinstance(product_id, str):
        raise ValueError(
            "The product ID must be a string."
        )

    product_id = product_id.strip()

    if not product_id:
        raise ValueError(
            "The product ID cannot be empty."
        )

    # Prevent a supplied product ID from modifying the URI structure.
    if "/" in product_id or "\\" in product_id:
        raise ValueError(
            "The product ID cannot contain slash characters."
        )

    concrete_uri = uri_template.replace(
        placeholder,
        product_id,
    )

    # A completed URI should not retain any template braces.
    if "{" in concrete_uri or "}" in concrete_uri:
        raise ValueError(
            "The expanded URI still contains an unresolved placeholder: "
            f"{concrete_uri}"
        )

    return concrete_uri

async def read_json_resource(
    session: ClientSession,
    resource_uri: str,
) -> tuple[Any, dict[str, Any] | list[Any]]:
    """
    Read one MCP resource and parse its JSON text.

    Verification performed
    ----------------------
    1. Resource content was returned.
    2. A content entry matches the requested URI.
    3. Its MIME type is application/json.
    4. Text content exists.
    5. The text contains valid JSON.

    Returns
    -------
    tuple[Any, dict[str, Any] | list[Any]]
        1. The complete ReadResourceResult
        2. The parsed JSON value
    """

    print(f"\nReading resource: {resource_uri}")

    read_result = await session.read_resource(
        resource_uri
    )

    print("Resource returned successfully.")

    # Keep the detailed Part 4A-style display.
    display_resource_read_result(read_result)

    contents = getattr(
        read_result,
        "contents",
        None,
    )

    if not contents:
        raise AssertionError(
            f"The server returned no content for {resource_uri}."
        )

    matching_content = None

    for content in contents:
        returned_uri = str(
            getattr(content, "uri", "")
        )

        if returned_uri == resource_uri:
            matching_content = content
            break

    if matching_content is None:
        raise AssertionError(
            "The response did not contain the requested resource URI: "
            f"{resource_uri}"
        )

    mime_type = get_mime_type(matching_content)

    if mime_type != "application/json":
        raise AssertionError(
            "Expected MIME type application/json for "
            f"{resource_uri}, but received {mime_type!r}."
        )

    resource_text = get_resource_text(
        matching_content
    )

    if resource_text is None:
        raise AssertionError(
            f"The resource {resource_uri} did not return text content."
        )

    parsed_value = parse_json_resource_text(
        resource_text
    )

    if not isinstance(
        parsed_value,
        (dict, list),
    ):
        raise AssertionError(
            "Expected the JSON resource to contain an object or list, "
            f"but received {type(parsed_value).__name__}."
        )

    return read_result, parsed_value


def extract_products_from_inventory(
    inventory_data: Any,
) -> list[dict[str, Any]]:
    """
    Extract product dictionaries from the inventory JSON resource.

    Supported shapes
    ----------------

    Shape A:

        [
            {"product_id": "P100"},
            {"product_id": "P101"}
        ]

    Shape B:

        {
            "products": [
                {"product_id": "P100"},
                {"product_id": "P101"}
            ]
        }

    Returns
    -------
    list[dict[str, Any]]
        The product records found in the inventory resource.
    """

    products: Any

    if isinstance(inventory_data, list):
        products = inventory_data

    elif isinstance(inventory_data, dict):
        products = inventory_data.get("products")

    else:
        raise AssertionError(
            "The inventory resource must contain either a JSON list "
            "or a JSON object with a 'products' list."
        )

    if not isinstance(products, list):
        raise AssertionError(
            "The inventory JSON does not contain a product list."
        )

    validated_products: list[dict[str, Any]] = []

    for index, product in enumerate(
        products,
        start=1,
    ):
        if not isinstance(product, dict):
            raise AssertionError(
                f"Inventory item {index} is not a JSON object."
            )

        validated_products.append(product)

    if not validated_products:
        raise AssertionError(
            "The inventory product list is empty."
        )

    return validated_products


def select_product_ids(
    products: list[dict[str, Any]],
    count: int = 2,
) -> list[str]:
    """
    Select distinct valid product IDs from inventory data.

    Part 4B uses the inventory resource as the source of truth rather than
    guessing whether IDs such as P101 exist.
    """

    product_ids: list[str] = []

    for product in products:
        product_id = product.get("product_id")

        if not isinstance(product_id, str):
            continue

        product_id = product_id.strip()

        if not product_id:
            continue

        if product_id not in product_ids:
            product_ids.append(product_id)

        if len(product_ids) == count:
            break

    if len(product_ids) < count:
        raise AssertionError(
            f"Part 4B requires at least {count} distinct product IDs, "
            f"but only found {len(product_ids)}."
        )

    return product_ids

    
async def test_product_resource_template(
    session: ClientSession,
    templates_result: Any,
) -> None:
    """
    Complete the Part 4B resource-template workflow.

    Workflow
    --------
    1. Find the advertised product resource template.
    2. Inspect its metadata.
    3. Read the static inventory list.
    4. Select two valid product IDs from that list.
    5. Expand the template for each ID.
    6. Read each concrete URI.
    7. Verify each returned product.
    8. Confirm the template produced two distinct resources.
    """

    expected_uri_template = (
        "inventory://products/{product_id}"
    )

    print("\n" + "=" * 70)
    print("RESOURCE TEMPLATE TEST")
    print("=" * 70)

    print(
        "Looking for resource template:",
        expected_uri_template,
    )

    template = find_resource_template(
        templates_result=templates_result,
        expected_uri_template=expected_uri_template,
    )

    if template is None:
        raise RuntimeError(
            "The server did not advertise the required resource template: "
            f"{expected_uri_template}"
        )

    print("Resource template found.")

    display_resource_template_metadata(
        template
    )

    discovered_uri_template = get_uri_template(
        template
    )

    if discovered_uri_template is None:
        raise AssertionError(
            "The discovered resource template has no URI pattern."
        )

    if "{product_id}" not in discovered_uri_template:
        raise AssertionError(
            "The discovered product resource template does not contain "
            "the {product_id} placeholder."
        )

    advertised_mime_type = get_mime_type(
        template
    )

    if advertised_mime_type not in (
        None,
        "application/json",
    ):
        raise AssertionError(
            "Expected the product template to advertise application/json, "
            f"but received {advertised_mime_type!r}."
        )

    # ---------------------------------------------------------
    # Obtain valid IDs from the server's own inventory data.
    #
    # This is safer than assuming that P101 or another particular
    # product ID exists.
    # ---------------------------------------------------------

    inventory_uri = "inventory://products"

    print("\nReading the inventory list to obtain valid product IDs.")

    _, inventory_data = await read_json_resource(
        session=session,
        resource_uri=inventory_uri,
    )

    products = extract_products_from_inventory(
        inventory_data
    )

    selected_product_ids = select_product_ids(
        products=products,
        count=2,
    )

    print(
        "\nSelected product IDs:",
        ", ".join(selected_product_ids),
    )

    verified_products: list[dict[str, Any]] = []

    # ---------------------------------------------------------
    # Use the same template once for each selected product.
    # ---------------------------------------------------------

    for product_id in selected_product_ids:
        print("\n" + "-" * 70)
        print(f"Testing product resource: {product_id}")
        print("-" * 70)

        concrete_uri = expand_product_resource_template(
            uri_template=discovered_uri_template,
            product_id=product_id,
        )

        print("Template:", discovered_uri_template)
        print("Product ID:", product_id)
        print("Concrete URI:", concrete_uri)

        _, product_data = await read_json_resource(
            session=session,
            resource_uri=concrete_uri,
        )

        verified_product = verify_product_resource(
            product_data=product_data,
            expected_product_id=product_id,
        )

        verified_products.append(
            verified_product
        )

        print("\nProduct verification: PASSED")
        print(
            "Verified product ID:",
            verified_product["product_id"],
        )
        print(
            "Verified product name:",
            verified_product["name"],
        )
        print(
            "Verified price:",
            verified_product["price"],
        )
        print(
            "Verified quantity:",
            verified_product["quantity"],
        )

    returned_ids = [
        product["product_id"]
        for product in verified_products
    ]

    if len(set(returned_ids)) != 2:
        raise AssertionError(
            "The two resource-template reads did not return two distinct "
            "products."
        )

    print("\n" + "=" * 70)
    print("PART 4B VERIFICATION: PASSED")
    print("=" * 70)

    print(
        "Confirmed resource template:",
        discovered_uri_template,
    )

    print(
        "Confirmed concrete resources:",
        ", ".join(
            f"inventory://products/{product_id}"
            for product_id in returned_ids
        ),
    )

    print(
        "Confirmed that the same template returned "
        "two distinct product resources."
    )

    
def verify_product_resource(
    product_data: Any,
    expected_product_id: str,
) -> dict[str, Any]:
    """
    Verify a product returned through the resource template.

    Validation includes:

    - JSON value is an object
    - required fields are present
    - product_id matches the requested ID
    - string fields contain strings
    - price is numeric
    - quantity is an integer
    - price and quantity are not negative
    """

    if not isinstance(product_data, dict):
        raise AssertionError(
            "The product resource must contain a JSON object."
        )

    required_fields = {
        "product_id",
        "name",
        "description",
        "category",
        "price",
        "quantity",
    }

    missing_fields = required_fields.difference(
        product_data.keys()
    )

    if missing_fields:
        missing_text = ", ".join(
            sorted(missing_fields)
        )

        raise AssertionError(
            "The product resource is missing required fields: "
            f"{missing_text}"
        )

    actual_product_id = product_data["product_id"]

    if actual_product_id != expected_product_id:
        raise AssertionError(
            "The returned product ID does not match the requested ID. "
            f"Requested {expected_product_id!r}; "
            f"received {actual_product_id!r}."
        )

    string_fields = (
        "product_id",
        "name",
        "description",
        "category",
    )

    for field_name in string_fields:
        field_value = product_data[field_name]

        if not isinstance(field_value, str):
            raise AssertionError(
                f"Product field {field_name!r} must be a string."
            )

        if not field_value.strip():
            raise AssertionError(
                f"Product field {field_name!r} cannot be empty."
            )

    price = product_data["price"]

    # bool is technically a subclass of int in Python, so explicitly
    # exclude it from numeric validation.
    if isinstance(price, bool) or not isinstance(
        price,
        (int, float),
    ):
        raise AssertionError(
            "Product field 'price' must be numeric."
        )

    if price < 0:
        raise AssertionError(
            "Product field 'price' cannot be negative."
        )

    quantity = product_data["quantity"]

    if isinstance(quantity, bool) or not isinstance(
        quantity,
        int,
    ):
        raise AssertionError(
            "Product field 'quantity' must be an integer."
        )

    if quantity < 0:
        raise AssertionError(
            "Product field 'quantity' cannot be negative."
        )

    return product_data   
    






