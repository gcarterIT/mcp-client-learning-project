"""
Connection lifecycle management for the reusable MCP client.

This module owns the complete lifecycle of an MCP STDIO connection:

1. Start the STDIO transport.
2. Create a ClientSession.
3. Initialize the MCP session.
4. Expose the initialized session to callers.
5. Close the session and transport cleanly.

The module deliberately does not perform tool, resource, or prompt
operations. Those responsibilities remain elsewhere in the client.
"""

from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class MCPConnection:
    """
    Manage the lifecycle of one MCP client connection.

    The class is used as an asynchronous context manager:

        async with MCPConnection(server_parameters) as connection:
            session = connection.session

    The session exposed inside the context is fully initialized and
    ready for MCP operations.
    """

    def __init__(
        self,
        server_parameters: StdioServerParameters,
    ) -> None:
        """
        Store the server parameters needed to start the MCP server.

        No connection is opened during object construction.

        Parameters
        ----------
        server_parameters:
            Configuration describing how the MCP server process should
            be started.
        """

        self._server_parameters = server_parameters

        # Context manager returned by stdio_client(...).
        #
        # We save it because its __aexit__ method must be called during
        # connection cleanup.
        self._stdio_context = None

        # Context manager returned by ClientSession(...).
        #
        # This is also saved so that the ClientSession can be closed
        # correctly during __aexit__.
        self._session_context = None

        # Streams produced by the STDIO transport.
        self._read_stream = None
        self._write_stream = None

        # Publicly accessible initialized MCP session.
        #
        # It starts as None because __init__ does not open a connection.
        self.session: Optional[ClientSession] = None

        # Store the initialization response for future inspection.
        #
        # The existing client currently assigns the result of
        # session.initialize(), so preserving it here avoids discarding
        # potentially useful server metadata.
        self.initialization_result = None

    async def __aenter__(self) -> "MCPConnection":
        """
        Open and initialize the MCP connection.

        Returns
        -------
        MCPConnection
            This connection object, containing an initialized session.

        Raises
        ------
        Exception
            Any exception raised while starting the transport, creating
            the session, or initializing the MCP protocol is allowed to
            propagate to the caller.
        """

        # -------------------------------------------------------------
        # Step 1: Create and enter the STDIO transport context.
        # -------------------------------------------------------------
        self._stdio_context = stdio_client(self._server_parameters)

        self._read_stream, self._write_stream = (
            await self._stdio_context.__aenter__()
        )

        try:
            # ---------------------------------------------------------
            # Step 2: Create and enter the MCP ClientSession context.
            # ---------------------------------------------------------
            self._session_context = ClientSession(
                self._read_stream,
                self._write_stream,
            )

            self.session = await self._session_context.__aenter__()

            # ---------------------------------------------------------
            # Step 3: Perform the MCP initialization handshake.
            # ---------------------------------------------------------
            self.initialization_result = await self.session.initialize()

            # The caller receives the connection wrapper rather than
            # the raw session. The session remains available through:
            #
            #     connection.session
            return self

        except BaseException:
            # If session creation or initialization fails, __aenter__
            # never completes. Python would therefore not call our
            # __aexit__ automatically.
            #
            # We must explicitly clean up anything that was already
            # opened before re-raising the original exception.
            await self._cleanup_after_failed_entry()
            raise

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> bool:
        """
        Close the MCP session and STDIO transport.

        Cleanup occurs in reverse startup order:

        1. Exit the ClientSession context.
        2. Exit the STDIO transport context.

        Returning False means exceptions raised inside the caller's
        async-with block are not suppressed.
        """

        # -------------------------------------------------------------
        # Step 1: Close the ClientSession.
        # -------------------------------------------------------------
        if self._session_context is not None:
            await self._session_context.__aexit__(
                exc_type,
                exc_value,
                traceback,
            )

        # -------------------------------------------------------------
        # Step 2: Close the STDIO transport.
        # -------------------------------------------------------------
        if self._stdio_context is not None:
            await self._stdio_context.__aexit__(
                exc_type,
                exc_value,
                traceback,
            )

        # Clear references after shutdown.
        self.session = None
        self._session_context = None
        self._stdio_context = None
        self._read_stream = None
        self._write_stream = None

        # Do not suppress exceptions from the async-with body.
        return False

    async def _cleanup_after_failed_entry(self) -> None:
        """
        Clean up resources if __aenter__ fails partway through.

        This method handles cases such as:

        - the STDIO transport started successfully;
        - the ClientSession was created successfully;
        - session initialization then failed.

        Since __aenter__ did not finish, Python will not automatically
        call __aexit__. We therefore perform cleanup explicitly.
        """

        if self._session_context is not None:
            await self._session_context.__aexit__(
                None,
                None,
                None,
            )

        if self._stdio_context is not None:
            await self._stdio_context.__aexit__(
                None,
                None,
                None,
            )

        self.session = None
        self._session_context = None
        self._stdio_context = None
        self._read_stream = None
        self._write_stream = None