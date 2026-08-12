"""
Regression tests for the MCP resource-template workflow.

These tests protect the architectural boundary between:

    previously discovered resource-template metadata
                +
        active MCP session
                ↓
    resource-template workflow
                ↓
    concrete resource URI expansion
                ↓
        session.read_resource(...)

The tests intentionally do not create a real MCP connection or start
the demonstration server.

Part 10B.3 protects workflow behavior rather than connection lifecycle,
capability discovery, formatter implementation, or server business logic.
"""

from types import SimpleNamespace

import pytest

from mcp_client.resource_template_workflow import (
    test_product_resource_template as run_product_resource_template,
)

class FakeResourceTemplateSession:
    """
    Minimal ClientSession test double for the successful template workflow.

    The fake records every resource URI that the workflow asks to read and
    returns deterministic resource data for exactly three expected reads:

        1. inventory://products
        2. inventory://products/P100
        3. inventory://products/P101

    It intentionally does NOT expose list_resource_templates(), because
    template discovery belongs to the discovery subsystem.
    """

    def __init__(self) -> None:
        self.read_uris = []

    async def read_resource(self, resource_uri: str):
        """
        Record the requested URI and return deterministic resource content.
        """

        uri = str(resource_uri)
        self.read_uris.append(uri)

        # ---------------------------------------------------------
        # First read:
        # static inventory used by the workflow to obtain valid IDs.
        # ---------------------------------------------------------

        if uri == "inventory://products":
            return SimpleNamespace(
                contents=[
                    SimpleNamespace(
                        uri="inventory://products",
                        mimeType="application/json",
                        text="""
[
    {
        "product_id": "P100",
        "name": "Mechanical Keyboard",
        "category": "computer-accessories",
        "description": "A compact mechanical keyboard.",
        "price": 89.99,
        "quantity": 14
    },
    {
        "product_id": "P101",
        "name": "Wireless Mouse",
        "category": "computer-accessories",
        "description": "An ergonomic wireless mouse.",
        "price": 34.50,
        "quantity": 28
    }
]
""",
                    ),
                ],
            )

        # ---------------------------------------------------------
        # Concrete resource produced from:
        #
        # inventory://products/{product_id}
        #                     +
        #                   P100
        # ---------------------------------------------------------

        if uri == "inventory://products/P100":
            return SimpleNamespace(
                contents=[
                    SimpleNamespace(
                        uri="inventory://products/P100",
                        mimeType="application/json",
                        text="""
{
    "product_id": "P100",
    "name": "Mechanical Keyboard",
    "category": "computer-accessories",
    "description": "A compact mechanical keyboard.",
    "price": 89.99,
    "quantity": 14
}
""",
                    ),
                ],
            )

        # ---------------------------------------------------------
        # Concrete resource produced from:
        #
        # inventory://products/{product_id}
        #                     +
        #                   P101
        # ---------------------------------------------------------

        if uri == "inventory://products/P101":
            return SimpleNamespace(
                contents=[
                    SimpleNamespace(
                        uri="inventory://products/P101",
                        mimeType="application/json",
                        text="""
{
    "product_id": "P101",
    "name": "Wireless Mouse",
    "category": "computer-accessories",
    "description": "An ergonomic wireless mouse.",
    "price": 34.50,
    "quantity": 28
}
""",
                    ),
                ],
            )

        # ---------------------------------------------------------
        # Any other URI indicates that the workflow delegated an
        # operation outside the contract established by this test.
        # ---------------------------------------------------------

        raise AssertionError(
            f"Unexpected resource URI requested: {uri}"
        )


