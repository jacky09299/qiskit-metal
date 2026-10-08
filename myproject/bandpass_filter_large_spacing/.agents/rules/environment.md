---
name: conda_environment_rule
description: Enforces the use of the 'metal' conda environment and package modification permissions.
trigger: always_on
---

# Environment Rules

1. **Conda Environment Constraint**: You MUST ONLY use the conda environment named `metal` to execute any code, commands, or tests within this workspace (`/home/jacky/文件/quantum-metal/myproject/bandpass_filter`). 
2. **Package Modification Restriction**: You MUST explicitly ask the user for permission before installing, updating, removing, or making any changes to packages or dependencies. Do not execute any package modification commands (like `pip install`, `conda install`, etc.) without the user's direct approval first. This is to ensure the working `metal` environment and other environments are not broken.
