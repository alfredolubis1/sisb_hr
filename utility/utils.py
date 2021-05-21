from datetime import datetime


def hour_float_to_time(time_float, is_24hr_format=True):
    """ Converts hour floats like 9.5 into 9:30 or 09:30 if is_24_hr_format is True """
    if type(time_float) is str:
        time_float = float(time_float)
    hour, minute = divmod(time_float * 60, 60)
    # print('hour n minute', hour, minute)
    hm_string = '{0:02.0f}:{1:02.0f}'.format(hour, minute)
    if is_24hr_format:
        return hm_string
    else:
        return datetime.strptime(hm_string, '%H:%M').strftime('%-I.%M %p')


def float_to_day_time(time_float):
    if type(time_float) is str:
        time_float = float(time_float)
    day = int(time_float)
    if time_float > 0:
        pass
        # print('time_float = ', time_float)
    day_left = (time_float % 1) * 24
    hour, minute = divmod(day_left * 60, 60)
    if minute >= 59.00:
        minute = 0
        hour += 1
    if hour >= 7.9:
        day += 1
        hour = 0
    hm_string = str(day) + ' - ' + '{0:02.0f}:{1:02.0f}'.format(hour, minute)
    return hm_string


def ordinal_num(number):
    return str(number) + ("th" if 4 <= number % 100 <= 20 else {1:"st",2:"nd",3:"rd"}.get(number % 10, "th"))