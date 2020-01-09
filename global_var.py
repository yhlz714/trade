data={}
def put(key, something):
    global data
    data[key] = something

def get(key):
    return data[key]