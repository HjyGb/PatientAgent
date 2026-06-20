from simulateflow import flow


def cache() -> int:
    """Read the current case number from cache file."""
    with open('./make_task/case_cache.txt', 'r', encoding='utf-8') as cc:
        case_number = cc.read()
    return int(case_number)


row_number = cache()
col_number = 1
sheet_name = '病程记录_首次病程'

while row_number <= 1300:
    row_number += 1
    flow(sheet_name, row_number, col_number)
    with open('./make_task/case_cache.txt', 'w', encoding='utf-8') as cc:
        cc.write(str(row_number))
