import { format, isValid, parseISO } from 'date-fns'
import { CalendarIcon, Clock3Icon, XIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import {
  Popover,
  PopoverContent,
  PopoverHeader,
  PopoverTitle,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

const parseDateTimeValue = (value) => {
  if (!value) {
    return null
  }

  const normalizedValue = value.length === 16 ? `${value}:00` : value
  const parsedValue = parseISO(normalizedValue)

  return isValid(parsedValue) ? parsedValue : null
}

const formatDateTimeValue = (value) => {
  const parsedValue = parseDateTimeValue(value)
  return parsedValue ? format(parsedValue, 'yyyy/MM/dd HH:mm') : ''
}

const toLocalDateTimeValue = (date) => format(date, "yyyy-MM-dd'T'HH:mm")
const hourOptions = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, '0'))
const minuteOptions = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, '0'))

const buildNextDateWithTime = (date, sourceDate) => {
  const nextDate = new Date(date)
  nextDate.setHours(sourceDate.getHours(), sourceDate.getMinutes(), 0, 0)
  return nextDate
}

const buildNextDateFromTime = (timeValue, sourceDate) => {
  if (!timeValue) {
    return sourceDate
  }

  const [hours = '0', minutes = '0'] = timeValue.split(':')
  const nextDate = new Date(sourceDate)
  nextDate.setHours(Number(hours), Number(minutes), 0, 0)
  return nextDate
}

const DateTimePicker = ({
  value,
  onChange,
  placeholder = '选择日期时间',
  className,
}) => {
  const selectedDate = parseDateTimeValue(value)
  const hourValue = selectedDate ? format(selectedDate, 'HH') : '00'
  const minuteValue = selectedDate ? format(selectedDate, 'mm') : '00'

  const handleSelectDate = (nextDate) => {
    if (!nextDate) {
      return
    }

    const baseDate = selectedDate || new Date()
    const nextValue = buildNextDateWithTime(nextDate, baseDate)
    onChange?.(toLocalDateTimeValue(nextValue))
  }

  const handleTimeChange = (nextTimeValue) => {
    const baseDate = selectedDate || new Date()
    const nextValue = buildNextDateFromTime(nextTimeValue, baseDate)
    onChange?.(toLocalDateTimeValue(nextValue))
  }

  const handleHourChange = (nextHour) => {
    handleTimeChange(`${nextHour}:${minuteValue}`)
  }

  const handleMinuteChange = (nextMinute) => {
    handleTimeChange(`${hourValue}:${nextMinute}`)
  }

  const handleClear = () => {
    onChange?.('')
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className={cn(
            'w-full justify-between text-left font-normal',
            !value && 'text-muted-foreground',
            className,
          )}
        >
          <span className="truncate">{value ? formatDateTimeValue(value) : placeholder}</span>
          <CalendarIcon data-icon="inline-end" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-auto p-0">
        <PopoverHeader className="border-b px-3 py-3">
          <PopoverTitle>选择日期时间</PopoverTitle>
        </PopoverHeader>
        <div className="flex flex-col gap-3 p-3">
          <Calendar
            mode="single"
            selected={selectedDate || undefined}
            onSelect={handleSelectDate}
            defaultMonth={selectedDate || new Date()}
            captionLayout="dropdown"
            startMonth={new Date(2000, 0)}
            endMonth={new Date(2035, 11)}
          />
          <div className="flex items-center gap-2">
            <div className="flex h-8 items-center rounded-md border bg-muted px-2 text-muted-foreground">
              <Clock3Icon className="size-4" />
            </div>
            <Select value={hourValue} onValueChange={handleHourChange}>
              <SelectTrigger className="w-[5.5rem]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent position="popper" className="max-h-56">
                <SelectGroup>
                  {hourOptions.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option} 时
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <Select value={minuteValue} onValueChange={handleMinuteChange}>
              <SelectTrigger className="w-[5.5rem]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent position="popper" className="max-h-56">
                <SelectGroup>
                  {minuteOptions.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option} 分
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <Button type="button" variant="ghost" size="icon-sm" onClick={handleClear}>
              <XIcon />
              <span className="sr-only">清空时间</span>
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

export default DateTimePicker
