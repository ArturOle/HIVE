# 29. public facing site uses separate database
Date: 02.07.2026
## Status
02.07.2026 approved
02.07.2026 proposed
## Context
There is a need for versioning of prompts in our system for A/B testing and comparisions/experimentations via evals. There is a number of options available for prompt versioning from jinja2 templating to extenal services holding the prompts.

### HIVE requiremnts to prompt versioning
1. Provides versioning of prompts
2. No external provider/service
3. Allows easy access and switching between versions
4. Does not allow overwrite of prompt versions
5. Can be traced in version control
6. Prompts unaccessable without key (encrypted)

### Options 
1. Files and directories + git versioning
    - Pros: intuitive, directly modifiable
    - Cons: can be easly accessed and leaked on security breach and become attack vector, versioning is ackward, hard to maintain metadata and the procedures with higher number of files
2. Jinja2
    - Pros: Jinja2
    - Cons: Jinja2
3. SQLite
    - Pros: Can hold all necessarty metadata, fast, easly encripted, prompts easly switchable, can be both local and hosted.
    - Cons: No direct access or modification, interface needed to be implemented for ease of use

## Decision
HIVE will implement the approach with the SQLite database as a prompt repository.
## Consequences
Potential problems with the appoach, especially around uploading new prompt versions and understanding but its cost of security and good practices.