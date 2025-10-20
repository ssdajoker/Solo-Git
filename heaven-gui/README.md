# Heaven UI - Solo Git Interface

> "Simplicity is the ultimate sophistication." - Leonardo da Vinci

A minimalist, keyboard-first desktop interface for Solo Git, built with React, TypeScript, Tailwind CSS, and Tauri.

## 🎨 Design Philosophy

Heaven UI embodies a clean, focused development experience:

- **Minimalism**: Uncluttered interface with purposeful use of space
- **Dark Theme**: Deep space aesthetic that reduces eye strain
- **Keyboard-First**: Every action accessible via keyboard shortcuts
- **Voice-Enabled**: Natural language input for AI-assisted workflows
- **Accessible**: WCAG AA compliant with comprehensive keyboard and screen reader support

## ✨ Features

### Command Palette
- **Quick Search**: Instantly find and execute commands
- **AI Suggestions**: Context-aware recommendations powered by AI
- **Keyboard Navigation**: Arrow keys to navigate, Enter to select, Escape to close
- **Categorized Commands**: Organized by Navigation, Editor, Testing, Git, AI, Settings, Help

### File Explorer
- **Tree View**: Hierarchical file browser with expand/collapse
- **Color-Coded Icons**: Visual file type identification
- **Collapsible**: Maximize screen space when needed
- **Keyboard Navigation**: Arrow keys and Enter for navigation

### Code Editor
- **Syntax Highlighting**: Custom Material Ocean theme
- **Monaco Integration**: Powered by VS Code's editor
- **Line Numbers**: Easy reference
- **Auto-Indent**: Smart code formatting

### Commit Timeline
- **Visual Git History**: See commits as a graph
- **Status Indicators**: Green (success), Orange (pending), Red (failed), Purple (AI-assisted)
- **Interactive**: Click to view commit details

### Status Bar
- **Test Results**: Real-time test execution feedback
- **Build Status**: CI/CD integration
- **Cost Tracking**: Monitor AI operation costs
- **Always Visible**: Key information at a glance

### Voice Input
- **Voice Commands**: Speak your intentions
- **Hybrid Input**: Type or speak, your choice
- **Visual Feedback**: Recording indicator

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- Rust 1.70+
- Tauri CLI

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run tauri:dev
```

### Development

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run tauri:build
```

## 📁 Project Structure

```
src/
├── components/
│   ├── web/              # Platform-agnostic React components
│   │   ├── CommandPalette.tsx
│   │   ├── FileExplorer.tsx
│   │   ├── StatusBar.tsx
│   │   ├── VoiceInput.tsx
│   │   └── EmptyState.tsx
│   │
│   ├── desktop/          # Tauri-specific components
│   │   └── (native integrations)
│   │
│   ├── shared/           # Common utilities
│   │   ├── types/        # TypeScript interfaces
│   │   ├── hooks/        # Custom React hooks
│   │   └── utils/        # Utility functions
│   │
│   └── ui/               # Base UI components
│
├── styles/               # Global styles
├── App.tsx              # Main application
└── main.tsx             # Entry point
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl+P` | Open Command Palette |
| `Cmd/Ctrl+B` | Toggle File Explorer |
| `Cmd/Ctrl+/` | Toggle AI Assistant |
| `Cmd/Ctrl+E` | Focus Editor (Zen Mode) |
| `Cmd/Ctrl+T` | Run Tests |
| `Cmd/Ctrl+,` | Open Settings |
| `?` | Show Keyboard Shortcuts |
| `Escape` | Close Modals |

## 🎨 Design System

### Color Palette
- **Primary Background**: `#0A0E1A` - Deep space black
- **Secondary Background**: `#0D1117` - Slightly lighter panels
- **Tertiary Background**: `#1A1F2E` - Elevated surfaces
- **Accent Colors**: Blue, Green, Orange, Red, Cyan, Purple, Pink

### Typography
- **Sans-Serif**: System fonts for UI
- **Monospace**: Fira Code, JetBrains Mono for code

### Spacing
- **4px Grid System**: Consistent rhythm throughout

See [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) for complete specifications.

## 🏗️ Architecture

Heaven UI uses a component-first architecture with clear separation:

- **Web Components**: Platform-agnostic React components
- **Desktop Components**: Tauri-specific native integrations
- **Shared Infrastructure**: Types, hooks, and utilities

Key patterns:
- **Component Composition**: Small, focused components
- **Type Safety**: Comprehensive TypeScript interfaces
- **Custom Hooks**: Reusable stateful logic
- **Utility Functions**: Pure, testable helpers

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed information.

## ♿ Accessibility

Heaven UI is built with accessibility as a first-class concern:

- **WCAG AA Compliance**: All text meets 4.5:1 contrast ratio
- **Keyboard Navigation**: All interactions accessible via keyboard
- **Screen Reader Support**: Proper ARIA labels and semantic HTML
- **Focus Management**: Visible focus indicators and focus trapping in modals
- **Reduced Motion**: Respects `prefers-reduced-motion`

## 🧪 Testing

```bash
# Run unit tests
npm test

# Run e2e tests
npm run test:e2e

# Coverage report
npm run test:coverage
```

## 📦 Building

```bash
# Development build
npm run build

# Production build (optimized)
npm run tauri:build
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines.

### Development Guidelines

1. **Code Style**: Follow existing patterns
2. **Type Safety**: Use TypeScript strictly
3. **Accessibility**: Ensure WCAG AA compliance
4. **Testing**: Write tests for new features
5. **Documentation**: Update docs for changes

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Design philosophy inspired by Jony Ive's minimalist approach
- Built with amazing open-source tools:
  - [React](https://react.dev/)
  - [TypeScript](https://www.typescriptlang.org/)
  - [Tailwind CSS](https://tailwindcss.com/)
  - [Tauri](https://tauri.app/)
  - [Monaco Editor](https://microsoft.github.io/monaco-editor/)
  - [D3.js](https://d3js.org/)

## 📚 Documentation

- [Design System](./DESIGN_SYSTEM.md) - Complete design specifications
- [Architecture](./ARCHITECTURE.md) - Technical architecture and patterns
- [API Documentation](./docs/api.md) - Component APIs (coming soon)

## 🗺️ Roadmap

### v1.0 (Current)
- [x] Command Palette with AI suggestions
- [x] File Explorer with tree view
- [x] Status Bar with test results
- [x] Voice-enabled input
- [x] Empty states
- [x] Comprehensive design system
- [x] TypeScript interfaces
- [x] Accessibility features

### v1.1 (Upcoming)
- [ ] Monaco editor integration
- [ ] Commit graph visualization
- [ ] Real-time test dashboard
- [ ] Advanced AI features
- [ ] Plugin system

### v2.0 (Future)
- [ ] Real-time collaboration
- [ ] Advanced Git operations
- [ ] Customizable themes
- [ ] Extension marketplace

## 💬 Support

- GitHub Issues: [Report bugs or request features]
- Discord: [Join our community]
- Documentation: [Read the docs]

---

**Built with ❤️ by the Solo Git Team**

*"Design is not just what it looks like and feels like. Design is how it works." - Steve Jobs*
