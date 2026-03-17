"use client"

import * as React from "react"
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"
import { DayPicker, getDefaultClassNames } from "react-day-picker"

import { buttonVariants } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

function CalendarDropdown({
  className,
  options = [],
  value,
  disabled,
  onChange,
  ...props
}) {
  const handleValueChange = (nextValue) => {
    onChange?.({
      target: { value: nextValue },
      currentTarget: { value: nextValue },
    })
  }

  return (
    <Select
      disabled={disabled}
      value={typeof value === "number" ? String(value) : value}
      onValueChange={handleValueChange}
    >
      <SelectTrigger
        aria-label={props["aria-label"]}
        className={cn("h-8 min-w-[5.5rem] gap-1 px-2 text-sm shadow-none", className)}
        style={props.style}
      >
        <SelectValue />
      </SelectTrigger>
      <SelectContent position="popper" className="max-h-72">
        <SelectGroup>
          {options.map((option) => (
            <SelectItem key={option.value} value={String(option.value)} disabled={option.disabled}>
              {option.label}
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  )
}

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  captionLayout = "label",
  ...props
}) {
  const defaultClassNames = getDefaultClassNames()

  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("rounded-lg border bg-background p-3", className)}
      captionLayout={captionLayout}
      classNames={{
        root: cn("w-fit", defaultClassNames.root),
        months: cn("relative flex flex-col gap-4", defaultClassNames.months),
        month: cn("flex flex-col gap-4", defaultClassNames.month),
        month_caption: cn("relative flex h-8 items-center justify-center px-8", defaultClassNames.month_caption),
        caption_label: cn("text-sm font-medium", defaultClassNames.caption_label),
        dropdowns: cn("flex h-8 items-center justify-center gap-2", defaultClassNames.dropdowns),
        dropdown_root: cn("relative rounded-md border bg-background", defaultClassNames.dropdown_root),
        dropdown: cn("absolute inset-0 opacity-0", defaultClassNames.dropdown),
        nav: cn("absolute inset-x-0 top-0 flex w-full items-center justify-between", defaultClassNames.nav),
        button_previous: cn(buttonVariants({ variant: "ghost", size: "icon-sm" }), defaultClassNames.button_previous),
        button_next: cn(buttonVariants({ variant: "ghost", size: "icon-sm" }), defaultClassNames.button_next),
        month_grid: cn("w-full border-collapse", defaultClassNames.month_grid),
        weekdays: cn("flex", defaultClassNames.weekdays),
        weekday: cn("flex-1 text-xs font-normal text-muted-foreground", defaultClassNames.weekday),
        week: cn("mt-2 flex w-full", defaultClassNames.week),
        day: cn("relative h-8 w-8 p-0 text-center text-sm", defaultClassNames.day),
        day_button: cn(
          buttonVariants({ variant: "ghost", size: "icon-sm" }),
          "size-8 rounded-md p-0 font-normal aria-selected:bg-primary aria-selected:text-primary-foreground",
          defaultClassNames.day_button,
        ),
        selected: cn("bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground", defaultClassNames.selected),
        today: cn("bg-muted text-foreground", defaultClassNames.today),
        outside: cn("text-muted-foreground opacity-50 aria-selected:bg-muted aria-selected:text-muted-foreground", defaultClassNames.outside),
        disabled: cn("text-muted-foreground opacity-50", defaultClassNames.disabled),
        hidden: cn("invisible", defaultClassNames.hidden),
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation, className: chevronClassName, ...componentProps }) =>
          orientation === "left" ? (
            <ChevronLeftIcon className={cn("size-4", chevronClassName)} {...componentProps} />
          ) : (
            <ChevronRightIcon className={cn("size-4", chevronClassName)} {...componentProps} />
          ),
        Dropdown: CalendarDropdown,
      }}
      {...props}
    />
  )
}

export { Calendar }
