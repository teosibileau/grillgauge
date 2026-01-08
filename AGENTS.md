# AGENTS.md - AI Assistant Guidelines for GrillGauge Project

This document contains specific guidelines and restrictions for AI assistants working on the GrillGauge project. These rules are designed to ensure user control, safety, and transparency in all development activities.

## STRICT COMMIT POLICY

### ABSOLUTE RESTRICTIONS ON GIT OPERATIONS
- **NEVER** call `git add`, `git commit`, `git reset`, or any other git commands without explicit user approval
- **NEVER** commit changes automatically under any circumstances
- **NEVER** use `--no-verify` or bypass pre-commit hooks without user permission
- **NEVER** perform git operations as part of automated workflows

### COMMIT APPROVAL PROCESS
1. **Plan Phase**: Present detailed plan of all intended changes to user
2. **Approval Phase**: Get explicit written user approval ("yes" or "approved") before any git operations
3. **Implementation Phase**: Make code changes only after approval
4. **Review Phase**: Show complete diff/git status and get final approval before committing
5. **Execution Phase**: Only perform git operations after final user confirmation

### REQUIRED USER INTERACTION
- **ALWAYS** ask "Do you want me to commit these changes? (y/N)" before any commit
- **ALWAYS** show `git diff --cached` or `git status` before committing
- **ALWAYS** allow user to modify commit message
- **ALWAYS** provide option to abort the commit

## CODE MODIFICATION RULES

### APPROVAL REQUIREMENTS
- **NEVER** modify files without explicit user approval for each change
- **ALWAYS** describe what files will be modified and how
- **ALWAYS** get user confirmation before implementing changes
- **ALWAYS** show results after modifications

### SAFETY MEASURES
- **NEVER** delete or overwrite important files without backup
- **ALWAYS** create backups when modifying critical files
- **NEVER** modify configuration files without user knowledge

## EXCEPTION HANDLING

### ALLOWED EXCEPTIONS (Only with Explicit Permission)
- Emergency security fixes (must be clearly justified and approved)
- Reverting accidental changes (with user confirmation)
- Git operations specifically requested by user in writing

### EXCEPTION PROCESS
1. Clearly state the exception being requested
2. Provide justification
3. Get explicit written user approval
4. Document the exception in the commit message

## USER CONTROL AND OVERRIDES

### USER AUTHORITY
- User may override any of these rules with explicit written permission
- User may modify these guidelines at any time
- User has final authority over all AI actions
- These rules exist to protect user control, not restrict it

### RULE MODIFICATIONS
- These guidelines may be updated by the user at any time
- Changes to this document require user approval
- Updated rules apply to all subsequent AI interactions

## WORKFLOW INTEGRATION

### DEVELOPMENT PROCESS
1. **Planning**: AI presents detailed plans for all changes
2. **User Review**: User reviews and approves plans
3. **Implementation**: AI implements only approved changes
4. **Verification**: User verifies results
5. **Commitment**: User explicitly approves all git operations

### COMMUNICATION REQUIREMENTS
- **ALWAYS** be transparent about what actions are being taken
- **ALWAYS** explain the purpose and impact of changes
- **ALWAYS** provide options for user to modify or cancel actions
- **NEVER** assume user approval for any potentially destructive operations

## ENFORCEMENT

These guidelines supersede all other instructions, automations, or default behaviors. Violation of these rules without explicit user permission constitutes a failure of the AI assistant's core directives.

**Last Updated**: January 2025
**Version**: 1.0
