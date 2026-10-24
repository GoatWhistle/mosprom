LEWIS_FORM_FACTOR = (
    (12, 0.245), (13, 0.261), (14, 0.277), (15, 0.290), (16, 0.296), (17, 0.303), (18, 0.309), (19, 0.314),
    (20, 0.322), (21, 0.328), (22, 0.331), (24, 0.337), (26, 0.346), (28, 0.353), (30, 0.359), (34, 0.371),
    (38, 0.384), (43, 0.397), (50, 0.409), (60, 0.422), (75, 0.435), (100, 0.447), (150, 0.460), (300, 0.472),
    (400, 0.480),
)


def form_factor(teeth):
    table = LEWIS_FORM_FACTOR
    if teeth <= table[0][0]:
        return table[0][1]
    for (low, low_value), (high, high_value) in zip(table, table[1:]):
        if teeth <= high:
            return low_value + (high_value - low_value) * (teeth - low) / float(high - low)
    return table[-1][1]
