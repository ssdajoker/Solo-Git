# Heaven UI Design System

## Overview
Heaven UI is a minimalist, keyboard-first interface for Solo Git, inspired by modern development tools with a focus on clarity, efficiency, and aesthetic beauty.

## Design Philosophy
> "Simplicity is the ultimate sophistication." - Leonardo da Vinci

- **Minimalism**: Clean, uncluttered interface with purposeful use of space
- **Dark Theme**: Deep space aesthetic that reduces eye strain during long coding sessions
- **Keyboard-First**: Every action accessible via keyboard shortcuts
- **Voice-Enabled**: Natural language input for AI-assisted workflows
- **Responsive**: Adapts seamlessly to different screen sizes and contexts
- **Accessible**: WCAG AA compliant with comprehensive keyboard and screen reader support

## Color Palette

### Background Colors
```css
--heaven-bg-primary: #0A0E1A      /* Deep space black */
--heaven-bg-secondary: #0D1117    /* Slightly lighter for panels */
--heaven-bg-tertiary: #1A1F2E     /* Elevated surfaces, modals */
--heaven-bg-hover: #252A3A        /* Interactive element hover state */
--heaven-bg-active: #2D3348       /* Active/pressed state */
```

### Accent Colors
```css
--heaven-blue-primary: #3B82F6    /* Primary actions, links */
--heaven-blue-hover: #2563EB      /* Hover state for blue elements */
--heaven-green: #22C55E           /* Success states, passing tests */
--heaven-orange: #F97316          /* Warnings, in-progress states */
--heaven-red: #EF4444             /* Errors, failing tests */
--heaven-cyan: #06B6D4            /* Information, neutral highlights */
--heaven-purple: #A855F7          /* AI suggestions, special features */
--heaven-pink: #EC4899            /* Accent highlights */
```

### Text Colors
```css
--heaven-text-primary: #FFFFFF    /* Main content, headings */
--heaven-text-secondary: #9CA3AF  /* Supporting text, labels */
--heaven-text-tertiary: #6B7280   /* Muted text, metadata */
--heaven-text-disabled: #4B5563   /* Disabled states */
```

### Syntax Highlighting Colors
```css
--syntax-keyword: #C792EA         /* Keywords (const, let, function) */
--syntax-function: #82AAFF        /* Function names */
--syntax-string: #C3E88D          /* Strings */
--syntax-number: #F78C6C          /* Numbers */
--syntax-comment: #546E7A         /* Comments */
--syntax-variable: #EEFFFF        /* Variables */
--syntax-tag: #F07178             /* HTML/JSX tags */
--syntax-attribute: #C792EA       /* Attributes */
```

## Typography

### Font Families
```css
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
--font-mono: "Fira Code", "JetBrains Mono", Monaco, Consolas, "Courier New", monospace;
```

### Font Sizes
| Name | Size | Usage |
|------|------|-------|
| xs | 0.75rem (12px) | Small labels, metadata, status bar |
| sm | 0.875rem (14px) | Body text, secondary content |
| base | 1rem (16px) | Primary body text, buttons |
| lg | 1.125rem (18px) | Subheadings |
| xl | 1.25rem (20px) | Section headings |
| 2xl | 1.5rem (24px) | Page titles |
| 3xl | 1.875rem (30px) | Hero text, branding |

### Font Weights
- **Normal**: 400 (body text)
- **Medium**: 500 (emphasized text)
- **Semibold**: 600 (subheadings)
- **Bold**: 700 (headings, important elements)

### Line Heights
- **Tight**: 1.25 (headings)
- **Normal**: 1.5 (body text)
- **Relaxed**: 1.6 (code editor)
- **Loose**: 1.75 (reading content)

## Spacing System
Based on 4px grid for consistent rhythm:

| Name | Value | Usage |
|------|-------|-------|
| 0 | 0 | Reset |
| 1 | 4px | Tight spacing |
| 2 | 8px | Small gaps |
| 3 | 12px | Compact padding |
| 4 | 16px | Default spacing |
| 5 | 20px | Comfortable padding |
| 6 | 24px | Section spacing |
| 8 | 32px | Large spacing |
| 10 | 40px | Extra large spacing |
| 12 | 48px | Section separation |
| 16 | 64px | Major layout spacing |

