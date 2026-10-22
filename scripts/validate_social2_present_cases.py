"""Authored adversarial option presenter inputs, no client data."""

import itertools


def cases():
    for option, selector, tag in itertools.product(
        [2, 21, 28, 29, 30, 31, 25, 258, 284], [0, 1, 2, 3, 255, 257], [3, 4, 259]
    ):
        yield "earring_numeric", dict(option=option, selector=selector, tag=tag)
        yield "earring_text", dict(
            option=option, selector=selector, tag=tag, enhancement_level=5
        )
    for option, enhancement, other in itertools.product(
        [28, 29, 30, 31], [-3, 0, 1, 15, 2147483647], [None, 0, 7 << 3, 0xFFFFFFFF]
    ):
        yield "earring_text", dict(
            option=option,
            selector=1,
            tag=3,
            enhancement_level=enhancement,
            other_full_l=other,
        )
    for option in [2, 29]:
        yield "earring_text", dict(
            option=option,
            selector=1,
            tag=3,
            enhancement_level=5,
            other_full_l=56,
            self_only=True,
        )
    for code, rank, option, level in itertools.product(
        [6365, 6366], [1, 2, 3, 5], [1, 2, 15], [-1, 0, 3, 10, 11, 15]
    ):
        yield "errtel_text", dict(
            code=code, physical_rank=rank, option=option, level=level
        )
    patterns = [
        [255] * 5,
        [0x11, 255, 0x2F, 255, 0x42],
        [0x1F, 255, 0xB1, 255, 255],
        [0, 0, 0, 0, 0],
        [255, 0xA1, 255, 0x12, 0xF2],
    ]
    for slots, count, line in itertools.product(patterns, [0, 1, 3, 5, 6, 255], [0, 4]):
        yield "standalone_errtel", dict(slots=slots, socket_count=count, line=line)
    for typ, flag, required, level in itertools.product(
        [1, 2, 3, 4, 5], [0, 1], [0, 455, 65535], [-1, 0, 7, 15]
    ):
        yield "pentagram_rank", dict(
            type=typ, defense_flag=flag, required_level=required, level=level, status=0
        )
    for key, value in itertools.product(
        [(2, 5), (2, 6), (3, 5), (4, 5), (2, 999), (9, 5)],
        [-2147483648, -21, -20, -5, 0, 10, 11, 20, 21, 30, 40, 41, 2147483647],
    ):
        yield "advanced_threshold", dict(group=key[0], option=key[1], value=value)
        for cv in [0, 1, 256, 257]:
            yield "advanced_text", dict(
                group=key[0], option=key[1], value=value, convert=cv
            )
