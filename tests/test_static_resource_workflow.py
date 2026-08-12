"""
Regression tests for the MCP static-resource workflow.

These tests protect the architectural boundary between:

    previously discovered resource metadata
                +
        active MCP session
                ↓
    static-resource workflow
                ↓
        session.read_resource(...)

The tests intentionally do not create a real MCP connection or start
the demonstration server.

Part 10B.2 protects workflow delegation rather than MCP transport,
connection lifecycle, capability discovery, presentation, or server
business logic.
"""

from types import SimpleNamespace

import pytest

from mcp_client.static_resource_workflow import (
    read_application_configuration,
)


class FakeResourceSession:
    """
    Minimal test double for the ClientSession dependency used by
    read_application_configuration().

    This fake intentionally exposes only read_resource().

    It does NOT implement list_resources(), because capability discovery
    belongs to the discovery subsystem rather than the workflow subsystem.
    """

    def __init__(self) -> None:
        self.read_count = 0
        self.read_uri = None

    async def read_resource(self, resource_uri: str):
        """
        Record the delegated resource read and return an obviously valid
        deterministic application-configuration resource.
        """

        self.read_count += 1
        self.read_uri = resource_uri

        resource_content = SimpleNamespace(
            uri="config://application",
            mimeType="application/json",
            text=(
                '{"application_name": '
                '"MCP Inventory Learning Server"}'
            ),
        )

        return SimpleNamespace(
            contents=[
                resource_content,
            ],
        )


@pytest.mark.asyncio
async def test_read_application_configuration_delegates_expected_resource_read():
    """
    Protect the successful static-resource delegation boundary.

    Given:
        - previously discovered metadata containing config://application
        - an active session capable of reading resources

    Verify that read_application_configuration():

        1. uses the supplied discovery metadata,
        2. reads config://application exactly once,
        3. completes successfully for a valid JSON resource.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------
    #
    # This represents resource metadata that was ALREADY obtained
    # by the discovery subsystem.
    #
    # Only the fields consumed by the workflow and its metadata
    # presentation helper are represented.
    # ---------------------------------------------------------

    application_resource = SimpleNamespace(
        uri="config://application",
        name="Application Configuration",
        description="Application configuration.",
        mimeType="application/json",
    )

    resources_result = SimpleNamespace(
        resources=[
            application_resource,
        ],
    )

    session = FakeResourceSession()

    # ---------------------------------------------------------
    # Act
    # ---------------------------------------------------------

    await read_application_configuration(
        session=session,
        resources_result=resources_result,
    )

    # ---------------------------------------------------------
    # Assert
    # ---------------------------------------------------------
    #
    # These assertions protect the workflow delegation boundary,
    # not the internal parsing or formatting implementation.
    # ---------------------------------------------------------

    assert session.read_count == 1

    assert session.read_uri == "config://application"
    

@pytest.mark.asyncio
async def test_read_application_configuration_does_not_read_when_required_resource_missing():
    """
    Protect the missing-required-resource workflow contract.

    Given discovery metadata that does NOT advertise
    config://application:

        1. read_application_configuration() must raise RuntimeError,
        2. session.read_resource() must not be invoked.

    This protects the architectural rule that the workflow must respect
    previously discovered capability metadata rather than blindly reading
    a hard-coded resource URI.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------
    #
    # Simulate a server that advertises a different resource but
    # does NOT advertise config://application.
    # ---------------------------------------------------------

    other_resource = SimpleNamespace(
        uri="inventory://products",
        name="Complete Product Inventory",
        description="A different static resource.",
        mimeType="application/json",
    )

    resources_result = SimpleNamespace(
        resources=[
            other_resource,
        ],
    )

    session = FakeResourceSession()

    # ---------------------------------------------------------
    # Act + Assert
    # ---------------------------------------------------------

    with pytest.raises(
        RuntimeError,
        match="config://application",
    ):
        await read_application_configuration(
            session=session,
            resources_result=resources_result,
        )

    # ---------------------------------------------------------
    # Architectural assertion
    # ---------------------------------------------------------
    #
    # The workflow must stop at the discovery-metadata boundary.
    # No resource read should occur for a capability that was
    # not advertised by discovery.
    # ---------------------------------------------------------

    assert session.read_count == 0
    
@pytest.mark.asyncio
async def test_read_application_configuration_rejects_invalid_configuration():
    """
    Protect the application-configuration verification contract.

    Given:
        - discovery metadata containing config://application
        - a successful resource read
        - valid JSON that is NOT a configuration object

    Verify that read_application_configuration():

        1. reads the required resource exactly once,
        2. does not accept the invalid configuration as workflow success,
        3. raises AssertionError.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    application_resource = SimpleNamespace(
        uri="config://application",
        name="Application Configuration",
        description="Application configuration.",
        mimeType="application/json",
    )

    resources_result = SimpleNamespace(
        resources=[
            application_resource,
        ],
    )

    class InvalidConfigurationSession:
        """
        Minimal ClientSession test double.

        The MCP resource operation itself succeeds.

        The returned body is valid JSON, but it is a JSON array rather
        than the nonempty JSON object required by this application
        configuration workflow.
        """

        def __init__(self) -> None:
            self.read_count = 0
            self.read_uri = None

        async def read_resource(self, resource_uri: str):
            self.read_count += 1
            self.read_uri = resource_uri

            resource_content = SimpleNamespace(
                uri="config://application",
                mimeType="application/json",

                # Valid JSON, but deliberately the wrong application
                # configuration shape.
                text="[]",
            )

            return SimpleNamespace(
                contents=[
                    resource_content,
                ],
            )

    session = InvalidConfigurationSession()

    # ---------------------------------------------------------
    # Act + Assert
    # ---------------------------------------------------------

    with pytest.raises(
        AssertionError,
        match="configuration JSON to contain an object",
    ):
        await read_application_configuration(
            session=session,
            resources_result=resources_result,
        )

    # ---------------------------------------------------------
    # Architectural assertions
    # ---------------------------------------------------------
    #
    # These prove that:
    #
    # 1. discovery allowed the workflow to proceed,
    # 2. the resource operation really occurred,
    # 3. failure happened because the returned application
    #    configuration was not acceptable.
    # ---------------------------------------------------------

    assert session.read_count == 1

    assert session.read_uri == "config://application"