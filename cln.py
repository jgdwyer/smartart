from bs4 import BeautifulSoup
import re

def convert_year(years, debug=False):
    for i, yr in years.iteritems():
        do_yr = 0
        if yr is None:
            continue
        if debug:
            print(yr)
        yr = q_html(yr)
        yr = q_all(yr)
        yr = dedashslash(yr)
        if is_int(yr):
            years.set_value(i, int(yr))
        else:
            years.set_value(i, None)
    return years


def q_space(yr):
    if yr[0] == ' ':
        yr = yr[1:]
    if yr[-1] ==  ' ':
        yr = yr[:-1]
    return yr

def q_circa_about(yr):
    if yr[:6] == 'circa ' or yr[:6] == 'about ' or yr[:6] == 'Circa ':
        yr = yr[6:]
    return yr

def q_around(yr):
    if yr[:7] == 'around ' or yr[:7] == 'Around ':
        yr = yr[7:]
    return yr

def q_cdot(yr):
    if yr[:2] == 'c.':
        yr = yr[2:]
    return yr

def q_c(yr):
    if yr[0] == 'c' and is_int(yr[1]):
        yr = yr[1:]
    return yr

def q_cadot(yr):
    if yr[0:4] == 'ca. ' or yr[0:4] == 'Ca. ':
        yr = yr[4:]
    return yr

def q_parens(yr):
    if yr[0] == '(' and yr[-1] == ')':
        yr = yr[1:-1]
    return yr

def q_CdotEdot(yr):
    if yr[-4:] == 'C.E.':
        yr = yr[:-4]
    return yr

def q_last4(yr):
    if yr[-6:-4] == ', ' and is_int(yr[-4:]):
        yr = yr[-4:]
    return yr

def q_all(yr):
    yr = q_space(yr)
    yr = q_last4(yr)
    yr = q_parens(yr)
    yr = q_circa_about(yr)
    yr = q_cdot(yr)
    yr = q_c(yr)
    yr = q_cadot(yr)
    yr = q_CdotEdot(yr)
    return yr

def q_html(yr):
    """Use beautiful soup on html tags. Many tags have this form"""
    if yr[:5] == '<span':
        soup = BeautifulSoup(yr, 'lxml')
        if soup.time is not None:
            yr = soup.time.text
    return yr

def is_int(x):
    if x is None:
        return False
    try:
        int(x)
        return True
    except ValueError:
        return False

def dedashslash(yrstr):
    """assumes data is like 1519-1521 or 1519-21 and finds average year"""
    if '-' not in yrstr and '/' not in yrstr:
        return yrstr
    if not is_int(yrstr[0]):
        return yrstr
    # Split string into list if there is a slash or hyphen
    yrlist = re.split('/|-', yrstr)
    yrlist = [q_all(yritem) for yritem in yrlist]
    if len(yrlist) != 2:
        return None
    if (not is_int(yrlist[0])) or (not is_int(yrlist[1])):
        return None
    if int(yrlist[0]) > int(yrlist[1]):
        # `1519-21` or 319-21
        yrlist[1] = yrlist[0][:-2] + yrlist[1]
    # Take average of range
    yr = (int(yrlist[0]) + int(yrlist[1])) / 2
    yr = int(round(yr))
    return yr