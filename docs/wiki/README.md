
# Solo Git Wiki

This directory contains the complete documentation wiki for Solo Git.

## Structure

```
docs/wiki/
├── Home.md                    # Wiki home page with timeline
├── README.md                  # This file
│
├── timeline/                  # Chronological documentation
│   ├── 2025-10-16-game-plan.md
│   ├── 2025-10-16-vision.md
│   └── 2025-10-16-concept.md
│
├── phases/                    # Phase-specific documentation
│   ├── phase-0-overview.md
│   ├── phase-0-completion.md
│   ├── phase-0-verification.md
│   ├── phase-1-overview.md
│   ├── phase-2-overview.md
│   ├── phase-3-overview.md
│   └── phase-4-overview.md
│
├── architecture/              # Technical architecture docs
│   ├── core-components.md
│   ├── git-engine.md
│   ├── test-orchestrator.md
│   └── model-routing.md
│
└── guides/                    # User guides
    ├── setup-guide.md
    ├── quick-start.md
    ├── cli-reference.md
    └── config-reference.md
```

## Navigation

Start at **[Home.md](./Home.md)** for the main entry point.

### Quick Links

#### Getting Started
- [Setup Guide](./guides/setup-guide.md) - Installation and configuration
- [Quick Start](./guides/quick-start.md) - Get up and running in 5 minutes

#### Reference
- [CLI Reference](./guides/cli-reference.md) - Complete command documentation
- [Configuration Reference](./guides/config-reference.md) - Config file options

#### Architecture
- [Core Components](./architecture/core-components.md) - System overview
- [Git Engine](./architecture/git-engine.md) - Git operations design
- [Test Orchestrator](./architecture/test-orchestrator.md) - Test execution

#### Project History
- [Vision Document](./timeline/2025-10-16-vision.md) - Core philosophy
- [Game Plan](./timeline/2025-10-16-game-plan.md) - Complete roadmap
- [Phase 0 Completion](./phases/phase-0-completion.md) - Foundation complete

## Contributing to Wiki

### Adding New Documentation

1. **Choose the Right Location**:
   - `timeline/` - Dated project milestones
   - `phases/` - Phase-specific docs
   - `architecture/` - Technical design docs
   - `guides/` - User-facing tutorials

2. **File Naming Convention**:
   - Timeline: `YYYY-MM-DD-title.md`
   - Phases: `phase-N-description.md`
   - Architecture: `component-name.md`
   - Guides: `topic-guide.md`

3. **Update Home.md**:
   - Add entry to chronological timeline
   - Update appropriate category section
   - Link to new document

4. **Cross-Reference**:
   - Link to related documents
   - Add "Related Documents" section at bottom

### Markdown Style Guide

- Use ATX headers (`#`, `##`, `###`)
- Include table of contents for long documents
- Use fenced code blocks with language hints
- Add last updated date at bottom

### Example Template

```markdown
# Document Title

**Date**: October 16, 2025  
**Status**: ✅ Complete / 🟡 In Progress / ⏳ Planned

## Overview

Brief description...

## Content

Main content here...

## Related Documents

- [Other Doc](./path/to/doc.md)
- [Another Doc](./path/to/another.md)

---

*Last Updated: October 16, 2025*
```

## Status Indicators

- ✅ Complete
- 🟡 In Progress
- ⏳ Planned
- 🔴 Blocked

## Viewing the Wiki

### Locally
```bash
# Browse with your favorite Markdown viewer
open docs/wiki/Home.md
```

### GitHub
The wiki will be available at:
`https://github.com/yourusername/solo-git/wiki`

### Rendered
For best experience, use:
- GitHub Wiki interface
- GitBook integration (future)
- MkDocs site (future)

---

*Last Updated: October 16, 2025*
