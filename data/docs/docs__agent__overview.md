# Cursor Agent

Agent is Cursor's assistant that can complete complex coding tasks independently, run terminal commands, and edit code. Access in sidepane with Cmd+I.

## How Agent works

An agent is built on three components:

1. **Instructions**: The system prompt and rules that guide agent behavior
2. **Tools**: File editing, codebase search, terminal execution, and more
3. **Model**: The agent model you pick for the task

Cursor's agent orchestrates these components for each model we support, tuning instructions and tools specifically for every frontier model.

## Tools

Tools are the building blocks of Agent. They are used to search your codebase and the web, make edits to your files, run terminal commands, and more. There is no limit on the number of tool calls Agent can make during a task.

### Semantic search
Perform semantic searches within your indexed codebase. Finds code by meaning, not just exact matches.

### Search files and folders
Search for files by name, read directory structures, and find exact keywords or patterns within files.

### Web
Generate search queries and perform web searches.

### Read files
Intelligently read the content of a file. Also supports image files and includes them in the conversation context.

### Edit files
Suggest edits to files and apply them automatically.

### Run shell commands
Execute terminal commands and monitor output. By default, Cursor uses the first terminal profile available.

### Browser
Control a browser to take screenshots, test applications, and verify visual changes.

### Image generation
Generate images from text descriptions or reference images.

### Ask questions
Ask clarifying questions during a task while continuing to work.

## Checkpoints

Checkpoints save snapshots of your codebase during an Agent session. Agent automatically creates them before making significant changes. If Agent takes a wrong turn, click any checkpoint in the chat timeline to preview and restore your files. Checkpoints are stored locally and separate from Git.

## Queued messages

Queue follow-up messages while Agent is working. Press Enter to add a message to the queue; press Cmd+Enter to send immediately, bypassing the queue.
