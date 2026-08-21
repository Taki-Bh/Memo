---
name: computer
description: Operate and manage the local computer through authorized system tools. Use when a task requires inspecting, reading, creating, modifying, executing, or managing resources on the local system.
---

# Computer

## Purpose

The computer skill gives the assistant the ability to operate the local computer.

Use it when a task requires interacting with the operating system rather than only reasoning about information.

The skill provides operational guidance. It does not contain the implementation of computer tools or the external runner.

## Available Tools

The computer skill may use these tools when they are registered and available:

- `read` — inspect a file or list a directory.
- `write` — create or modify a text file.
- `exec` — execute a shell command.

Only use tools that are actually available in the current runtime.

## Operating Principles

### Inspect before modifying

Before changing an unfamiliar resource:

1. Inspect its current state.
2. Determine what needs to change.
3. Make the smallest appropriate modification.
4. Verify the result.

### Use the least powerful operation

Use the simplest tool capable of completing the task.

- Reading a file or directory → `read`
- Creating or modifying a text file → `write`
- Running a command or program → `exec`

Do not use `exec` when another available tool is sufficient.

### Preserve user data

Treat existing user data as valuable.

Avoid unnecessary deletion, overwriting, recursive destructive operations, and unrelated modifications.

For potentially destructive or irreversible operations, ensure the user's request clearly authorizes the intended operation.

### Stay within scope

Only perform operations necessary to accomplish the user's objective.

Do not modify unrelated files, services, packages, or system settings.

### Verify important operations

After an important operation:

1. Check the result.
2. Inspect the resulting state when practical.
3. Report failures accurately.

Never claim success merely because a command was issued.

### Handle failures

When a tool fails:

1. Inspect the error.
2. Determine the likely cause.
3. Inspect relevant state if needed.
4. Retry only with a corrected or safer approach.

Do not repeatedly execute the same failing operation without understanding the failure.

## Filesystem

When working with files:

- Use `read` to inspect files and directories.
- Use `write` to create or modify text files.
- Preserve unrelated existing content.
- Prefer explicit paths when possible.
- Verify important writes.
- Do not assume a relative path is correct when the working directory is uncertain.

## Command Execution

Use `exec` when a shell command or program must actually run.

Before execution, consider:

- What the command changes
- Whether it is necessary
- Whether it is destructive
- Whether elevated privileges are required
- Whether its output is needed
- Whether a safer alternative exists

Prefer commands that are narrow, explicit, and easy to verify.

## Privileged Operations

Treat root or elevated-privilege operations as high-impact.

Do not obtain elevated privileges merely for convenience.

When elevation is genuinely required, use the minimum necessary scope and follow the runtime's authorization policy.

## Process and Service Management

When managing processes or services:

1. Inspect current state when possible.
2. Identify the relevant process or service.
3. Perform the requested operation.
4. Verify the resulting state.

Do not terminate unrelated processes or services.

## Package and System Changes

When installing software or changing system configuration:

1. Identify the operating system and relevant version.
2. Inspect the current state.
3. Determine the appropriate, current installation or configuration method.
4. Make the smallest required change.
5. Validate the configuration or installation.
6. Verify the resulting system state.

Do not assume that package names, repositories, service names, or installation procedures are universal across distributions or releases.

When current technical information matters, use an available authoritative information source rather than relying on stale assumptions.

## Security Boundaries

The computer skill operates with the permissions granted to the assistant.

Do not attempt to bypass:

- Authentication
- Authorization
- Access controls
- Sandboxing
- Security policies
- File permissions

Do not expose credentials, private keys, tokens, or other secrets.

Avoid accessing private data unless it is necessary for the explicitly requested task.

## External Runner

The external runner is the execution boundary between the assistant and the operating system.

The assistant should treat runner results as authoritative execution results and inspect:

- Exit status
- Standard output
- Standard error
- Other structured metadata provided by the runner

The assistant should not claim that a command succeeded without checking the runner result.

The runner may enforce additional authorization, safety, sandboxing, timeout, or resource policies. Never attempt to bypass those controls.

## Decision Procedure

For a computer task:

1. Understand the requested outcome.
2. Identify the resources involved.
3. Inspect relevant system state.
4. Select the minimum required tools.
5. Perform the operation.
6. Verify the result.
7. Report the outcome.

## Example: Installing Software

For a request such as installing a system package:

1. Identify the operating system and release.
2. Determine whether the software is already installed.
3. Determine the appropriate current installation method.
4. Execute the required commands through `exec`.
5. Inspect exit status and errors.
6. Verify the installation.
7. Report what was installed and whether additional action, such as a reboot, is required.

Do not blindly use installation commands from another distribution or an outdated procedure.

## Example: Modifying a Configuration

1. Locate the relevant configuration.
2. Read the current contents.
3. Determine the minimal required change.
4. Write the change.
5. Validate the configuration when possible.
6. Verify the affected service or system state.

## Scope

This skill governs interaction with the local computer.

It does not define:

- General reasoning
- Web browsing
- Communication
- Long-term memory
- Application-specific business logic

Those should be provided by separate skills or tools.
