import * as React from "react"

const DropdownMenuContext = React.createContext<{
  isOpen: boolean
  setIsOpen: (open: boolean) => void
}>({
  isOpen: false,
  setIsOpen: () => {}
})

const DropdownMenu = ({ children }: { children: React.ReactNode }) => {
  const [isOpen, setIsOpen] = React.useState(false)
  
  return (
    <DropdownMenuContext.Provider value={{ isOpen, setIsOpen }}>
      <div className="relative inline-block text-left">
        {children}
      </div>
    </DropdownMenuContext.Provider>
  )
}

const DropdownMenuTrigger = React.forwardRef<HTMLButtonElement, { children: React.ReactNode; asChild?: boolean } & React.ButtonHTMLAttributes<HTMLButtonElement>>(
  ({ children, asChild = false, onClick, ...props }, ref) => {
    const { isOpen, setIsOpen } = React.useContext(DropdownMenuContext)
    
    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation()
      setIsOpen(!isOpen)
      onClick?.(e)
    }
    
    if (asChild) {
      return React.cloneElement(
        children as React.ReactElement<React.ButtonHTMLAttributes<HTMLButtonElement> & React.RefAttributes<HTMLButtonElement>>,
        { onClick: handleClick, ref }
      )
    }
    
    return (
      <button ref={ref} onClick={handleClick} {...props}>
        {children}
      </button>
    )
  }
)

const DropdownMenuContent = ({ children, align = "end", className }: { 
  children: React.ReactNode
  align?: "start" | "end"
  className?: string
}) => {
  const { isOpen, setIsOpen } = React.useContext(DropdownMenuContext)
  
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      const dropdown = target.closest('.relative.inline-block.text-left')
      if (!dropdown) {
        setIsOpen(false)
      }
    }
    
    if (isOpen) {
      // Use setTimeout to ensure this runs after the current click event
      setTimeout(() => {
        document.addEventListener('click', handleClickOutside, true)
      }, 0)
      return () => document.removeEventListener('click', handleClickOutside, true)
    }
  }, [isOpen, setIsOpen])
  
  if (!isOpen) return null
  
  const alignmentClass = align === "start" ? "left-0" : "right-0"
  
  return (
    <div className={`absolute ${alignmentClass} z-10 mt-2 w-56 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none ${className || ""}`}>
      <div className="py-1">
        {children}
      </div>
    </div>
  )
}

const DropdownMenuItem = ({ children, onClick }: { children: React.ReactNode; onClick?: (e: React.MouseEvent) => void }) => {
  const { setIsOpen } = React.useContext(DropdownMenuContext)
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsOpen(false)
    onClick?.(e)
  }
  
  return (
    <button
      onClick={handleClick}
      className="flex items-center w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
    >
      {children}
    </button>
  )
}

export { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem }
