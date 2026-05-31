import re

def parse_seats(svg):
    seats = []
    for m in re.finditer(r'aria-label="Miejsce (\d+)([^"]*)"', svg):
        number = m.group(1)  
        rest   = m.group(2) 
        free = "Niedostepne" not in rest
        seats.append({
            "number": number,
            "free": free,
        })
    return seats