def save_result(old_func):
    def new_func(*args, **kwargs):
        result = old_func(*args, **kwargs)
        with open('result.txt', 'a', encoding='utf-8') as f:
            print(f'{result}', file = f)
    return new_func

@save_result

def calculate(a, b, operation='+'):
    if operation == '+':
        return a + b
    elif operation == '-':
        return a - b
    elif operation == '*':
        return a * b
    elif operation == '/':
        if b == 0:
            return "ОШИБКА: Деление на ноль."
        return a / b
    elif operation == '**':
        return a ** b
    else:
        print('Указанная операция не распознана.')
        return None

calculate(1, 2)

calculate(2, 2, "-")

calculate(3, 2, "**")
