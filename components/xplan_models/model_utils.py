def get_old_sub_model(model, old_model):
    if old_model:
        for old_sub_model in  old_model['models']:
            if old_sub_model.__class__.__name__ == model.__class__.__name__:
                return old_sub_model
    return None

def keyin(km, ks):
    for kq in ks:
        if keyeq(km, kq):
            return True
    return False

def keyeq(k1, k2):
    def valueseq(a1, a2):
        for k,v in a1.items():
            if a2[k] != v:
                return False
        return True
    return valueseq(k1, k2) and valueseq(k2, k1)