@pytest.mark.asyncio
async def test_product_resource_template_expands_and_reads_expected_resources():
    """
    Protect the successful resource-template workflow boundary.

    Given:
        - previously discovered metadata containing the expected template
        - server inventory containing valid product IDs P100 and P101
        - concrete resources for those IDs

    Verify that the workflow:

        1. uses the supplied template metadata,
        2. reads the inventory to obtain valid parameter values,
        3. expands the template for P100 and P101,
        4. reads both concrete resource URIs,
        5. completes successfully.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------
    #
    # This represents resource-template metadata that was ALREADY
    # obtained by the discovery subsystem.
    # ---------------------------------------------------------

    product_template = SimpleNamespace(
        uriTemplate="inventory://products/{product_id}",
        name="Inventory Product",
        description="Retrieve a single inventory product by product ID.",
        mimeType="application/json",
    )

    templates_result = SimpleNamespace(
        resourceTemplates=[
            product_template,
        ],
    )

    session = FakeResourceTemplateSession()

    # ---------------------------------------------------------
    # Act
    # ---------------------------------------------------------

    await run_product_resource_template(
        session=session,
        templates_result=templates_result,
    )

    # ---------------------------------------------------------
    # Assert
    # ---------------------------------------------------------
    #
    # Protect the observable resource-delegation sequence.
    # ---------------------------------------------------------

    assert session.read_uris == [
        "inventory://products",
        "inventory://products/P100",
        "inventory://products/P101",
    ]
    
@pytest.mark.asyncio
async def test_product_resource_template_does_not_read_when_required_template_missing():
    """
    Protect the missing-required-template workflow contract.

    Given discovery metadata that does NOT advertise
    inventory://products/{product_id}:

        1. the workflow must raise RuntimeError,
        2. session.read_resource() must not be invoked.

    This protects the architectural rule that resource-template
    workflows must respect previously discovered capability metadata
    rather than proceeding with hard-coded resource reads.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    other_template = SimpleNamespace(
        uriTemplate="inventory://categories/{category}",
        name="Inventory Category",
        description="Retrieve products by category.",
        mimeType="application/json",
    )

    templates_result = SimpleNamespace(
        resourceTemplates=[
            other_template,
        ],
    )

    class NoReadSession:
        """
        Minimal session double.

        If the workflow tries to read any resource, record that fact.
        """

        def __init__(self) -> None:
            self.read_count = 0

        async def read_resource(self, resource_uri: str):
            self.read_count += 1

            raise AssertionError(
                f"read_resource() should not have been called: {resource_uri}"
            )

    session = NoReadSession()

    # ---------------------------------------------------------
    # Act + Assert
    # ---------------------------------------------------------

    with pytest.raises(
        RuntimeError,
        match="inventory://products",
    ):
        await run_product_resource_template(
            session=session,
            templates_result=templates_result,
        )

    # ---------------------------------------------------------
    # Architectural assertion
    # ---------------------------------------------------------

    assert session.read_count == 0
    
@pytest.mark.asyncio
async def test_product_resource_template_rejects_mismatched_product_identity():
    """
    Protect the resource-template identity contract.

    Given:
        - the required product resource template is advertised,
        - inventory data provides valid product IDs,
        - the workflow requests inventory://products/P100,
        - the returned resource incorrectly claims product_id == P999,

    Verify that the workflow rejects the mismatched resource.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    product_template = SimpleNamespace(
        uriTemplate="inventory://products/{product_id}",
        name="Inventory Product",
        description="Retrieve a single inventory product by product ID.",
        mimeType="application/json",
    )

    templates_result = SimpleNamespace(
        resourceTemplates=[
            product_template,
        ],
    )

    class MismatchedProductSession:
        """
        Minimal session double for the identity-mismatch path.

        The inventory itself is valid. The first concrete product read,
        however, deliberately returns the wrong product_id.
        """

        def __init__(self) -> None:
            self.read_uris = []

        async def read_resource(self, resource_uri: str):
            uri = str(resource_uri)
            self.read_uris.append(uri)

            # -------------------------------------------------
            # Step 1:
            # Return inventory data containing two valid IDs.
            # -------------------------------------------------

            if uri == "inventory://products":
                return SimpleNamespace(
                    contents=[
                        SimpleNamespace(
                            uri="inventory://products",
                            mimeType="application/json",
                            text="""
[
    {
        "product_id": "P100",
        "name": "Mechanical Keyboard",
        "category": "computer-accessories",
        "description": "A compact mechanical keyboard.",
        "price": 89.99,
        "quantity": 14
    },
    {
        "product_id": "P101",
        "name": "Wireless Mouse",
        "category": "computer-accessories",
        "description": "An ergonomic wireless mouse.",
        "price": 34.50,
        "quantity": 28
    }
]
""",
                        ),
                    ],
                )

            # -------------------------------------------------
            # Step 2:
            # The workflow correctly requests P100...
            #
            # ...but the server response deliberately identifies
            # itself as P999.
            # -------------------------------------------------

            if uri == "inventory://products/P100":
                return SimpleNamespace(
                    contents=[
                        SimpleNamespace(
                            uri="inventory://products/P100",
                            mimeType="application/json",
                            text="""
{
    "product_id": "P999",
    "name": "Wrong Product",
    "category": "computer-accessories",
    "description": "Deliberately incorrect identity.",
    "price": 89.99,
    "quantity": 14
}
""",
                        ),
                    ],
                )

            raise AssertionError(
                f"Unexpected resource URI requested: {uri}"
            )

    session = MismatchedProductSession()

    # ---------------------------------------------------------
    # Act + Assert
    # ---------------------------------------------------------

    with pytest.raises(
        AssertionError,
        match="P100",
    ):
        await run_product_resource_template(
            session=session,
            templates_result=templates_result,
        )

    # ---------------------------------------------------------
    # Architectural assertions
    # ---------------------------------------------------------
    #
    # These prove that:
    #
    # 1. inventory was read,
    # 2. the P100 concrete URI was correctly generated,
    # 3. failure occurred only after the mismatched P100
    #    resource was returned.
    # ---------------------------------------------------------

    assert session.read_uris == [
        "inventory://products",
        "inventory://products/P100",
    ]