def fully_free_seats(legs_free):
    result = legs_free[0]
    for leg in legs_free[1:]:
        result = result & leg
    return result

def seat_reach(seat, legs_free, start):
    i = start 
    while i < len(legs_free) and seat in legs_free[i]:
        i += 1
    return i

def find_plan(legs_free):
    n = len(legs_free)
    position = 0
    plan = []
    while position < n:
        best_seat = None
        best_reach = position
        for seat in legs_free[position]:
            reach = seat_reach(seat, legs_free, position)
            if reach > best_reach:
                best_seat = seat
                best_reach = reach
        if best_seat is None:
            return None
        plan.append((best_seat, position, best_reach))
        position = best_reach
    return plan