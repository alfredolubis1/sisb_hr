import datetime

def date_range(start, end, step):
    steps = datetime.timedelta(days=step)
    # starts = datetime.date(start)
    # ends = datetime.date(end)
    d1=start.split('-')
    d2=end.split('-')
    d1[2]=d1[2].split(' ')
    d2[2]=d2[2].split(' ')
    a=datetime.date(int(d1[0]),int(d1[1]),int(d1[2][0]))
    b=datetime.date(int(d2[0]),int(d2[1]),int(d2[2][0]))
    while a <= b:
        yield a
        a += steps
