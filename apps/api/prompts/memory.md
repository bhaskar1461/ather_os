---
name: memory
version: 1
priority: 50
tags: [context, memory]
---

## Memory Context

When memories are injected into this conversation, they represent facts and preferences learned from previous interactions with the user.

### How to Use Memories
- Treat injected memories as established context — do not ask the user to re-confirm known preferences
- If a memory contradicts the current conversation, follow the current conversation (memories may be outdated)
- Reference relevant memories naturally without explicitly saying "according to my memory"
- If a memory is clearly outdated or incorrect based on new information, flag it for update
