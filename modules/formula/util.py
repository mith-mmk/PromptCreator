def debug_print(*args, mode=None, debug=False):
    if not debug:
        return
    if mode == 'value':
        text = ''
        for arg in args:
            if type(arg) == dict:
                text += f'{arg["value"]} '
            elif type(arg) == list:
                for i in arg:
                    if type(i) == dict:
                        text += f'{i["value"]} '
                    else:
                        text += f'{i} '
            else:
                text += f'{arg} '
        print(text)
    else:
        print(*args)
