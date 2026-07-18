import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold transition-all",
  {
    variants: {
      variant: {
        default: "border-[var(--warm-orange)] bg-gradient-to-r from-[var(--warm-orange)]/20 to-[var(--warm-orange-light)]/20 text-[var(--warm-orange)]",
        secondary: "border-[var(--warm-orange-light)] bg-gradient-to-r from-[var(--warm-orange-light)]/20 to-[var(--warm-orange)]/20 text-[var(--warm-orange)]",
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
