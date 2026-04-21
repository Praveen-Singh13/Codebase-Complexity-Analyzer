def alpha(values):
    total = 0
    for i in values:
        for j in values:
            for k in values:
                for m in values:
                    total += i + j + k + m
    return total


def beta(limit):
    result = []
    for i in range(limit):
        if i % 2 == 0:
            result.append(i)
    return result


class Demo:
    def method(self, n):
        count = 0
        while n > 0:
            for i in range(n):
                count += i
            n -= 1
        return count
