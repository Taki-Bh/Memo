# Computer Safety Reference

This reference contains additional guidance for high-impact operations.

## High-impact operations

Treat these as high-impact:

- Recursive deletion
- Disk or partition modification
- Package removal
- Bootloader changes
- Firewall changes
- User and permission changes
- Service shutdown or disabling
- System-wide configuration changes
- Operations requiring root privileges

For these operations, inspect first, make the narrowest change possible, and verify the result.

## Destructive commands

Do not execute destructive commands merely because they are technically valid.

Examples include commands that:

- Delete large directory trees
- Format disks
- Overwrite block devices
- Remove system packages
- Disable security controls
- Change ownership or permissions recursively

The user's explicit objective and the exact scope of the operation must justify the action.

## Secrets

Never intentionally print or expose:

- Passwords
- API keys
- Private keys
- Authentication tokens
- Session cookies
- Other credentials

If command output contains secrets, avoid reproducing them in the final response.
