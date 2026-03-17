import * as React from "react"
import { Label as LabelPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

function Label({
  className,
  required = false,
  invalid = false,
  children,
  ...props
}) {
  return (
    <LabelPrimitive.Root
      data-slot="label"
      data-invalid={invalid}
      data-required={required}
      className={cn(
        "flex items-center gap-1.5 text-sm leading-none font-medium select-none group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:opacity-50 data-[invalid=true]:text-destructive",
        className
      )}
      {...props}>
      {children}
      {required ? (
        <>
          <span
            aria-hidden="true"
            className={cn(
              "font-semibold text-destructive",
              invalid && "opacity-100",
            )}
          >
            *
          </span>
          <span className="sr-only">必填</span>
        </>
      ) : null}
    </LabelPrimitive.Root>
  );
}

export { Label }
