MCP Client Learning Project — Context

Project Goal:

This project is a comprehensive tutorial on learning the Model Context Protocol (MCP) by building a deterministic Python MCP client from scratch.

The objective is to understand the MCP protocol itself before introducing AI agents or LLMs.

The final project will contain three applications sharing one reusable client library:
Terminal application
Jupyter Notebook application
Streamlit GUI application

All three applications will use the same reusable MCP client library.


Tutorial Philosophy:
The project is intended to teach software engineering as well as MCP.
Every new feature should be introduced incrementally.
Every major code segment should be tested before introducing additional complexity.
The tutorial should explain not only what is being done but why it is being done.
The explanations should resemble those of a university professor teaching an upper-level software engineering course.


Current Status:

Completed:

Part 1
Development environment
Virtual environment
requirements.txt
Jupyter kernel
project structure
environment verification

Completed:

Part 2
Fully functional deterministic MCP demo server
Business logic separated from protocol layer
Unit tests
MCP Inspector validation
Tools
Static resources
Resource templates
Prompts

Inspector version:
MCP Inspector v0.22.0


The demo server has been validated successfully.


Design Decisions:
STDIO transport first.
Streamable HTTP second.
Deterministic client first.
LLM integration discussed later.
Shared reusable client library.
Configuration-driven server selection.
No LangChain.
No LangGraph.
No OpenAI during the deterministic client tutorial.

Current Demo Server
The server exposes:

Tools
add_numbers
divide_numbers
search_inventory
update_demo_setting

Resources
config://application
inventory://products
settings://current

Resource Template
inventory://products/{product_id}

Prompts
summarize_inventory
analyze_customer_request
Validation Completed

Verified using MCP Inspector:
Tool discovery
Tool execution
Resource discovery
Static resources
Resource template
Prompt discovery
Prompt rendering


Everything is functioning correctly.


Preferred Teaching Style:
Very detailed.
Professor-level explanations.
Explain every design decision.
Include diagrams.
Include extensive comments.
Provide minimal examples before abstractions.
Explain common pitfalls.
Discuss future improvements.
Never skip steps.
Every major milestone must include testing.


Development Environment:
Windows 11
PowerShell
Python virtual environment
Jupyter Notebook
Python 3.12
MCP SDK 1.28.0