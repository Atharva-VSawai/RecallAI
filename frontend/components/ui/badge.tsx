import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold transition-all",
  {
    variants: {
      variant: {
        default: "border-blue-400 bg-gradient-to-r from-blue-100 to-cyan-100 text-blue-700",
        secondary: "border-cyan-400 bg-gradient-to-r from-cyan-100 to-blue-100 text-cyan-700",
        success: "border-green-400 bg-gradient-to-r from-green-100 to-emerald-100 text-green-700",
        outline: "border-gray-300 text-gray-700",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
