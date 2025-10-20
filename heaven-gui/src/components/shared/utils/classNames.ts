
/**
 * Utility for conditionally joining classNames
 */

export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}

export function clsx(...classes: (string | undefined | null | false | Record<string, boolean>)[]): string {
  return classes
    .map(c => {
      if (typeof c === 'string') return c
      if (typeof c === 'object' && c !== null) {
        return Object.entries(c)
          .filter(([_, value]) => value)
          .map(([key]) => key)
          .join(' ')
      }
      return ''
    })
    .filter(Boolean)
    .join(' ')
}
