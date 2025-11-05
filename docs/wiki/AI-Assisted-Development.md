# AI-Assisted Development with Solo Git

Solo Git is designed from the ground up to be an AI-native version control system. This guide explores the various ways you can leverage Solo Git's AI capabilities to accelerate your development workflow.

---

## The Core Workflow: `pair`

The `pair` command is the heart of Solo Git's AI functionality. It's a single command that encapsulates the entire development loop:

```bash
evogitctl pair "<your-prompt>"
```

When you run this command, Solo Git's AI orchestrator takes over, performing a sequence of actions that we call the "pair loop":

1.  **Plan**: A high-level AI model (like GPT-4 or Claude 3.5 Sonnet) analyzes your prompt and the existing codebase to create a detailed implementation plan.
2.  **Code**: A specialized coding model (like DeepSeek Coder or CodeLlama) generates the code changes based on the plan.
3.  **Test**: The project's test suite is run in a sandboxed environment to verify the changes.
4.  **Promote**: If the tests pass, the changes are automatically merged into the trunk.

---

## The Three-Tier Model Selection

Solo Git uses a three-tier model selection system to ensure the best AI model is used for each task, balancing performance, cost, and intelligence.

| Tier | Models | Use Cases |
|---|---|---|
| **Planning** | GPT-4, Claude 3.5 Sonnet | Architecture, complex logic, failure diagnosis |
| **Coding** | DeepSeek-Coder, CodeLlama | Patch generation, refactoring, standard tasks |
| **Fast** | Llama 3.1 8B, Gemma 2 9B | Simple edits, boilerplate, documentation |

The system automatically escalates to more powerful (and expensive) models based on factors like code complexity, security keywords, and test failure history.

---

## Advanced AI Commands

In addition to the main `pair` command, Solo Git provides more granular AI commands for specific tasks:

- **`evogitctl ai generate "<prompt>"`**: Generate code without immediately running tests.
- **`evogitctl ai refactor <file>`**: Refactor a specific file with AI.
- **`evogitctl ai test-gen <file>`**: Generate a test suite for a file.
- **`evogitctl test analyze`**: Use AI to analyze test failures and suggest fixes.

---

## Best Practices for AI Prompts

- **Be Specific**: The more specific your prompt, the better the results. Instead of "add auth," try "add a login endpoint that accepts a username and password and returns a JWT."
- **Provide Context**: If you're working on a specific file, mention it in the prompt.
- **Iterate**: If the first result isn't perfect, refine your prompt and try again. The `pair` loop is designed to be fast and iterative.

By mastering these AI-powered workflows, you can significantly reduce the time and effort required to develop and ship high-quality code.
