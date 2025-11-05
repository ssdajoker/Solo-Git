# Solo Git Beta Launch Checklist

This checklist outlines the essential steps to get Solo Git up and running for the beta.

---

## 1. System Prerequisites

- [ ] **Python 3.9+**: Verify with `python3 --version`.
- [ ] **Git 2.30+**: Verify with `git --version`.
- [ ] **Abacus.ai API Account**: Ensure you have a valid API key.

---

## 2. Installation & Configuration

- [ ] **Install Solo Git**: Follow the instructions in the **[Setup Guide](Setup-Guide.md)**.
- [ ] **Run Interactive Setup**: Use `evogitctl config setup` to configure your API credentials and preferences.
- [ ] **Verify Configuration**: Run `evogitctl config test` to ensure your API connection is working correctly.

---

## 3. Your First Workflow

- [ ] **Initialize a Repository**: Use `evogitctl repo init` to import your first project.
- [ ] **Create a Workpad**: Use `evogitctl pad create` to create a new workpad.
- [ ] **Run the AI Pair Loop**: Use `evogitctl pair` to have the AI make changes to your project.
- [ ] **Verify Promotion**: Check the commit history to confirm that the AI's changes were successfully promoted to the trunk.

---

## 4. Exploring the Heaven Interface

- [ ] **Launch the TUI**: Run `evogitctl tui` to explore the terminal user interface.
- [ ] **Use the Command Palette**: Press `Ctrl+P` in the TUI to access the command palette.
- [ ] **(Optional) Build the GUI**: If you have a Rust development environment, you can build and run the desktop GUI.

---

## 5. Providing Feedback

- [ ] **Report Bugs**: If you encounter any bugs, please open an issue on our [GitHub repository](https://github.com/yourusername/solo-git/issues).
- [ ] **Share Your Experience**: We'd love to hear your feedback on the overall experience. Please share your thoughts in the [GitHub Discussions](https://github.com/yourusername/solo-git/discussions).

Thank you for helping us make Solo Git the best it can be!