## Component Specifications

### Header
- **Height**: 60px
- **Background**: `heaven-bg-secondary`
- **Border**: 1px solid `rgba(255, 255, 255, 0.05)` bottom
- **Branding**: "HEAVEN" - 24px, semibold
- **Subtitle**: "Zen mode · Solo Git" - 14px, secondary color

### Command Palette
- **Position**: Fixed, center overlay
- **Width**: 600px max (90% on mobile)
- **Background**: `heaven-bg-tertiary` with backdrop-blur(12px)
- **Border Radius**: 12px
- **Shadow**: 0 20px 25px rgba(0, 0, 0, 0.5)
- **Input Height**: 48px
- **Item Height**: 40px
- **Sections**: 
  - AI Suggestions (purple icon)
  - Commands (grouped by category)

### File Explorer
- **Width**: 240px (collapsed: 60px)
- **Background**: `heaven-bg-secondary`
- **Item Height**: 32px
- **Indent**: 16px per nesting level
- **Icons**: 16px, color-coded by file type
  - JS/TS: Yellow (#F0DB4F)
  - HTML: Orange (#E34C26)
  - CSS: Blue (#264DE4)
  - JSON: Green (#5FB04C)
  - MD: Blue (#0969DA)

### Code Editor
- **Background**: `heaven-bg-primary`
- **Font**: Monospace, 14px
- **Line Height**: 1.6
- **Gutter Width**: 48px
- **Tab Size**: 2 spaces
- **Syntax Theme**: Material Ocean (custom)
- **Features**: Line numbers, bracket matching, auto-indent

### Commit Timeline (Right Sidebar)
- **Width**: 280px
- **Background**: `heaven-bg-secondary`
- **Node Size**: 12px circle
- **Line Width**: 2px
- **Line Color**: `rgba(255, 255, 255, 0.2)`
- **Commit Spacing**: 48px vertical
- **Status Colors**:
  - Green: Merged/successful
  - Orange: In progress
  - Red: Failed
  - Purple: AI-assisted

### Status Bar
- **Height**: 32px
- **Background**: `heaven-bg-tertiary`
- **Font Size**: 12px
- **Layout**: 3 sections (left, center, right)
- **Sections**:
  - Left: Current status, active file
  - Center: Test results with pass/fail counts
  - Right: Build info, operations count

### Voice Input
- **Height**: 48px
- **Border Radius**: 24px (pill shape)
- **Background**: `heaven-bg-tertiary`
- **Padding**: 12px 20px
- **Voice Button**: 32px circle, cyan color
- **Placeholder**: "Type or hold to speak"

### Buttons
```
Primary Button:
- Background: heaven-blue-primary
- Height: 40px
- Padding: 8px 16px
- Border Radius: 6px
- Font: medium, 14px

Secondary Button:
- Background: transparent
- Border: 1px solid heaven-text-tertiary
- Height: 40px
- Padding: 8px 16px
- Border Radius: 6px

Icon Button:
- Size: 32px square
- Background: transparent (hover: heaven-bg-hover)
- Border Radius: 6px
```

## Layout Structure

### Desktop Layout (> 1024px)
```
┌──────────────────────────────────────────────────────────────┐
│ Header (60px) - HEAVEN | Zen mode · Solo Git         ⌨️ ⚙️ │
├─────────────┬──────────────────────────────┬─────────────────┤
│             │                              │                 │
│  File       │      Code Editor             │   Commit        │
│  Explorer   │      (flex-1)                │   Timeline      │
│  (240px)    │                              │   (280px)       │
│             │                              │                 │
│  - README   │  [Code with syntax           │   ● feat: xyz   │
│  - src/     │   highlighting]              │   │             │
│    main.ts  │                              │   ● fix: abc    │
│    auth.ts  │                              │   │             │
│  - tests/   │                              │   ● Initial     │
│             ├──────────────────────────────┤                 │
│             │   Test Dashboard             │                 │
│             │   ✓ 42 tests passed          │                 │
│             │   (200px height)             │                 │
├─────────────┴──────────────────────────────┴─────────────────┤
│ Status: Ready | ✓ unit/auth.test.ts 42 | build #384 SUCCESS │
└──────────────────────────────────────────────────────────────┘
```

### Tablet Layout (768px - 1024px)
- File Explorer: Collapsible overlay
- Code Editor: Full width
- Commit Timeline: Collapsible overlay

### Mobile Layout (< 768px)
- Single column
- All sidebars as modal overlays
- Command Palette full width

## Interactions & Animations

### Hover States
```css
Opacity: 0.8 for icons
Background: Lighter shade for surfaces
Transition: 150ms ease-in-out
```

### Focus States
```css
Outline: 2px solid heaven-blue-primary
Offset: 2px
Border Radius: Matches element
Shadow: 0 0 0 3px rgba(59, 130, 246, 0.1)
```

### Active States
```css
Scale: 0.98 for buttons
Background: Darker shade
Transform: translateY(1px)
```

### Transition Timings
- **Fast**: 100ms - Immediate feedback (hover)
- **Default**: 150ms - Standard interactions
- **Slow**: 300ms - Layout changes, modals
- **Smooth**: 500ms - Page transitions

### Loading States
```css
Skeleton: Subtle pulse animation
Spinner: Circular, 2px stroke
Progress: Linear bar with gradient
```

## Accessibility

### ARIA Labels
- All interactive elements have descriptive `aria-label`
- Icon buttons include text alternatives
- Form inputs have associated `<label>` elements
- Dynamic content uses `aria-live` regions

### Keyboard Navigation
| Key | Action |
|-----|--------|
| Tab | Navigate forward |
| Shift+Tab | Navigate backward |
| Enter | Activate/Submit |
| Escape | Close modal/Cancel |
| ↑↓ | Navigate lists |
| ←→ | Navigate timeline |
| Cmd/Ctrl+P | Command Palette |
| Cmd/Ctrl+B | Toggle File Explorer |
| Cmd/Ctrl+/ | Toggle AI Assistant |
| ? | Show keyboard shortcuts |

### Focus Management
- Visible focus indicators (never `outline: none`)
- Focus trap in modals
- Focus restoration on modal close
- Skip links for main content

### Color Contrast
- All text meets WCAG AA: 4.5:1 (normal), 3:1 (large)
- Interactive elements: 3:1 contrast
- Status indicators use color + icon/text

### Screen Reader Support
- Semantic HTML (`<nav>`, `<main>`, `<aside>`)
- Landmark regions
- Button vs link distinction
- Form validation messages

## Animation Principles

### Micro-interactions
- **Button Press**: Scale 0.98, shadow reduce
- **Hover**: Subtle color/opacity change
- **Loading**: Gentle pulse or rotate

### Modal Animations
```css
Enter: opacity 0→1, scale 0.95→1 (200ms)
Exit: opacity 1→0, scale 1→0.95 (150ms)
Backdrop: opacity 0→0.5 (200ms)
```

### Page Transitions
- Fade: 200ms
- Slide: 300ms with easing
- Scale: 250ms for emphasis

### Performance
- Use CSS `transform` and `opacity`
- Avoid animating `width`, `height`, `top`, `left`
- Respect `prefers-reduced-motion`
- Use `will-change` sparingly

## Icons

### Style Guidelines
- **Type**: Outline style, consistent stroke
- **Size**: 16px (inline), 20px (buttons), 24px (featured)
- **Stroke Width**: 2px
- **Color**: Inherits from parent text color
- **Library**: Lucide React or Heroicons

### Icon Usage
```tsx
// Example
import { FileText, Folder, GitBranch } from 'lucide-react'

<FileText size={16} className="text-heaven-text-secondary" />
```

## Shadows

```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.3);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.4);
--shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.5);
--shadow-2xl: 0 25px 50px rgba(0, 0, 0, 0.6);
```

## Border Radius

```css
--rounded-sm: 4px      /* Small elements */
--rounded: 6px         /* Default buttons, inputs */
--rounded-md: 8px      /* Cards, panels */
--rounded-lg: 12px     /* Modals, large surfaces */
--rounded-xl: 16px     /* Hero elements */
--rounded-full: 9999px /* Pills, avatars */
```

## Z-Index Scale

```css
--z-base: 0
--z-dropdown: 10
--z-sticky: 20
--z-fixed: 30
--z-modal-backdrop: 40
--z-modal: 50
--z-popover: 60
--z-tooltip: 70
--z-notification: 80
```

## Component States

### Input States
| State | Border | Background | Text |
|-------|--------|------------|------|
| Default | `rgba(255,255,255,0.1)` | tertiary | primary |
| Focus | blue primary | tertiary | primary |
| Error | red | tertiary | primary |
| Success | green | tertiary | primary |
| Disabled | `rgba(255,255,255,0.05)` | secondary | disabled |

### Button States
| State | Opacity | Scale | Shadow |
|-------|---------|-------|--------|
| Default | 1.0 | 1.0 | sm |
| Hover | 0.9 | 1.0 | md |
| Active | 1.0 | 0.98 | none |
| Disabled | 0.5 | 1.0 | none |
| Loading | 0.7 | 1.0 | sm |

## Best Practices

### Do's ✓
- Use consistent spacing from the spacing system
- Maintain WCAG AA color contrast
- Provide keyboard shortcuts for common actions
- Use semantic HTML elements
- Include ARIA labels for assistive technologies
- Test with keyboard navigation
- Respect `prefers-reduced-motion`
- Keep animations subtle and purposeful
- Use loading states for async operations
- Provide clear error messages

### Don'ts ✗
- Don't use arbitrary spacing values
- Don't rely solely on color to convey information
- Don't create keyboard traps
- Don't use `<div>` for interactive elements
- Don't remove focus indicators
- Don't animate layout properties (width, height)
- Don't ignore accessibility guidelines
- Don't use tiny click targets (< 44x44px)
- Don't make animations too fast or slow
- Don't hide important information in tooltips

## Implementation Guidelines

### File Organization
```
src/
├── components/
│   ├── web/              # Platform-agnostic React components
│   │   ├── CommandPalette/
│   │   ├── FileExplorer/
│   │   ├── CodeEditor/
│   │   ├── CommitTimeline/
│   │   └── ...
│   ├── desktop/          # Tauri-specific components
│   │   ├── NativeMenuBar/
│   │   ├── FileSystemBridge/
│   │   └── ...
│   ├── shared/           # Common utilities
│   │   ├── types/
│   │   ├── hooks/
│   │   └── utils/
│   └── ui/               # Base UI components (Button, Input, etc.)
├── styles/
│   └── globals.css       # Tailwind + custom CSS variables
└── App.tsx               # Main application
```

### Component Naming
- Use PascalCase: `CommandPalette.tsx`
- Index files for complex components: `CommandPalette/index.tsx`
- Co-locate styles if needed: `CommandPalette/styles.css`
- Tests alongside: `CommandPalette/CommandPalette.test.tsx`

### Props Interface Pattern
```tsx
export interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  commands: Command[]
  className?: string
  'aria-label'?: string
}
```

### Tailwind Usage
```tsx
// Prefer Tailwind classes
<div className="bg-heaven-bg-tertiary rounded-lg p-4 shadow-lg">

// Avoid inline styles (except dynamic values)
<div style={{ width: `${progress}%` }}>
```

## Testing Checklist

### Visual Testing
- [ ] Renders correctly in all layout sizes
- [ ] Text is readable with proper contrast
- [ ] Icons are properly sized and aligned
- [ ] Spacing is consistent
- [ ] Animations are smooth

### Functional Testing
- [ ] All interactions work as expected
- [ ] Keyboard navigation works
- [ ] Focus management is correct
- [ ] Loading states display properly
- [ ] Error states are clear

### Accessibility Testing
- [ ] Screen reader announces correctly
- [ ] All interactive elements are keyboard accessible
- [ ] Focus indicators are visible
- [ ] Color contrast meets WCAG AA
- [ ] Form validation is clear

### Performance Testing
- [ ] Initial render is fast
- [ ] Animations don't cause jank
- [ ] Large lists are virtualized
- [ ] Images are optimized
- [ ] Bundle size is reasonable

---

**Version**: 1.0.0  
**Last Updated**: October 2025  
**Maintained by**: Solo Git Team  
**Design Philosophy**: "Simplicity is the ultimate sophistication"
