import { useState, useEffect, useRef } from 'react'

/**
 * IntersectionObserver-based hook that tracks which section is currently
 * nearest the top of the viewport. Used to highlight the active TOC item.
 */
export function useActiveSection(sectionIds: string[]): string | null {
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null)
  const observerRef = useRef<IntersectionObserver | null>(null)

  useEffect(() => {
    if (sectionIds.length === 0) {
      setActiveSectionId(null)
      return
    }

    observerRef.current?.disconnect()

    const visibleEntries = new Map<string, IntersectionObserverEntry>()

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          const id = entry.target.id.replace('section-', '')
          if (entry.isIntersecting) {
            visibleEntries.set(id, entry)
          } else {
            visibleEntries.delete(id)
          }
        })

        if (visibleEntries.size > 0) {
          let topmost: string | null = null
          let topValue = Infinity
          visibleEntries.forEach((entry, id) => {
            const top = entry.boundingClientRect.top
            if (top < topValue) {
              topValue = top
              topmost = id
            }
          })
          setActiveSectionId(topmost)
        }
      },
      {
        rootMargin: '-80px 0px -60% 0px',
        threshold: [0, 0.1]
      }
    )

    sectionIds.forEach(id => {
      const element = document.getElementById(`section-${id}`)
      if (element) {
        observerRef.current!.observe(element)
      }
    })

    return () => {
      observerRef.current?.disconnect()
    }
  }, [sectionIds.join(',')])

  return activeSectionId
}
